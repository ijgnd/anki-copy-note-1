# -*- coding: utf-8 -*-
# Copyright: Arthur Milchior arthur@milchior.fr
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
# Select any number of cards in the card browser and create exact copies of each card in the deck
# Feel free to contribute to this code on https://github.com/Arthur-Milchior/anki-copy-note
# Anki's add-on number: 1566928056

# This add-ons is heavily based on Kealan Hobelmann's addon 396494452


from typing import Optional

import anki.notes
from anki.utils import guid64, intTime

from aqt import mw
from aqt.qt import *
from aqt.utils import tooltip

from .config import getUserOption


def duplicate_notes(browser, keepCreationTime, keepIvlEtc, keepLog):
    selected_note_ids = browser.selectedNotes()
    mw.checkpoint("Copy Notes")
    mw.progress.start()
    for nid in selected_note_ids:
        duplicate_one_note(nid, keepCreationTime, keepIvlEtc, keepLog)
    # Reset collection and main window
    mw.progress.finish()
    mw.col.reset()
    mw.reset()
    browser.onSearchActivated()
    tooltip("""Notes copied.""")


def duplicate_one_note(nid, keepCreationTime, keepIvlEtc, keepLog):
    note = mw.col.get_note(nid)
    old_cards = note.cards()
    old_cards_sorted = sorted(old_cards, key=lambda x: x.ord) # , reverse=True)

    new_note, new_cards = add_note_with_id(note, nid if keepCreationTime else None)
    new_cards_sorted = sorted(new_cards, key=lambda x: x.ord) # , reverse=True)
    
    note.id = new_note.id
    note.guid = new_note.guid

    if getUserOption("relate copies", False):
        if not getRelationsFromNote(note):
            note.addTag(createRelationTag())
            note.flush()
    for old, new in zip(old_cards_sorted, new_cards_sorted):
        copy_card(old, new, keepIvlEtc, keepLog)
    
    note.add_tag(getUserOption("tag for copies"))
    note.usn = mw.col.usn()
    note.flush()


def copy_card(old_card, new_card, keepIvlEtc, keepLog):
    oid = old_card.id
    # Setting id to 0 is Card is seen as new; which lead to a different process in backend
    old_card.id = new_card.id
    # new_cid = timestampID(note.col.db, "cards", oid)
    if not keepIvlEtc:
        old_card.type = 0
        old_card.ivl = 0
        old_card.factor = 0
        old_card.reps = 0
        old_card.lapses = 0
        old_card.left = 0
        old_card.odue = 0
    old_card.nid = new_card.nid
    old_card.usn = mw.col.usn()
    old_card.flush()
    # I don't care about the card creation time
    if keepLog:
        for data in mw.col.db.all("select * from revlog where cid = ?", oid):
            copy_log(data, old_card.id)


def copy_log(data, new_cid):
    id, cid, usn, ease, ivl, lastIvl, factor, time, type = data
    usn = mw.col.usn()
    id = timestampID(mw.col.db, "revlog", t=id)
    cid = new_cid
    mw.col.db.execute("insert into revlog values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      id, cid, usn, ease, ivl, lastIvl, factor, time, type)


def add_note_with_id(old_note, id: Optional[int]= None):
    """Add a note, in the db with unique guid, and id as close as id possible, (now if id=None), without card."""
    note = mw.col.new_note(mw.col.models.get(old_note.mid))
    note.fields = old_note.fields
    mw.col.add_note(note, 1)
    new_id = timestampID(note.col.db, "notes", id)
    cards_for_new_note = note.cards()
    mw.col.db.execute("""
    update notes
    set id=?
    where id=?
    """, new_id, note.id)
    for c in cards_for_new_note:
        c.nid = new_id
        c.usn = mw.col.usn()
        c.flush()
    note.id = new_id
    return note, cards_for_new_note


def timestampID(db, table, t=None, before=False):
    "Return a non-conflicting timestamp for table."
    # be careful not to create multiple objects without flushing them, or they
    # may share an ID.
    t = t or intTime(1000)
    while db.scalar("select id from %s where id = ?" % table, t):
        if before:
            t -= 1
        else:
            t += 1
    return t


def getRelationsFromNote(note):
    relations = set()
    for relation in note.tags:
        for prefix in getUserOption("tag prefixes", ["relation_"]):
            if relation.startswith(prefix):
                relations.add(relation)
                break
    return relations


def createRelationTag():
    return f"""{getUserOption("current tag prefix", "relation_")}{intTime(1000)}"""
