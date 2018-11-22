
wallpapermgr
============

|

A simple, configurable tool to manage, categorize, and display
wallpaper collections. Wallpapers collections are stored in tar archives,  
and are synchronized between computers using git. 

Method of applying wallpapers is customizable, and rules can be created 
so that specific wallpaper collections are used by default whenever
certain conditions are met (ex: multimonitor, operating system, hostname, ...).

Custom apply_methods/archive_conditions can be written in any language that
can read/write JSON.

.. code-block:: bash

   #### Some Common Commands
   ## (see `wallmgr [section] --help` for more info)

   wallmgr prev/next                                       ## display previous/next wallpaper
   wallmgr shuffle                                         ## re-randomize order of wallpapers
   wallmgr pull                                            ## pull the latest wallpaper collections from git
   wallmgr archive [archive_name/current] --append  *.png  ## add files to a wallpaper collection
   wallmgr display --daemonize [seconds]                   ## run in background and change wallpapers every N seconds

.. code-block:: yaml

   #### Sample Configuration
   
   archives:
   
      landscapes:
         archive:      ~/.wallpapers/landscapes1.tar
         description:  nothing but landscapes.
         apply_method: feh
         conditions:
            - is_hostname: 
              - workpc
              - dadspc
            - is_xineramawide: False

|
|


!! WARNING !!
--------------

This works reasonably well, but it is composed of some pretty
horrendous code. I'll need to rewrite this.


_________________________________________

|
|

.. contents:: Table Of Contents

|
|

_________________________________________


**__WARNING__**: Still in Alpha, some documented CLI commands are still unfinished.


Background
----------

I like wallpapers a lot. Being surprised by a wallpaper I collected
a year ago or more always makes my day. After years of amassing wallpapers,
I found that the most painless way of collecting/distributing them between 
home,work, and laptops (for online/offline) was storing them in a 
git-project, and categorizing them into different tar-archives.

This tool grew around that use-case. 



What it Does
------------
In a nutshell, simplifies creation/synchronizing/displaying a wallpaper collection
by interfacing with it from a single commandline interface.


* associate collections of wallpapers with computers matching customizable conditions (multimonitor setups, hostnames, operating systems, etc). Custom conditions can be written.
* apply wallpapers using method using a method that suits your OS and WM. Custom apply-methods can be written.
* randomized sequence of images is saved (run through entire sequence before repeating wallpapers, persists across reboots)
* create, delete, append-to, push, and pull git archive containing wallpapers
* custom conditions/apply methods communicate using JSON. You can write your own extensions in whichever language is most appropriate/familiar for you.


Install
-------


External Dependencies
.....................

I tried to keep dependencies for the core-program to a minimum
(not hard, this is basically glue for other more fully featured programs).

==============      ==================================
Python Modules
------------------------------------------------------
Dependencies:       Description
==============      ==================================
`six`               python2/3 compatibility tools
`GitPython`         python interface for git
`PyYaml`            parses/dumps yaml files
==============      ==================================

==============      ==================================
Programs
------------------------------------------------------
Dependencies:       Description
==============      ==================================
git                 version-control system
==============      ==================================

|
|


However, **archive_conditions** and **apply_methods** occasionally have
dependencies of their own. You'll need to read each extension's documentation
in order to see what other dependencies are required for your particular setup.





Configuration Overview
-----------------------


Quick YAML tutorial
...................


Example Config
...............


.. code-block:: yaml

   #### ~/.config/wallpapermgr/config.yml
   general: Null


   archives:

      wallpapers_wide:
         archive:      ~/.wallpapers/wide.tar
         apply_method: feh
         conditions:
            - is_xineramawide: True

      wallpapers_default_settings:
         archive:      ~/.wallpapers/normal.tar
         apply_method: feh
         conditions:   
            - is_default: True





Configuration Sections
-----------------------


general
.......

Nothing yet.


archives
........

In the archives section, you define collections of wallpapers, along with
when/how to apply them. Each archive consists of a name, then a collection
of keys that are used to configure it.

