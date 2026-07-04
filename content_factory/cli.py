from __future__ import annotations

import argparse
import json
from pathlib import Path

from .workflow import CaseSpec, Factory


def main() -> None:
    parser = argparse.ArgumentParser(prog="content-factory")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "run"):
        command = sub.add_parser(name)
        command.add_argument("spec", type=Path)
        command.add_argument("--provider", choices=("demo", "openai"), default="demo")
        if name == "run":
            command.add_argument("--auto-approve", action="store_true")
            command.add_argument("--reset", action="store_true")
    status = sub.add_parser("status")
    status.add_argument("case_id")
    approve = sub.add_parser("approve")
    approve.add_argument("case_id")
    approve.add_argument("stage")
    approve.add_argument("--by", required=True)
    args = parser.parse_args()
    factory = Factory(Path.cwd(), getattr(args, "provider", "demo"))
    if args.command == "init":
        result = {"manifest": str(factory.initialize(CaseSpec.load(args.spec)))}
    elif args.command == "run":
        result = factory.run(CaseSpec.load(args.spec), auto_approve=args.auto_approve, reset=args.reset)
    elif args.command == "approve":
        result = factory.approve(args.case_id, args.stage, args.by)
    else:
        result = factory.status(args.case_id)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
