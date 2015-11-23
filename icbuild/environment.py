# icbuild - a tool to ease building collections of source packages
# Copyright (C) 2001-2006  James Henstridge
# Copyright (C) 2007-2008  Frederic Peters
# Copyright (C) 2014 Canonical Limited
# Copyright (C) 2015 Ignacio Casal Quinteiro
#
#   environment.py: environment variable setup
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import sys
import os

from icbuild.errors import FatalError, CommandError

def addpath(envvar, path, prepend=True):
    '''Adds a path to an environment variable.'''
    pathsep = os.pathsep

    envval = os.environ.get(envvar, path)
    parts = envval.split(pathsep)
    if prepend:
        parts.insert(0, path)
    else:
        parts.append(path)
    # remove duplicate entries:
    i = 1
    while i < len(parts):
        if parts[i] in parts[:i]:
            del parts[i]
        else:
            i += 1
    envval = pathsep.join(parts)

    os.environ[envvar] = envval

def setup_env(config):
    '''set environment variables for using prefix'''
    # PATH
    msys2bindir = os.path.join(config.msys2dir, 'bin')
    addpath('PATH', msys2bindir)
