apply_methods/commandline.rst
=============================

Defaults
--------

.. code-block:: yaml

   args: [ '--bg-scale' '{filename}' ]
   kwds: {}


Usage
-----

The feh module is parsed almost exactly the same as the
commandline module, except that `feh` will always be the first
item in **args**, and it already has a default behaviour.

If you would like to change the command feh is using, I recommend
that you treat **args** as a single line.

.. code-block:: yaml

   my_wallpapers:
      apply_method: feh
      apply_args:   --bg-scale {filename}


