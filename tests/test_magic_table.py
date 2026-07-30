"""Check the hand-maintained table of built-in magics against the code.

IPython registers its own magics lazily, from the static tables in
:mod:`IPython.core.magics._table`, so that starting a shell does not import
every magics module.  Those tables are only correct as long as somebody keeps
them correct -- that is what this module is for.
"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

import inspect
import pkgutil
import subprocess
import sys
import textwrap
from importlib import import_module

import pytest
from traitlets.config import Config, Configurable

import IPython.core.magics
from IPython.core.interactiveshell import InteractiveShellABC
from IPython.core.magic import Magics
from IPython.core.magics import _table
from IPython import get_ipython


def _shipped_magics_classes():
    """Every ``Magics`` subclass defined under ``IPython/core/magics``."""
    found = {}
    for info in pkgutil.iter_modules(IPython.core.magics.__path__):
        module_name = f"{IPython.core.magics.__name__}.{info.name}"
        module = import_module(module_name)
        for name, obj in vars(module).items():
            if (
                inspect.isclass(obj)
                and issubclass(obj, Magics)
                and obj is not Magics
                # Only where it is defined, not where it is imported.
                and obj.__module__ == module_name
            ):
                found[name] = obj
    return found


class _UnconfiguredShell(Configurable):
    """Just enough of a shell for a ``Magics`` class to be instantiated.

    The magics a class provides has to be compared against the *default*
    configuration, not against whatever the session-wide test shell has been
    configured with along the way (``tests/test_magic.py`` adds script magics
    to it, for one).
    """

    def __init__(self):
        super().__init__(config=Config())
        self.configurables = []


# So that `MagicsManager.shell` accepts one of these.
InteractiveShellABC.register(_UnconfiguredShell)


def _actual_magics(cls):
    """The line and cell magics an instance of `cls` registers."""
    instance = cls(shell=_UnconfiguredShell())
    return {
        kind: tuple(sorted(instance.magics[kind])) for kind in ("line", "cell")
    }


def _render(table):
    """Render a name table as the source that should live in ``_table.py``."""
    lines = ["BUILTIN_MAGICS = {"]
    for class_name, kinds in table.items():
        lines.append(f'    "{class_name}": {{')
        for kind in ("line", "cell"):
            lines.append(f'        "{kind}": {kinds[kind]!r},')
        lines.append("    },")
    lines.append("}")
    return "\n".join(lines)


def test_every_shipped_class_is_in_the_table():
    """A new Magics class must be added to ``BUILTIN_MAGICS``."""
    shipped = set(_shipped_magics_classes())
    # UserMagics is a placeholder for magics defined at runtime; it never
    # provides any magic of its own and is instantiated eagerly.
    shipped.discard("UserMagics")
    missing = shipped - set(_table.BUILTIN_MAGICS)
    assert not missing, (
        f"{sorted(missing)} are not listed in IPython.core.magics._table."
        "BUILTIN_MAGICS, so their magics would not be registered at startup."
    )


def test_every_shipped_class_is_importable_from_the_package():
    """``MAGICS_CLASSES`` drives ``IPython.core.magics.__getattr__``."""
    for class_name, cls in _shipped_magics_classes().items():
        if class_name == "UserMagics":
            continue
        assert _table.MAGICS_CLASSES.get(class_name) == cls.__module__, (
            f"IPython.core.magics._table.MAGICS_CLASSES[{class_name!r}] should"
            f" be {cls.__module__!r}"
        )
        assert getattr(IPython.core.magics, class_name) is cls


def test_all_covers_the_lazily_exported_names():
    """``__all__`` is written out by hand so tools can read it statically."""
    assert set(_table.MAGICS_CLASSES) <= set(IPython.core.magics.__all__)
    for name in IPython.core.magics.__all__:
        assert getattr(IPython.core.magics, name) is not None
    assert set(IPython.core.magics.__all__) <= set(dir(IPython.core.magics))


def test_magics_classes_entries_resolve():
    """Every entry of ``MAGICS_CLASSES`` points at something that exists."""
    for name, module_name in _table.MAGICS_CLASSES.items():
        assert hasattr(import_module(module_name), name), (
            f"{module_name} does not define {name}"
        )
        assert getattr(IPython.core.magics, name) is getattr(
            import_module(module_name), name
        )


def test_builtin_magics_table_is_accurate():
    """``BUILTIN_MAGICS`` lists exactly the magics each class provides."""
    expected = {}
    for class_name in _table.BUILTIN_MAGICS:
        cls = getattr(IPython.core.magics, class_name)
        expected[class_name] = _actual_magics(cls)

    # ScriptMagics generates one cell magic per configured interpreter; the
    # table only carries the fixed ones, `init_magics` adds the rest.
    generated = set(_table.default_script_magics())
    expected["ScriptMagics"]["cell"] = tuple(
        name for name in expected["ScriptMagics"]["cell"] if name not in generated
    )

    declared = {
        class_name: {
            kind: tuple(sorted(kinds[kind])) for kind in ("line", "cell")
        }
        for class_name, kinds in _table.BUILTIN_MAGICS.items()
    }

    assert declared == expected, (
        "IPython.core.magics._table.BUILTIN_MAGICS is out of sync with the "
        "magics classes. It should read:\n\n" + _render(expected)
    )


def test_no_magic_is_claimed_by_two_classes():
    """Lazy registration assumes one class per name.

    With eager registration a duplicated name resolved to whichever class was
    registered last.  Lazily, whichever class happens to be imported first
    would win instead, so duplicates must not happen.
    """
    for kind in ("line", "cell"):
        owners = {}
        for class_name, kinds in _table.BUILTIN_MAGICS.items():
            for magic_name in kinds[kind]:
                owners.setdefault(magic_name, []).append(class_name)
        duplicated = {name: cls for name, cls in owners.items() if len(cls) > 1}
        assert not duplicated, f"duplicated {kind} magics: {duplicated}"


def test_registered_names_match_the_table():
    """A live shell knows every magic the table declares."""
    ip = get_ipython()
    for kind in ("line", "cell"):
        declared = {
            name
            for kinds in _table.BUILTIN_MAGICS.values()
            for name in kinds[kind]
        }
        if kind == "cell":
            declared |= set(_table.default_script_magics())
        missing = declared - set(ip.magics_manager.magics[kind])
        assert not missing


def test_aliases_point_at_known_magics():
    for alias, target, kind in _table.BUILTIN_MAGIC_ALIASES:
        assert any(
            target in kinds[kind] for kinds in _table.BUILTIN_MAGICS.values()
        ), f"%{alias} aliases {target}, which no built-in class provides"


def test_configured_script_magics():
    from traitlets.config import Config

    assert _table.configured_script_magics(None) == _table.default_script_magics()
    assert _table.configured_script_magics(Config()) == _table.default_script_magics()

    config = Config()
    config.ScriptMagics.script_magics = ["nodejs"]
    assert _table.configured_script_magics(config) == ["nodejs"]


EXECUTION_SPEC = "IPython.core.magics.execution:ExecutionMagics"


@pytest.fixture
def manager():
    """A standalone MagicsManager, so tests don't disturb the shared shell."""
    from IPython.core.magic import MagicsManager

    return MagicsManager(shell=_UnconfiguredShell())


