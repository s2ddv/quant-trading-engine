"""Probe installed Codex config/skill discovery without starting a model turn (POSIX)."""

import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import tempfile
import time

from tools.validate_environment import ROOT, ROLES, SKILLS


def main():
    binary = shutil.which("codex")
    if not binary:
        raise SystemExit("Codex CLI is not installed; static checks remain available.")
    with tempfile.TemporaryDirectory(prefix="qtre-codex-") as temporary:
        home = Path(temporary)
        # Trust exists only in this disposable home; no auth file is copied.
        (home / "config.toml").write_text(
            "[features]\nplugins = false\napps = false\n"
            + "[projects."
            + json.dumps(str(ROOT))
            + ']\ntrust_level = "trusted"\n'
        )
        with tempfile.TemporaryFile() as errors:
            process = subprocess.Popen(
                [binary, "--strict-config", "app-server", "--stdio"],
                cwd=ROOT,
                env={**os.environ, "CODEX_HOME": str(home)},
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=errors,
            )
            pending = bytearray()

            def send(payload):
                process.stdin.write(json.dumps(payload).encode() + b"\n")
                process.stdin.flush()

            def request(identifier, method, params):
                send({"id": identifier, "method": method, "params": params})
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    if b"\n" in pending:
                        line, _, remainder = pending.partition(b"\n")
                        pending[:] = remainder
                        response = json.loads(line)
                        if response.get("id") == identifier:
                            if "error" in response:
                                raise ValueError(response["error"])
                            return response["result"]
                    elif select.select([process.stdout], [], [], 1)[0]:
                        chunk = os.read(process.stdout.fileno(), 65536)
                        if not chunk:
                            raise RuntimeError("Codex exited before response")
                        pending.extend(chunk)
                raise TimeoutError(method)

            try:
                request(1, "initialize", {"clientInfo": {"name": "qtre-probe", "version": "1"}})
                send({"method": "initialized"})
                config = request(2, "config/read", {"cwd": str(ROOT), "includeLayers": True})
                skills = request(3, "skills/list", {"cwds": [str(ROOT)], "forceReload": True})
                agents = config["config"]["agents"]
                if agents["max_concurrent_threads_per_session"] != 2 or not ROLES <= agents.keys():
                    raise ValueError("Expected project agent roles/concurrency were not loaded")
                for name in ROLES:
                    path = Path(agents[name]["config_file"]).resolve()
                    if not path.is_relative_to(ROOT / ".codex/agents") or not path.is_file():
                        raise ValueError(f"Role path is not the local role: {name}")
                discovered = {
                    s["name"]
                    for item in skills["data"]
                    for s in item["skills"]
                    if Path(s["path"]).resolve().is_relative_to(ROOT / ".agents/skills")
                }
                failures = [e for item in skills["data"] for e in item.get("errors", [])]
                if not SKILLS <= discovered or failures:
                    raise ValueError(f"Skill discovery failed: {discovered}; errors={failures}")
                print(
                    json.dumps(
                        {
                            "roles": sorted(ROLES),
                            "skills": sorted(discovered),
                            "max_child_agents": 2,
                            "status": "PASS",
                            "limit": "No configured role was spawned; no desktop UI click.",
                        },
                        indent=2,
                    )
                )
            finally:
                process.stdin.close()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                process.stdout.close()


if __name__ == "__main__":
    main()
