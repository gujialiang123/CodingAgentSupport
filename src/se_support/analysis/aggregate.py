"""Analysis: aggregate runs into paired tables + statistics (EP-10).

Reads a completed experiment's run directories and produces the RQ2/RQ3 tables:
resolution-by-condition, paired contrasts vs C0 (McNemar + bootstrap CIs), and
quality summaries. Pure/offline: derives everything from saved artifacts so tables
can be regenerated without re-running.

Only the standard library + the package are used (no scipy/statsmodels dependency);
the exact McNemar test uses the binomial distribution, and CIs use a bootstrap.
"""

from __future__ import annotations

import json
import math
import random
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RunRow:
    task_id: str
    condition: str
    seed: int
    resolved: bool
    patch_applies: bool
    quality: str
    manipulation_passed: bool | None = None


def load_runs(experiment_dir: Path, allow_mixed_protocol: bool = False) -> list[RunRow]:
    """Load all completed runs under ``runs/<experiment_id>/<experiment_id>/``.

    Runs flagged ``infrastructure_failure`` (unclean base tree) are excluded — they
    are invalid infrastructure, not agent outcomes. Refuses to aggregate across
    differing ``protocol_version`` values unless ``allow_mixed_protocol`` is set
    (integrity fix, Phase 5: 0.3.0 results are not comparable with earlier ones).
    """
    experiment_dir = Path(experiment_dir)
    rows: list[RunRow] = []
    protocols: set[str] = set()
    for run_dir in sorted(experiment_dir.glob("*/")):
        qc = run_dir / "quality_card.json"
        ev = run_dir / "eval_result.json"
        rs = run_dir / "run_spec.json"
        if not (qc.exists() and ev.exists() and rs.exists()):
            continue
        status = run_dir / "integrity" / "status.json"
        if status.exists():
            try:
                if json.loads(status.read_text()).get("status") == "infrastructure_failure":
                    continue
            except (OSError, json.JSONDecodeError):
                pass
        spec = json.loads(rs.read_text())
        protocols.add(spec.get("protocol_version", "unknown"))
        evalr = json.loads(ev.read_text())
        card = json.loads(qc.read_text())
        mc = run_dir / "manipulation.json"
        manip = json.loads(mc.read_text()).get("passed") if mc.exists() else None
        rows.append(RunRow(
            task_id=spec["task_id"], condition=spec["condition"], seed=spec.get("seed", 0),
            resolved=bool(evalr.get("resolved")), patch_applies=bool(evalr.get("patch_applies")),
            quality=card.get("quality_level", "Q0_invalid"), manipulation_passed=manip,
        ))
    if len(protocols) > 1 and not allow_mixed_protocol:
        raise ValueError(
            f"refusing to aggregate mixed protocol_versions {sorted(protocols)}; "
            "0.3.0 (integrity-fixed) results are not comparable with earlier runs. "
            "Pass allow_mixed_protocol=True to override."
        )
    return rows


@dataclass
class ConditionSummary:
    condition: str
    n: int
    resolved: int
    applying: int
    q2_plus: int

    @property
    def resolution_rate(self) -> float:
        return self.resolved / self.n if self.n else 0.0


def p2p_regression_stats(evals: list[dict]) -> dict:
    """Correct PASS_TO_PASS regression stats over per-run eval dicts (Phase 1C).

    Denominator = applying patches with a usable P2P result (patch_applies and
    ``pass_to_pass_total`` > 0). A regression = at least one PASS_TO_PASS test
    failed (``pass_to_pass_passed`` < ``pass_to_pass_total``). Runs whose P2P is
    unavailable are reported separately, never silently folded into the rate.
    """
    applying = [e for e in evals if e.get("patch_applies")]
    usable = [e for e in applying if (e.get("pass_to_pass_total") or 0) > 0]
    regressing = [e for e in usable
                  if (e.get("pass_to_pass_passed") or 0) < (e.get("pass_to_pass_total") or 0)]
    missing = [e for e in applying if not ((e.get("pass_to_pass_total") or 0) > 0)]
    rate = (len(regressing) / len(usable)) if usable else None
    return {
        "applying": len(applying), "p2p_usable": len(usable),
        "p2p_regressing": len(regressing), "p2p_missing": len(missing),
        "p2p_regression_rate": round(rate, 3) if rate is not None else None,
    }


def summarize_by_condition(rows: list[RunRow]) -> list[ConditionSummary]:
    by = defaultdict(list)
    for r in rows:
        by[r.condition].append(r)
    out = []
    for cond in sorted(by):
        rs = by[cond]
        out.append(ConditionSummary(
            condition=cond, n=len(rs),
            resolved=sum(r.resolved for r in rs),
            applying=sum(r.patch_applies for r in rs),
            q2_plus=sum(r.quality.startswith(("Q2", "Q3", "Q4", "Q5")) for r in rs),
        ))
    return out


def _binom_cdf(k: int, n: int, p: float = 0.5) -> float:
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1))


