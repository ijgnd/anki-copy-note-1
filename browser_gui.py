from anki.hooks import addHook
from aqt.qt import *

from .config import getUserOption
from .note_processing import duplicate_notes



def setupMenu(browser):
    a = QAction("Note Copy", browser)
    # Shortcut for convenience. Added by Didi
    a.setShortcut(QKeySequence(getUserOption("Shortcut: copy", "Ctrl+C")))
    a.triggered.connect(lambda: duplicate_notes(browser))
    browser.form.menu_Notes.addSeparator()
    browser.form.menu_Notes.addAction(a)
addHook("browser.setupMenus", setupMenu)
