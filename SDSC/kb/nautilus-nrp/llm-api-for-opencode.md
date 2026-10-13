---
origin: kb
title: Using the NRP (Nautilus) LLM API with OpenCode / hpcgpt-cli
author: Yash Parikh (illuminati1618)
updated: 2026-10-12
verified: docs-only
sources:
  - nrp-llm-managed
  - nrp-llm-api-access
  - nrp-llm-client-configs
  - nrp-llm-model-catalog
  - nrp-llm-fair-use
  - nrp-llm-lifecycle
  - nrp-llm-token
  - nrp-llm-status
  - opencode-v1-providers
  - opencode-v1-config
  - opencode-v1-agents
  - opencode-v1-models
  - hpcgpt-mkandes-notes
  - nrp-llm-status-page
  - nrp-aup
---

> **SDSC KB DOC** (written for hpcgpt-cli; not mirrored from upstream). How to point the SDSC hpcgpt-cli pack (OpenCode **V1**) at NRP's free managed LLMs. NRP's own [client-configs page](https://nrp.ai/documentation/userdocs/ai/llm-managed/client-configs/) gives OpenCode configs in the **V2** shape. This page is the V1 translation plus the NRP rules that matter for an agent. The endpoint and the unauthenticated `/v1/models` list were checked live on 2026-10-12; the token test and provider block were not run.

# Using the NRP LLM API with OpenCode / hpcgpt-cli

## Get access and a token

1. Log in at <https://nrp.ai> with CILogon (pick your institution).
2. Be a member of a **group (namespace) that has the LLM flag**. Check at <https://nrp.ai/namespaces>. Students get added
   by their advisor ([getting started](https://nrp.ai/documentation/userdocs/start/getting-started/)).
3. Create a token at <https://nrp.ai/llmtoken> ([API access](https://nrp.ai/documentation/userdocs/ai/llm-managed/api-access/)).
4. Test it. `/v1/models` answers **without** a token (checked 2026-10-12), so it proves nothing about your key; send a
   tiny chat request instead. `200` means the token works; without a token the gateway returns `403`.

```bash
export NRP_LLM_API_KEY='...'      # the env var SDSC/opencode.jsonc references (NRP's own recipe uses NRP_API_KEY)
curl -s -o /dev/null -w '%{http_code}\n' https://ellm.nrp-nautilus.io/v1/chat/completions \
  -H "Authorization: Bearer $NRP_LLM_API_KEY" -H 'Content-Type: application/json' \
  -d '{"model":"gpt-oss","messages":[{"role":"user","content":"Say OK"}],"max_tokens":16}'
```

Endpoint: `https://ellm.nrp-nautilus.io/v1`, OpenAI-compatible (chat/completions, models), served through an Envoy AI
Gateway. There's also an Anthropic-compatible route at `/anthropic`.

## Which model for hpcGPT?

From NRP's [model catalog](https://nrp.ai/documentation/userdocs/ai/llm-managed/models/) and [fair use](https://nrp.ai/documentation/userdocs/ai/llm-managed/fair-use/) page. The live `/v1/models` list also shows ids that aren't in the catalog (`gemma-vl`, `qwen3-vl`, `gemma4-*`, `gemma-small-e4b`); stick to catalog aliases.

| Alias | Status | Size | Context | Output limit* | Per-user concurrency | Notes for an HPC support agent |
|---|---|---|---|---|---|---|
| `qwen3` | main | 180B MoE (6B active) | 1,000,000 | 65,536 | 16 | **Best default**: top agentic-coding score in the catalog, high concurrency. Reasoning defaults to `xhigh` and it's verbose |
| `qwen3-small` | main | 27B | 1,000,000 | 65,536 | 8 | NRP's pick for session titles; cheaper subagents |
| `gpt-oss` | main | 120B | 131,072 | 32,768 | 16 | Strong tool calling, text-only, NRP's long-term-support candidate |
| `gemma` | main | 31B (4-bit QAT) | 262,144 | 32,768 | 8 | Gemma 4 31B, the same model family as SDSC's current Triton default (`api-gemma-4-31b`) |
| `glm-5` | evaluating | 753B | 1,048,576 | 65,536 | 2 | Strong, but concurrency is only 2 |
| `kimi`, `minimax-m2`, `deepseek-v4-flash`, `gemma-small` | evaluating | | | | 2–8 | May change or disappear ([lifecycle](https://nrp.ai/documentation/userdocs/ai/llm-managed/lifecycle/)) |

\*Output limits come from NRP's own OpenCode recipe. **Never set output to the full context** (the request errors); if a
client needs a value, NRP suggests about ⅓–¼ of the context. Concurrency limits are not enforced automatically, but are
NRP policy.

**Always use aliases** (`qwen3`, not a Hugging Face or served-model name). NRP swaps weights behind aliases, as with
Qwen3.5 → Qwen3.8 in August 2026.

## OpenCode V1 provider block (drop-in for `SDSC/opencode.jsonc`)

In V1 the key under `models` **is the model id sent to the API**, and `name` is just the label
([providers](https://opencode.ai/docs/providers)). SDSC's existing `nrp` block already uses the aliases as keys; its
labels name specific checkpoints and go stale when NRP swaps weights. Add `"nrp"` to `enabled_providers`, or the
provider stays hidden ([known-issues A10](../hpcgpt-cli/known-issues.md)); SDSC's own
[Expanse test of NRP](https://github.com/mkandes/notes/blob/main/2026/10/12a.md) does exactly that and sets the
top-level `model` to `nrp/gemma`.

```jsonc
{
  "enabled_providers": ["nrp", "triton-ai"],
  "model": "nrp/qwen3",
  "small_model": "nrp/qwen3-small",          // titles/summaries; keeps load off big GPUs
  "provider": {
    "nrp": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "NRP (Nautilus)",
      "options": {
        "baseURL": "https://ellm.nrp-nautilus.io/v1",
        "apiKey": "{env:NRP_LLM_API_KEY}"
      },
      "models": {
        "qwen3":       { "name": "qwen3 (NRP)",       "limit": { "context": 1000000, "output": 65536 } },
        "qwen3-small": { "name": "qwen3-small (NRP)", "limit": { "context": 1000000, "output": 65536 } },
        "gpt-oss":     { "name": "gpt-oss (NRP)",     "limit": { "context": 131072,  "output": 32768 } },
        "gemma":       { "name": "gemma (NRP)",       "limit": { "context": 262144,  "output": 32768 } },
        "glm-5":       { "name": "glm-5 (NRP)",       "limit": { "context": 1048576, "output": 65536 } }
      }
    }
  }
}
```

- Which model a session uses: an agent's own `model` overrides the top-level `model`
  ([agents](https://opencode.ai/docs/agents)). `SDSC/agents/hpcgpt.md:5` pins `triton-ai/api-gemma-4-31b`, but because
  of [known-issues A0](../hpcgpt-cli/known-issues.md) the default agent `hpcgpt` is a bare agent without a `model`, so
  today the top-level `model` is what users get. Once A0 is fixed, the agent's pin wins: change it too, or switch with
  `/models` in the TUI. Whether `-m` beats an agent-pinned model is **unverified**
  ([checklist O7](../expanse/verify-on-expanse.md)).
- `small_model` is the documented V1 key for lightweight tasks such as titles ([config](https://opencode.ai/docs/config)).
- The provider `name` is mixed-case here and in SDSC's config. NRP warns that `/models` hides a mixed-case provider in its
  V2 `/connect` flow; whether V1 cares is untested.
- Reasoning controls are per model: `qwen3`/`qwen3-small` take a top-level `reasoning_effort` (`low`, `medium`, `xhigh`)
  and `chat_template_kwargs.enable_thinking: false`; `glm-5` and `deepseek-v4-flash` take `reasoning_effort` inside
  `chat_template_kwargs` ([client configs](https://nrp.ai/documentation/userdocs/ai/llm-managed/client-configs/)).
  Turning thinking **off** for simple support questions saves tokens and latency. V1 has `models.<id>.options` and
  `variants` ([models](https://opencode.ai/docs/models)); whether they pass these fields through
  `@ai-sdk/openai-compatible` is untested.

## Rules that affect an agent deployment

From [fair use](https://nrp.ai/documentation/userdocs/ai/llm-managed/fair-use/) and [API access](https://nrp.ai/documentation/userdocs/ai/llm-managed/api-access/):

- **200,000 output tokens/minute per token and model** (HTTP 429 beyond that; input tokens don't count). Watch the
  `x-ratelimit-remaining` and `x-ratelimit-reset` headers.
- **Concurrency**: requests using ≥ 35% of a model's context are limited to **1 at a time per user**. Keep hpcGPT
  sessions compact (`/compact`), and don't dump huge logs into context.
- SDSC and Internet2 contributed GPU nodes, so **their affiliates get 2× limits** and can arrange higher-volume
  sessions. That's relevant if hpcGPT serves many Expanse users through one token.
- **Prompt caching is shared across a tenant** unless you send a `cache_salt` (a secret, base64-encoded random value of
  at least 256 bits; vLLM/SGLang models). A multi-user hpcGPT deployment on one shared key should set one per user, since
  cached prompts could otherwise mix across users. How to send it from OpenCode V1 is untested.
- Non-commercial use only ([AUP](https://nrp.ai/NRP-AUP.pdf)). Models can go down for maintenance, so clients should retry
  with backoff. Live status: [nrp.ai/llm-status](https://nrp.ai/llm-status),
  [nautilus-llm-status](https://github.com/nrp-nautilus/nautilus-llm-status), and the Grafana board linked from the
  fair-use page.

## Triton AI vs NRP (current SDSC default vs alternative)

| | Triton AI (`tritonai-api.ucsd.edu`) | NRP (`ellm.nrp-nautilus.io/v1`) |
|---|---|---|
| Who | UCSD campus AI service | National Research Platform (SDSC contributes GPUs) |
| Key | `TRITON_AI_API_KEY` (UCSD) | `NRP_LLM_API_KEY` (nrp.ai/llmtoken, LLM-flagged namespace) |
| SDSC config ids | `api-gemma-4-31b` (default) and others in `SDSC/opencode.jsonc` | aliases above |
| Model list | <https://tritonai-api.ucsd.edu/ui/model_hub_table> | `GET /v1/models`, [catalog](https://nrp.ai/documentation/userdocs/ai/llm-managed/models/) |