def mcnemar_exact(b: int, c: int) -> float:
    """Exact two-sided McNemar p-value for discordant pairs (b, c)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = 2 * _binom_cdf(k, n, 0.5)
    return min(1.0, p)


@dataclass
class PairedContrast:
    condition: str
    baseline: str
    n_pairs: int
    both_resolved: int
    only_treat: int   # treatment resolved, baseline not (b)
    only_base: int    # baseline resolved, treatment not (c)
    neither: int
    delta_rate: float  # treat_rate - base_rate over paired tasks
    mcnemar_p: float
    boot_lo: float
    boot_hi: float


def _paired(rows: list[RunRow], condition: str, baseline: str) -> list[tuple[bool, bool]]:
    """Return (treat_resolved, base_resolved) for tasks present in both (seed 0)."""
    def idx(cond):
        return {r.task_id: r.resolved for r in rows if r.condition == cond and r.seed == 0}
    t, b = idx(condition), idx(baseline)
    common = sorted(set(t) & set(b))
    return [(t[k], b[k]) for k in common]


def paired_contrast(
    rows: list[RunRow], condition: str, baseline: str = "C0_minimal",
    n_boot: int = 5000, seed: int = 0,
) -> PairedContrast:
    pairs = _paired(rows, condition, baseline)
    n = len(pairs)
    both = sum(1 for x, y in pairs if x and y)
    only_t = sum(1 for x, y in pairs if x and not y)
    only_b = sum(1 for x, y in pairs if not x and y)
    neither = sum(1 for x, y in pairs if not x and not y)
    delta = ((both + only_t) - (both + only_b)) / n if n else 0.0
    p = mcnemar_exact(only_t, only_b)
    # Bootstrap CI for the paired difference in resolution rate.
    rng = random.Random(seed)
    diffs = []
    if n:
        for _ in range(n_boot):
            sample = [pairs[rng.randrange(n)] for _ in range(n)]
            tr = sum(x for x, _ in sample) / n
            br = sum(y for _, y in sample) / n
            diffs.append(tr - br)
        diffs.sort()
        lo = diffs[int(0.025 * len(diffs))]
        hi = diffs[int(0.975 * len(diffs)) - 1]
    else:
        lo = hi = 0.0
    return PairedContrast(
        condition=condition, baseline=baseline, n_pairs=n, both_resolved=both,
        only_treat=only_t, only_base=only_b, neither=neither,
        delta_rate=delta, mcnemar_p=p, boot_lo=lo, boot_hi=hi,
    )


@dataclass
class AnalysisReport:
    experiment_id: str
    condition_summaries: list[ConditionSummary]
    contrasts: list[PairedContrast]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "experiment_id": self.experiment_id,
            "condition_summaries": [vars(c) | {"resolution_rate": round(c.resolution_rate, 4)}
                                    for c in self.condition_summaries],
            "contrasts": [vars(c) for c in self.contrasts],
            "warnings": self.warnings,
        }


def analyze(experiment_dir: Path, experiment_id: str,
            baseline: str = "C0_minimal",
            allow_mixed_protocol: bool = False) -> AnalysisReport:
    rows = load_runs(experiment_dir, allow_mixed_protocol=allow_mixed_protocol)
    summaries = summarize_by_condition(rows)
    conds = [s.condition for s in summaries if s.condition != baseline]
    contrasts = [paired_contrast(rows, c, baseline) for c in conds]
    warnings = []
    bad = sum(1 for r in rows if r.manipulation_passed is False)
    if bad:
        warnings.append(f"{bad} runs failed the manipulation check")
    if summaries and summaries[0].n < 20:
        warnings.append(
            f"small cohort (n={summaries[0].n}/condition): directional only, no stats claim"
        )
    return AnalysisReport(experiment_id, summaries, contrasts, warnings)


def format_report(report: AnalysisReport) -> str:
    lines = [f"# Analysis: {report.experiment_id}", ""]
    lines.append("## Resolution by condition")
    lines.append("| condition | n | resolved | applying | >=Q2 | resolution_rate |")
    lines.append("|---|---|---|---|---|---|")
    for s in report.condition_summaries:
        lines.append(f"| {s.condition} | {s.n} | {s.resolved} | {s.applying} | "
                     f"{s.q2_plus} | {s.resolution_rate:.2f} |")
    lines.append("")
    base = report.contrasts[0].baseline if report.contrasts else "C0"
    lines.append(f"## Paired contrasts vs {base}")
    lines.append("| condition | n_pairs | Δresolve | 95% CI | b(only treat) | "
                 "c(only base) | McNemar p |")
    lines.append("|---|---|---|---|---|---|---|")
    for c in report.contrasts:
        lines.append(f"| {c.condition} | {c.n_pairs} | {c.delta_rate:+.2f} | "
                     f"[{c.boot_lo:+.2f}, {c.boot_hi:+.2f}] | {c.only_treat} | "
                     f"{c.only_base} | {c.mcnemar_p:.3f} |")
    if report.warnings:
        lines.append("")
        lines.append("## Caveats")
        for w in report.warnings:
            lines.append(f"- {w}")
    return "\n".join(lines) + "\n"
