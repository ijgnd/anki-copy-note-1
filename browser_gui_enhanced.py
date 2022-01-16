from aqt.utils import tooltip

msg = "Copy Notes Addon: Enhanced gui mode is not implemented yet. Falling back to basic mode."
print(msg)
tooltip(msg)

from . import browser_gui_basic
