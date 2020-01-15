#!/usr/bin/env python

# Copyright 2020 The Pigweed Authors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
"""Environment setup script for Pigweed.

This script installs everything and writes out a file for the user's shell
to source.

For now, this is valid Python 2 and Python 3. Once we switch to running this
with PyOxidizer it can be upgraded to recent Python 3.
"""

from __future__ import print_function

import argparse
import contextlib
import glob
import os
import subprocess
import sys

import cipd.update
import cipd.wrapper
import host_build.init
import cargo.init
import virtualenv.init


class UnexpectedAction(ValueError):
    pass


# TODO(mohrr) use attrs.
class _Action(object):  # pylint: disable=useless-object-inheritance
    # pylint: disable=redefined-builtin,too-few-public-methods
    def __init__(self, type, name, value, *args, **kwargs):
        pathsep = kwargs.pop('pathsep', os.pathsep)
        super(_Action, self).__init__(*args, **kwargs)
        assert type in ('set', 'prepend', 'append')
        self.type = type
        self.name = name
        self.value = value
        self.pathsep = pathsep


# TODO(mohrr) remove disable=useless-object-inheritance once in Python 3.
# pylint: disable=useless-object-inheritance
class Environment(object):
    """Stores the environment changes necessary for Pigweed.

    These changes can be accessed by writing them to a file for bash-like
    shells to source or by using this as a context manager.
    """
    def __init__(self, *args, **kwargs):
        pathsep = kwargs.pop('pathsep', os.pathsep)
        super(Environment, self).__init__(*args, **kwargs)
        self._actions = []
        self._pathsep = pathsep

    def set(self, name, value):
        self._actions.append(_Action('set', name, value))

    def clear(self, name):
        self._actions.append(_Action('set', name, None))

    def append(self, name, value):
        self._actions.append(_Action('append', name, value))

    def prepend(self, name, value):
        self._actions.append(_Action('prepend', name, value))

    def _action_str(self, action):
        if action.type == 'set':
            if action.value is None:
                fmt = 'unset {name}\n'
            else:
                fmt = '{name}="{value}"\nexport {name}\n'
        elif action.type == 'append':
            fmt = '{name}="${name}{sep}{value}"\nexport {name}\n'
        elif action.type == 'prepend':
            fmt = '{name}="{value}{sep}${name}"\nexport {name}\n'
        else:
            raise UnexpectedAction(action.name)

        return fmt.format(
            name=action.name,
            value=action.value,
            sep=self._pathsep,
        )

    def write(self, outs):
        for action in self._actions:
            outs.write(self._action_str(action))
        outs.write('# This should detect bash and zsh, which have a hash \n'
                   '# command that must be called to get it to forget past \n'
                   '# commands. Without forgetting past commands the $PATH \n'
                   '# changes we made may not be respected.\n')
        outs.write('if [ -n "${BASH:-}" -o -n "${ZSH_VERSION:-}" ] ; then\n')
        outs.write('    hash -r\n')
        outs.write('fi\n')

    @contextlib.contextmanager
    def __call__(self):
        """Set environment as if this was written to a file and sourced."""

        orig_env = os.environ.copy()
        try:
            for action in self._actions:
                if action.type == 'set':
                    if action.value is None:
                        if action.name in os.environ:
                            del os.environ[action.name]
                    else:
                        os.environ[action.name] = action.value
                elif action.type == 'append':
                    os.environ[action.name] = self._pathsep.join(
                        os.environ.get(action.name, ''), action.value)
                elif action.type == 'prepend':
                    os.environ[action.name] = self._pathsep.join(
                        (action.value, os.environ.get(action.name, '')))
                else:
                    raise UnexpectedAction(action.type)
            yield self

        finally:
            for action in self._actions:
                if action.name in orig_env:
                    os.environ[action.name] = orig_env[action.name]
                else:
                    os.environ.pop(action.name, None)


class EnvSetup(object):
    """Run environment setup for Pigweed."""
    def __init__(self, pw_root, cipd_cache_dir, shell_file, *args, **kwargs):
        super(EnvSetup, self).__init__(*args, **kwargs)
        self._env = Environment()
        self._pw_root = pw_root
        self._cipd_cache_dir = cipd_cache_dir
        self._shell_file = shell_file

        if isinstance(self._pw_root, bytes):
            self._pw_root = self._pw_root.decode()

        self._env.set('PW_ROOT', self._pw_root)

    def setup(self):
        steps = [
            ('cipd', self.cipd),
            ('python', self.virtualenv),
            ('host_tools', self.host_build),
            ('cargo', self.cargo),
        ]

        for name, step in steps:
            print('Setting up {}...\n'.format(name), file=sys.stdout)
            step()
            print('\nSetting up {}...done.'.format(name), file=sys.stdout)

        self._env.write(self._shell_file)

    def cipd(self):
        install_dir = os.path.join(self._pw_root, '.cipd')

        cipd_client = cipd.wrapper.init(install_dir)

        ensure_files = glob.glob(
            os.path.join(self._pw_root, 'env_setup', 'cipd', '*.ensure'))
        cipd.update.update(
            cipd=cipd_client,
            root_install_dir=install_dir,
            ensure_files=ensure_files,
            cache_dir=self._cipd_cache_dir,
            env_vars=self._env,
        )

    def virtualenv(self):
        venv_path = os.path.join(self._pw_root, '.python3-env')

        requirements = os.path.join(self._pw_root, 'env_setup', 'virtualenv',
                                    'requirements.txt')

        with self._env():
            # TODO(mohrr) use shutil.which('python3') (Python 3.3+ only).
            cmd = ['python3', '-c', 'import sys; print(sys.executable)']
            python = subprocess.check_output(cmd).strip()

        virtualenv.init.init(
            venv_path=venv_path,
            requirements=[requirements],
            python=python,
            env=self._env,
        )

    def host_build(self):
        host_build.init.init(pw_root=self._pw_root, env=self._env)

    def cargo(self):
        cargo.init.init(pw_root=self._pw_root, env=self._env)


def parse(argv=None):
    parser = argparse.ArgumentParser()

    try:
        pw_root = subprocess.check_output(
            ['git', 'rev-parse', '--show-toplevel']).strip()
    except subprocess.CalledProcessError:
        pw_root = None
    parser.add_argument(
        '--pw-root',
        default=pw_root,
        required=not pw_root,
    )

    parser.add_argument(
        '--cipd-cache-dir',
        default=os.environ.get('CIPD_CACHE_DIR',
                               os.path.expanduser('~/.cipd-cache-dir')),
    )

    parser.add_argument(
        '--shell-file',
        type=argparse.FileType('w'),
        help='Where to write the file for shells to source.',
    )

    return parser.parse_args(argv)


if __name__ == '__main__':
    sys.exit(EnvSetup(**vars(parse())).setup())