ex:
   .. code-block:: yaml

      #### ~/.config/wallpapermgr/config.yml   

      archives:
         
         my_wallpapers:                                                    ## archive name:
            archive:      ~/.wallpapers/archive1.tar                       #    + 
            description:  nothing but landscapes                           #    |
            apply_method: feh                                              #    | (archive settings)
            conditions:                                                    #    |
               - is_default: True                                          #    +

         home wallpapers wide:                                             ## archive name:
            description:  |                                                #    +
               wallpapers to use at home, on multimonitor                  #    |
               Xinerama setups.                                            #    |
            archive:      ~/.wallpapers/archive2.tar                       #    | 
            apply_method: feh                                              #    | (archive settings)
            conditions:                                                    #    |
               - is_xineramawide: True                                     #    |
               - is_hostname:                                              #    |
                   - wintermute                                            #    |
                   - mordin                                                #    |
                   - oracle                                                #    +

archive config keys:
``````````````````````
 

archive:
~~~~~~~~

Filepath to the tar archive of wallpapers this collection will use. Use of `~` is allowed.

(opt) description:
~~~~~~~~~~~~~~~~~~

Optionally provide a description for the archive, it's configuration, or anything
else you might want to remember in the future.


(opt) git:
~~~~~~~~~~

I use git to keep my wallpaper-collections in sync between different computers.
If you'd like to do the same, you can make use of an additional couple of keys:

* `gitroot`:   the root-directory of the git project containing your wallpaper-archives (or where you'd like to clone it)
* `gitsource`: the git-remote you'd like to pull wallpapers from, and push wallpaper collections to.

   .. code-block:: yaml

      my_wallpapers:
         archive:      ~/.wallpapers/default.tar
         apply_method: feh
         conditions:   default
         gitroot:      ~/.wallpapers
         gitsource:    ssh://host.myserver.com:22/home/git/wallpapers


`gitroot` and `gitsource` must be used together. If they are present,
wallmgr performs the following additional tasks:

* after appending images to the archive, ``git push`` is used to update the repo.
* ``wallmgr push/pull`` become available
* if `gitroot` does not exist, the user is prompted if they would like to clone the repository
  on ``push/pull/next/prev/append`` operations.


apply_methods:
~~~~~~~~~~~~~~

**apply_methods** are configured under each archive.
If possible, each module should be equipped with sane default 
values, but in case more information is required, or altered behaviour
is desired, additional parameters can be provided with the following keys.:

* `apply_method`  determines the method we are applying wallpapers with
* `apply_args`    (optional) applied first, and in order to the command
* `apply_kwds`    (optional) come after arguments, are unordered, but each key's value always follows the keyword.

   .. code-block:: yaml
   
     wallpapers_custom_settings:
        archive:      ~/.wallpapers/archive1.tar
        apply_method: feh
        apply_args:   ['--bg-seamless', '{filepath}']
        apply_kwds:
           --font:     Droid Sans Mono
           --fontpath: /usr/share/fonts/TTF
        conditions:    default
   


archive_conditions
~~~~~~~~~~~~~~~~~~

**archive_conditions** are also configured under each archive. Each archive's conditions
are evaluated in order on the computer. The first archive where all conditions are satisfied
is used. If all archives are tested, and none are satisfied, the archive with the **default**
condition is used (regardless of what other conditions are attached to it).

Multiple conditions can be stacked by preserving their indent.


   .. code-block:: yaml
   
     wallpapers_wide:
        apply_method: feh
        archive:      ~/.wallpapers/wallpapers_wide.tar
        conditions:
           is_xineramawide: True
           is_hostname:     mordin
   


Multiple acceptable return-values can be defined for a condition
by providing a list:

   .. code-block:: yaml
   
     wallpapers_home:
        apply_method: feh
        archive:      ~/.wallpapers/wallpapers_home2.tar
        conditions:
           is_hostname: 
              - wintermute
              - mordin
              - oracle
   





Recommendations
---------------

git
...

If your wallpaper collection gets really big, you might want to alter
the `~/.gitconfig` file on your git-repository with the following info.
(I was having issues cloning the repository once it got quite large)

   .. code-block:: ini
   
      [pack]
         windowMemory = 1000m
         SizeLimit    = 1000m
         threads      = 1
         window       = 0




See Also
--------

other wallpaper tools
......................



nice wallpaper websites
........................

* https://alpha.wallhaven.cc/


