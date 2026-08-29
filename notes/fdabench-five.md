# FDABench five-query spot check

gpt-5.5, official PlanningAgent, August 2026. Treat 2/5 as a check that FM1–FM4 travel, not a new accuracy claim. FDABench does not replace DAB (multi-DB, dirty IDs, hints).

## FDABench-Lite (BIRD SQLite)

`experiments/fdabench/selected_five/summary.json`

| Task | Gold → pred | Result |
| --- | --- | --- |
| FDA0804 | A / A | pass |
| FDA0791 | D → C | fail |
| FDA0792 | B → A | fail |
| FDA0794 | B → D | fail |
| FDA0788 | B / B | pass |

2/5. ~65k total tokens stored without I/O split. Frozen web/vector evidence instead of live Perplexity. Runner used local import stubs + 180s LLM timeout (`patches/fdabench-import-stubs-and-timeout.patch`).

How it maps: FM2 after successful SQL (wrong extra formula); planner skip SQL on at least one fail.

Upstream: [FDABench](https://github.com/fdabench/FDAbench). Paper: [arxiv](https://arxiv.org/html/2509.02473v2).
