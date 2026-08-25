from __future__ import annotations

import subprocess
import sys


def test_simulator_tracing_example():
    result = subprocess.run(
        [sys.executable, "docs/how-tos/code/simulator_tracing.py"],
        capture_output=True,
        check=True,
        text=True,
        timeout=30,
    )

    assert "sim.local.Input" in result.stderr
    assert "mosaik -> simulator: step" in result.stderr
    assert "simulator -> mosaik: step returned" in result.stderr
    assert "sim.local.Output" not in result.stderr
    assert "Collected data:" in result.stdout
