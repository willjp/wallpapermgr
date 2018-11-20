#!/usr/bin/env python
# builtin
from __future__ import absolute_import, division, print_function
import os
# external
import xdg.BaseDirectory
import six
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
            filepath = '{}/config.yml'.format(filedir)

        self.__filepath = filepath
        self.data = {}

    @property
    def filepath(self):
        return self.__filepath

    def read(self, force=False):
        if not self.data and not force:
            return self.data

        with open(self.filepath, 'r') as fd:
            data = yaml.safe_load(fd.read())

        self.validate(data)
        self.data = data

        return self.data

    def validate(self, data):
        validate.dictkeys('data', data, reqd_keys=set(['archives']))

        for name in data['archives']:
            archive = data['archives'][name]

            def _validate_abspath(key, val):
                validate.abspath(
                    'data["archives"]["{}"]["{}"]'.format(name, key),
                    archive[key],
                )

            validate.dictkeys(
                'data["archives"]["{}"]'.format(archive),
                data['archives'][archive],
                reqd_keys=(
                    'apply_method',
                    'archive',
                    'gitroot',
                    'gitsource',
                    'desc',
                    'conditions'
                ),
                types={
                    'apply_method': text_types,
                    'archive':      text_types,
                    'gitroot':      [type(None)] + list(text_types),
                    'gitsource':    [type(None)] + list(text_types),
                    'desc':         text_types,
                    'conditions':   (list, tuple),
                },
                validators={
                    'apply_method': self._validate_apply_method,
                    'archive': functools.partial(_validate_abspath, 'archive'),
                    'gitroot': functools.partial(_validate_abspath, 'gitroot'),
                    'conditions':   self._validate_conditions,
                }
            )

    def _validate_apply_method(self, varname, applymethod):
        pass

    def _validate_conditions(self, varname, conditions):
        pass


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
        if not self.data and not force:
            return self.data

        with open(self.filepath, 'r') as fd:
            data = yaml.safe_load(fd.read())

        self.validate(data)
        self.data = data

        return self.data

    def validate(self, data):
        validate.dictkeys('data', data, reqd_keys=set(['archives']))

        for name in data['archives']:
            for path in data['archives'][name]:
                archive = data['archives'][name][path]

                validate.dictkeys(
                    varname='data["archives"]["{}"]["{}"]'.format(name, path),
                    reqd_keys=('last_fileno', 'sequence'),
                    types={'last_fileno': int, 'sequence': list},
                )
