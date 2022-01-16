import anki.notes
from anki.hooks import addHook
from anki.importing.anki2 import Anki2Importer
from anki.utils import guid64
from aqt import mw
from aqt.utils import askUser, showWarning

from .config import getUserOption


def check():
    checkedGui = getUserOption("checkedGui", [])
    if mw.pm.name in checkedGui:
        return
    lastGuid = None
    accepted = False
    for guid, nid in mw.col.db.all("select guid, id from notes order by guid, id"):
        if lastGuid == guid:
            if accepted is False:
                accepted = askUser(
                    ("A previous version of copy note created a bug. Correcting it will require "
                     "to do a full sync of your collection. Do you want to correct it now ?"
                    ))
            if accepted is False:
                return
            mw.col.modSchema(True)
            mw.col.db.execute(
                "update notes set guid = ? where id = ? ", guid64(), nid)
        lastGuid = guid
    checkedGui.append(mw.pm.name)
addHook("profileLoaded", check)



firstBug = False
NID = 0
GUID = 1
MID = 2
MOD = 3
# determine if note is a duplicate, and adjust mid and/or guid as required
# returns true if note should be added


def _uniquifyNote(self, note):
    global firstBug
    srcMid = note[MID]
    dstMid = self._mid(srcMid)

    if srcMid != dstMid:
        # differing schemas and note doesn't exist?
        note[MID] = dstMid

    if note[GUID] in self._notes:
        destId, destMod, destMid = self._notes[note[GUID]]
        if note[NID] == destId:  # really a duplicate
            if srcMid != dstMid:  # schema changed and don't import
                self._ignoredGuids[note[GUID]] = True
            return False
        else:  # Probably a copy made by buggy version. Change guid to a new one.
            while note[GUID] in self._notes:
                note[GUID] = guid64()
            if not firstBug:
                firstBug = True
                showWarning("""Hi. Sorry to disturb you. 
The deck you are importing seems to have a bug, created by a version of the add-on 1566928056 before 
the 26th of september 2019. Can you please tell the author of the imported deck that you were warned 
of this bug, and that it should update the shared deck to remove the bug ? Please send them the 
link https://github.com/Arthur-Milchior/anki-copy-note so they can have more informations. And let 
me know on this link whether there is any trouble.""")

            return True
    else:
        return True


if getUserOption("correct import", True):
    Anki2Importer._uniquifyNote = _uniquifyNote


def _importNotes(self):
    # build guid -> (id,mod,mid) hash & map of existing note ids
    self._notes = {}
    existing = {}
    for id, guid, mod, mid in self.dst.db.execute(
            "select id, guid, mod, mid from notes"):
        self._notes[guid] = (id, mod, mid)
        existing[id] = True
    # we may need to rewrite the guid if the model schemas don't match,
    # so we need to keep track of the changes for the card import stage
    self._changedGuids = {}
    # we ignore updates to changed schemas. we need to note the ignored
    # guids, so we avoid importing invalid cards
    self._ignoredGuids = {}
    # iterate over source collection
    add = []
    update = []
    dirty = []
    usn = self.dst.usn()
    dupesIdentical = []
    dupesIgnored = []
    total = 0
    for note in self.src.db.execute(
            "select * from notes"):
        total += 1
        # turn the db result into a mutable list
        note = list(note)
        shouldAdd = self._uniquifyNote(note)
        if shouldAdd:
            # ensure id is unique
            while note[0] in existing:
                note[0] += 999
            existing[note[0]] = True
            # bump usn
            note[4] = usn
            # update media references in case of dupes
            note[6] = self._mungeMedia(note[MID], note[6])
            add.append(note)
            dirty.append(note[0])
            # note we have the added the guid
            self._notes[note[GUID]] = (note[0], note[3], note[MID])
        else:
            # a duplicate or changed schema - safe to update?
            if self.allowUpdate:
                oldNid, oldMod, oldMid = self._notes[note[GUID]]
                # will update if incoming note more recent
                if oldMod < note[MOD]:
                    # safe if note types identical
                    if oldMid == note[MID]:
                        # incoming note should use existing id
                        note[0] = oldNid
                        note[4] = usn
                        note[6] = self._mungeMedia(note[MID], note[6])
                        update.append(note)
                        dirty.append(note[0])
                    else:
                        dupesIgnored.append(note)
                        self._ignoredGuids[note[GUID]] = True
                else:
                    dupesIdentical.append(note)
