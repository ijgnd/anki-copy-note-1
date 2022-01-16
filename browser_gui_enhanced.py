# Copyright: 2019- ijgnd
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html


from pprint import pprint as pp
import uuid

from aqt import mw
from anki.hooks import addHook, wrap
from aqt.browser import Browser
from aqt.utils import tooltip
from aqt.qt import *

from .config import getUserOption, gc
from .menu_key_navigation import keyFilter, alternative_keys
from .note_add_empty import make_new_notes
from .note_processing import duplicate_notes


def copy_notes_helper(browser, keepNotetype, keepCreationTime, keepIvlEtc, keepLog, keepContent):
    '''
    print(f"""
     browser: {browser},
keepNotetype: {keepNotetype},
        time: {keepCreationTime},
  keepIvlEtc: {keepIvlEtc},
         log: {keepLog},
 keepContent: {keepContent}""")
    '''
    # keepCreationTime = getUserOption("Preserve creation time", True)
    # keepLog = getUserOption("Copy log", True)
    # keepIvlEtc = getUserOption("Preserve ease, due, interval...", True)

    if keepContent:
        duplicate_notes(browser, keepCreationTime, keepIvlEtc, keepLog)
    else:
        make_new_notes(browser, keepNotetype, keepCreationTime)


def cNFB(browser, keepNotetype=True, keepCreationTime=True, keepIvlEtc=True, keepLog=True, keepContent=True):
    if not browser.selected_notes():
        tooltip("No notes selected.")
        return
    browser.editor.saveNow(lambda b=browser: copy_notes_helper(b, keepNotetype, keepCreationTime, keepIvlEtc, keepLog, keepContent))


basic_stylesheet = """
QMenu::item {
    padding-top: 6px;
    padding-bottom: 6px;
    padding-right: 10px;
    padding-left: 10px;
    font-size: 13px;
}
QMenu::item:selected {
    background-color: #fd4332;
}
"""

requiredKeys = [
    "label",
    # "shortcut",  # not necessary for menu so I add it later only for the shortcuts
    # I can just use .get() and default values?
    # "keepCreationTime",
    # "keepIvlEtc",
    # "keepLog",
    # "keepContent",
]


def menu_cut_helper(browser, entry):
    cNFB(browser=browser, 
        keepNotetype=entry.get("keep-note-type", True),
        keepCreationTime=entry.get("keepCreationTime", False), 
        keepIvlEtc=entry.get("keepIvlEtc", False), 
        keepLog=entry.get("keepLog", False), 
        keepContent=entry.get("keepContent", True))


