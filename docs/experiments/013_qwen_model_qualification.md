# Experiment 013 — Qwen model freeze + D0 qualification

Freezes the E1 model and confirms it is usable with the scaffold before any E1
run. **Not** a model comparison and **not** part of paper statistics.

## Frozen model

- **Model ID:** `qwen3-coder-30b-a3b-instruct` (intended open-weight family
  `Qwen3-Coder-30B-A3B-Instruct`, Apache-2.0).
- **Serving:** 302.ai OpenAI-compatible endpoint `https://api.302.ai/v1` (per user
  directive — same endpoint/key as prior runs; not self-served vLLM).
- **Settings:** temperature 0.0, max_output_tokens 4096, plaintext ```bash```
  command format (multi-block per message, cap 5), 25 turns, 900 s wall-time cap,
  history window 16, in-container, `--network none`.
- Full manifest: `configs/models/qwen3_coder_e1.yaml`,
  `docs/MODEL_FREEZE_QWEN3_CODER_E1.md`.

### Provenance limitation (accepted)

Served via API, so exact HF revision and weight-file SHAs are **not verifiable**.
The server `model` field is asserted on every call (returns
`qwen3-coder-30b-a3b-instruct`). Weight-level reproducibility would require
self-hosting the pinned checkpoint — recorded as a known limitation.

## Endpoint qualification

| Check | Result |
|-------|--------|
| Server `model` field matches | ✓ `qwen3-coder-30b-a3b-instruct` |
| Determinism (temp=0, 3× same prompt) | ✓ 3/3 identical |
| `max_tokens` respected | ✓ (=20 → 20 completion tokens) |
| Usage + latency logged | ✓ (~1.5 s/short call) |

## D0 qualification run (6 tasks × C0 × seed 0)

Deterministically selected 6 D0 tasks over 5 repos
(`data/partitions/d0_qual6.jsonl`). Bounded budget (900 s wall-time, block cap 5,
history window 16).

| Task | applies | resolved |
|------|---------|----------|
| requests-1142 | ✗ | ✗ |
| flask-5014 | ✓ | ✗ |
| xarray-3677 | ✗ | ✗ |
| pytest-10051 | ✓ | ✗ |
| requests-1724 | ✓ | ✓ |
| pylint-4551 | ✓ | ✗ |

**Applying 4/6, resolved 1/6, infrastructure failures 0.**

### Verdict: PASS

- Not 0/6 and not 6/6 resolved ✓
- Applying-patch rate ≥ 4/6 ✓
- Infra failures = 0 ✓
- Agent uses shell/edit/test tools and produces real patches ✓

### Scaffold compatibility fix (found during qualification)

The first (unbounded) qualification run exposed two model-driven pathologies,
fixed **before** E1 (model-agnostic, pre-registered):
1. Qwen3-Coder emits many ```bash``` blocks per message → the scaffold now runs
   all blocks per message (cap 5) instead of only the first (otherwise empty
   patches).
2. Verbose runs accumulated 200+ commands → unbounded context slowed the API to a
   crawl. Added a 900 s wall-time cap and a sliding history window (system + last
   16 messages).

The model is frozen. No model or budget change is permitted during E1.
