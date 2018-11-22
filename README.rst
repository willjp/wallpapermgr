
wallpapermgr
============

Configurable tool to manage display/synchronization of wallpapers between computers.

Wallpapers are grouped into tar archives. files are synchronized between
computers using git. You may define your own command that determines which
archive gets used by default on your computer.

Includes zsh autocomplete script.


Usage
......

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


Install
.......

.. code-block:: bash

    python setup.py install --user  # install for current user only
    sudo python setup.py install    # install for all users


Configuration
..............

Configuration is stored in your `$XDG_CONFIG_HOME` (generally ``~/.config/wallpapermgr/config2.yml`` .

It uses the following format:

.. code-block:: yaml

    # stdout of this SHELL command determines archive to use by default
    choose_archive_cmd: ['echo', 'normal_walls']

    # the command to display a wallpaper.
    # ${wallpaper} will be substituted with the path of 
    # the wallpaper to display everywhere it appears.
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

