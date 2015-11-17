# icbuild - a tool to ease building collections of source packages
# Copyright (C) 2001-2006  James Henstridge
# Copyright (C) 2007-2008  Frederic Peters
# Copyright (C) 2014 Canonical Limited
#
#   config.py: configuration file parser
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
import os.path
import re
import sys
import traceback
import time
import types
import logging

from icbuild.errors import FatalError

if sys.platform.startswith('win'):
    # For munging paths for MSYS's benefit
    import icbuild.utils.subprocess_win32

__all__ = [ 'Config' ]

_defaults_file = os.path.join(os.path.dirname(__file__), 'defaults.icbuildrc')

_known_keys = [ 'moduleset', 'modules', 'skip', 'tags', 'prefix',
                'partial_build', 'checkoutroot', 'buildroot', 'top_builddir',
                'msys2dir',
                'makeargs', 'jobs',
                'repos', 'branches',
                'builddir_pattern', 'module_autogenargs', 'module_makeargs',
                'interact', 'buildscript', 'nonetwork', 'nobuild',
                'noinstall',
                'module_makecheck',
                'sticky_date', 'tarballdir',
                'checkout_mode',
                'copy_dir', 'module_checkout_mode', 'build_policy',
                'min_age',
                'quiet_mode',
                'progress_bar', 'module_extra_env',
                'use_local_modulesets', 'ignore_suggests', 'modulesets_dir',
                'build_targets', 'cmakeargs', 'module_cmakeargs',
                'print_command_pattern',
                'help_website', 'conditions', 'extra_prefixes',
                'cacheroot', 'exit_on_error'
              ]

env_prepends = {}
def prependpath(envvar, path):
    env_prepends.setdefault(envvar, []).append(path)

def parse_relative_time(s):
    m = re.match(r'(\d+) *([smhdw])', s.lower())
    if m:
        coeffs = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w':7*86400}
        return float(m.group(1)) * coeffs[m.group(2)]
    else:
        raise ValueError

def modify_conditions(conditions, conditions_modifiers):
    for flag in conditions_modifiers:
        for mod in flag.split(','):
            if mod.startswith('+'):
                conditions.add(mod[1:])
            elif mod.startswith('-'):
                conditions.discard(mod[1:])
            else:
                raise FatalError("Invalid condition set modifier: '%s'.  Must start with '+' or '-'." % mod)

