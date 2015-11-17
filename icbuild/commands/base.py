# icbuild - a tool to ease building collections of source packages
# Copyright (C) 2001-2006  James Henstridge
# Copyright (C) 2015  Ignacio Casal Quinteiro
#
#   base.py: the most common icbuild commands
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

import os
import optparse
import re
import stat
import sys
import time
from optparse import make_option
import logging

import icbuild.moduleset
import icbuild.frontends
from icbuild.errors import UsageError, FatalError, CommandError
from icbuild.commands import Command, BuildCommand, register_command

from icbuild.config import parse_relative_time


class cmd_build(BuildCommand):
    doc = 'Update and compile all modules (the default)'

    name = 'build'
    usage_args = '[ options ... ] [ modules ... ]'

    def __init__(self):
        Command.__init__(self, [
            make_option('-c', '--clean',
                        action='store_true', dest='clean', default=False,
                        help='clean before building'),
            make_option('-n', '--no-network',
                        action='store_true', dest='nonetwork', default=False,
                        help='skip version control update'),
            make_option('-s', '--skip', metavar='MODULES',
                        action='append', dest='skip', default=[],
                        help='treat the given modules as up to date'),
            make_option('-t', '--start-at', metavar='MODULE',
                        action='store', dest='startat', default=None,
                        help='start building at the given module'),
            make_option('-f', '--force',
                        action='store_true', dest='force_policy', default=False,
                        help='build even if policy says not to'),
            make_option('-m', '--arch',
                        action='store', dest='arch', default='Win32',
                        choices=['Win32', 'x64'],
                        help='build for a specific architecture'),
            ])

    def run(self, config, options, args, help=None):
        config.set_from_cmdline_options(options)

        module_set = icbuild.moduleset.load(config)
        modules = args or config.modules
        full_module_list = module_set.get_full_module_list \
                               (modules, config.skip,
                                include_suggests=not config.ignore_suggests)
        module_list = module_set.remove_tag_modules(full_module_list,
                                                    config.tags)
        # remove modules up to startat
        if options.startat:
            while module_list and module_list[0].name != options.startat:
                del module_list[0]
            if not module_list:
                raise FatalError('%s not in module list' % options.startat)

        if len(module_list) == 0 and modules[0] in (config.skip or []):
            logging.info(
                    'requested module is in the ignore list, nothing to do.')
            return 0

        build = icbuild.frontends.get_buildscript(config, module_list, module_set=module_set)
        return build.build()

register_command(cmd_build)


class cmd_buildone(BuildCommand):
    doc = 'Update and compile one or more modules'

    name = 'buildone'
    usage_args = '[ options ... ] [ modules ... ]'

    def __init__(self):
        Command.__init__(self, [
            make_option('-c', '--clean',
                        action='store_true', dest='clean', default=False,
                        help='clean before building'),
            make_option('-n', '--no-network',
                        action='store_true', dest='nonetwork', default=False,
                        help='skip version control update'),
            make_option('-f', '--force',
                        action='store_true', dest='force_policy', default=False,
                        help='build even if policy says not to'),
            make_option('-m', '--arch',
                        action='store', dest='arch', default='Win32',
                        choices=['Win32', 'x64'],
                        help='build for a specific architecture'),
            ])

    def run(self, config, options, args, help=None):
        config.set_from_cmdline_options(options)

        module_set = icbuild.moduleset.load(config)
        module_list = []
        for modname in args:
            modname = modname.rstrip(os.sep)
            try:
                module = module_set.get_module(modname, ignore_case=True)
            except KeyError as e:
                default_repo = icbuild.moduleset.get_default_repo()
                if not default_repo:
                    continue
                from icbuild.modtypes.autotools import AutogenModule
                module = AutogenModule(modname, default_repo.branch(modname))
                module.config = config
                logging.info('module "%(modname)s" does not exist, created automatically using repository "%(reponame)s"' % \
                             {'modname': modname, 'reponame': default_repo.name})
            module_list.append(module)

        if not module_list:
            self.parser.error('This command requires a module parameter.')

        build = icbuild.frontends.get_buildscript(config, module_list, module_set=module_set)
        return build.build()

register_command(cmd_buildone)
