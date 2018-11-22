#!/usr/bin/env python
# builtin
# external
import setuptools
# internal
import wallpapermgr2


__version__ = wallpapermgr2.__version__


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
    # TODO: zsh completer
    # TODO: man-page
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
