"""Command-line entry point for se_support.

Implemented now (T0/T1):
    se-support schemas export --output schemas/   # export JSON schemas

Stubbed (later tickets, print a clear "not implemented in v0" notice):
    se-support import ...     # T2 dataset importers
    se-support run ...        # T3-T7 runner
    se-support evaluate ...   # T5 gates / official eval
    se-support quality ...    # T8 patch quality cards

Kept dependency-free (argparse only) per the proposal's "no unnecessary
dependencies" constraint.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from se_support import __version__
from se_support.config import schemas_dir
from se_support.schemas import EXPORTED_MODELS, export_schemas

_NOT_IMPLEMENTED = (
    "not implemented in v0 (see PROJECT_PROPOSAL.md tickets); "
    "only `schemas export` is available in the current milestone."
)


def _cmd_schemas(args: argparse.Namespace) -> int:
    if args.schemas_command == "export":
        out = Path(args.output) if args.output else schemas_dir()
        written = export_schemas(out)
        for p in written:
            print(f"wrote {p}")
        print(f"exported {len(written)} schema(s) to {out}")
        return 0
    if args.schemas_command == "list":
        for name, model in EXPORTED_MODELS.items():
            print(f"{name}: {model.__name__}")
        return 0
    print("usage: se-support schemas {export,list}", file=sys.stderr)
    return 2


def _cmd_stub(args: argparse.Namespace) -> int:
    print(f"`se-support {args.command}`: {_NOT_IMPLEMENTED}", file=sys.stderr)
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="se-support",
        description="SE-Support Study: controlled ablation of coding-agent support structures.",
    )
    parser.add_argument("--version", action="version", version=f"se-support {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    # schemas (implemented)
    p_schemas = sub.add_parser("schemas", help="Export/list JSON schemas for the data models.")
    schemas_sub = p_schemas.add_subparsers(dest="schemas_command", required=True)
    p_export = schemas_sub.add_parser("export", help="Export JSON schemas to a directory.")
    p_export.add_argument("--output", "-o", default=None, help="Output dir (default: schemas/).")
    schemas_sub.add_parser("list", help="List exported models.")
    p_schemas.set_defaults(func=_cmd_schemas)

    # stubs (later tickets)
    for name, help_text in (
        ("import", "Import tasks into TaskSpec JSONL (T2)."),
        ("run", "Run an experiment (T3-T7)."),
        ("evaluate", "Evaluate patches / run gates (T5)."),
        ("quality", "Compute patch quality cards (T8)."),
    ):
        p = sub.add_parser(name, help=help_text)
        p.set_defaults(func=_cmd_stub)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
