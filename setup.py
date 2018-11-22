#!/usr/bin/env python
# builtin
# external
import setuptools
import os
# internal
import wallpapermgr2


__version__ = wallpapermgr2.__version__


def get_man_path():
    paths = ('/usr/man/man1',)
    for path in paths:
        if os.path.isdir(path):
            return path
    raise RuntimeError(
        'Unable to determine manpath'
    )


def get_zsh_completionpath():
    paths = (
        '/usr/local/share/zsh/functions/Completion/Unix',
        '/usr/share/zsh/functions/Completion/Unix',
    )
    for path in paths:
        if os.path.isdir(path):
            return path
    raise RuntimeError(
        'No fpath could be found for installation in: %s' % repr(paths))


setuptools.setup(
    name='wallpapermgr',
    version=__version__,
    author='Will Pittman',
    url='https://github.com/willjp/wallpapermgr',
    license='BSD',
    keywords='wallpaper synchronize sync',
    packages=setuptools.find_packages(),
    entry_points={
        'console_scripts': [
            'wallmgr = wallpapermgr2.cli:CommandlineInterface.show',
        ]
    },
    data_files=[
        (get_zsh_completionpath(), ['data/autocomplete.zsh/_wallmgr']),
        (get_man_path(), ['data/man/wallmgr.1']),
    ],
    install_requires=[
        'GitPython',
        'PyYaml',
        'setuptools',
        'six',
        'supercli>=0.0.a2',
    ],
    classifiers=[
        # windows not currently supported, using unix-domain-sockets
        'Operating System :: POSIX :: Linux',
        'Operating System :: POSIX :: BSD',
    ]
)
