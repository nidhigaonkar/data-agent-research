# Local patches (do not fork)

Apply on a fresh clone of the upstream repo. Needed to run a 5-query FDABench subset locally (circular imports, LLM timeout).

## FDABench

From the FDABench clone root:

```bash
git apply /path/to/data-agent-research/patches/fdabench-import-stubs-and-timeout.patch
```

Changes:

- Stub `FDABench` / `PUDDING` package `__init__` imports so PlanningAgent can load without pulling the full package graph
- Raise LLM timeout 20s → 180s in `FDABench/core/base_agent.py`