# don't use the code from quick note menu: too complicated
def mymenu(browser):
    outermenu = QMenu(mw)
    outermenu.setStyleSheet(basic_stylesheet)
    quicksets = gc("quicksets")
    directCommands = {}
    if quicksets:
        for entry in quicksets:
            for k in requiredKeys:
                if not k in entry:
                    continue
            n = uuid.uuid4()   
            directCommands[n] = outermenu.addAction(entry["label"])
            directCommands[n].triggered.connect(lambda _, b=browser, e=entry: menu_cut_helper(b,e))
    # """
    c = QMenu("duplicate - custom ...")
    c.setStyleSheet(basic_stylesheet)
    outermenu.addMenu(c)

    p = QMenu("preserve creation time ...")
    p.setStyleSheet(basic_stylesheet)
    c.addMenu(p)
    n = QMenu("don't ...")
    n.setStyleSheet(basic_stylesheet)
    c.addMenu(n)

    pa = QMenu("after")
    pa.setStyleSheet(basic_stylesheet)
    p.addMenu(pa)
    pb = QMenu("before")
    pb.setStyleSheet(basic_stylesheet)
    p.addMenu(pb)


    pa_props = QMenu("preserve ease, due, interval")
    pa_props.setStyleSheet(basic_stylesheet)
    pa.addMenu(pa_props)

    pa_none = QMenu("don't")
    pa_none.setStyleSheet(basic_stylesheet)
    pa.addMenu(pa_none)


    pb_props = QMenu("preserve ease, due, interval")
    pb_props.setStyleSheet(basic_stylesheet)
    pb.addMenu(pb_props)

    pb_none = QMenu("don't")
    pb_none.setStyleSheet(basic_stylesheet)
    pb.addMenu(pb_none)


    n_props = QMenu("preserve ease, due, interval")
    n_props.setStyleSheet(basic_stylesheet)
    n.addMenu(n_props)

    n_none = QMenu("don't")
    n_none.setStyleSheet(basic_stylesheet)
    n.addMenu(n_none)


    x1 = pa_props.addAction("keep log")
    x1.triggered.connect(lambda _, n=browser: cNFB(browser=n, keepCreationTime="after", keepIvlEtc=True, keepLog=True, keepContent=True))
    x2 = pa_props.addAction("don't")
    x2.triggered.connect(lambda _, n=browser: cNFB(browser=n, keepCreationTime="after", keepIvlEtc=True, keepLog=False, keepContent=True))

    x3 = pa_none.addAction("keep log")
    x3.triggered.connect(lambda _, n=browser: cNFB(browser=n, keepCreationTime="after", keepIvlEtc=False, keepLog=True, keepContent=True))
    x4 = pa_none.addAction("don't")
    x4.triggered.connect(lambda _, n=browser: cNFB(browser=n, keepCreationTime="after", keepIvlEtc=False, keepLog=False, keepContent=True))


    x1 = pb_props.addAction("keep log")
    x1.triggered.connect(lambda _, n=browser: cNFB(browser=n, keepCreationTime="before", keepIvlEtc=True, keepLog=True, keepContent=True))
    x2 = pb_props.addAction("don't")
    x2.triggered.connect(lambda _, n=browser: cNFB(browser=n, keepCreationTime="before", keepIvlEtc=True, keepLog=False, keepContent=True))

    x3 = pb_none.addAction("keep log")
    x3.triggered.connect(lambda _, n=browser: cNFB(browser=n, keepCreationTime="before", keepIvlEtc=False, keepLog=True, keepContent=True))
    x4 = pb_none.addAction("don't")
    x4.triggered.connect(lambda _, n=browser: cNFB(browser=n, keepCreationTime="before", keepIvlEtc=False, keepLog=False, keepContent=True))


    x5 = n_props.addAction("keep log")
    x5.triggered.connect(lambda _, n=browser: cNFB(browser=n, keepCreationTime=False, keepIvlEtc=True, keepLog=True, keepContent=True))
    x6 = n_props.addAction("don't")
    x6.triggered.connect(lambda _, n=browser: cNFB(browser=n, keepCreationTime=False, keepIvlEtc=True, keepLog=False, keepContent=True))

    x7 = n_none.addAction("keep log")
    x7.triggered.connect(lambda _, n=browser: cNFB(browser=n, keepCreationTime=False, keepIvlEtc=False, keepLog=True, keepContent=True))
    x8 = n_none.addAction("don't")
    x8.triggered.connect(lambda _, n=browser: cNFB(browser=n, keepCreationTime=False, keepIvlEtc=False, keepLog=False, keepContent=True))
    #"""

    if gc("menu_use_alternative_keys_for_navigation"):
        for m in [outermenu, c, p, n, pa, pb, pa_props, pa_none, pb_props, pb_none, n_props, n_none]:
        # for m in [outermenu]:
            menufilter = keyFilter(m)
            m.installEventFilter(menufilter)
            m.alternative_keys = alternative_keys
    outermenu.exec(QCursor.pos())


def create_copy_action(browser):
    action = QAction("Duplicate/Insert Note", browser)
    key = gc("Shortcut: copy")
    if key:
        action.setShortcut(QKeySequence(key))
    action.triggered.connect(lambda _, b=browser: mymenu(b))
    return action


def setupMenu(browser):
    browser.form.menubar_show_copy_menu_action = create_copy_action(browser)    
    browser.form.menu_Notes.addSeparator()
    browser.form.menu_Notes.addAction(browser.form.menubar_show_copy_menu_action)
    if not browser.table.is_notes_mode():
        browser.form.menubar_show_copy_menu_action.setEnabled(False)
    
    # add global shortcuts:
    quicksets = gc("quicksets")
    directCommands = {}
    if quicksets:
        extended = requiredKeys + ["shortcut"]
        for entry in quicksets:
            for k in extended:
                if not k in entry :
                    continue
            n = uuid.uuid4()
            directCommands[n] = QShortcut(QKeySequence(entry["shortcut"]), browser) 
            qconnect(directCommands[n].activated, lambda b=browser, e=entry: menu_cut_helper(b,e))
addHook("browser.setupMenus", setupMenu)


# Set the action active only if in notes mode
def on_browser_mode_changed(browser, is_note_mode):
    browser.form.menubar_show_copy_menu_action.setEnabled(is_note_mode)
Browser.on_table_state_changed = wrap(Browser.on_table_state_changed, on_browser_mode_changed)


def add_to_editor_context(view, menu):
    browser = view.editor.parentWindow
    if not isinstance(browser, Browser):
        return
    if browser.table.is_notes_mode(): 
        a = menu.addAction("Copy note")
        a.triggered.connect(lambda _, b=browser: mymenu(b))
addHook("EditorWebView.contextMenuEvent", add_to_editor_context)
