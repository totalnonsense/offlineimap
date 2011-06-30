# Base folder support
# Copyright (C) 2002 John Goerzen
# <jgoerzen@complete.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

from threading import *
from IMAP import IMAPFolder
import os.path

class MappingFolderMixIn:
    """Helper class to map between Folder() instances where both side assign a uid

    Instance variables (self.):
      r2l: dict mapping message uids: self.r2l[remoteuid]=localuid
      l2r: dict mapping message uids: self.r2l[localuid]=remoteuid
      #TODO: what is the difference, how are they used?
      diskr2l: dict mapping message uids: self.r2l[remoteuid]=localuid
      diskl2r: dict mapping message uids: self.r2l[localuid]=remoteuid"""
    def _initmapping(self):
        self.maplock = Lock()
        (self.diskr2l, self.diskl2r) = self._loadmaps()
        self._mb = self.__class__.__bases__[1]

    def _getmapfilename(self):
        return os.path.join(self.repository.getmapdir(),
                            self.getfolderbasename())
        
    def _loadmaps(self):
        self.maplock.acquire()
        try:
            mapfilename = self._getmapfilename()
            if not os.path.exists(mapfilename):
                return ({}, {})
            file = open(mapfilename, 'rt')
            r2l = {}
            l2r = {}
            while 1:
                line = file.readline()
                if not len(line):
                    break
                try:
                    line = line.strip()
                except ValueError:
                    raise Exception("Corrupt line '%s' in UID mapping file '%s'" \
                                        %(line, mapfilename))
                (str1, str2) = line.split(':')
                loc = long(str1)
                rem = long(str2)
                r2l[rem] = loc
                l2r[loc] = rem
            return (r2l, l2r)
        finally:
            self.maplock.release()

    def _savemaps(self, dolock = 1):
        mapfilename = self._getmapfilename()
        if dolock: self.maplock.acquire()
        try:
            file = open(mapfilename + ".tmp", 'wt')
            for (key, value) in self.diskl2r.iteritems():
                file.write("%d:%d\n" % (key, value))
            file.close()
            os.rename(mapfilename + '.tmp', mapfilename)
        finally:
            if dolock: self.maplock.release()

    def _uidlist(self, mapping, items):
        return [mapping[x] for x in items]

    def cachemessagelist(self):
        self._mb.cachemessagelist(self)
        reallist = self._mb.getmessagelist(self)

        self.maplock.acquire()
        try:
            # OK.  Now we've got a nice list.  First, delete things from the
            # summary that have been deleted from the folder.

            for luid in self.diskl2r.keys():
                if not reallist.has_key(luid):
                    ruid = self.diskl2r[luid]
                    del self.diskr2l[ruid]
                    del self.diskl2r[luid]

            # Now, assign negative UIDs to local items.
            self._savemaps(dolock = 0)
            nextneg = -1

            self.r2l = self.diskr2l.copy()
            self.l2r = self.diskl2r.copy()

            for luid in reallist.keys():
                if not self.l2r.has_key(luid):
                    ruid = nextneg
                    nextneg -= 1
                    self.l2r[luid] = ruid
                    self.r2l[ruid] = luid
        finally:
            self.maplock.release()

    def uidexists(self, ruid):
        """Checks if the (remote) UID exists in this Folder"""
        # This implementation overrides the one in BaseFolder, as it is
        # much more efficient for the mapped case.
        return ruid in self.r2l

    def getmessageuidlist(self):
        """Gets a list of (remote) UIDs.
        You may have to call cachemessagelist() before calling this function!"""
        # This implementation overrides the one in BaseFolder, as it is
        # much more efficient for the mapped case.
        return self.r2l.keys()

    def getmessagecount(self):
        """Gets the number of messages in this folder.
        You may have to call cachemessagelist() before calling this function!"""
        # This implementation overrides the one in BaseFolder, as it is
        # much more efficient for the mapped case.
        return len(self.r2l)

    def getmessagelist(self):
        """Gets the current message list. This function's implementation
        is quite expensive for the mapped UID case.  You must call
        cachemessagelist() before calling this function!"""

        retval = {}
        localhash = self._mb.getmessagelist(self)
        self.maplock.acquire()
        try:
            for key, value in localhash.items():
                try:
                    key = self.l2r[key]
                except KeyError:
                    # Sometimes, the IMAP backend may put in a new message,
                    # then this function acquires the lock before the system
                    # has the chance to note it in the mapping.  In that case,
                    # just ignore it.
                    continue
                value = value.copy()
                value['uid'] = self.l2r[value['uid']]
                retval[key] = value
            return retval
        finally:
            self.maplock.release()

    def getmessage(self, uid):
        """Returns the content of the specified message."""
        return self._mb.getmessage(self, self.r2l[uid])

    def savemessage(self, uid, content, flags, rtime):
        """Writes a new message, with the specified uid.

        The UIDMaps class will not return a newly assigned uid, as it
        internally maps different uids between IMAP servers. So a
        successful savemessage() invocation will return the same uid it
        has been invoked with. As it maps between 2 IMAP servers which
        means the source message must already have an uid, it requires a
        positive uid to be passed in. Passing in a message with a
        negative uid will do nothing and return the negative uid.

        If the uid is > 0, the backend should set the uid to this, if it can.
        If it cannot set the uid to that, it will save it anyway.
        It will return the uid assigned in any case.
        """
        # Mapped UID instances require the source to already have a
        # positive UID, so simply return here.
        if uid < 0:
            return uid

        #if msg uid already exists, just modify the flags
        if uid in self.r2l:
            self.savemessageflags(uid, flags)
            return uid

        newluid = self._mb.savemessage(self, -1, content, flags, rtime)
        if newluid < 1:
            raise ValueError("Backend could not find uid for message")
        self.maplock.acquire()
        try:
            self.diskl2r[newluid] = uid
            self.diskr2l[uid] = newluid
            self.l2r[newluid] = uid
            self.r2l[uid] = newluid
            self._savemaps(dolock = 0)
        finally:
            self.maplock.release()

    def getmessageflags(self, uid):
        return self._mb.getmessageflags(self, self.r2l[uid])

    def getmessagetime(self, uid):
        return None

    def savemessageflags(self, uid, flags):
        self._mb.savemessageflags(self, self.r2l[uid], flags)

    def addmessageflags(self, uid, flags):
        self._mb.addmessageflags(self, self.r2l[uid], flags)

    def addmessagesflags(self, uidlist, flags):
        self._mb.addmessagesflags(self, self._uidlist(self.r2l, uidlist),
                                  flags)

    def _mapped_delete(self, uidlist):
        self.maplock.acquire()
        try:
            needssave = 0
            for ruid in uidlist:
                luid = self.r2l[ruid]
                del self.r2l[ruid]
                del self.l2r[luid]
                if ruid > 0:
                    del self.diskr2l[ruid]
                    del self.diskl2r[luid]
                    needssave = 1
            if needssave:
                self._savemaps(dolock = 0)
        finally:
            self.maplock.release()

    def deletemessageflags(self, uid, flags):
        self._mb.deletemessageflags(self, self.r2l[uid], flags)

    def deletemessagesflags(self, uidlist, flags):
        self._mb.deletemessagesflags(self, self._uidlist(self.r2l, uidlist),
                                     flags)

    def deletemessage(self, uid):
        self._mb.deletemessage(self, self.r2l[uid])
        self._mapped_delete([uid])

    def deletemessages(self, uidlist):
        self._mb.deletemessages(self, self._uidlist(self.r2l, uidlist))
        self._mapped_delete(uidlist)

# Define a class for local part of IMAP.
class MappedIMAPFolder(MappingFolderMixIn, IMAPFolder):
    def __init__(self, *args, **kwargs):
	IMAPFolder.__init__(self, *args, **kwargs)
        self._initmapping()
