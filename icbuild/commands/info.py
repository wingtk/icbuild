# icbuild - a tool to ease building collections of source packages
# Copyright (C) 2001-2006  James Henstridge
#
#   info.py: show information about a module
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
import time

import icbuild.moduleset
import icbuild.frontends
from icbuild.errors import FatalError
from icbuild.commands import Command, register_command
from icbuild.modtypes import MetaModule
from icbuild.versioncontrol.tarball import TarballBranch


class cmd_info(Command):
    doc = 'Display information about one or more modules'

    name = 'info'
    usage_args = '[ modules ... ]'


    def run(self, config, options, args, help=None):
        module_set = icbuild.moduleset.load(config)
        packagedb = module_set.packagedb

        if args:
            for modname in args:
                try:
                    module = module_set.get_module(modname, ignore_case = True)
                except KeyError:
                    raise FatalError('unknown module %s' % modname)
                self.show_info(module, packagedb, module_set)
        else:
            for module in module_set.modules.values():
                self.show_info(module, packagedb, module_set)

    def show_info(self, module, packagedb, module_set):
        package_entry = packagedb.get(module.name)

        uprint('Name:', module.name)
        uprint('Module Set:', module.moduleset_name)
        uprint('Type:', module.type)

        if package_entry is not None:
            uprint('Install version:', package_entry.version)
            uprint('Install date:', time.strftime('%Y-%m-%d %H:%M:%S',
                                                     time.localtime(packagedb.installdate(module.name))))
        else:
            uprint('Install version:', 'not installed')
            uprint('Install date:', 'not installed')

        if isinstance(module, MetaModule):
            pass
        elif isinstance(module.branch, TarballBranch):
            uprint('URL:', module.branch.module)
            uprint('Version:', module.branch.version)
        try:
            tree_id = module.branch.tree_id()
            uprint('Tree-ID:', tree_id)
        except (NotImplementedError, AttributeError):
            pass
        try:
            source_dir = module.branch.srcdir
            uprint('Sourcedir:', source_dir)
        except (NotImplementedError, AttributeError):
            pass

        # dependencies
        if module.dependencies:
            uprint('Requires:', ', '.join(module.dependencies))
        requiredby = [ mod.name for mod in module_set.modules.values()
                       if module.name in mod.dependencies ]
        if requiredby:
            uprint('Required by:', ', '.join(requiredby))
        if module.suggests:
            uprint('Suggests:', ', '.join(module.suggests))
        if module.after:
            uprint('After:', ', '.join(module.after))
        before = [ mod.name for mod in module_set.modules.values()
                   if module.name in mod.after ]
        if before:
            uprint('Before:', ', '.join(before))

        print

register_command(cmd_info)
