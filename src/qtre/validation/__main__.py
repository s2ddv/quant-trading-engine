"""Run the persisted F1 audit from the command line."""

import argparse
import json

from . import audit_f1_run


def main():
    parser = argparse.ArgumentParser(description="Audit a persisted F1 run")
    parser.add_argument("directory", help="directory containing manifest.json")
    args = parser.parse_args()
    try:
        report = audit_f1_run(args.directory)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"audit input: {exc}\n")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "VALID" else 1


if __name__ == "__main__":
    raise SystemExit(main())
