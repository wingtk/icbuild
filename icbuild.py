# -*- coding: utf-8 -*-

import sys
import os
import builtins
import icbuild

pkgdatadir = None
datadir = None
srcdir = os.path.abspath(os.path.join(os.path.dirname(icbuild.__file__), '..'))

builtins.__dict__['PKGDATADIR'] = pkgdatadir
builtins.__dict__['DATADIR'] = datadir
builtins.__dict__['SRCDIR'] = srcdir

import icbuild.main
icbuild.main.main(sys.argv[1:])
