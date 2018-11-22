#!/usr/bin/env python2
"""
Name :          excepts.py
Created :       August 28 2016
Author :        Will Pittman
Contact :       willjpittman@gmail.com
________________________________________________________________________________
Description :   List of all custom-exceptions used by module.
________________________________________________________________________________
"""
from __future__ import unicode_literals
from __future__ import absolute_import


class ConfigKeyMissing(Exception):
    """ When reading user-config, if a required key is missing, raise this exception.  """
    pass


class InvalidJSONReturn(Exception):
    """ Improperly formatted JSON, missing key, etc.  """
    pass
