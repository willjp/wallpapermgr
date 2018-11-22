#!/usr/bin/env python2
"""
Name :          wallpapermgr/filedata.py
Created :       August 31 2016
Author :        Will Pittman
Contact :       willjpittman@gmail.com
________________________________________________________________________________
Description :   lowerlevel operations on the datafile.
________________________________________________________________________________
"""
# builtin
from __future__ import unicode_literals
from __future__ import absolute_import
import os
import logging
import json
# external
import yaml

logger = logging.getLogger(__name__)


class DataFileIO(object):
    """
    Object that represents the JSON datafile ``~/.config/wallpapermgr/data.json``
    that contains.

        * archive-path
        * last-displayed image
        * wallpapers in archive

    """

    def __init__(self, datafile):
        self.datafile = datafile
        self.data = None  # contents of the datafile

    def read(self):
        """
        Reads datafile, and enforces the correct datatypes
        """
        data = self._read_datafile()
        data = self._verify_data(data)
        data = self._set_datatypes(data)
        self.data = data
        return data

    def _read_datafile(self):
        """
        Reads the raw contents of the datafile.
        """
        datafile = self.datafile

        if os.path.isfile(datafile):
            with open(datafile, 'r') as stream:
                data = json.load(stream)
        else:
            data = {}

        logger.debug('Storing program data in: "%s"' % datafile)
        return data

    def _verify_data(self, data):
        """
        If datafile format changes, not yet written, or otherwise invalid,
        corrects file (and writes) so that script can continue to use it.

        The bare minimum for the configfile is currently:
            {
                archives:{}
            }
        """
        needs_write = False
        datafile = self.datafile

        if not os.path.isdir(os.path.dirname(datafile)):
            logger.debug('Creating directory: "%s"' %
                         os.path.dirname(datafile))
            os.makedirs(os.path.dirname(datafile))
            needs_write = True

        if not 'archives' in data:
            data['archives'] = {}
            needs_write = True

        if needs_write:
            logger.debug('Creating/Updating datafile: "%s"' % datafile)
            with open(datafile, 'w') as fw:
                fw.write(json.dumps(data, indent=2))

        self.data = data
        return data

    def _set_datatypes(self, data):
        """
        JSON datatypes are not exactly analogous to python's datatypes.
        We also do some additional parsing here '~'=='$HOME' etc.
        """

        #!NOTE: I believe this is the wrong datastrucutre. oops.

        # parse environment variables, and '~' in all filepaths
        if data['archives']:
            for key in ('gitroot', 'gitsource', 'archive'):
                if key in data['archives']:
                    data['archives'][key] = data['archives'][key].replace(
                        '~', os.environ['HOME'])
                    data['archives'][key] = data['archives'][key].format(
                        **os.environ)

        return data


class ConfigFileIO(object):
    def __init__(self, configfile):
        self.configfile = configfile
        self.config = None

    def read(self):
        config = self._read_configfile()
        config = self._validate_config(config)
        config = self._set_datatypes(config)
        self.config = config
        return config

    def _read_configfile(self):

        configfile = self.configfile
        if not os.path.isfile(configfile):
            raise RuntimeError('ConfigFile is expected at "%s"' % configfile)

        logger.debug('Reading config: "%s"' % configfile)
        with open(configfile, 'r') as stream:
            config = yaml.load(stream)

        return config

    def _validate_config(self, config):
        # every archive should have
        #  apply_method
        #  archive
        #  conditions
        #  (at least one condition)

        # at least one archive should have condition: default
        return config

    def _set_datatypes(self, config):
        """
        Expands environment variables,
        and makes any required adjustments between datatypes
        between json and python/what program needs.
        """

        if config['archives']:
            for archive_name in config['archives']:
                for key in ('gitroot', 'gitsource', 'archive'):
                    if key in config['archives'][archive_name]:
                        config['archives'][archive_name][key] = config['archives'][archive_name][key].replace(
                            '~', os.environ['HOME'])
                        config['archives'][archive_name][key] = config['archives'][archive_name][key].format(
                            **os.environ)

        return config


if __name__ == '__main__':
    pass
