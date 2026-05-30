"""pytest wrapper for mock ops simulator."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ORCH_DIR = Path(__file__).resolve().parents[1]


@pytest.mark.asyncio
async def test_ops_simulator_mock_mode_exits_zero():
    env = os.environ.copy()
    env.setdefault("OPENROUTER_API_KEY", "or-test-key")
    env.setdefault("ORCHESTRATOR_API_KEY", "test-key")
    env["OPENROUTER_REFRESH_CATALOG_ON_STARTUP"] = "false"
    report = ORCH_DIR / "reports" / "pytest-ops-mock.json"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "gpthub_orchestrator.tools.ops_simulator",
            "--mode=mock",
            f"--report={report}",
        ],
        cwd=ORCH_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert report.is_file()
