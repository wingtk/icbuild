# icbuild - a tool to ease building collections of source packages
# Copyright (C) 2015  Ignacio Casal Quinteiro
#
#   msvc.py: msvc module type definitions.
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

__metaclass__ = type

import os

from icbuild.errors import BuildStateError, CommandError
from icbuild.modtypes import \
     Package, DownloadableModule, register_module_type, MakeModule

__all__ = [ 'MSVCModule' ]

class MSVCModule(Package, DownloadableModule):
    """Base type for modules that use MSBuild build system."""
    type = 'msvc'

    PHASE_CHECKOUT = DownloadableModule.PHASE_CHECKOUT
    PHASE_FORCE_CHECKOUT = DownloadableModule.PHASE_FORCE_CHECKOUT
    PHASE_BUILD = 'build'
    PHASE_INSTALL = 'install'

    def __init__(self, name, branch=None,
                 solution='', msvcargs=''):
        Package.__init__(self, name, branch=branch)
        self.solution = solution
        self.msvcargs = msvcargs

    def get_srcdir(self, buildscript):
        return self.branch.srcdir

    def get_builddir(self, buildscript):
        return self.get_srcdir(buildscript)

    def do_build(self, buildscript):
        buildscript.set_action('Building', self)
        srcdir = self.get_srcdir(buildscript)
        msbuild = buildscript.config.msbuild
        cmd = [ msbuild, self.solution, self.makeargs ]
        buildscript.execute(cmd, cwd = srcdir)
    do_build.depends = [PHASE_CHECKOUT]
    do_build.error_phases = [PHASE_FORCE_CHECKOUT]

    def do_install(self, buildscript):
        buildscript.set_action('Installing', self)
        # do nothing for now
    do_install.depends = [PHASE_BUILD]

    def xml_tag_and_attrs(self):
        return 'msvc', [('id', 'name', None)]

def collect_args(instance, node, argtype):
    if node.hasAttribute(argtype):
        args = node.getAttribute(argtype)
    else:
        args = ''

    for child in node.childNodes:
        if child.nodeType == child.ELEMENT_NODE and child.nodeName == argtype:
            if not child.hasAttribute('value'):
                raise FatalError(_("<%s/> tag must contain value=''") % argtype)
            args += ' ' + child.getAttribute('value')

    return instance.eval_args(args)

def parse_msvc(node, config, uri, repositories, default_repo):
    instance = MSVCModule.parse_from_xml(node, config, uri, repositories, default_repo)

    instance.msvcargs = collect_args(instance, node, 'msvcargs')

    return instance

register_module_type('msvc', parse_msvc)
