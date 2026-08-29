# data-agent-research

Notes and run artifacts for data-agent evaluation (DataAgentBench, FDABench, related interactive SQL benches). Not a fork of those projects.

Not in this repo: cloned benches, databases, venvs, or API keys.

## Layout

| Path | What |
| --- | --- |
| `notes/` | FM1–FM4 taxonomy, DAB error writeup, related work, FDABench 5-query recap |
| `experiments/fdabench/` | 5 FDABench-Lite queries (runner + summaries) |
| `patches/` | Local FDABench import/timeout patch as a diff, not a full fork |

## What is not here

- `ucbepic/DataAgentBench`, `fdabench/FDAbench` (use those remotes)
- `bird_databases/`, `.env`

## Cost estimates

`cost = (input_tokens * input_rate) + (output_tokens * output_rate)`. Ignore caching. Rates from the model's published pricing. See `notes/llm-cost-estimation.md`.