def test_register_lazy_class_validates_spec(manager):
    with pytest.raises(ValueError):
        manager.register_lazy_class("IPython.core.magics.execution")


def test_lazy_magic_resolves_and_replaces_itself(manager):
    from IPython.core.magic import LazyMagic

    manager.register_lazy_class(EXECUTION_SPEC, line_magics=["timeit"])
    placeholder = manager.magics["line"]["timeit"]
    assert isinstance(placeholder, LazyMagic)
    assert placeholder._lazy_class_name == "ExecutionMagics"
    assert "timeit" in repr(placeholder)

    # Resolving loads the class and puts the real magic in the table.
    assert manager.find("line", "timeit") is not None
    assert not isinstance(manager.magics["line"]["timeit"], LazyMagic)
    # ... and the placeholder still works for anything holding on to it.
    assert placeholder.__doc__ == manager.magics["line"]["timeit"].__doc__


def test_lazy_magic_with_a_wrong_table_fails_loudly(manager):
    from IPython.core.error import UsageError

    manager.register_lazy_class(EXECUTION_SPEC, line_magics=["dummy_lazy"])
    # ExecutionMagics provides no `%dummy_lazy`: resolving must raise and drop
    # the stale entry rather than recurse or silently do nothing.
    with pytest.raises(UsageError):
        manager.magics["line"]["dummy_lazy"]._lazy_resolve()
    assert "dummy_lazy" not in manager.magics["line"]


def test_register_lazy_class_does_not_shadow_a_loaded_class(manager):
    from IPython.core.magic import LazyMagic

    manager.register_lazy_class(EXECUTION_SPEC, line_magics=["timeit"])
    manager.load_lazy_class(EXECUTION_SPEC)
    manager.register_lazy_class(EXECUTION_SPEC, line_magics=["timeit"])
    assert not isinstance(manager.magics["line"]["timeit"], LazyMagic)


def test_registry_loads_lazily(manager):
    manager.register_lazy_class(EXECUTION_SPEC, line_magics=["timeit"])
    assert "ExecutionMagics" not in dict(manager.registry)

    assert manager.registry["ExecutionMagics"].__class__.__name__ == "ExecutionMagics"

    with pytest.raises(KeyError):
        manager.registry["NoSuchMagics"]


def test_load_all_lazy_magics(manager):
    from IPython.core.magic import LazyMagic

    for class_name, kinds in _table.BUILTIN_MAGICS.items():
        manager.register_lazy_class(
            f"{_table.MAGICS_CLASSES[class_name]}:{class_name}",
            kinds["line"],
            kinds["cell"],
        )
    manager.load_all_lazy_magics()
    left = [
        name
        for table in manager.magics.values()
        for name, fn in table.items()
        if isinstance(fn, LazyMagic)
    ]
    assert left == []


STARTUP_CHECK = textwrap.dedent(
    """
    import sys
    from IPython.core.interactiveshell import InteractiveShell

    shell = InteractiveShell.instance()
    loaded = sorted(
        name
        for name in sys.modules
        if name.startswith("IPython.core.magics.")
        and not name.rsplit(".", 1)[1].startswith("_")
    )
    print(",".join(loaded))
    """
)


def test_startup_does_not_import_the_magics_modules():
    """The whole point: starting a shell imports no magics implementation."""
    result = subprocess.run(
        [sys.executable, "-c", STARTUP_CHECK],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "", (
        "starting a shell imported magics modules eagerly: " + result.stdout
    )
