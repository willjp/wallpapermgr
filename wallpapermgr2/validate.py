#!/usr/bin/env python
# builtin
from __future__ import absolute_import, division, print_function
# external
# internal


def dictkeys(varname, d, reqd_keys, avail_keys=None, types=None):

    if avail_keys is None:
        avail_keys = set()

    extra_keys = set(d.keys()) - (set(reqd_keys) + set(avail_keys))
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
            if not isinstance(d[key], types[key]):
                raise TypeError(
                    'expected `d[key]` to be type: {}'.format(repr(types[key]))
                )


