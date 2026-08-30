# data-agent-research

Notes for data-agent evaluation: DataAgentBench failure modes and related user-in-the-loop SQL benches. 


## Layout

| Path | What |
| --- | --- |
| `notes/fm-taxonomy.txt` | FM1–FM4 definitions |
| `notes/dab-cross-dataset-error-analysis.md` | gpt-5.5 DAB error writeup |
| `notes/related-work-user-interact.md` | 2025–2026 benches with a user turn |
| `notes/llm-cost-estimation.md` | Token cost formula |

## Cost estimates

`cost = (input_tokens * input_rate) + (output_tokens * output_rate)`. Ignore caching. Rates from the model's published pricing. See `notes/llm-cost-estimation.md`.
