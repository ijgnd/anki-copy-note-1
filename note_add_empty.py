# Copyright: Arthur Milchior arthur@milchior.fr
#            2017 Glutanimate
#            2019- ijgnd
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html

import collections
from pprint import pprint as pp
import re

from anki.utils import guid64
from aqt import mw
from aqt.qt import *
from aqt.studydeck import StudyDeck
from aqt.utils import askUser, tooltip

from .config import gc
from .note_processing import (
    createRelationTag,
    timestampID,
    getRelationsFromNote,
)


# I keep this misleading name so that the structure is similar to duplicate_notes
def make_new_notes(browser, keepNotetype, keepCreationTime):
    selected_note_ids = browser.selectedNotes()
    if len(selected_note_ids) > 1:
        tooltip("Aborting. You can only insert one blank note at a time based on one selected note")
        return
    mw.checkpoint("Insert Empty Note")
    # don't use progress.start/finish: these are dated and creating one note is quick
    # mw.progress.start()
    for nid in selected_note_ids:
        make_one_new_note(browser, nid, keepNotetype, keepCreationTime)
    # Reset collection and main window
    # mw.progress.finish()
    mw.col.reset()
    mw.reset()
    browser.onSearchActivated()
    tooltip("""Inserted empty note.""")


def make_one_new_note(browser, source_nid, keepNotetype, keepCreationTime):
    did = get_new_did(browser, source_nid)
    model = get_model(browser, source_nid, keepNotetype)
    new_nid = get_new_nid(source_nid, keepCreationTime)
    old_note = browser.col.get_note(source_nid)
    if new_nid:
        create_new_empty_note(model, did, new_nid, fields=None, tags=old_note.tags)


# copied over from ijgnd's Duplicate and reorder fork from 2022-01
def directly_set_note_id(col, old_nid, new_nid):
    note = col.get_note(old_nid)
    note.cards()
    note.id = 0
    note.guid = guid64()
    col.add_note(note, 0)
    col.db.execute(f"DELETE FROM cards WHERE nid = {note.id}")  # needed?
    col.db.execute(f"update notes set id={new_nid} WHERE id = {note.id}")
    col.db.execute(f"update cards set nid={new_nid} WHERE nid = {old_nid}")
    col.remove_notes([old_nid])

    note = col.get_note(new_nid)
    for card in note.cards():
        card.usn = col.usn()
        card.flush()


def create_new_empty_note(model, did=0, newnid=None, fields=None, tags=None):
    # source card is relevant to determine the new deck: If only one card for the note is 
    # selected use its deck, else ask user
    if did:
        source_deck = mw.col.decks.get(did)
        # Assign model to deck
        mw.col.decks.select(did)
        source_deck['mid'] = model['id']
        mw.col.decks.save(source_deck)
    # Assign deck to model
    mw.col.models.set_current(model)
    model['did'] = did
    mw.col.models.save(model)
    
    # Create new note
    new_note = mw.col.new_note(model)
    if fields:
        new_note.fields = fields
    else:
        # original solution: fill all fields to avoid notes without cards
        #    fields = ["."] * len(new_note.fields)
        # problem: That's a hassle for note types that generate e.g. up to 20 cards ...
        new_note.fields = [""] * len(new_note.fields)
        tofill = fields_to_fill_for_nonempty_front_template(new_note.mid)
        if not tofill:  # no note of the note type exists
            new_note.fields = ["."] * len(new_note.fields)
        else:
            for i in tofill:
                new_note.fields[i] = "."

    if tags:
        new_note.tags = tags
    if gc("relate copies"):  # and not getRelationsFromNote(new_note):  # ?
        new_note.addTag(createRelationTag())

    new_note.id = 0
    new_note.guid = guid64()
    mw.col.add_note(new_note, did)  # after this note.id is no longer 0.
    
    # https://addon-docs.ankiweb.net/#/getting-started?id=the-collection
    # mw.col.db.execute("update cards set ivl = ? where id = ?", newIvl, cardId)
    # Note that these changes won’t sync, as they would if you used the functions mentioned in the previous section.
    # mw.col.db.execute(f"update notes set id={newnid} WHERE id = {new_note.id}")
    # mw.col.db.execute(f"update cards set nid={newnid} WHERE nid = {new_note.id}")

    directly_set_note_id(mw.col, new_note.id, newnid)


# I could fill every field with "." to make sure at least one card is generated
# with e.g.       note.fields = ["."] * len(note._model["flds"])
# this is save (and used by the note organizer add-on). But this means that I might
# have to manually delete a lot. This takes a least some seconds
# So it's probably quicker to wait for about five seconds so that Anki finds out
# the minimal amount of fields to fill
# start to empty existing fields:
#   note.fields = [""] * len(note._model["flds"])
# I can't just fill all the fields named in the first template because of conditional
# replacement.
# I can't randomly try out all combinations ...
# I have never read the code for card generation so it should take some time
# to extract the relevant code
# Instead use ugly workaround:
#    - get existing notes that generate a card 1
#    - narrow down to notes with the fewest cards generated
#    - narrow down to a note with the fewest fields filled
#    - only fill these fields
def fields_to_fill_for_nonempty_front_template(mid):
    wco = mw.col.find_cards("mid:%s card:1" %mid)
    if not wco:  # no note of the note type exists
        return False
    totalcards = {}
    for cid in wco:
        card = mw.col.get_card(cid)
        totalcards.setdefault(card.nid, 0)
        totalcards[card.nid] += 1
    nid_filled_map = {}
    for nid, number_of_cards in totalcards.items():
        if number_of_cards == 1:
            othernote = mw.col.get_note(nid)
            nid_filled_map[nid] = 0
            for f in othernote.fields:
                if f:
                    nid_filled_map[nid] += 1
    lowestnid = min(nid_filled_map, key=nid_filled_map.get)
    othernote = mw.col.get_note(lowestnid)
    tofill = []
    for idx, cont in enumerate(othernote.fields):
        if cont:
            tofill.append(idx)
    return tofill



