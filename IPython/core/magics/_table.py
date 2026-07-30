"""Static description of the magics IPython ships with.

Importing a module and instantiating the ``Magics`` subclasses it defines is
expensive, and most of the magics in a given session are never used.  To keep
``import IPython`` and shell startup fast, IPython registers its own magics
lazily: only the tables below are consulted at startup, and the module
implementing a magic is imported the first time that magic is looked up.

That means these tables are hand maintained and *must* be kept in sync with the
code.  ``tests/test_magic_table.py`` imports every magics module, instantiates every
``Magics`` subclass, and fails if anything here is missing, stale, or pointing
at the wrong class -- and prints the corrected table.
"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

from __future__ import annotations

import os
import typing as t

if t.TYPE_CHECKING:
    from traitlets.config import Config


#: Every public name re-exported by :mod:`IPython.core.magics`, mapped to the
#: module that defines it.  Used by that package's module ``__getattr__`` so
#: that ``from IPython.core.magics import ExecutionMagics`` keeps working
#: without importing all the sibling modules.
MAGICS_CLASSES: dict[str, str] = {
    "AsyncMagics": "IPython.core.magics.basic",
    "AutoMagics": "IPython.core.magics.auto",
    "BasicMagics": "IPython.core.magics.basic",
    "CodeMagics": "IPython.core.magics.code",
    "ConfigMagics": "IPython.core.magics.config",
    "DisplayMagics": "IPython.core.magics.display",
    "ExecutionMagics": "IPython.core.magics.execution",
    "ExtensionMagics": "IPython.core.magics.extension",
    "HistoryMagics": "IPython.core.magics.history",
    "LoggingMagics": "IPython.core.magics.logging",
    "MacroToEdit": "IPython.core.magics.code",
    "NamespaceMagics": "IPython.core.magics.namespace",
    "OSMagics": "IPython.core.magics.osm",
    "PackagingMagics": "IPython.core.magics.packaging",
    "PylabMagics": "IPython.core.magics.pylab",
    "ScriptMagics": "IPython.core.magics.script",
}

#: The magics each built-in ``Magics`` subclass provides, in the order the
#: classes are registered by ``InteractiveShell.init_magics``.  Order matters:
#: a name defined by two classes resolves to the one registered last.
#:
#: ``ScriptMagics`` is a special case -- on top of the names listed here it
#: generates one cell magic per configured interpreter, see
#: :func:`configured_script_magics`.
BUILTIN_MAGICS: dict[str, dict[str, tuple[str, ...]]] = {
    "AutoMagics": {
        "line": ("autocall", "automagic"),
        "cell": (),
    },
    "BasicMagics": {
        "line": (
            "alias_magic",
            "colors",
            "doctest_mode",
            "gui",
            "lsmagic",
            "magic",
            "notebook",
            "page",
            "pprint",
            "precision",
            "quickref",
            "xmode",
        ),
        "cell": (),
    },
    "CodeMagics": {
        "line": ("edit", "load", "loadpy", "pastebin", "save"),
        "cell": (),
    },
    "ConfigMagics": {
        "line": ("config",),
        "cell": (),
    },
    "DisplayMagics": {
        "line": (),
        "cell": ("html", "javascript", "js", "latex", "markdown", "svg"),
    },
    "ExecutionMagics": {
        "line": (
            "code_wrap",
            "debug",
            "macro",
            "pdb",
            "prun",
            "run",
            "tb",
            "time",
            "timeit",
        ),
        "cell": ("capture", "code_wrap", "debug", "prun", "time", "timeit"),
    },
    "ExtensionMagics": {
        "line": ("load_ext", "reload_ext", "unload_ext"),
        "cell": (),
    },
    "HistoryMagics": {
        "line": ("history", "recall", "rerun"),
        "cell": (),
    },
    "LoggingMagics": {
        "line": ("logoff", "logon", "logstart", "logstate", "logstop"),
        "cell": (),
    },
    "NamespaceMagics": {
        "line": (
            "pdef",
            "pdoc",
            "pfile",
            "pinfo",
            "pinfo2",
            "psearch",
            "psource",
            "reset",
            "reset_selective",
            "who",
            "who_ls",
            "whos",
            "xdel",
        ),
        "cell": (),
    },
    "OSMagics": {
        "line": (
            "alias",
            "bookmark",
            "cd",
            "dhist",
            "dirs",
            "env",
            "popd",
            "pushd",
            "pwd",
            "pycat",
            "rehashx",
            "sc",
            "set_env",
            "sx",
            "system",
            "unalias",
        ),
        "cell": ("!", "sx", "system", "writefile"),
    },
    "PackagingMagics": {
        "line": ("conda", "mamba", "micromamba", "pip", "uv"),
        "cell": (),
    },
    "PylabMagics": {
        "line": ("matplotlib", "pylab"),
        "cell": (),
    },
    "ScriptMagics": {
        "line": ("killbgscripts",),
        "cell": ("script",),
    },
    "AsyncMagics": {
        "line": ("autoawait",),
        "cell": (),
    },
}

#: Aliases ``InteractiveShell.init_magics`` registers, as
#: ``(alias, target, kind)``.  Aliases resolve their target when called, so
#: registering them does not force any magics module to be imported.
BUILTIN_MAGIC_ALIASES: tuple[tuple[str, str, str], ...] = (
    ("ed", "edit", "line"),
    ("hist", "history", "line"),
    ("rep", "recall", "line"),
    ("SVG", "svg", "cell"),
    ("HTML", "html", "cell"),
    ("file", "writefile", "cell"),
)


def default_script_magics() -> list[str]:
    """Interpreters ``%%script`` shortcuts are generated for by default.

    This is the default value of the ``ScriptMagics.script_magics`` trait; it
    lives here so that the lazy registration can know the generated names
    without importing :mod:`IPython.core.magics.script`.
    """
    defaults = [
        "sh",
        "bash",
        "perl",
        "ruby",
        "python",
        "python2",
        "python3",
        "pypy",
    ]
    if os.name == "nt":
        defaults.extend(
            [
                "cmd",
            ]
        )

    return defaults


def configured_script_magics(config: Config | None) -> list[str]:
    """Cell magic names ``ScriptMagics`` will provide for the given config.

    ``ScriptMagics.script_magics`` is configurable, so the generated names are
    not known statically; peek at the config rather than instantiating the
    class, which is what we are trying to avoid in the first place.
    """
    section = getattr(config, "ScriptMagics", None) if config is not None else None
    if section is not None and "script_magics" in section:
        return list(section["script_magics"])
    return default_script_magics()
