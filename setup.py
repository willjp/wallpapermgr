#!/usr/bin/env python
from   distutils.core import setup, Extension
import setuptools
import os
import sys
import re
import shutil

def get_pkginfo():
    cwd     = os.path.realpath(__file__).replace('\\','/')
    pkgpath = os.path.dirname( cwd ).replace('\\','/')
    pkgname = cwd.split('/')[-2]
    if '-' in pkgname:
        pkgname = '-'.join( pkgname.split('-')[:-1] )
    return (pkgpath,pkgname)

def get_version():
    """
    obtains __version__ value from package's __init__.py
    """
    (pkgpath,pkgname) = get_pkginfo()
    pkginit = '{pkgpath}/{pkgname}/__init__.py'.format(**locals())

    if not os.path.isfile( pkginit ):
        raise IOError('expected __init___ file not found at: %s' % pkginit)


    with open( pkginit, 'r' ) as fr:
        for line in fr:
            if re.match( '^[ \t]*__version__[ \t]*=.*?$', line ):
                version = re.sub( '^[ \t]*__version__[ \t]*=[ \t]*', '', line )
                version = version.strip()
                version = version.replace('"','')
                version = version.replace("'",'')
                return version
    raise RuntimeError('unable to find a value for __version__ in : %s' % pkginit )

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

def get_zsh_completionpath():
    paths = (
        '/usr/local/share/zsh/functions/Completion/Unix',
        '/usr/share/zsh/functions/Completion/Unix',
        )
    for path in paths:
        if os.path.isdir( path ):
            return path
    raise RuntimeError('No fpath could be found for installation in: %s' % repr(paths) )



## get info
(pkgpath,pkgname) = get_pkginfo()

setup(
    name     = 'wallpapermgr',
    version  = get_version(),
    author   = 'Will Pittman',
    url      = 'https://github.com/willjp/wallpapermgr',
    license  = 'BSD',

    description      = 'Rule-Based management/display of wallpaper collections using git to synchronize collections between computers',
    long_description = read('README.rst'.format(**locals())),

    keywords         = 'supercli cli color colour argparse logging interface',
    install_requires = ['PyYaml','six','GitPython','daemon'],
    packages         = setuptools.find_packages( exclude=['tests*','images*'] ),
    py_modules       = ['wallpapermgr'],
    scripts          = ['bin/wallmgr'],
    zip_safe     = False, ## zip safe, but I'd prefer people can browse source
    package_data = {
        ''         : [
                        '*.txt',
                        '*.rst',
                        'apply_methods/*',
                        'archive_conditions/*'
                    ],
        'supercli' : ['examples/*'],
    },
    data_files = [
        ( get_zsh_completionpath() + '/_wallmgr', ['bin/_wallmgr'] ),
        ],

    classifiers      = [
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',

        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Operating System :: POSIX :: BSD',
    ],
)



