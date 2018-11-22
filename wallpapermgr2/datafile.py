#!/usr/bin/env python
# builtin
from __future__ import absolute_import, division, print_function
import functools
import os
import subprocess
import random
import tarfile
import json
# external
from six.moves import input
import xdg.BaseDirectory
import six
import yaml
import git
# internal
from wallpapermgr2 import validate


text_types = (bytes, str)


class PidFile(object):
    """ ContextManager that writes current processid to a pidfile.
    """
    def __init__(self, filepath=None):
        if filepath is None:
            filedir = xdg.BaseDirectory.save_data_path('wallpapermgr')
            filepath = '{}/wallpapermgr.pid'.format(filedir)

        self.__filepath = filepath

    @property
    def filepath(self):
        return self.__filepath

    def __enter__(self):
        pid = os.getpid()

        # confirm not already running
        pidfile_pid = self.is_active()
        if pidfile_pid:
            if pidfile_pid == pid:
                return self
            else:
                raise RuntimeError(
                    'Another wallpapermgr process is running. (pid {})'.format(
                        pidfile_pid
                    )
                )

        # write pidfile
        else:
            self.open(pid)
            return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        if all([exc_type, exc_val, exc_tb]):
            six.reraise(exc_type, exc_val, exc_tb)

    def is_active(self):
        if os.path.isfile(self.filepath):
            with open(self.filepath, 'r') as fd:
                pid = int(fd.read())

            if pid_exists(pid):
                return pid

        return False

    def open(self, pid=None):
        if pid is None:
            pid = os.getpid()

        with open(self.filepath, 'w') as fd:
            fd.write(str(pid))

    def close(self):
        if os.path.isfile(self.filepath):
            os.remove(self.filepath)


def pid_exists(pid):
    """ Returns True/False if pid exists.
    """
    try:
        os.kill(pid, 0)
    except(OSError):
        return False
    return True


class Config(object):
    """ Object representing the configfile.

    Example:

        .. code-block:: yaml

            archives:

               normal_walls:
                  apply_method: feh
                  archive:      ~/Downloads/wallpapers/normal_walls.tar
                  gitroot:      ~/Downloads/wallpapers
                  gitsource:    ssh://yourgit:/gitrepos/wallpapers
                  desc:         "wallpapers with a normal aspect ratio (ex: 16:9)"
                  conditions:
                     is_default: True

               wide_walls:
                  apply_method: feh
                  archive:      ~/Downloads/wallpapers/wide_walls.tar
                  gitroot:      ~/Downloads/wallpapers
                  gitsource:    ssh://yourgit:/gitrepos/wallpapers
                  desc:         "wallpapers for wide-multimonitor aspect ratios (ex: 32:9, 48:9)"
                  conditions:
                     is_xineramawide: True

    """
    def __init__(self, filepath=None):
        if filepath is None:
            filedir = xdg.BaseDirectory.save_config_path('wallpapermgr')
            filepath = '{}/config2.yml'.format(filedir)

        self.__filepath = filepath
        self.data = {}

    @property
    def filepath(self):
        return self.__filepath

    def read(self, force=False):
        if self.data and not force:
            return self.data

        with open(self.filepath, 'r') as fd:
            data = yaml.safe_load(fd.read())

        self.validate(data)
        self.data = data

        return self.data

    def write(self, data):
        self.validate(data)
        with open(self.filepath, 'r') as fd:
            fd.write(data)

    def validate(self, data):
        validate.dictkeys(
            'data', data, reqd_keys=set(['archives', 'choose_archive_cmd'])
        )

        # validate choose_archive
        if not isinstance(data['choose_archive_cmd'], list):
            raise TypeError(
                'expected data["choose_archive_cmd"] to be a list.'
            )

        # validate archives
        for name in data['archives']:
            archive = data['archives'][name]

            def _validate_abspath(key, val):
                validate.abspath(
                    'data["archives"]["{}"]["{}"]'.format(name, key),
                    archive[key],
                )

            validate.dictkeys(
                'data["archives"]["{}"]'.format(name),
                archive,
                reqd_keys=(
                    'apply_method',
                    'archive',
                    'gitroot',
                    'gitsource',
                    'desc',
                ),
                types={
                    'apply_method': text_types,
                    'archive':      text_types,
                    'gitroot':      [type(None)] + list(text_types),
                    'gitsource':    [type(None)] + list(text_types),
                    'desc':         text_types,
                },
                validators={
                    'apply_method': self._validate_apply_method,
                    'archive': functools.partial(_validate_abspath, 'archive'),
                    'gitroot': functools.partial(_validate_abspath, 'gitroot'),
                }
            )

    def determine_archive(self, force_read=False):
        data = self.read(force_read)

        cmds = data['choose_archive_cmd']
        stdout = subprocess.check_output(cmds, universal_newlines=True)
        archive = stdout.split('\n')[0]

        if archive not in data['archives']:
            raise RuntimeError('archive "{}" does not exist'.format(archive))

        return archive

    def archives(self):
        data = self.read()
        return sorted(list(data['archives'].keys()))

    def archive_path(self, archive):
        data = self.read()
        path = data['archives'][archive]['archive']
        return os.path.expanduser(path)

    def _validate_apply_method(self, applymethod):
        pass


