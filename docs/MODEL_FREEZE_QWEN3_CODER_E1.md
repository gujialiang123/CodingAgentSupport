# Model freeze — Qwen3-Coder-30B-A3B-Instruct (E1, protocol 0.3.1)

The E1 study is frozen to a single model served via the 302.ai OpenAI-compatible
API, per the user directive to keep the same endpoint/key and switch only the
model. See `configs/models/qwen3_coder_e1.yaml` for the machine-readable manifest.

## Identity

- Model ID (server `model` field, asserted per call): `qwen3-coder-30b-a3b-instruct`
- Intended open-weight family: `Qwen/Qwen3-Coder-30B-A3B-Instruct` (Apache-2.0)
- Endpoint: `https://api.302.ai/v1` (OpenAI-compatible `chat/completions`)

## Inference settings (identical for all E1 conditions)

| Setting | Value |
|---------|-------|
| temperature | 0.0 |
| top_p | server default (not overridden) |
| max output tokens | 4096 |
| seed param sent | none (determinism via temp=0; verified 3/3 identical) |
| stop sequences | none |
| command format | plaintext ```bash``` blocks; all blocks per message run in order (cap 5) |
| max turns | 25 |
| wall-time cap | 900 s / run |
| history window | system message + last 16 messages |
| context cap | uniform per above; single hard token cap not enforced client-side |
| execution | in SWE-bench instance container, `--network none` |

## Provenance limitation (IMPORTANT)

Because the model is consumed through a hosted API, the following **cannot** be
verified or pinned from our side:

- exact Hugging Face repository revision / commit;
- weight-file names and SHA-256 hashes;
- tokenizer revision/hashes; chat-template hash;
- BF16 vs FP8; serving stack (vLLM/SGLang) version; transformers/CUDA/driver.

We assert only the server-returned `model` field per call and freeze all
client-side inference settings. **Publication-grade weight-level reproducibility
would require self-hosting the pinned `Qwen/Qwen3-Coder-30B-A3B-Instruct`
checkpoint** with recorded revision and SHAs. This is documented as a limitation
of the E1 results and a recommended upgrade for any headline rerun.

## Qualification

Endpoint + D0 qualification passed — see
`docs/experiments/013_qwen_model_qualification.md`. The model is frozen; no model
or budget change is permitted during E1.
