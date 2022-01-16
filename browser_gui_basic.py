from anki.hooks import addHook
from aqt.qt import *

from .config import getUserOption
from .note_processing import duplicate_notes



def setupMenu(browser):
    a = QAction("Note Copy", browser)
    # Shortcut for convenience. Added by Didi
    a.setShortcut(QKeySequence(getUserOption("Shortcut: copy", "Ctrl+C")))
    keepCreationTime = getUserOption("Preserve creation time", True)
    keepLog = getUserOption("Copy log", True)
    keepIvlEtc = getUserOption("Preserve ease, due, interval...", True)
    a.triggered.connect(lambda: duplicate_notes(browser, keepCreationTime, keepIvlEtc, keepLog))
    browser.form.menu_Notes.addSeparator()
    browser.form.menu_Notes.addAction(a)
addHook("browser.setupMenus", setupMenu)
