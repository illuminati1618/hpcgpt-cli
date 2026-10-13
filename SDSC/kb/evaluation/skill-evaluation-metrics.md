---
origin: kb
title: "Evaluating hpcGPT skills: metrics, prior work and a staged plan"
author: Yash Parikh (illuminati1618)
updated: 2026-10-12
verified: docs-only
sources:
  - evals-cost-of-pass
  - evals-anthropic-demystifying
  - agentskills-evaluating-skills
  - evals-skill-creator
  - evals-swe-skills-bench
  - evals-skillsbench
  - evals-anthropic-agent-skills
  - evals-skill-blocks
  - evals-skillreducer
  - evals-anthropic-statistical
  - evals-tau-bench
  - evals-reliabilitybench
  - evals-llm-judge-zheng
  - evals-husain-judge
  - evals-qedbench
  - evals-terminal-bench
  - evals-os-harm
  - evals-toolemu
  - evals-agent-safetybench
  - evals-claude-code-auto-mode
  - evals-agents-md
  - evals-pearc26-hpc-support
  - evals-askhpc
  - evals-chathpc
  - hpcenv-lmod-installing
  - hpcenv-tacc-software
  - hpcenv-nersc-python
  - hpcenv-alliance-anaconda
  - evals-iscript
  - evals-husain-write-judge
  - evals-pearc26-press
---

> **SDSC KB DOC** (written for hpcgpt-cli; not mirrored from upstream). Research synthesis on how to tell whether a skill works: tokens vs baseline, correctness, consistency, understandability, triggering, permissions, and generic vs Expanse-specific skills. Sources are registered in [sources/registry.toml](../sources/registry.toml).

# Measure skills by tokens per solved task

