
Extension Writer's Readme
=========================

This system was (almost) shamelessly borrowed from the fantastic project
**taskwarrior**. The central idea is that **JSON** is read directly from
STDOUT, so that extensions can be written in virtually any language.


There are two types of extensions that you can write:

* `apply_methods` provide different ways to set wallpapers
* `archive_conditions` are used to determine which archive of wallpapers to use.


|
|

.. contents:: Table Of Contents

|
|


extension stdin/stdout
----------------------

In order to allow people to write scripts in the language of their choosing,
we are passing information between programs using JSON.

Program input is sent using STDIN (note that this is different from an argument).
The JSON object is expected to have the following keys: 

* **args**: arguments to pass to module
* **kwds**: keyword arguments to pass to module (after arguments)
* **specialvars**: dictionary of special-variables to parse in default args/kwds if module has any.
* **loglevel**: reports the python loglevel. Use if meaningful to your module/language. (0=notset,10=debug,20=info,30=warn,40=error,50=critical)


.. code-block:: bash

   ## INPUT
   extension.sh < {
                     "args"        : ["-v","-d"]                           ,
                     "kwds"        : {"--user":"will"}                     ,
                     "specialvars" : {"filename":"/var/tmp/wallpaper.png"} ,
                     "loglevel"    : 10
                  }


Program output is also printed to stdout in JSON. The return-value is
stored in the key `return`.


.. code-block:: python

   ## OUTPUT
   import json
   print( json.loads({"return" : True}) )



Extensions
----------

apply_methods
.............

Apply methods do not report any information back
to the caller except for the program's error-code.

simply pass info from STDIN, and handle however you please.
Your script should handle the following keys:

* `args` arguments to pass to script
* `kwds` keyword arguments to pass to script
* `specialvars` a dictionary of values to replace. This is how words like `~` and `{filepath}`.
                

.. code-block:: bash

   ## YAML CONFIG
   archives:
      normal_wallpapers:
         apply_method:   feh
         apply_args:
            - '--bg-scale'
            - {filename}
         apply_kwds:
            --filelist:  /tmp/fileA   /tmp/fileB

   ## INPUT
   apply_methods/feh < {"args":["--bg-scale","{filename}"],"kwds":{"--filelist":"/tmp/fileA   /tmp/fileB"}}

   ## RESULT
   # (depends based on the module. for feh, this works out to be commandline args)


archive_conditions
..................

Archive conditions simply report information
about a system. They do not expect any arguments
or info from STDIN, and the user configures what
type of reply they will accept.

.. code-block:: bash


   ## OUTPUT
   # (from is_hostname)
   {"return": "my-hostname"}


   ## YAML CONFIG
   archives:
      normal_wallpapers:
         apply_method:  feh
         archive:       ~/.wallpapers/archive.tar
         conditions:
            is_hostname: my-hostname

   ## RESULT         
   #  the condition is_hostname is True
   



