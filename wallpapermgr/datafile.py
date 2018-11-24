#!/usr/bin/env python
# builtin
from __future__ import absolute_import, division, print_function
import functools
import json
import numbers
import os
import random
import string
import subprocess
import tarfile
# external
from six.moves import input
import xdg.BaseDirectory
import six
import yaml
import git
# internal
from wallpapermgr import validate


text_types = (bytes, str)


class PidFile(object):
    """ ContextManager that writes current processid to a pidfile.

    Example:

        pidfiles contan a single line with a pid.
        No newlines.

        ::
            5431

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
            'data', data,
            reqd_keys={
                'archives',
                'choose_archive_cmd',
                'show_wallpaper_cmd',
            },
            avail_keys={'change_interval', },
        )

        # validate top-level keys
        if not isinstance(data['choose_archive_cmd'], list):
            raise TypeError(
                'expected data["choose_archive_cmd"] to be a list.'
            )
        if not isinstance(data['show_wallpaper_cmd'], list):
            raise TypeError(
                'expected data["show_wallpaper_cmd"] to be a list.'
            )
        if 'change_interval' in data:
            if not isinstance(data['change_interval'], numbers.Number):
                raise TypeError(
                    ('expected data["change_interval"] to be a number.'
                     'Received {}').format(data['change_interval'])
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
                    'archive',
                    'gitroot',
                    'gitsource',
                    'desc',
                ),
                types={
                    'archive':      text_types,
                    'gitroot':      [type(None)] + list(text_types),
                    'gitsource':    [type(None)] + list(text_types),
                    'desc':         text_types,
                },
                validators={
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

    def show_wallpaper_cmd(self, wallpaper):
        """ Adds the wallpaper into user-provided show-wallpaper command.

        Args:
            wallpaper (str): ``(ex: '/path/to/wallpaper.png')``
                path to a wallpaper you'd like to display

        Returns:
            list:
                The configured ``show_wallpaper_cmd`` with the
                wallpaper substituted in.

                .. code-block:: python

                    ['feh', '--bg-scale', '/path/to/wallpaper.png']

        """
        data = self.read()
        out_cmds = []

        for arg in data['show_wallpaper_cmd']:
            t = string.Template(arg)
            out_cmds.append(
                t.safe_substitute({'wallpaper': wallpaper})
            )
        return out_cmds

    def archives(self):
        data = self.read()
        return sorted(list(data['archives'].keys()))

    def archive_path(self, archive):
        data = self.read()
        path = data['archives'][archive]['archive']
        return os.path.expanduser(path)


class Archive(object):
    """ Object representing a tar-archive of wallpapers in a git repo.

    Archives contain a flat list of image files. No directories/subdirectories.
    """
    def __init__(self, archive, config=None):
        """ Constructor.

        Args:
            archive (str): ``(ex: 'wide_wallpapers')``
                name of archive (in config).

            config (wallpapermgr.datafile.Config, optional):
                You may reuse a config, if you already have one instantiated.
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

    def add(self, filepaths, commit=True, push=True):
        self._validate_modifyable()

        # confirm all files exist
        for filepath in filepaths:
            if not os.path.isfile(filepath):
                raise RuntimeError('no such file: "{}"'.format(filepath))

        # write to archive
        with tarfile.open(self.filepath, 'a') as archive_fd:
            for filepath in filepaths:
                archive_fd.add(filepath, os.path.basename(filepath))

        # commit/push
        if commit:
            self.commit('add', [os.path.basename(x) for x in filepaths])
        if push:
            self.push()

    def remove(self, filepaths, commit=True, push=True):
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

    def is_submodule(self):
        # check if submodule
        parentdir = os.path.dirname(self.gitroot)
        try:
            repo = git.Repo(parentdir, search_parent_directories=True)
            return repo
        except(git.InvalidGitRepositoryError, git.NoSuchPathError):
            return False

    def clone(self):
        self._validate_loaded()

        # dir if repo, file if submodule
        if os.path.exists('{}/.git'.format(self.gitroot)):
            return True

        # git submodule update --init
        parent_repo = self.is_submodule()
        if parent_repo:
            parent_gitroot = os.path.dirname(parent_repo.git_dir)
            submodule_path = self.gitsource[len(parent_gitroot) + 1:]
            submodule = parent_repo.submodule(submodule_path)
            submodule.update(init=True)
            return True

        # git clone
        else:
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

        print((
            'pulling from {} in {}. \n'
            'Depending on size of repo, this may take several minutes...'
        ).format(self.gitsource, repo.git_dir))
        # not using ``remote.pull('master')`` because:
        #    1. no stdout
        #    2. synchronizing large tarfiles may take a very long time
        #    3. remote.pull() seems to have a timeout
        #
        # remote.pull('master')  # this works, but no stdout! may take long time...

        subprocess.check_call(
            ['git', '-C', os.path.dirname(repo.git_dir), 'pull']
        )
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

    def commit(self, operation, filepaths):
        """ performs a git commit, recording the operation
        and the files it affects.
        """
        self._validate_loaded()
        repo = git.Repo(self.gitroot)

        if not repo.is_dirty(untracked_files=True):
            return

        # add all changes
        repo.git.add(update=True)
        repo.git.commit(
            '-m',
            '{} {}'.format(operation, repr(filepaths)),
            author='wallpapermgr@domain.com'
        )


