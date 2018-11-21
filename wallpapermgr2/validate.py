#!/usr/bin/env python
# builtin
from __future__ import absolute_import, division, print_function
import os
# external
# internal


def abspath(varname, val):
    if not os.path.isabs(val):
        return '`{}` expects absolute path. received {}'.format(varname, val)


def dictkeys(varname, d, reqd_keys, avail_keys=None, types=None, validators=None):

    if avail_keys is None:
        avail_keys = set()

    avail_keys.update(reqd_keys)

    extra_keys = set(d.keys()) - avail_keys
    missing_keys = set(reqd_keys) - set(d.keys())

    if extra_keys:
        raise RuntimeError(
            '`{}` contains extra keys: {}'.format(varname, repr(extra_keys))
        )

    if missing_keys:
        raise RuntimeError(
            '`{}` is missing keys: {}'.format(varname, repr(extra_keys))
        )

    if types is not None:
        for key in types:
            keytypes = types[key]
            if isinstance(keytypes, (list, set)):
                keytypes = tuple(keytypes)
            if not isinstance(d[key], keytypes):
                raise TypeError(
                    'expected `d[key]` to be type: {}'.format(repr(types[key]))
                )

    if validators is not None:
        for key in validators:
            if key in d:
                error = validators[key](d[key])
                if error:
                    raise TypeError(error)
