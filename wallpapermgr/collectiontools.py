#!/usr/bin/env python2
"""
Name :          collectiontools.py
Created :       August 31 2016
Author :        Will Pittman
Contact :       willjpittman@gmail.com
________________________________________________________________________________
Description :   A collection of tools for working with... collections...
________________________________________________________________________________
"""
from   __future__    import unicode_literals


def has_items( collection, items ):
    """
    Returns True if 'collection' contains all of the items in the list 'items'
    """

    ## Validation
    if not hasattr( collection, '__iter__' ):
        raise TypeError('collection must be iterable: %s' % repr(collection))

    if not hasattr( items, '__iter__' ):
        raise TypeError('items must be iterable: %s' % repr(items))



    ## Check
    satisfied_items = []

    for item in items:
        if item in collection:
            satisfied_items.append(item)
        else:
            return False

    if len(satisfied_items) == len(items):
        return True

    return False