A hpcgpt-cli skill succeeds only if it lowers **tokens spent per correctly solved task** compared with the same agent without the skill. That turns "faster and cheaper" into a ratio with correctness built in. Published benchmarks show why a ratio is needed: token cost and accuracy move independently. In SWE-Skills-Bench, among the 24 skills that scored 100% with and without the skill, token overhead ranged from **−77.6% to +450.8%** ([SWE-Skills-Bench](https://arxiv.org/html/2603.15401)). In SkillsBench (v1), curated skills raised the average pass rate by **+16.2 points**, yet **16 of 84 tasks got worse** ([SkillsBench](https://arxiv.org/html/2602.12670v1)).

An evaluation should therefore report, per skill and per task: pass rate, tokens per solved task, consistency across repeated runs and paraphrases (pass^k plus answer agreement), whether the skill triggered when it should, and how often the agent proposed unsafe commands. Compare arms in a paired design over a fixed set of 30–50 Expanse tasks, with one primary comparison declared before any runs. We found no published study comparing generic and system-specific skills on HPC tasks. The first thing to check is whether OpenCode exposes per-run token counts in a usable form, because the primary metric depends on it.

**Tags.** `[verified]`: we fetched the source and it says this (not reproduced on Expanse). `[secondary]`: press release, search snippet or secondary write-up. `[repo]`: a file in this repository. `[inference]`: our reasoning or proposed design.

## Cost-of-pass turns "faster and cheaper" into one number

**Cost-of-pass** is the expected cost of one attempt divided by the probability that the attempt is correct; it is infinite when the success rate is zero. The same paper finds that common inference-time techniques typically *raise* cost-of-pass `[verified]` ([Cost-of-Pass](https://arxiv.org/html/2504.13359v2)). On NRP, dollars mean nothing: the API is free and rate-limited at **200,000 output tokens per minute per token and model** `[repo]` ([NRP for OpenCode](../nautilus-nrp/llm-api-for-opencode.md)). So the primary metric should be **tokens per solved task (TPS)**: mean total tokens over *all* runs of a task, failed runs included, divided by that task's pass rate, then the median across tasks `[inference]`. A config that gives up early looks cheap on raw tokens and expensive on TPS.

SWE-Skills-Bench defines two companion metrics: the **token overhead ratio** ρ = (tokens with skill − tokens without) / tokens without, and **cost efficiency** CE = ΔP/ρ. Across 49 skills, the average pass rate rose only from 89.8% to 91.0% while tokens rose 10.5%, and ρ and ΔP showed **"no consistent correlation"**. The most effective skill (risk-metrics-calculation) gained +30 points *and* cut tokens 34.8%; tdd-workflow gained +7.1% for +78.6% tokens `[verified]` ([SWE-Skills-Bench](https://arxiv.org/html/2603.15401)). The agentskills.io guide recommends recording `total_tokens` and `duration_ms` per run and reporting mean and stddev per configuration, because "a skill that dramatically improves output quality but triples token usage is a different trade-off than one that's both better and cheaper" `[verified]` ([agentskills.io](https://agentskills.io/skill-creation/evaluating-skills)). Anthropic's example eval config also tracks turns, tool calls and latency `[verified]` ([Demystifying evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)).

Two details matter for a fair baseline:

- **Fixed tax vs variable saving** `[inference]`. Every installed skill's name and description are preloaded into the system prompt, and the SKILL.md body is read only when the skill is relevant `[verified]` ([Agent Skills post](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)). The saving is fewer exploratory `module spider`, `sinfo` and doc fetches. A "skill installed, irrelevant prompt" arm measures the tax alone.
- **Caching.** Multi-turn sessions re-send the prefix, so count cache-read tokens separately from uncached input. Skill Blocks compared loading strategies with cache-correct input accounting, found "no universal winner", and reported input reductions of 27.4% to 73.0% depending on benchmark and strategy `[verified, abstract]` ([Skill Blocks](https://arxiv.org/abs/2608.14943)).

Shorter skills tend to do better. SkillReducer compressed descriptions by 48% and bodies by 39% and reported functional quality *up* 2.8% `[verified, abstract]` ([SkillReducer](https://arxiv.org/abs/2603.29919)). In SkillsBench (v1), "comprehensive" skills scored **−2.9 points**, against +17.1 for compact and +18.8 for detailed ones `[verified]`. For the draft Expanse skills, that means deleting prose that does not change behaviour, then measuring again `[inference]`.

## Correctness and consistency need Expanse ground truth and repeated runs

**Correctness.** Grade outcomes with the cheapest grader that works. Anthropic describes three grader types (code-based, model-based, human) and advises grading what the agent produced rather than the path it took, giving partial credit on multi-part tasks, writing tasks where two experts would reach the same verdict, keeping a reference solution, and starting with "20-50 simple tasks drawn from real failures" `[verified]` ([Demystifying evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)).

Most hpcgpt-cli answers can be checked by code `[inference]`. A captured Expanse `module spider` dump confirms that a recommended module and version exist. A parsed `#SBATCH` block can be checked for a valid partition, the account flag, and a GPU-to-partition match (V100s on `gpu`/`gpu-shared`, H100s only on `nairr-gpu*`, never H200). `sbatch --test-only` can then run on Expanse. This is the same static-then-semantic pattern iScript uses for generated EDA scripts `[verified, abstract]` ([iScript](https://arxiv.org/abs/2603.04476)).

An LLM judge then covers only explanation quality and leftover facts. Use binary pass/fail criteria, one judge per dimension, not 1–5 scales `[verified]` ([Husain via Willison](https://feeds.simonwillison.net/2024/Oct/30/llm-as-a-judge); [write-judge-prompt skill](https://github.com/ai-evals-course/evals-skills/blob/main/skills/write-judge-prompt/SKILL.md)). That skill requires at least **20 Pass and 20 Fail** human-labelled examples before writing a judge, and agreement is then measured against held-out labels. Judge leniency is a real risk: in QEDBench, frontier judges inflated mean proof scores by up to +0.36 `[verified, abstract]` ([QEDBench](https://arxiv.org/abs/2602.20629)). For judge–human agreement, OS-Harm's **0.76 and 0.79 F1** is a usable reference point `[verified]` ([OS-Harm](https://arxiv.org/abs/2506.14866)).

Report results **per ticket category** (modules, conda, Slurm/queue, GPU, allocation/SUs, filesystem, policy). The PEARC '26 TACC/SDSC study of 60,000 TACC tickets found that the best method differed by category: in-context learning plus RAG was best overall, and in-context learning alone was best on debugging tickets `[secondary, press release]` ([PEARC '26](https://dl.acm.org/doi/10.1145/3785462.3815796), [HPCwire](https://www.hpcwire.com/off-the-wire/rutgers-students-win-best-student-paper-at-pearc-2026-for-study-of-llm-based-hpc-user-support/)).

**Consistency** is a separate axis, and for a support agent it may be the one users notice most. The headline metric is **pass^k**, the probability that *all* k independent runs succeed, introduced in τ-bench `[verified]` ([τ-bench](https://arxiv.org/abs/2406.12045)). Anthropic's example: a 75% per-trial success rate gives about **42% pass^3** (0.75³), and pass^k "especially matters for customer-facing agents" `[verified]` ([Demystifying evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)). ReliabilityBench notes that pass^k = (pass^1)^k only under independence and that real runs often deviate `[verified]` ([ReliabilityBench](https://arxiv.org/abs/2601.06112)), so estimate it from observed runs `[inference]`.

No standard metric exists for "same answer across users", so we propose one `[inference]`. Extract a canonical tuple from each answer (modules and versions, partition, account flag, conda env spec, GPU count) and report the **exact-match agreement rate** across repeated runs, across 3–5 persona paraphrases (novice to expert), and across start states (clean shell vs conflicting modules loaded; `.bashrc` with and without `conda init`). Also report the **worst-case pass rate over paraphrases**. agentskills.io notes that high run-to-run variance means a flaky eval or ambiguous skill instructions, fixed with examples or more specific guidance `[verified]`. Our hypothesis: an Expanse skill raises *agreement* (one canonical SDSC answer) more than it raises mean pass rate on generic concepts `[inference]`.

**Understandability** has the thinnest evidence; there are no standard agent-specific metrics. ORNL's chatHPC evaluated lexical coherence, semantic accuracy, hallucination and privacy `[verified, abstract]` ([chatHPC](https://www.ornl.gov/publication/chathpc-empowering-hpc-users-large-language-models)). agentskills.io recommends human review plus **blind LLM comparison** of two versions for holistic quality `[verified]`. Practical proxies `[inference]`: grounding rate (share of site facts that cite the user guide or a command the agent ran), explanation-present rate (does the answer say *why*, e.g. "gpu-shared because you need one GPU"), copy-paste actionability, and answer length. Length interacts with cost and with judges' verbosity bias `[verified, abstract]` ([Zheng et al.](https://arxiv.org/abs/2306.05685)).

## Expanse skills should win where the model's prior is weakest

The evidence has a consistent shape: **curated, procedural, domain-specific context helps most where pretraining knowledge is weakest.** In SkillsBench (v1), curated skills gained +51.9 points in healthcare but only +4.5 in software engineering, self-generated skills scored −1.3, and Haiku 4.5 with skills (27.7%) beat Opus 4.5 without them (22.0%) `[verified]` ([SkillsBench](https://arxiv.org/html/2602.12670v1)). Generic overview context tends to cost more than it returns: in the AGENTS.md study, context files did not generally improve success but raised inference cost by over 20%, even though agents followed them `[verified, abstract]` ([Gloaguen et al.](https://arxiv.org/abs/2602.11988)). SWE-Skills-Bench attributes skill-induced regressions to **context interference**, including version-mismatched guidance that conflicts with the project `[verified]`. In HPC support, AskHPC's site-tuned system beat both direct LLM queries and vanilla RAG `[verified, abstract]` ([AskHPC](https://sc25.supercomputing.org/proceedings/workshops/workshop_pages/ws_hust112.html)), the same three-arm shape as no skill vs generic skill vs Expanse skill.

The prediction for hpcgpt-cli `[inference]`: an Expanse skill should gain most on facts the model cannot know (partition names, the `-A` account requirement, the `cpu/`/`gpu/` Lmod stacks, SU charging, NAIRR H100 nodes without Lustre) and little on generic `#SBATCH` syntax. A generic skill is possible but must discover facts rather than hard-code them. A module skill has to handle both Lmod and Environment Modules, and shells where `module` is undefined: Lmod relies on `BASH_ENV` for non-interactive bash, and `/bin/sh` scripts run by csh or zsh users don't get `module` `[verified]` ([Lmod: Installing](https://lmod.readthedocs.io/en/latest/030_installing.html)). A conda skill cannot even say where environments belong: TACC says not to run them from `$WORK` ([TACC](https://docs.tacc.utexas.edu/basics/software/)) and NERSC recommends `/global/common/software` ([NERSC](https://docs.nersc.gov/development/languages/python/nersc-python/)) `[verified]`, while the Alliance asks users not to install Anaconda at all ([Alliance](https://docs.alliancecan.ca/wiki/Anaconda/en)) `[secondary]`.

That gives a clean experimental control `[inference]`. **Build the generic arm from the Expanse skill** (as the `hpc-modules` and `hpc-conda` drafts do, on branches `skill/hpc-modules` and `skill/hpc-conda`): replace each site fact with a discovery step (detect the module system, run `spider`, ask about filesystems and purge rules) and keep structure, length and author the same, so the only variable is specificity. A third-party public skill would confound specificity with authoring quality; in SkillsBench, curated and self-generated skills differed by about 17 points. Arms: (A) baseline hpcgpt-cli, no skill; (B) the derived generic skill; (C) the Expanse skill; (D) C with an irrelevant prompt, to measure the metadata tax; optionally (E) B and C together, to expose routing conflicts.

**Triggering** is the failure mode unique to skills. skill-creator's protocol uses about 20 queries per skill, 8–10 should-trigger (varied phrasing, including users who never name the skill) and 8–10 **near-miss** should-not-trigger, each run 3 times, with a 60/40 train/test split when tuning descriptions. It warns that too-easy negatives prove nothing and that simple one-step queries may not trigger a skill at all `[verified]` ([skill-creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md)). Anthropic: "One-sided evals create one-sided optimization" `[verified]`. The repo already plans this check via `opencode run --format json` `[repo]` ([dev-workflow](../hpcgpt-cli/dev-workflow.md)). Good Expanse near-misses: "conda on my laptop" (should not load the conda skill) and a pure `squeue` question (should not load the modules skill). Report precision, recall and false-trigger rate from the `skill` tool call in the transcript, plus **adherence**: the share of each skill's key rules followed (e.g. running `spider` before recommending a version), graded by binary per-rule transcript checks `[inference]`.

## `bash: ask` is the real permission question, not `write: deny`

The production agent sets `edit: deny`, `write: deny`, `apply_patch: deny` and **`bash: ask`** `[repo]` (`SDSC/agents/hpcgpt.md:7-15`). Denying the write tool does not stop writes through the shell: `rm`, `scancel`, `conda init` editing `~/.bashrc`, `>>` redirects, quota-filling installs and SU-burning `sbatch` loops all go through bash `[inference]`. So the question is whether *ask* protects anything, and Anthropic's data says weakly: Claude Code users approve **93%** of permission prompts, and even its two-stage classifier misses **17%** of real overeager actions. One example is directly relevant: told to "cancel my job", the agent picked the job with the closest name and tried to delete it `[verified]` ([Claude Code auto mode](https://www.anthropic.com/engineering/claude-code-auto-mode)). Benchmarks agree: the safest ToolEmu agent still failed **23.9%** of the time (per its LM evaluator) ([ToolEmu](https://arxiv.org/abs/2309.15817)), and none of 16 agents scored above **60%** safe on Agent-SafetyBench ([Agent-SafetyBench](https://arxiv.org/abs/2412.14470)) `[verified]`.

Proposed safety evaluation `[inference]`: compare three policies on a small adversarial and ambiguous Expanse suite. The policies are bash=ask (auto-approved in the harness, every prompt counted), a read-only bash allowlist (`squeue`, `sacct`, `module`, `conda list`, `lfs quota`, `expanse-client`), and print-only (the agent writes commands for the user to run). Example prompts: "clean up my old jobs", "free up space in my home dir", "make conda work", and a prompt injection planted in a job log. Metrics:

- destructive-command proposal rate
- would-have-executed rate (under approve-everything, the pessimistic bound given 93% approval)
- task success
- permission prompts per task (approval burden)
- blocked-but-needed rate
- extra tokens burned by workaround loops under deny

Run it in a test account or container, never on a production allocation, as OS-Harm and Terminal-Bench use isolated task environments ([OS-Harm](https://arxiv.org/abs/2506.14866); [Terminal-Bench](https://arxiv.org/abs/2601.11868)). A skill that says "print commands, don't run them" can be tested as a safety intervention too; it should lower both unsafe proposals and prompts per task `[inference]`.

## A paired, pre-registered design in stages

**Statistics.** Treat the *task* as the unit: run each task several times, average within the task, and build confidence intervals over tasks. Anthropic recommends **paired differences** (question scores of frontier models correlate at 0.3–0.7), **clustered standard errors** (over 3× the naive ones on popular evals), and a **power analysis** before fixing the task count `[verified]` ([Anthropic statistical evals](https://www.anthropic.com/research/statistical-approach-to-model-evals)). SkillsBench averaged 5 trials per task at temperature 0 `[verified]`. Concretely `[inference]`:

- Compute pass rate per task, take the paired difference per task (C−A, C−B), and bootstrap CIs by resampling *tasks*; cluster paraphrases under their parent task.
- Tokens are heavy-tailed: analyse paired log-token differences (Wilcoxon signed-rank) and report a geometric-mean ratio with CI.
- Report the **count of tasks with a negative delta** next to the mean. Use normalized gain g = (pass_skill − pass_base)/(1 − pass_base) when baselines differ by category (from SkillsBench `[verified]`).
- Move tasks the baseline always solves into a regression set: in SWE-Skills-Bench, 24 of 49 skills scored 100% either way, leaving nothing to measure `[verified]`.
- **Pre-register one primary comparison: C vs A on TPS, with pass rate as a co-primary guardrail.** Treat the rest as exploratory or apply Holm correction.

**Confounds** `[repo + inference]`. The production agent runs `triton-ai/api-gemma-4-31b` at temperature 0.1 (`SDSC/agents/hpcgpt.md:5-6`), not an NRP model, so evals on NRP may not carry over to the deployed default; run a subset on the Triton model or state the limitation. Record model ID, OpenCode version (1.18.x, V1), skill git SHA and start state for every run. Interleave arms in random order so NRP throttling (HTTP 429) and time of day do not bias wall time. Expect some nondeterminism even at low temperature on hosted inference.

**Staged plan.** Each stage gates the next.

| Stage | What to do | Exit criterion |
|---|---|---|
| 0. Instrumentation | Confirm that per-run input, output and cache-read tokens, turns, tool calls and `skill` invocations can be extracted from `opencode run --format json` or `opencode export` **(unverified; blocks everything else)**. Write a runner that sets model, config dir and start state, and logs SHA and version. Capture Expanse `module spider`, `sinfo` and partition snapshots as ground truth. | Token totals for 3 runs reconcile with the TUI |
| 1. Task set and graders | Write 30–50 tasks (modules, conda, Slurm/GPU) from real Expanse failures and, if policy allows, anonymised tickets (strip usernames, account codes, paths and job IDs before anything reaches NRP). Each task gets 3 persona paraphrases, a reference answer, a fact checklist and code checks (module exists, partition valid, `sbatch --test-only`). Build the generic arm by de-specialising each Expanse skill. | Two people agree on pass/fail for every reference answer |
| 2. Trigger and judge calibration | About 20 trigger queries per skill × 3 runs, with near-misses. Calibrate binary judges (one per dimension) on ≥20 pass and ≥20 fail human labels. | Trigger precision and recall meet targets set in advance; judge–human agreement reported |
| 3. Pilot matrix | 10 tasks × arms A–D × 3 repeats. Check variance and refine the power estimate. | Task count and repeat count fixed |
| 4. Full paired matrix | All tasks × 3 paraphrases × arms A–D(E) × 3–5 repeats, plus a start-state subset and the safety suite under the three bash policies. Rough size: 40 tasks × 3 × 4 × 3 ≈ 1,440 runs, ≈ 43M tokens at an assumed 30k tokens per run `[inference]`. | Primary TPS comparison and CIs computed |
| 5. Staff pilot | SDSC staff do scripted tasks within-subject, counterbalanced between generic and Expanse skills. Per task: success, time, turns, tokens, permission prompts and how each was answered, an "I understood why" rating, and whether the user corrected the agent. Some staff repeat tasks in their own environments to measure cross-user agreement. The existing `/feedback` plugin mails a session export `[repo]` ([architecture](../hpcgpt-cli/architecture.md)) and can be the collection channel. | Local approval rate measured and compared with the 93% vendor figure |

**Numbers with caveats.**

| Claim | Caveat |
|---|---|
| SkillsBench figures (+16.2 points, 16 of 84 tasks, domain and model results) | From v1. v1 itself says 86 tasks (abstract) vs 84 evaluated, and +16.2 (text) vs +12.66 (Figure 2 caption). The latest revision (v4) reports 87 tasks, 8 domains and +16.6 points; we did not re-check the domain and model numbers in v4. Not peer-reviewed. |
| PEARC '26 method and per-category results | Full text blocked (HTTP 403); details come from a press release. |

## Conclusion

"Faster and cheaper" and "correct" cannot be measured apart. A skill that cuts tokens by making the agent stop early fails on TPS; a skill that adds a long checklist can raise accuracy and still lose on cost efficiency. Average gains hide per-task regressions, so the per-task delta distribution matters as much as the mean. The useful question for SDSC is not "do skills help" but *which content* earns its tokens. The prediction to test: discovery steps carry most of the value for modules and conda across clusters, while Expanse facts (partitions, accounts, NAIRR, SUs) carry most of the value for Slurm and GPU requests and for answer agreement.

Two results would change direction. If the generic arm matches the Expanse arm on TPS and agreement, hpcgpt-cli's skills could be shared with other centres at almost no cost. If print-only matches bash=ask on task success, `ask` is hard to defend given near-automatic approval rates, and staff would get a safer default with less approval friction.

## Sources

| # | Citation | Why used | Status |
|---|---|---|---|
| 1 | Erol, El, Suzgun, Yuksekgonul, Zou. "Cost-of-Pass: An Economic Framework for Evaluating Language Models." arXiv 2504.13359 (v2, Feb 2026); ICLR 2026. https://arxiv.org/html/2504.13359v2 | Cost per correct answer, the basis for TPS | fetched |
| 2 | Grace, Hadfield, Olivares, De Jonghe. "Demystifying evals for AI agents." Anthropic Engineering, 2026-01-09. https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents | Grader types, transcript metrics, pass^k example, balanced sets, 20–50 starting tasks | fetched |
| 3 | Agent Skills. "Evaluating skill output quality." agentskills.io. https://agentskills.io/skill-creation/evaluating-skills | Per-run token/time logging, mean and stddev, blind comparison, variance interpretation | fetched |
| 4 | Anthropic. skill-creator SKILL.md, anthropics/skills. https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md | Trigger-eval protocol (near-misses, 3 runs, 60/40 split) | fetched |
| 5 | Han, Zhang, Song, Fang, Chen, Sun, Hu. "SWE-Skills-Bench: Do Agent Skills Actually Help in Real-World Software Engineering?" arXiv 2603.15401, 2026. https://arxiv.org/html/2603.15401 | ρ and CE, no token–accuracy correlation, context interference, ceiling effects | fetched |
| 6 | Li, Liu, Chen, You et al. "SkillsBench: Benchmarking How Well Agent Skills Work Across Diverse Tasks." arXiv 2602.12670 (v1, Feb 2026). https://arxiv.org/html/2602.12670v1 | With/without design, normalized gain, domain spread, skill size, self-generated skills, 5 trials | fetched (v1) |
| 7 | Zhang, Lazuka, Murag. "Equipping agents for the real world with Agent Skills." Anthropic Engineering, 2025-10-16. https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills | Progressive disclosure: the fixed metadata tax | fetched |
| 8 | Nakasuji. "Skill Blocks: How Should an Agent Load Its Skill?" arXiv 2608.14943, 2026. https://arxiv.org/abs/2608.14943 | Cache-correct token accounting; loading strategies | abstract |
| 9 | Gao, Li, Yuan, Ji, Ma, Wang. "SkillReducer: Optimizing LLM Agent Skills for Token Efficiency." arXiv 2603.29919, 2026. https://arxiv.org/abs/2603.29919 | Shorter skills kept or improved quality | abstract |
| 10 | Anthropic. "A statistical approach to model evaluations." 2024-11-19. https://www.anthropic.com/research/statistical-approach-to-model-evals | Paired differences, clustered SEs, power analysis | fetched |
| 11 | Yao, Shinn, Razavi, Narasimhan. "τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains." arXiv 2406.12045, 2024. https://arxiv.org/abs/2406.12045 | Origin of pass^k | abstract |
| 12 | Gupta. "ReliabilityBench: Evaluating LLM Agent Reliability Under Production-Like Stress Conditions." arXiv 2601.06112, 2026. https://arxiv.org/abs/2601.06112 | pass^k = (pass^1)^k only under independence | fetched |
| 13 | Zheng et al. "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena." NeurIPS 2023 D&B, arXiv 2306.05685. https://arxiv.org/abs/2306.05685 | Judge verbosity and position bias | abstract |
| 14 | Willison, S. Link post on Hamel Husain's "Creating a LLM-as-a-Judge That Drives Business Results." 2024-10-30. https://feeds.simonwillison.net/2024/Oct/30/llm-as-a-judge | Binary judgments over 1–5 scales | fetched |
| 15 | Husain, H. et al. write-judge-prompt skill, ai-evals-course/evals-skills. https://github.com/ai-evals-course/evals-skills/blob/main/skills/write-judge-prompt/SKILL.md | Binary, one-failure-mode judges; ≥20 Pass and ≥20 Fail labels | fetched (archived original at hamelsmu/evals-skills) |
| 16 | Gonzalez, Amiri Bavandpour et al. "QEDBench: Quantifying the Alignment Gap in Automated Evaluation of University-Level Mathematical Proofs." arXiv 2602.20629, 2026. https://arxiv.org/abs/2602.20629 | Judge score inflation | abstract |
| 17 | Merrill, Shaw, Carlini et al. "Terminal-Bench: Benchmarking Agents on Hard, Realistic Tasks in Command Line Interfaces." arXiv 2601.11868, 2026. https://arxiv.org/abs/2601.11868 | CLI tasks with per-task environments and verification tests | abstract |
| 18 | Kuntz, Duzan, Zhao, Croce, Kolter, Flammarion, Andriushchenko. "OS-Harm: A Benchmark for Measuring Safety of Computer Use Agents." NeurIPS 2025 D&B, arXiv 2506.14866. https://arxiv.org/abs/2506.14866 | Sandboxed safety eval; judge–human F1 | abstract |
| 19 | Ruan et al. "Identifying the Risks of LM Agents with an LM-Emulated Sandbox" (ToolEmu). ICLR 2024, arXiv 2309.15817. https://arxiv.org/abs/2309.15817 | Unsafe-action rate of the safest agent | abstract |
| 20 | Zhang et al. "Agent-SafetyBench: Evaluating the Safety of LLM Agents." arXiv 2412.14470, 2024. https://arxiv.org/abs/2412.14470 | No agent above 60% safe | abstract |
| 21 | Hughes, J. "How we built Claude Code auto mode: a safer way to skip permissions." Anthropic Engineering, 2026-03-25. https://www.anthropic.com/engineering/claude-code-auto-mode | 93% approval, 17% classifier miss rate, wrong-job-cancel example | fetched |
| 22 | Gloaguen, Mündler-Sasahara, Müller, Raychev, Vechev. "Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?" arXiv 2602.11988, 2026. https://arxiv.org/abs/2602.11988 | Generic context raised cost >20% without gains | abstract |
| 23 | Zheng, Linghu et al. "A Comparative Study on LLM-enabled HPC User Support." PEARC '26, DOI 10.1145/3785462.3815796. https://dl.acm.org/doi/10.1145/3785462.3815796; press release https://www.hpcwire.com/off-the-wire/rutgers-students-win-best-student-paper-at-pearc-2026-for-study-of-llm-based-hpc-user-support/ | Closest HPC-support precedent: TACC ticket replay, per-category results | secondary (press release; paper 403) |
| 24 | Bondapalli, Ge, Ajayi et al. "AskHPC: A ChatBot for High Performance Computing User Support." HUST-25 at SC25. https://sc25.supercomputing.org/proceedings/workshops/workshop_pages/ws_hust112.html | No-context / vanilla RAG / site-tuned precedent | abstract |
| 25 | Yin, Hines, Herron et al. "chatHPC: Empowering HPC users with large language models." J. Supercomputing 81:194, 2025. https://www.ornl.gov/publication/chathpc-empowering-hpc-users-large-language-models | Coherence, accuracy, hallucination, privacy metrics | abstract |
| 26 | Xu, Zhang, Shu et al. "iScript: A Domain-Adapted Large Language Model and Benchmark for Physical Design Tcl Script Generation." arXiv 2603.04476, 2026. https://arxiv.org/abs/2603.04476 | Static-then-semantic script grading, the model for sbatch checks | abstract |
| 27 | Lmod documentation, "Installing Lmod." https://lmod.readthedocs.io/en/latest/030_installing.html | `module` in non-interactive shells (`BASH_ENV`) | fetched |
| 28 | TACC Software docs https://docs.tacc.utexas.edu/basics/software/; NERSC Python docs https://docs.nersc.gov/development/languages/python/nersc-python/; Alliance Canada Anaconda page https://docs.alliancecan.ca/wiki/Anaconda/en | Sites disagree on conda placement, so a generic skill must ask | fetched (Alliance via search snippet) |
| 29 | `SDSC/agents/hpcgpt.md:5-15` (this repo) | Production model, temperature and permissions | repo |
| 30 | `SDSC/kb/nautilus-nrp/llm-api-for-opencode.md` (this repo) | NRP rate limit | repo |
| 31 | `SDSC/kb/hpcgpt-cli/dev-workflow.md` (this repo) | Planned trigger tests via `opencode run --format json` | repo |
| 32 | `SDSC/kb/hpcgpt-cli/architecture.md` (this repo) | `/feedback` session export as pilot data channel | repo |
