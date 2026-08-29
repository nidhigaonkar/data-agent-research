#!/usr/bin/env python3
"""Run 5 FDABench-Lite single-choice queries with the official PlanningAgent."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

load_dotenv()  # OPENAI_API_KEY / AGENT_MODEL_API_KEY; optional .env in cwd

from FDABench.agents.planning_agent import PlanningAgent
from FDABench.tools.schema_tools import SchemaInfoTool
from FDABench.tools.sql_tools import (
    SQLDebugTool,
    SQLExecutionTool,
    SQLGenerationTool,
    SQLOptimizationTool,
)
from FDABench.utils.database_connection_manager import DatabaseConnectionManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("run_five")

TASKS_PATH = ROOT / "selected_five" / "tasks.jsonl"
RESULTS_PATH = ROOT / "selected_five" / "results.jsonl"
BIRD_DB_PATH = str(ROOT / "bird_databases")
MODEL = os.environ.get("FDA_MODEL", "gpt-5.5")


class FrozenEvidenceTool:
    """Return construction-time frozen search evidence instead of live APIs."""

    def __init__(self, kind: str):
        self.kind = kind
        self.payload = None

    def execute(self, query: str = None, **kwargs):
        if not self.payload:
            return {
                "status": "success",
                "results": f"No frozen {self.kind} evidence available for this task.",
            }
        parts = []
        for search in self.payload.get("searches", []):
            summary = search.get("context_summary")
            files = search.get("results") or []
            file_names = [item.get("file_name", "") for item in files if isinstance(item, dict)]
            parts.append(
                f"query: {search.get('query', query)}\n"
                f"summary: {summary or '(filenames only)'}\n"
                f"files: {', '.join(file_names)}"
            )
        return {"status": "success", "results": "\n\n".join(parts) or str(self.payload)}


class ContextHistoryTool:
    def execute(self, **kwargs):
        return {"status": "success", "results": "Context history is empty for this standalone run."}


class FileSystemTool:
    def execute(self, **kwargs):
        return {
            "status": "success",
            "results": "No extra local files beyond the SQLite database for this task.",
        }


def load_tasks():
    tasks = []
    with TASKS_PATH.open() as f:
        for line in f:
            if line.strip():
                tasks.append(json.loads(line))
    return tasks


def normalize_choice(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip().upper().replace("[", "").replace("]", "").replace("'", "") for v in value]
    text = str(value).strip().upper()
    for ch in ["[", "]", "'", '"']:
        text = text.replace(ch, "")
    letters = [tok.strip() for tok in text.replace(",", " ").split() if tok.strip() in list("ABCDEFGH")]
    return letters or [text]


def build_agent():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is not set")

    agent = PlanningAgent(
        model=MODEL,
        api_base="https://api.openai.com/v1",
        api_key=api_key,
        max_planning_steps=8,
        max_execution_time=600,
    )
    agent.db_manager = DatabaseConnectionManager(
        config_overrides={"bird_db_path": BIRD_DB_PATH}
    )

    web_tool = FrozenEvidenceTool("web")
    vector_tool = FrozenEvidenceTool("vector")
    agent._frozen_web = web_tool
    agent._frozen_vector = vector_tool

    agent.register_tool(
        "get_schema_info",
        SchemaInfoTool(agent.db_manager),
        category="database",
        description="Get database schema information",
    )
    sql_gen = SQLGenerationTool(llm_client=agent, db_manager=agent.db_manager)
    agent.register_tool("generated_sql", sql_gen, category="database", description="Generate SQL")
    agent.register_tool("generate_sql", sql_gen, category="database", description="Generate SQL")
    agent.register_tool(
        "execute_sql",
        SQLExecutionTool(agent.db_manager),
        category="database",
        description="Execute SQL queries",
    )
    agent.register_tool(
        "sql_optimize",
        SQLOptimizationTool(llm_client=agent, db_manager=agent.db_manager),
        category="database",
        description="Optimize SQL queries",
    )
    agent.register_tool(
        "sql_debug",
        SQLDebugTool(llm_client=agent, db_manager=agent.db_manager),
        category="database",
        description="Debug SQL query errors",
    )
    agent.register_tool("web_context_search", web_tool, category="search", description="Frozen web evidence")
    agent.register_tool("perplexity_search", web_tool, category="search", description="Frozen web evidence")
    agent.register_tool("web_search", web_tool, category="search", description="Frozen web evidence")
    agent.register_tool("vectorDB_search", vector_tool, category="search", description="Frozen vector evidence")
    agent.register_tool("vector_search", vector_tool, category="search", description="Frozen vector evidence")
    agent.register_tool("file_system", FileSystemTool(), category="file", description="File system stub")
    agent.register_tool("context_history", ContextHistoryTool(), category="context", description="Context stub")
    return agent


def main():
    tasks = load_tasks()
    agent = build_agent()
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text("")

    summary = []
    for i, task in enumerate(tasks, 1):
        agent._frozen_web.payload = task.get("frozen_web_search")
        agent._frozen_vector.payload = task.get("frozen_vector_search")
        logger.info("=" * 72)
        logger.info("FDABench %s/%s  %s  db=%s  gold=%s", i, len(tasks), task["task_id"], task["db"], task.get("correct_answer"))
        logger.info("Q: %s", task["query"][:240])
        start = time.time()
        try:
            result = agent.process_query_from_json(task)
            error = result.get("error")
        except Exception as exc:
            result = {"error": str(exc), "selected_answer": None, "metrics": {}}
            error = str(exc)
            logger.exception("Task %s failed", task["task_id"])
        elapsed = time.time() - start

        selected = result.get("selected_answer")
        gold = task.get("correct_answer") or []
        pred = normalize_choice(selected)
        gold_n = normalize_choice(gold)
        correct = pred == gold_n and bool(pred)
        metrics = result.get("metrics") or {}
        tokens = (metrics.get("token_summary") or {})
        row = {
            "task_id": task["task_id"],
            "db": task["db"],
            "level": task["level"],
            "query": task["query"],
            "gold": gold,
            "selected_answer": selected,
            "correct": correct,
            "error": error,
            "elapsed_sec": round(elapsed, 1),
            "tools_executed": metrics.get("tools_executed"),
            "input_tokens": tokens.get("total_input_tokens"),
            "output_tokens": tokens.get("total_output_tokens"),
            "total_tokens": tokens.get("total_tokens"),
        }
        summary.append(row)
        with RESULTS_PATH.open("a") as f:
            f.write(json.dumps(row) + "\n")
        logger.info(
            "RESULT %s selected=%s gold=%s correct=%s tokens=%s time=%.1fs",
            task["task_id"],
            selected,
            gold,
            correct,
            tokens.get("total_tokens"),
            elapsed,
        )

    n_correct = sum(1 for r in summary if r["correct"])
    print("\n===== FDABench 5-query summary =====")
    for row in summary:
        mark = "PASS" if row["correct"] else "FAIL"
        print(f"{mark}  {row['task_id']:8}  gold={row['gold']}  pred={row['selected_answer']}  {row['elapsed_sec']}s")
    print(f"Accuracy: {n_correct}/{len(summary)}")
    (ROOT / "selected_five" / "summary.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
