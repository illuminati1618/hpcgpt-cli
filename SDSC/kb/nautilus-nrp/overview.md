---
origin: kb
title: NRP / Nautilus — what it is and how it relates to this project
author: Yash Parikh (illuminati1618)
updated: 2026-10-12
verified: docs-only
sources:
  - nrp-getting-started
  - nrp-using-nautilus
  - nrp-policies
  - nrp-gpu-pods
  - nrp-resources
  - nrp-llm-managed
  - nrp-support
  - hpcgpt-mkandes-notes
  - nrp-contact
  - expanse-sdsc-systems-nrp
---

> **SDSC KB DOC** (written for hpcgpt-cli; not mirrored from upstream). Orientation only. The [NRP docs](https://nrp.ai/documentation/) are the authority.

# NRP / Nautilus

**What it is:** the National Research Platform, a **Kubernetes** cluster ("Nautilus") of contributed CPUs, GPUs, FPGAs
and storage spread across the US (plus a few sites in Asia and Europe). SDSC lists it among the systems it operates. It's a
completely different model from Expanse:

| | Expanse | NRP/Nautilus |
|---|---|---|
| Scheduler | Slurm (`sbatch`, `srun`) | Kubernetes (`kubectl`, Job/Deployment/Pod YAML) |
| Access | ACCESS allocation (SUs), SSH + 2FA | CILogon → namespace membership; kubeconfig via kubelogin |
| Cost model | charged SUs against an allocation | free, but **utilization-policed** (bans for idle requests) |
| GPUs | V100, H100 (NAIRR) | many types, incl. A100 (on request), H100/H200/GH200 (**contributors only**, or preemptible via `priorityClassName: opportunistic`) |
| Role in this project | where researchers run work; what hpcGPT helps with | **free managed LLM API** that can power the agent ([llm-api-for-opencode](llm-api-for-opencode.md)); optionally hosting services |

## Why it matters here

1. **LLM backend.** `https://ellm.nrp-nautilus.io/v1` (OpenAI-compatible) serves `qwen3`, `gpt-oss`, `glm-5` and more for
   free to members of a group with the LLM flag. It is defined, but not in `enabled_providers`, in `SDSC/opencode.jsonc`.
2. **Where the H200s are.** If a researcher asks about H200s, they're thinking of NRP, not Expanse. Even there they're
   not user-requestable, except as preemptible opportunistic pods ([gpu-pods](https://nrp.ai/documentation/userdocs/running/gpu-pods/)).
3. **Hosting.** Long-running services (a shared hpcGPT MCP server, a RAG backend) belong on Kubernetes, never on
   Expanse login nodes. SDSC's hpcGPT Chat backend has been deployed for testing on SDSC's Voyager
   ([Aug 2026 notes](https://github.com/mkandes/notes/blob/main/2026/08/14a.md)). On NRP, a service needs a Deployment, and
   Deployments are deleted after 2 weeks unless the namespace gets an exception for a permanent service. OSC's Helm chart in `charts/osc-mcp` is a
   starting point.

## Policies that bite (if you run anything on Nautilus itself)

From [cluster policies](https://nrp.ai/documentation/userdocs/start/policies/):

- Use a **Job** for batch work and a **Deployment** for long-running services with minimal requests. Bare pods count as
  "interactive": max 2 GPUs / 32 GB / 16 cores, **deleted after 6 hours**.
- Pods must use what they request: GPU > 40%, CPU 20–200%, RAM 20–150% of requests. A user may not have more than
  4 pods outside these ranges, and namespaces that keep under-using their requests get banned. A **Job that ends in
  `sleep` gets you banned**.
- `limits` must be within 20% of `requests`. Storage not accessed for **6 months can be purged** without notice.
- Join Nautilus Support (Matrix) for help and announcements ([contact](https://nrp.ai/contact/)).

## Other NRP services you may touch

JupyterHub ([docs](https://nrp.ai/documentation/userdocs/jupyter/jupyterhub/)), Coder remote dev environments ([docs](https://nrp.ai/documentation/userdocs/coder/coder/)),
chat UIs for the managed LLMs ([docs](https://nrp.ai/documentation/userdocs/ai/llm-managed/chat-interfaces/)), and an accounting MCP server
([docs](https://nrp.ai/documentation/userdocs/ai/accounting-mcp/)).
