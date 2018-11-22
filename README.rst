
wallpapermgr
============

Configurable tool to synchornize/display wallpapers between computers.

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
    wallmgr archive <archive_name>  # use wallpapers from archive


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

    choose_archive_cmd: ['echo', 'normal_walls']      # stdout of this SHELL command determines archive to use by default
    
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


**NOTE: currently hardcoded to display wallpaper using feh. must fix.**

