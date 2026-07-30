IPython's own magics are now registered lazily. Starting a shell used to import
all fifteen modules under :mod:`IPython.core.magics` and instantiate every
:class:`~IPython.core.magic.Magics` class in them, even though a given session
typically uses a handful of magics at most. Now only the magic *names* are known
up front -- from the hand-maintained tables in ``IPython.core.magics._table`` --
and the module implementing a magic is imported the first time that magic is
looked up. This shaves roughly 35 ms off ``import IPython`` and shell startup.

This is invisible in normal use: ``%lsmagic``, completion, ``%foo?`` and calling
a magic all behave as before. Two details are worth knowing if you poke at the
internals:

* ``shell.magics_manager.magics['line']`` (and ``['cell']``) may hold
  :class:`~IPython.core.magic.LazyMagic` placeholders rather than bound methods.
  Calling one, or reading any attribute of one, transparently loads the real
  magic. Use :meth:`~IPython.core.magic.MagicsManager.find` --- or
  ``shell.find_line_magic`` / ``find_cell_magic`` / ``find_magic``, which go
  through it --- to get the real callable.
* A magics class only appears in ``shell.configurables`` once it has been
  loaded. ``%config`` (and its completions) load everything first, so the list
  of configurable classes it shows is unchanged.

Third-party code can use the same mechanism for its own magics::

    shell.magics_manager.register_lazy_class(
        "my_package.magics:MyMagics",
        line_magics=["my_magic"],
        cell_magics=["my_magic"],
    )

which, unlike the existing ``MagicsManager.lazy_magics`` configuration, does not
require the magics to be packaged as an IPython extension.