class Data(object):
    """ Object representing the wallpapermgr datafile (wallpaper order).

    Example:

        .. code-block:: python

            {
                "archives": {
                    "normal_walls": {
                        "last_index": 0,
                        "sequence": [
                            "wallhaven-474183.png",
                            "wallhaven-258640.jpg",
                            "wallhaven-185456.png",
                            ...
                        ]
                    },
                    "wide_walls": {
                        "last_index": 23,
                        "sequence": [
                            "wallhaven-185466.png",
                            "oscarthegrouch.jpg",
                            "wallhaven-134328.jpg"
                            ...
                        ]
                    }
                }
            }

    """
    def __init__(self, filepath=None):
        """ Constructor.

        Args:
            filepath (str, optional):
                If provided, you may use a non-default datafile.
                Otherwise one will be instantiated for you.
        """
        if filepath is None:
            filedir = xdg.BaseDirectory.save_data_path('wallpapermgr')
            filepath = '{}/data.json'.format(filedir)

        self.__filepath = filepath
        self.data = {}

    @property
    def filepath(self):
        """ Returns filepath to this datafile.
        """
        return self.__filepath

    def read(self, force=False, skip_validate=False):
        """ Read the datafile.

        Returns:
            dict: datafile contents. See object example.
        """
        if self.data and not force:
            return self.data

        data = {'archives': {}}
        if os.path.isfile(self.filepath):
            with open(self.filepath, 'r') as fd:
                fileconts = fd.read()
                if fileconts:
                    data = json.loads(fileconts)

        if not skip_validate:
            self.validate(data)
        self.data = data

        return self.data

    def write(self, data=None):
        """ Replace the contents of datatfile with `data` .
        """
        if data is None:
            data = self.read()

        self.validate(data)
        with open(self.filepath, 'w') as fd:
            fd.write(json.dumps(data))
        self.data = data

    def validate(self, data):
        """ Validate the contents of a datafile.
        """
        validate.dictkeys('data', data, reqd_keys=set(['archives']))

        for name in data['archives']:
            validate.dictkeys(
                varname='data["archives"]["{}"]'.format(name),
                d=data['archives'][name],
                reqd_keys=('last_index', 'sequence'),
                types={'last_index': int, 'sequence': list},
            )

            for path in data['archives'][name]['sequence']:
                if any([x in path for x in ('\\', '/')]):
                    raise RuntimeError(
                        'path must be filename only. Received "{}"'.format(path)
                    )

    def index(self, archive):
        """ Returns value of `last_index` in archive.

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
        """ Updates `last_index` key for this archive in the datafile.
        """
        data = self.read()
        data['archives'][archive]['last_index'] = index
        self.data = data

    def wallpaper(self, archive, index):
        """ Returns the path to wallpaper at `index` in archive.
        """
        data = self.read()
        return data['archives'][archive]['sequence'][index]

    def archive_len(self, archive):
        """ Returns number of images contained within an archive.
        """
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

        data = self.read(skip_validate=True)
        cfgdata = config.read()

        def load_archive_contents(archive):
            path = config.archive_path(archive)
            with tarfile.open(path, 'r') as archive_fd:
                contents = list(archive_fd.getnames())
                random.shuffle(contents)
                data['archives'][archive] = {
                    'last_index': 0,
                    'sequence': [
                        p.replace('./', '')
                        for p in contents
                        if p not in ('..', '.')
                    ],
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
    """ Prints all configured archives, descriptions, and paths.
    """
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