class Archive(object):
    """ Object representing a tar-archive of wallpapers in a git repo.
    """
    def __init__(self, archive, config=None):
        """ Constructor.

        Args:
            archive (str): ``(ex: 'wide_wallpapers')``
                name of archive (in config).
        """
        if config is None:
            config = Config()

        self.__config = config
        if archive:
            self.load(archive)

    @property
    def config(self):
        return self.__config

    @property
    def filepath(self):
        return self.__filepath

    @property
    def gitroot(self):
        return self.__gitroot

    @property
    def gitsource(self):
        return self.__gitsource

    def load(self, archive):
        data = self.config.read()
        if archive not in data['archives']:
            raise RuntimeError(
                'no archive exists in config with name "{}"'.format(archive)
            )

        self.__filepath = os.path.expanduser(data['archives'][archive]['archive'])
        self.__gitroot = os.path.expanduser(data['archives'][archive]['gitroot'])
        self.__gitsource = os.path.expanduser(data['archives'][archive]['gitsource'])

    def _validate_loaded(self):
        if any([not x for x in (self.filepath, self.gitroot, self.gitsource)]):
            raise RuntimeError(
                'this archive obj has not been loaded with an archive'
            )

    def _validate_modifyable(self):
        self._validate_loaded()

        # if repo not exists, want to to clone? otherwise reject
        if not os.path.exists('{}/.git'.format(self.gitroot)):
            if not self.request_clone():
                raise RuntimeError(
                    'Aborted - will not modify archive without '
                    'git project present'
                )

    def add(self, filepaths):
        self._validate_modifyable()

        # confirm all files exist
        for filepath in filepaths:
            if not os.path.isfile(filepath):
                raise RuntimeError('no such file: "{}"'.format(filepath))

        # write to archive
        with tarfile.open(self.filepath, 'a') as archive_fd:
            for filepath in filepaths:
                archive_fd.add(filepath, os.path.basename(filepath))

    def remove(self, filepaths):
        self._validate_modifyable()

        raise NotImplementedError(
            'todo - will need to extract all, '
            'create new archive, '
            'then replace orig'
        )

    def request_clone(self):
        """
        Returns:
            bool: whether clone was performed/successful.
        """
        self._validate_loaded()

        # dir if repo, file if submodule
        if os.path.exists('{}/.git'.format(self.gitroot)):
            return True

        while True:
            reply = input(
                'archive repo does not exist on disk, '
                'would you like to clone it? (y/n)'
            ).lower()
            if reply in ('y', 'n'):
                break
        if reply != 'y':
            return False

        return self.clone()

        # confirm all files exist
        for filepath in filepaths:
            if not os.path.isfile(filepath):
                raise RuntimeError('no such file: "{}"'.format(filepath))

        # write to archive
        with tarfile.open(self.filepath, 'a') as archive_fd:
            for filepath in filepaths:
                archive_fd.add(filepath, os.path.basename(filepath))

    def clone(self):
        self._validate_loaded()

        # dir if repo, file if submodule
        if os.path.exists('{}/.git'.format(self.gitroot)):
            return True

        repo = git.Repo.init(self.gitroot)
        repo.create_remote('origin', self.gitsource)
        return self.pull()

    def pull(self):
        self._validate_loaded()

        # if not exist, ask if wants to clone
        if not os.path.exists('{}/.git'.format(self.gitroot)):
            return self.request_clone()

        repo = git.Repo(self.gitroot)
        if repo.is_dirty(untracked_files=True):
            raise RuntimeError(
                (
                    'cannot git-pull, '
                    'repo contains untracked-files/changes: '
                    '"{}"'
                ).format(self.gitroot)
            )

        remote = repo.remote()
        if not remote.exists():
            raise RuntimeError(
                'git source does not exist: {}'.format(self.gitsource)
            )
        remote.pull('master')
        return True

    def push(self):
        self._validate_loaded()
        repo = git.Repo(self.gitroot)
        remote = repo.remote()
        if not remote.exists():
            raise RuntimeError(
                'git source does not exist: {}'.format(self.gitsource)
            )
        remote.push()


