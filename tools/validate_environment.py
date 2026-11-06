"""Offline structural checks; runtime Codex discovery is a separate live check."""

from pathlib import Path
import re

import tomli
import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILLS = {"quant-research", "quant-backtest", "quant-risk", "quant-ml", "quant-performance"}
ROLES = {"quant_research", "quant_developer", "statistical_validation", "risk_code_review"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def toml(path):
    return tomli.loads(path.read_text())


def main():
    require((ROOT / "AGENTS.md").is_file(), "root instructions missing")
    config = toml(ROOT / ".codex/config.toml")
    agents = config["agents"]
    require(agents["max_concurrent_threads_per_session"] == 2, "expected two child slots")
    require(set(agents) - {"max_concurrent_threads_per_session"} == ROLES, "role set differs")
    for role in ROLES:
        entry = agents[role]
        require(bool(entry["description"]), f"{role}: description missing")
        path = (ROOT / ".codex" / entry["config_file"]).resolve()
        require(path.is_relative_to(ROOT / ".codex/agents"), f"{role}: external role path")
        layer = toml(path)
        require(set(layer) == {"developer_instructions"}, f"{role}: unexpected overrides")
        require(bool(layer["developer_instructions"].strip()), f"{role}: empty instructions")
    for name in SKILLS:
        path = ROOT / ".agents/skills" / name / "SKILL.md"
        parts = path.read_text().split("---", 2)
        require(len(parts) == 3 and not parts[0].strip(), f"{name}: frontmatter missing")
        metadata = yaml.safe_load(parts[1])
        require(metadata["name"] == name, f"{name}: mismatched name")
        require(
            isinstance(metadata["description"], str) and metadata["description"].strip(),
            f"{name}: description missing",
        )
        require(not re.search(r"\bTODO\b|\[TODO", parts[2]), f"{name}: unfinished scaffold")
        interface = yaml.safe_load((path.parent / "agents/openai.yaml").read_text())["interface"]
        require(bool(interface["display_name"]), f"{name}: display name missing")
        if "default_prompt" in interface:
            require(f"${name}" in interface["default_prompt"], f"{name}: invocation mismatch")
    environment = toml(ROOT / ".codex/environments/environment.toml")
    require(environment["version"] == 1 and environment["name"], "invalid environment")
    require(environment["setup"]["script"] == "make setup", "setup command differs")
    makefile = (ROOT / "Makefile").read_text()
    for action in environment["actions"]:
        require(action["icon"] in {"tool", "run", "debug", "test"}, "unsupported action icon")
        target = action["command"].removeprefix("make ")
        require(
            action["command"] == f"make {target}" and f"\n{target}:" in makefile,
            f"unknown action: {action['command']}",
        )
    # BaseLoader preserves GitHub's YAML 1.2 'on' key (YAML 1.1 treats it as boolean).
    workflow = yaml.load(
        (ROOT / ".github/workflows/quant-validation.yml").read_text(), Loader=yaml.BaseLoader
    )
    require(set(workflow["on"]) == {"push", "pull_request", "workflow_dispatch"}, "CI triggers")
    require(workflow["permissions"] == {"contents": "read"}, "CI token permissions")
    job = workflow["jobs"]["validate"]
    require(job["strategy"]["max-parallel"] == "1", "parallel builds exceed budget")
    require(job["strategy"]["matrix"]["python-version"] == ["3.10", "3.14"], "Python matrix")
    toml(ROOT / "pyproject.toml")
    print("PASS: instructions, 5 skills, 4 roles, desktop actions, TOML and CI YAML structure")
    print("Limit: structural checks do not run GitHub CI or spawn configured Codex roles.")


if __name__ == "__main__":
    main()
