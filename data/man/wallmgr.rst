
NAME
====

wallmgr - Configurable tool to manage display/synchronization of wallpapers between computers.


SYNOPSIS
========

**wallmgr** 

::

    [-h|--help] [-v|--verbose] [-vv|--very-verbose]
    [ls] [next] [prev] [reload] [stop]
    [archive name [--add] [--remove] [--pull] [--push]]


DESCRIPTION
===========

Wallpapers are added to tar archives, which get synchronized between computers using git.
You can define as many different archives as you like, they may share a git repository 
(but do not need to).

This program is just glue, hopefully reducing the amount of work you need to do 
to setup machines, and grab your wallpapers.

OPTIONS
=======

**ls**
    List all configured archives

**next**
    Show next wallpaper from active archive. Start server if not running.

**prev**
    Show previous wallpaper from active archive. Start server if not running.

**reload**
    Reload config, re-index archives. If server is alrady running,
    re-load config/data within server.

**stop**
    Request the server stops.

**archive [archive]**
    If used without options below, changes current archive wallpapers
    are being displayed from. Otherwise, indicates the archive below 
    methods are targeting.

    * **--add** 

          add files to archive

    * **--remove**

          remove files from archive

    * **--push**

          push archive's git repo

    * **--pull**

          pull archive's git repo


FILES
=====

::

    $XDG_CONFIG_HOME/wallpapermgr/config2.yml
    $XDG_CONFIG_DATA/wallpapermgr/data.json
    $XDG_CONFIG_DATA/wallpapermgr.pid
    $XDG_CONFIG_DATA/wallpapermgr.sock
    $XDG_CONFIG_DATA/wallpapers/\*.\*


CONFIGURATION
=============


.. code-block:: yaml

    # =========================================
    # $XDG_CONFIG_HOME/wallpapermgr/config2.yml
    # =========================================

    choose_archive_cmd: ['echo', 'normal_walls']
    show_wallpaper_cmd: ['feh', '--bg-scale', '${wallpaper}']
    
    archives:
       normal_walls:
          archive:      ~/progs/misc/wallpapers/normal_walls.tar
          gitroot:      ~/progs/misc/wallpapers
          gitsource:    ssh://gitbox:/home/gitrepos/misc/wallpapers
          desc:         "wallpapers with a normal aspect ratio (ex: 16:9)"
    
       wide_walls:
          archive:      ~/progs/misc/wallpapers/wide_walls.tar
          gitroot:      ~/progs/misc/wallpapers
          gitsource:    ssh://gitbox:/home/gitrepos/misc/wallpapers
          desc:         "wallpapers for wide-multimonitor aspect ratios (ex: 32:9, 48:9)"


EXAMPLES
========

.. code-block:: bash

    # basics
    wallmgr ls                      # print configured archives
    wallmgr prev/next               # show previous/next wallpaper
    wallmgr reload                  # reload config/re-index archive contents
    wallmgr stop                    # stop the wallpaper server
    wallmgr archive <archive_name>  # use wallpapers from different archive


    # add/remove wallpapers from an archive
    wallmgr archive <archive_name> \
        --add/--remove file1.png file2.png


    # git push/pull an archive's git-repository (to sync)
    wallmgr archive <archive_name> \
        --push/--pull


AUTHOR
======

Will Pittman - https://github.com/willjp