class Config:
    _orig_environ = None

    def __init__(self, filename, conditions_modifiers):
        self._config = {
            '__file__': _defaults_file,
            'prependpath':  prependpath,
            'include': self.include,
            }

        if not self._orig_environ:
            self.__dict__['_orig_environ'] = os.environ.copy()
        os.environ['UNMANGLED_PATH'] = os.environ.get('PATH', '')

        env_prepends.clear()
        try:
            exec(compile(open(_defaults_file, "rb").read(), _defaults_file, 'exec'), self._config)
        except:
            traceback.print_exc()
            raise FatalError('could not load config defaults')

        config_file = os.path.expanduser('~/icbuild/icbuildrc')

        if filename:
            if not os.path.exists(filename):
                raise FatalError('could not load config file, %s is missing' % filename)
        else:
            if os.path.exists(config_file):
                filename = config_file

        if filename:
            self._config['__file__'] = filename
            self.filename = filename
        else:
            self._config['__file__'] = config_file
            self.filename = config_file

        # we might need to redo this process on config reloads, so save these
        self.saved_conditions_modifiers = conditions_modifiers

        self._config['conditions'] = conditions_modifiers
        self.load(filename)
        modify_conditions(self.conditions, conditions_modifiers)

        self.create_directories()

        self.update_build_targets()

    def reload(self):
        os.environ = self._orig_environ.copy()
        self.__init__(filename=self._config.get('__file__'), conditions_modifiers=self.saved_conditions_modifiers)
        self.set_from_cmdline_options(options=None)

    def include(self, filename):
        '''Read configuration variables from a file.'''
        try:
            exec(compile(open(filename, "rb").read(), filename, 'exec'), self._config)
        except:
            traceback.print_exc()
            raise FatalError('Could not include config file (%s)' % filename)

    def load(self, filename=None):
        config = self._config
        if filename:
            try:
                exec(compile(open(filename, "rb").read(), filename, 'exec'), config)
            except Exception as e:
                if isinstance(e, FatalError):
                    # raise FatalErrors back, as it means an error in include()
                    # and it will print a traceback, and provide a meaningful
                    # message.
                    raise e
                traceback.print_exc()
                raise FatalError('could not load config file')

        if not config.get('quiet_mode'):
            unknown_keys = []
            for k in config.keys():
                if k[0] == '_':
                    continue
                if type(config[k]) in (types.ModuleType, types.FunctionType, types.MethodType):
                    continue
                unknown_keys.append(k)
            if unknown_keys:
                logging.info(
                        'unknown keys defined in configuration file: %s' % \
                        ', '.join(unknown_keys))

        for path_key in ('checkoutroot', 'buildroot', 'top_builddir',
                         'tarballdir', 'copy_dir',
                         'modulesets_dir',
                         'prefix'):
            if config.get(path_key):
                config[path_key] = os.path.expanduser(config[path_key])

        # copy known config keys to attributes on the instance
        for name in _known_keys:
            setattr(self, name, config[name])

        # default tarballdir to checkoutroot
        if not self.tarballdir: self.tarballdir = self.checkoutroot

        # Ensure top_builddir is absolute
        if not os.path.isabs(self.top_builddir):
            self.top_builddir = os.path.join(self.prefix, self.top_builddir)

        # check possible checkout_mode values
        seen_copy_mode = (self.checkout_mode == 'copy')
        possible_checkout_modes = ('update', 'clobber', 'export', 'copy')
        if self.checkout_mode not in possible_checkout_modes:
            raise FatalError('invalid checkout mode')
        for module, checkout_mode in self.module_checkout_mode.items():
            seen_copy_mode = seen_copy_mode or (checkout_mode == 'copy')
            if checkout_mode not in possible_checkout_modes:
                raise FatalError('invalid checkout mode (module: %s)' % module)
        if seen_copy_mode and not self.copy_dir:
            raise FatalError('copy mode requires copy_dir to be set')

        if not os.path.exists(self.modulesets_dir):
            if self.use_local_modulesets:
                logging.warning(
                        'modulesets directory (%s) not found, '
                        'disabling use_local_modulesets' % self.modulesets_dir)
                self.use_local_modulesets = False
            self.modulesets_dir = None

        if self.buildroot and not os.path.isabs(self.buildroot):
            raise FatalError('%s must be an absolute path' % 'buildroot')
        if not os.path.isabs(self.checkoutroot):
            raise FatalError('%s must be an absolute path' % 'checkoutroot')
        if not os.path.isabs(self.prefix):
            raise FatalError('%s must be an absolute path' % 'prefix')
        if not os.path.isabs(self.tarballdir):
            raise FatalError('%s must be an absolute path' % 'tarballdir')

    def get_original_environment(self):
        return self._orig_environ

    def create_directories(self):
        if not os.path.exists(self.prefix):
            try:
                os.makedirs(self.prefix)
            except:
                raise FatalError('install prefix (%s) can not be created' % self.prefix)

        if not os.path.exists(self.top_builddir):
            try:
                os.makedirs(self.top_builddir)
            except OSError:
                raise FatalError(
                        'working directory (%s) can not be created' % self.top_builddir)

    def update_build_targets(self):
        # update build targets according to old flags
        if self.nobuild:
            # nobuild actually means "checkout"
            for phase in ('configure', 'build', 'check', 'clean', 'install'):
                if phase in self.build_targets:
                    self.build_targets.remove(phase)
            self.build_targets.append('checkout')

    def set_from_cmdline_options(self, options=None):
        if options is None:
            options = self.cmdline_options
        else:
            self.cmdline_options = options
        if hasattr(options, 'clean') and (
                options.clean and not 'clean' in self.build_targets):
            self.build_targets.insert(0, 'clean')
        if hasattr(options, 'nonetwork') and options.nonetwork:
            self.nonetwork = True
        if hasattr(options, 'skip'):
            for item in options.skip:
                self.skip += item.split(',')
        if hasattr(options, 'quiet') and options.quiet:
            self.quiet_mode = True
        if hasattr(options, 'force_policy') and options.force_policy:
            self.build_policy = 'all'
        if hasattr(options, 'arch'):
            self.arch = options.arch

    def __setattr__(self, k, v):
        '''Override __setattr__ for additional checks on some options.'''
        if k == 'quiet_mode' and v:
            try:
                import curses
                logging.getLogger().setLevel(logging.ERROR)
            except ImportError:
                logging.warning(
                        'quiet mode has been disabled because the Python curses module is missing.')
                v = False

        self.__dict__[k] = v

