# -*- coding: utf-8 -*-
# Copyright: Arthur Milchior arthur@milchior.fr
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
# Select any number of cards in the card browser and create exact copies of each card in the deck
# Feel free to contribute to this code on https://github.com/Arthur-Milchior/anki-copy-note
# Anki's add-on number: 1566928056

# This add-ons is heavily based on Kealan Hobelmann's addon 396494452

"""To use:

1) Open the card browser
2) Select the desired notes (at least one card by note)
3) Go to "Edit > Copy Notes in place" or "Edit > Full note copy"

Both option consider the note you did select, and create a new note with the same content. (Fields and tags)
Both option add the card of the copied note to the deck in which the original card is (this is the main difference with addon 396494452)

"Copy notes in place" create  cards which are new. Empty card's are not copied.
"Full note copy" also copy the reviews paramater (number of reviews,  of leeches, easiness, due date...). Empty card's are copied.

Recall that an «empty cards» is a card that should be deleted by
«check empty card».
"""

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import anki.notes
from anki.hooks import addHook
from anki.importing.anki2 import Anki2Importer
from anki.lang import _
from anki.utils import guid64
from aqt import mw
from aqt.utils import showWarning, tooltip

from .config import getUserOption
from .utils import createRelationTag, getRelationsFromNote
from .new_note_id import add_note_with_id
from .time import timestampID

#import profile


def setupMenu(browser):
    a = QAction("Note Copy", browser)
    # Shortcut for convenience. Added by Didi
    a.setShortcut(QKeySequence(getUserOption("Shortcut: copy", "Ctrl+C")))
    a.triggered.connect(lambda: copyNotes(browser))
    browser.form.menu_Notes.addSeparator()
    browser.form.menu_Notes.addAction(a)


def copyNotes(browser):
    """
    nids -- id of notes to copy
    """
    nids = browser.selectedNotes()
    mw.checkpoint("Copy Notes")
    mw.progress.start()
    for nid in nids:
        copyNote(nid)
    # Reset collection and main window
    mw.progress.finish()
    mw.col.reset()
    mw.reset()
    browser.onSearchActivated()
    tooltip("""Cards copied.""")


def copyNote(nid):
    note = mw.col.getNote(nid)
    old_cards = note.cards()
    old_cards_sorted = sorted(old_cards, key=lambda x: x.ord) # , reverse=True)
    oid = note.id

    new_note, new_cards = add_note_with_id(note, nid if getUserOption("Preserve creation time", True) else None)
    new_cards_sorted = sorted(new_cards, key=lambda x: x.ord) # , reverse=True)
    
    note.id = new_note.id
    note.guid = new_note.guid

    if getUserOption("relate copies", False):
        if not getRelationsFromNote(note):
            note.addTag(createRelationTag())
            note.flush()
    for old, new in zip(old_cards_sorted, new_cards_sorted):
        copyCard(old, new)
    
    note.addTag(getUserOption("tag for copies"))
    note.usn = mw.col.usn()
    note.flush()


def copyCard(old_card, new_card):
    oid = old_card.id
    # Setting id to 0 is Card is seen as new; which lead to a different process in backend
    old_card.id = new_card.id
    # new_cid = timestampID(note.col.db, "cards", oid)
    if not getUserOption("Preserve ease, due, interval...", True):
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
    if getUserOption("Copy log", True):
        for data in mw.col.db.all("select * from revlog where cid = ?", oid):
            copyLog(data, old_card.id)


def copyLog(data, newCid):
    id, cid, usn, ease, ivl, lastIvl, factor, time, type = data
    usn = mw.col.usn()
    id = timestampID(mw.col.db, "revlog", t=id)
    cid = newCid
    mw.col.db.execute("insert into revlog values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      id, cid, usn, ease, ivl, lastIvl, factor, time, type)


addHook("browser.setupMenus", setupMenu)
