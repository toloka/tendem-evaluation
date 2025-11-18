# Tendem Benchmark

This repository contains the benchmark dataset and evaluation results for **Tendem** — a hybrid AI+Human system where AI agents handle structured work and Human Experts ensure quality.

**Product:** [tendem.ai](https://tendem.ai)
**Full Paper:** [Tendem: A Hybrid AI+Human Agentic System](https://toloka.ai/files/tendem_whitepaper.pdf)

---

## Overview

Tendem combines AI automation with human expertise:
- **AI Agents** execute routine tasks (web browsing, data processing, file operations)
- **Human Experts** verify results, handle ambiguous cases, and ensure quality
- **Multi-layer QA** validates every deliverable before client delivery

We evaluated **94 real-world tasks** comparing Tendem against ChatGPT Agent (AI-only) and Upwork freelancers (human-only).

---

## Main Results

| System | Quality (% Good) | Median Time (hours) | Median Price (USD) |
|--------|-----------------|---------------------|-------------------|
| **Tendem** | **74.5%** | **16.4** | **$32** |
| Upwork | 53.2% | 35.0 | $50 |
| ChatGPT Agent | 40.4% | 0.13 | subscription |

**Key Findings:**
- **+21.3pp** higher quality vs Upwork
- **53% faster** delivery than Upwork
- **36% lower** median cost than Upwork

For detailed quality breakdown (Accuracy, Completeness, Style & Formatting), external benchmark results, and methodology, see the [full paper](https://toloka.ai/files/tendem_whitepaper.pdf).

---

## Repository Structure

```
tendem-benchmark/
├── input_tasks.jsonl          # 94 task descriptions
├── output_results.jsonl       # Results with quality ratings & timing
├── input_files/               # Input files by task_id
│   └── {task_id}/
└── output_files/              # System outputs
    ├── gpt/                   # ChatGPT Agent
    ├── tendem/                # Tendem
    └── upwork/                # Upwork freelancers
```

**Quality Scale:** Good (client-ready) | Mediocre (needs edits) | Bad (needs rework) | Decline (refused)

---

## Task Distribution

94 tasks across 4 areas:
- **Operations** (28): Data collection, format conversion, automation
- **Marketing** (24): Content creation, competitive research
- **Analyst** (22): Data analysis, dashboards, research
- **Sales** (20): Contact data, enrichment

---

## Contact

Questions? Visit [tendem.ai](https://tendem.ai) or see the [full paper](https://toloka.ai/files/tendem_whitepaper.pdf).

