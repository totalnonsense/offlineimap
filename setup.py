#!/usr/bin/env python

# $Id: setup.py,v 1.1 2002/06/21 18:10:49 jgoerzen Exp $

# IMAP synchronization
# Module: installer
# COPYRIGHT #
# Copyright (C) 2002 - 2006 John Goerzen
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
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
# END OF COPYRIGHT #


from distutils.core import setup
import offlineimap

setup(name = "offlineimap",
      version = offlineimap.__version__,
      description = offlineimap.__description__,
      author = offlineimap.__author__,
      author_email = offlineimap.__author_email__,
      url = offlineimap.__homepage__,
      packages = ['offlineimap', 'offlineimap.folder',
                  'offlineimap.repository', 'offlineimap.ui'],
      scripts = ['bin/offlineimap'],
      license = offlineimap.__copyright__ + \
                ", Licensed under the GPL version 2"
)

