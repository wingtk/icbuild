# icbuild - a tool to ease building collections of source packages
# Copyright (C) 2001-2006  James Henstridge
#
#   __init__.py: a package holding the various icbuild subcommands
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
__all__ = [
    'Command',
    'register_command',
    'run'
    ]

import optparse
import sys

from icbuild.errors import UsageError, FatalError


class OptionParser(optparse.OptionParser):
    def exit(self, status=0, msg=None):
        if msg:
            sys.stderr.write(uencode(msg))
        sys.exit(status)


class Command:
    """Base class for Command objects"""

    doc = ''
    name = None
    usage_args = '[ options ... ]'

    def __init__(self, options=[]):
        self.options = options

    def execute(self, config, args, help):
        options, args = self.parse_args(args)
        return self.run(config, options, args, help)

    def parse_args(self, args):
        self.parser = OptionParser(
            usage='%%prog %s %s' % (self.name, self.usage_args),
            description=self.doc)
        self.parser.add_options(self.options)
        return self.parser.parse_args(args)

    def run(self, config, options, args, help=None):
        """The body of the command"""
        raise NotImplementedError

class BuildCommand(Command):
    """Abstract class for commands that build modules"""

    def required_system_dependencies_installed(self, module_state):
        '''Returns true if all required system dependencies are installed for
        modules in module_state.'''
        for module, (req_version, installed_version, new_enough, systemmodule) in module_state.iteritems():
            if systemmodule:
                if not new_enough:
                    return False
        return True

    def print_system_dependencies(self, module_state):

        def fmt_details(pkg_config, req_version, installed_version):
            fmt_list = []
            if pkg_config:
                fmt_list.append(pkg_config)
            if req_version:
                fmt_list.append('required=%s' % req_version)
            if installed_version and installed_version != 'unknown':
                fmt_list.append('installed=%s' % installed_version)
            # Translators: This is used to separate items of package metadata
            fmt_str = ', '.join(fmt_list)
            if fmt_str:
                return '(%s)' % fmt_str
            else:
                return ''

        print('Required packages:')
        print('  System installed packages which are too old:')
        have_too_old = False
        for module, (req_version, installed_version, new_enough, systemmodule) in module_state.iteritems():
            if (installed_version is not None) and (not new_enough) and systemmodule:
                have_too_old = True
                print ('    %s %s' % (module.name,
                                      fmt_details(module.pkg_config,
                                                  req_version,
                                                  installed_version)))
        if not have_too_old:
            print('    (none)')

        print('  No matching system package installed:')
        have_missing = False
        for module, (req_version, installed_version, new_enough, systemmodule) in module_state.iteritems():
            if installed_version is None and (not new_enough) and systemmodule:
                have_missing = True
                print ('    %s %s' % (module.name,
                                      fmt_details(module.pkg_config,
                                                  req_version,
                                                  installed_version)))
        if not have_missing:
            print('    (none)')


def print_help():
    import os
    thisdir = os.path.abspath(os.path.dirname(__file__))

    # import all available commands
    for fname in os.listdir(os.path.join(thisdir)):
        name, ext = os.path.splitext(fname)
        if not ext == '.py':
            continue
        try:
            __import__('icbuild.commands.%s' % name)
        except ImportError:
            pass

    uprint('JHBuild commands are:')
    commands = [(x.name, x.doc) for x in get_commands().values()]
    commands.sort()
    for name, description in commands:
        uprint('  %-15s %s' % (name, description))
    print
    uprint('For more information run "icbuild <command> --help"')

# handle registration of new commands
_commands = {}
def register_command(command_class):
    _commands[command_class.name] = command_class

# special help command, never run
class cmd_help(Command):
    doc = 'Information about available JHBuild commands'

    name = 'help'
    usage_args = ''

    def run(self, config, options, args, help=None):
        if help:
            return help()

register_command(cmd_help)


def get_commands():
    return _commands

def run(command, config, args, help):
    # if the command hasn't been registered, load a module by the same name
    if command not in _commands:
        try:
            __import__('icbuild.commands.%s' % command)
        except ImportError:
            pass
    if command not in _commands:
        import icbuild.moduleset
        module_set = icbuild.moduleset.load(config)
        try:
            module_set.get_module(command)
            raise FatalError('no such command (did you mean "icbuild build %s"?)' % command)
        except KeyError:
            raise FatalError('no such command (did you mean "icbuild run %s"?)' % command)

    command_class = _commands[command]

    cmd = command_class()
    return cmd.execute(config, args, help)


from icbuild.commands import base
