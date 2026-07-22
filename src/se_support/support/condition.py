"""Support-condition system (T4): the experimental independent variable.

A :class:`SupportCondition` toggles the five support structures. The **same**
agent + model is run under different conditions; only these flags change, which
is what makes the ablation causal.

Two mechanisms implement the toggles (see docs/experiment_protocol.md §5):
* prompt/artifact injection -- ``context`` and ``memory`` add text to the prompt.
* loop/tool interception -- ``gates`` validate before accepting a patch,
  ``harness`` enforces workflow phases, ``tests`` supplies reproduction tests.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SupportCondition:
    id: str
    context: bool = False
    tests: bool = False
    gates: bool = False
    harness: bool = False
    memory: bool = False

    @property
    def is_full_stack(self) -> bool:
        return all((self.context, self.tests, self.gates, self.harness, self.memory))


# PROJECT_PROPOSAL.md §6 condition table (one-factor-at-a-time + full stack).
CONDITIONS: dict[str, SupportCondition] = {
    "C0_minimal": SupportCondition("C0_minimal"),
    "C1_context": SupportCondition("C1_context", context=True),
    "C2_tests": SupportCondition("C2_tests", tests=True),
    "C3_gates": SupportCondition("C3_gates", gates=True),
    "C4_harness": SupportCondition("C4_harness", harness=True),
    "C5_memory": SupportCondition("C5_memory", memory=True),
    "C6_full_stack": SupportCondition(
        "C6_full_stack", context=True, tests=True, gates=True, harness=True, memory=True
    ),
    # Diagnostic condition (Exp 009A): full stack WITHOUT the enforced harness,
    # to isolate whether C6's deficit is driven by the C4 state machine overhead.
    "C6_minus_C4": SupportCondition(
        "C6_minus_C4", context=True, tests=True, gates=True, harness=False, memory=True
    ),
}


def get_condition(condition_id: str) -> SupportCondition:
    try:
        return CONDITIONS[condition_id]
    except KeyError as exc:
        raise KeyError(
            f"unknown condition '{condition_id}'; valid: {', '.join(CONDITIONS)}"
        ) from exc
