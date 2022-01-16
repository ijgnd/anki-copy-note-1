from .config import getUserOption

if getUserOption("Basic Mode: Always use config presets", True):
    from . import browser_gui_basic
else:
    from . import browser_gui_enhanced

from . import debug
