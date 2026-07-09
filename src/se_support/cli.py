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
from se_support.config import runs_dir, schemas_dir
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


def _cmd_import(args: argparse.Namespace) -> int:
    from se_support.datasets import import_swebench_verified

    if args.dataset != "swebench-verified":
        print(f"dataset '{args.dataset}': {_NOT_IMPLEMENTED}", file=sys.stderr)
        return 2
    fixture = Path(args.fixture) if args.fixture else None
    n = import_swebench_verified(
        Path(args.output), limit=args.limit, fixture_path=fixture
    )
    print(f"imported {n} task(s) -> {args.output}")
    return 0


def _cmd_sample(args: argparse.Namespace) -> int:
    from se_support.datasets import load_tasks, sample_tasks, write_tasks

    tasks = load_tasks(Path(args.input))
    chosen = sample_tasks(tasks, args.n, strategy=args.strategy, seed=args.seed)
    write_tasks(chosen, Path(args.output))
    print(f"sampled {len(chosen)}/{len(tasks)} ({args.strategy}) -> {args.output}")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    import json

    from se_support.agents import LLMAgent, MockAgent, OpenAIChatClient
    from se_support.runner.run_manager import run_single
    from se_support.schemas import TaskSpec

    task = TaskSpec.model_validate(json.loads(Path(args.task).read_text()))
    if args.agent == "mock":
        agent = MockAgent(mode=args.mock_mode)
        model = f"mock[{args.mock_mode}]"
    elif args.agent == "llm":
        client = OpenAIChatClient(
            model=args.model, base_url=args.base_url, api_key=args.api_key
        )
        agent = LLMAgent(client, max_turns=args.max_turns)
        model = args.model
    else:
        print(f"agent '{args.agent}': {_NOT_IMPLEMENTED}", file=sys.stderr)
        return 2

    runs_root = Path(args.output) if args.output else runs_dir()
    outcome = run_single(
        task=task,
        agent=agent,
        condition=args.condition,
        runs_root=runs_root,
        experiment_id=args.experiment_id,
        model=model,
        seed=args.seed,
    )
    ev = outcome.eval_result
    print(f"run_id={outcome.run_id} dir={outcome.run_dir}")
    print(
        f"resolved={ev.resolved} patch_applies={ev.patch_applies} "
        f"F2P={ev.fail_to_pass_passed}/{ev.fail_to_pass_total} "
        f"P2P={ev.pass_to_pass_passed}/{ev.pass_to_pass_total} "
        f"quality={outcome.quality_card.quality_level}"
    )
    return 0


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

    # run (mock pipeline implemented; real agents later)
    p_run = sub.add_parser("run", help="Run one task end-to-end (mock + llm agents).")
    p_run.add_argument("--task", required=True, help="Path to a TaskSpec JSON file.")
    p_run.add_argument("--agent", default="mock", help="Agent scaffold (mock | llm).")
    p_run.add_argument("--mock-mode", default="gold", choices=["gold", "empty", "broken"],
                       help="Mock agent behaviour.")
    p_run.add_argument("--model", default="Qwen/Qwen2.5-Coder-7B-Instruct",
                       help="Model id for --agent llm.")
    p_run.add_argument("--base-url", default="http://localhost:8000/v1",
                       help="OpenAI-compatible endpoint (e.g. local vLLM server).")
    p_run.add_argument("--api-key", default="EMPTY", help="API key for the endpoint.")
    p_run.add_argument("--max-turns", type=int, default=20, help="Max agent turns (llm).")
    p_run.add_argument("--condition", default="C0_minimal", help="Support condition id.")
    p_run.add_argument("--experiment-id", default="adhoc", help="Experiment id (runs/<id>/).")
    p_run.add_argument("--seed", type=int, default=0)
    p_run.add_argument("--output", "-o", default=None, help="Runs root (default: runs/).")
    p_run.set_defaults(func=_cmd_run)

    # import (implemented for swebench-verified)
    p_import = sub.add_parser("import", help="Import a dataset into TaskSpec JSONL.")
    p_import.add_argument("dataset", help="Dataset name (swebench-verified).")
    p_import.add_argument("--output", "-o", required=True, help="Output JSONL path.")
    p_import.add_argument("--limit", type=int, default=None, help="Max tasks to import.")
    p_import.add_argument("--fixture", default=None,
                          help="Offline JSONL of raw records (skip download).")
    p_import.set_defaults(func=_cmd_import)

    # sample (implemented)
    p_sample = sub.add_parser("sample", help="Sample a task subset from a TaskSpec JSONL.")
    p_sample.add_argument("--input", "-i", required=True, help="Input TaskSpec JSONL.")
    p_sample.add_argument("--output", "-o", required=True, help="Output TaskSpec JSONL.")
    p_sample.add_argument("--n", type=int, required=True, help="Number to sample.")
    p_sample.add_argument("--strategy", default="stratified",
                          choices=["stratified", "head"], help="Sampling strategy.")
    p_sample.add_argument("--seed", type=int, default=0)
    p_sample.set_defaults(func=_cmd_sample)

    # stubs (later tickets)
    for name, help_text in (
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
