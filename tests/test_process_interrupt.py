import sys

import pexpect
import pytest

from IPython.utils._process_posix import ProcessHandler

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX-specific test")


def test_system_interrupt_before_child_spawned(monkeypatch):
    """An interrupt during spawn is not masked by an unbound child variable."""
    handler = ProcessHandler()
    handler._sh = "sh"

    def interrupted_spawn(*args, **kwargs):
        raise KeyboardInterrupt

    spawn_name = "spawnb" if hasattr(pexpect, "spawnb") else "spawn"
    monkeypatch.setattr(pexpect, spawn_name, interrupted_spawn)

    with pytest.raises(KeyboardInterrupt):
        handler.system("echo never-runs")
