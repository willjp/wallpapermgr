apply_methods/commandline.rst
=============================

Defaults
---------

None

Usage
-----

The simplest way of using the **commandline** apply_method
is to write the entire line to **apply_args**.

ex:

.. code-block:: yaml

   normal_walls:
      apply_method: commandline
      apply_args:   feh --bg-scale {filename}


Technically, you can split this into args/kwds,
but YAML would then parse `{filename}` as a dictionary.
It is not recommended.


