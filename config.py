import sys

from aqt import mw
from aqt.utils import showWarning

# to be configured by Dev
############################
addonName = "Copy notes"
version = 2


def newVersion():
    pass


"""A string stating what could occurs with a wrong configuration file"""
otherwise = ""


# end configuration

userOption = None


def _getUserOption():
    global userOption
    if userOption is None:
        userOption = mw.addonManager.getConfig(__name__)


def getUserOption(key=None, default=None):
    _getUserOption()
    if key is None:
        return userOption
    if key in userOption:
        return userOption[key]
    else:
        return default
gc = getUserOption


lastVersion = getUserOption(version, 0)
if lastVersion < version:
    newVersion()
    pass
if lastVersion > version:
    t = f"Please update add-on {addonName}. It seems that your configuration file is made for a more recent version of the add-on."
    if otherwise:
        t += "\n"+otherwise
    showWarning(t)


def writeConfig():
    mw.addonManager.writeConfig(__name__, userOption)


def update(_):
    global userOption, fromName
    userOption = None
    fromName = None


mw.addonManager.setConfigUpdatedAction(__name__, update)

fromName = None


def getFromName(name):
    global fromName
    if fromName is None:
        fromName = dict()
        for dic in getUserOption("columns"):
            fromName[dic["name"]] = dic
    return fromName.get(name)


def setUserOption(key, value):
    _getUserOption()
    userOption[key] = value
    writeConfig()



def get_anki_version():
    try:
        # 2.1.50+ because of bdd5b27715bb11e4169becee661af2cb3d91a443, https://github.com/ankitects/anki/pull/1451
        from anki.utils import point_version
    except:
        try:
            # introduced with 66714260a3c91c9d955affdc86f10910d330b9dd in 2020-01-19, should be in 2.1.20+
            from anki.utils import pointVersion
        except:
            # <= 2.1.19
            from anki import version as anki_version
            return int(anki_version.split(".")[-1]) 
        else:
            return pointVersion()
    else:
        return point_version()
anki_21_version = get_anki_version()