class Data(object):
    """ Object representing the wallpapermgr datafile (wallpaper order).
    """
    def __init__(self, filepath=None):
        if filepath is None:
            filedir = xdg.BaseDirectory.save_data_path('wallpapermgr')
            filepath = '{}/data.json'.format(filedir)

        self.__filepath = filepath
        self.data = {}

    @property
    def filepath(self):
        return self.__filepath

    def read(self, force=False):
        if self.data and not force:
            return self.data

        data = {'archives': {}}
        if os.path.isfile(self.filepath):
            with open(self.filepath, 'r') as fd:
                fileconts = fd.read()
                if fileconts:
                    data = json.loads(fileconts)

        self.validate(data)
        self.data = data

        return self.data

    def write(self, data=None):
        if data is None:
            data = self.read()

        self.validate(data)
        with open(self.filepath, 'w') as fd:
            fd.write(json.dumps(data))
        self.data = data

    def validate(self, data):
        validate.dictkeys('data', data, reqd_keys=set(['archives']))

        for name in data['archives']:
            validate.dictkeys(
                varname='data["archives"]["{}"]'.format(name),
                d=data['archives'][name],
                reqd_keys=('last_index', 'sequence'),
                types={'last_index': int, 'sequence': list},
            )

    def index(self, archive):
        """
        Args:
            archive (str):  ``(ex: 'wide_wallpapers')``
                name of archive
        """
        data = self.read()
        if not data:
            return 0

        if archive not in data['archives']:
            self.reload_archive()
            return 0

        return data['archives'][archive]['last_index']

    def set_index(self, archive, index):
        data = self.read()
        self.data['archives'][archive]['last_index'] = index

    def wallpaper(self, archive, index):
        data = self.read()
        return data['archives'][archive]['sequence'][index]

    def archive_len(self, archive):
        data = self.read()

        if archive not in data['archives']:
            self.reload_archives()

        return len(data['archives'][archive]['sequence'])

    def shuffle(self, archive=None):
        """ Randomize the wallpaper order.
        """
        data = self.read()

        def shuffle(archive):
            sequence = data['archive'][archive]['squence']
            sequence = random.shuffle(sequence)
            data['archives'][archive]['sequence'] = sequence
            return data

        if archive is not None:
            data = shuffle(archive)
        else:
            for archive in data['archives']:
                data = shuffle(archive)

        self.validate(data)
        self.write(data)
        self.data = data

    def reload_archive(self, config=None, archive=None):
        """ Re-Reads archive members, shuffles order.
        """
        if config is None:
            config = Config()

        data = self.read()
        cfgdata = config.read()

        def load_archive_contents(archive):
            path = config.archive_path(archive)
            with tarfile.open(path, 'r') as archive_fd:
                contents = list(archive_fd.getnames())
                random.shuffle(contents)
                data['archives'][archive] = {
                    'last_index': 0,
                    'sequence': contents,
                }
            return data

        if archive is not None:
            data = load_archive_contents(archive)
        else:
            for archive in cfgdata['archives']:
                data = load_archive_contents(archive)

        self.validate(data)
        self.write(data)
        self.data = data


def print_archive_list(config=None):
    if config is None:
        config = Config()

    printlines = ['']
    data = config.read()
    fmt = '{name:>15} {sep}  {desc:<70}   {path}'

    for header in (
        dict(name='Archive Name', sep=' ', desc='Description', path='Location'),
        dict(name='============', sep=' ', desc='===========', path='========'),
    ):
        printlines.append(fmt.format(**header))

    if 'archives' in data:
        for archive in data['archives']:
            archive_data = data['archives'][archive]
            line_data = dict(
                name=archive,
                sep='-',
                desc=archive_data['desc'],
                path=archive_data['archive'],
            )
            printlines.append(fmt.format(**line_data))
    printlines.append('')

    print('\n'.join(printlines))