def adjusted_diff(higher, lower, towardslower):
    diff = higher - lower
    # limit diff, if you are on a 10 day vacation and late want to insert a note before
    # the first one created after the holiday this inserted note would be 5 days older.
    # That's confusing. so limit to 10 seconds. 
    diff = min(diff, 10000) 
    #diff = int(diff/2)  # downside: doesn't give many options for insertions: maybe I want to 
                         # add 20 notes around a long note/IR note.
    diff = int(diff/2)
    return diff


def timestampID_Middle(db, table, oldnid, before=False):
    """Return a non-conflicting timestamp for table. Don't use the next free one but so 
    that other notes may be inserted later.
    """
    # be careful not to create multiple objects without flushing them, or they
    # may share an ID.
    ids = db.list("select id from notes")
    ids.sort()
    idx = ids.index(oldnid)
    if idx == 0:
        return oldnid - 30
    if idx + 1 == len(ids):  # copying newest note id
        return oldnid + 30
    elif before:
        prior = ids[idx-1]
        if prior + 1 == oldnid:  # there's no middle. Auto search next free one.
            # I can't ask here because in non-ancient anki versions the askUser dialog is blocked
            # by the progress window
            # if askUser("No unused neighboring nid found. Use next free one?"):
            if True:
                return timestampID(db, table, oldnid, before)
            else:
                return None
        else:
            diff = adjusted_diff(oldnid, prior, False)
            new = oldnid - diff
            # pp(f"oldnid is: {oldnid}, prior is: {prior} and diff is {diff}, new is {new}")
            return new
    else:
        plusone = ids[idx+1]
        if plusone - 1 == oldnid:  # there's no middle. Auto search next free one.
            return timestampID(db, table, oldnid, before)
        else:
            diff = adjusted_diff(plusone, oldnid, True)
            diff = min(diff, 10000)
            new = oldnid + diff        
            # pp(f"oldnid is: {oldnid}, plusone is: {plusone} and diff is {diff}, new is {new}")
            return new


def get_new_did(browser, source_nid):
    note = browser.col.get_note(source_nid)
    cards = note.cards()
    used_decks = set([])
    for c in cards:
        used_decks.add(c.did)
    if len(used_decks) > 1:
        used_deck_names = []
        for did in used_decks:
            deck = mw.col.decks.get(did)
            used_deck_names.append(deck['name'])
        deck_name = selected_new_deck_name(browser, used_deck_names)
        source_did = mw.col.decks.by_name(deck_name)['id']
    else:
        source_did = list(used_decks)[0]
    return source_did


def get_model(browser, source_nid, keepNotetype):
    if keepNotetype:
        note = mw.col.get_note(source_nid)
        model = mw.col.models.get(note.mid)
    else:
        newname = selected_new_model_name(browser)
        model = mw.col.models.by_name(newname)
    return model


def get_new_nid(sourcenid, keepCreationTime):
    oldid = sourcenid if keepCreationTime else None
    if not oldid:
        newnid = timestampID(mw.col.db, "notes", oldid, before=False)
    else:
        if keepCreationTime == "before":
            before = True
        else:
            before = False
        newnid = timestampID_Middle(mw.col.db, "notes", oldid, before)
    return newnid


def selected_new_model_name(parent):
    current = mw.col.models.current()["name"]
    def nameFunc():
        # return sorted(mw.col.models.all_names())  # deprecated
        return sorted([nt.name for nt in mw.col.models.all_names_and_ids()])
    prevent_add_button = QPushButton("")  # type: ignore
    ret = StudyDeck(
        mw,
        names=nameFunc,
        accept="Choose",
        title="Choose Note Type",
        help="_notes",
        current=current,
        parent=parent,
        buttons=[prevent_add_button],
        cancel=False,
        geomKey="mySelectModel",
    )
    return ret.name


def selected_new_deck_name(parent, relevantdecks):
    def nameFunc():
        return sorted(relevantdecks)
    prevent_add_button = QPushButton("")  # type: ignore
    ret = StudyDeck(
        mw,
        names=nameFunc,
        accept="Choose",
        title="Choose Deck",
        help=None,
        current=None,
        parent=parent,
        buttons=[prevent_add_button],
        cancel=False,
        geomKey="mySelectModel",
    )
    return ret.name


# mod of clayout.py/CardLayout._fieldsOnTemplate 
def myFieldsOnTemplate(fmt):
    matches = re.findall("{{[^#/}]+?}}", fmt)
    charsAllowed = 30
    result = collections.OrderedDict()
    for m in matches:
        # strip off mustache
        m = re.sub(r"[{}]", "", m)
        # strip off modifiers
        m = m.split(":")[-1]
        # don't show 'FrontSide'
        if m == "FrontSide":
            continue

        if m not in result:
            result[m] = True
            charsAllowed -= len(m)
            if charsAllowed <= 0:
                break
    return result.keys()
