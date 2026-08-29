# Related work: user-in-the-loop database benchmarks (2025–2026)

DAB tests agent ↔ tools on messy multi-DB data. It does not test agent ↔ user: when the query is ambiguous or the data is dirty, does the agent ask, or invent a plan (FM2)?

Spider 2.0 is agent ↔ environment (run queries, read docs, navigate files). BIRD-INTERACT adds a simulated user on top of the DB. This list is user-turn only.

## Live user simulator

| Year | Bench | User | Links |
| --- | --- | --- | --- |
| 2025 | BIRD-INTERACT | Function-driven simulator; c-Interact vs a-Interact; GPT-5 8.67% / 17% on 600 full tasks | [arxiv](https://arxiv.org/abs/2510.05318) · [code](https://github.com/bird-bench/BIRD-Interact) · [site](https://bird-interact.github.io/) |
| 2025 | DySQL-Bench | LLM-simulated user + live SQLite; evolving intent; CRUD; 1,072 tasks | [arxiv](https://arxiv.org/abs/2510.26495) · [ACL](https://aclanthology.org/2026.findings-acl.1654/) · [code](https://github.com/Aurora-slz/DySQL-Bench) |
| 2026 | ABISS | Style-aware simulated users; 8-way ambiguous/unanswerable taxonomy | [arxiv](https://arxiv.org/abs/2607.23340) · [code](https://github.com/giosullutrone/ABISS-Evaluating-Text-to-SQL-Systems-Through-Agent-Interaction) |
| 2026 | CLARITY | Helpful vs incomplete vs unhelpful replies; schema-grounded ambiguity | [arxiv](https://arxiv.org/abs/2604.22313) · [ACL](https://aclanthology.org/2026.acl-industry.86/) |
| 2026 | CITBench (online) | Evolving table-processing specs; not NL2SQL | [arxiv](https://arxiv.org/abs/2608.00018) · [code](https://github.com/SSndot/CITBench) |

## Scripted user turns

| Year | Bench | User | Links |
| --- | --- | --- | --- |
| 2025 | PRACTIQ | Four-turn clarify scripts (NAACL 2025) | [arxiv](https://arxiv.org/abs/2410.11076) · [code](https://github.com/amazon-science/conversational-ambiguous-unanswerable-text2sql) |
| 2025 | Learn-to-Clarify / AmbigSQL | Ask vs guess on perturbed Spider (ICLR 2025) | [arxiv](https://arxiv.org/abs/2406.00222) · [code](https://github.com/google-research/google-research/tree/master/learning_to_clarify) |

## Next slice

BIRD-INTERACT **a-Interact** so traces label asked vs guessed on top of FM1–FM4. Then ABISS or DySQL-Bench. CITBench if the claim is processing, not NL2SQL.

Dropped: CoSQL/SParC (2019); PACIFIC (table+text, not a DBMS); AmbiSQL (demo system); Spider 2.0 / LiveSQLBench / InterCode / ELT-Bench / DataClawEval (environment only); AMBROSIA / TrustSQL (no user to ask).
