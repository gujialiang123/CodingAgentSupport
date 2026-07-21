"""Support layer: the experimental conditions C0-C6 and their generators."""

from se_support.support.bundle import (
    SupportArtifact,
    SupportBundle,
    SupportBundleManifest,
    build_bundle,
)
from se_support.support.condition import (
    CONDITIONS,
    SupportCondition,
    get_condition,
)
from se_support.support.gates import blocking_failures, run_gates
from se_support.support.harness import HarnessState, HarnessStateMachine
from se_support.support.prompts import build_system_prompt

__all__ = [
    "SupportCondition",
    "CONDITIONS",
    "get_condition",
    "build_system_prompt",
    "run_gates",
    "blocking_failures",
    "SupportBundle",
    "SupportArtifact",
    "SupportBundleManifest",
    "build_bundle",
    "HarnessStateMachine",
    "HarnessState",
]
