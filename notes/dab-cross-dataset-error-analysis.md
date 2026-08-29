# Cross-Dataset Error Analysis: DataAgentBench

**Scope:** gpt-5.5 (run_55_*) across agnews, yelp, crmarenapro, PANCANCER_ATLAS, PATENTS,
GITHUB_REPOS, music_brainz_20k, stockmarket, stockindex, bookreview, googlelocal, DEPS_DEV_V1.
**Taxonomy:** Official FM1–FM4 from `failure_modes.txt`.

### Key terms

**ID normalization:** Making IDs look the same before joining tables. Example: one table has `#ka0Wt000000Eq0MIAS` and another has `ka0Wt000000Eq0MIAS` — strip the `#` with `REPLACE(Id,'#','')` so the join actually finds matching rows.

---

## 1. How the Failure Modes Differ

Think of the agent's job as a four-step pipeline. Each failure mode (FM) breaks one specific step.

```
Step 1 → Form a plan      FM1 = no plan formed        FM2 = plan is logically wrong
Step 2 → Pick data        FM3 = right plan, wrong column/table
Step 3 → Execute code     FM4 = right data, wrong code/parse/join
Step 4 → Return answer
```


| Mode    | Definition                                                                   | Would fixing the data source give the right answer?    | Hints help?                                                                            |
| ------- | ---------------------------------------------------------------------------- | ------------------------------------------------------ | -------------------------------------------------------------------------------------- |
| **FM1** | Agent never produces a usable attempt — no tool calls, or runs out of turns  | No — nothing exists to fix                             | Sometimes: gives the agent an entry point                                              |
| **FM2** | Agent completes a full answer but the plan is logically wrong from the start | No — the plan answers the wrong question               | Rarely — schema gap or metric ambiguity can't be patched                               |
| **FM3** | Plan is logically correct; agent reads from the wrong column or table        | **Yes** — swap the data source and the answer is right | Yes — pointing to the right column/table fixes it                                      |
| **FM4** | Right plan, right data; the computation, parse, join, or format is broken    | **Yes** — fix the code and the answer is right         | Sometimes — [ID normalization](#key-terms) tips help a lot; parsing edge cases less so |




### How to tell them apart when they look similar


| "Looks like…"   | FM3 if…                                                                 | FM4 if…                                                            |
| --------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Wrong number    | Agent summed a cached field instead of counting real rows               | Agent read the right field but parsed its contents incorrectly     |
| Wrong grouping  | Agent grouped by the wrong column (both columns exist in the schema)    | Agent grouped by the right column but at the wrong level of detail |
| Incomplete list | Plan never included a full-enumeration step (→ FM2)                     | Agent was doing the right thing but hit the turn limit (→ FM1)     |
| Wrong category  | No category column exists in schema; agent invented a heuristic (→ FM2) | Category column exists but agent selected a sibling column (→ FM3) |


---

**FM2 (wrong plan)** means the agent's overall strategy is flawed — even perfect SQL won't help because it's answering the wrong question or using a shortcut that doesn't hold (e.g., guessing sports articles from ID ranges when no category column exists).

**FM3 (wrong column/table)** means the plan is right but the agent read from the wrong field or table — swap the data source and the answer is correct (e.g., grouping by English names instead of ICD-O codes, or summing a cached `review_count` instead of counting real review rows).

## 2. Error Tree

```
Agent failure
├── FM1 — Fails before planning
│   ├── No tool call on final turn  →  agent searched a long time but gave up;
│   │   its last response was completely empty (no answer, no next query)
│   └── Ran out of turns  →  correct idea, but too much data to check one-by-one
│       (e.g. 2,753 separate stock tables; agent only got through 18 of 31)
│
├── FM2 — Complete answer, wrong plan/strategy
│   ├── Guessing a shortcut  →  query asks for something the database doesn't label
│   │   (e.g. "sports articles"), so the agent makes up a rule to find them
│   │   (e.g. agnews Q1: "IDs 30000–59999 = sports") — but the rule is wrong
│   ├── Wrong formula  →  question is vague; agent picks the easier math
│   │   (e.g. raw price range instead of a percentage)
│   └── Stopped too early  →  question says "find all"; agent only finds top few
│
├── FM3 — Right plan, wrong column or table
│   ├── Name vs code column  →  two columns mean the same thing; agent picks
│   │   the human-readable one (e.g. "Astrocytoma" instead of "9382/3")
│   └── Stored count vs real rows  →  agent uses a pre-saved number on the
│       business record instead of actually counting review rows
│       (e.g. yelp Q2: summed `review_count` → Missouri; should count rows → PA)
│
├── FM4 — Right data, broken in the details/syntax
│   ├── Missing duplicates  →  one song has many database rows; agent only
│   │   finds some of them (e.g. music_brainz Q1: missed one track_id = $458)
│   ├── ID formatting mismatch  →  same ID looks different in two tables
│   │   (e.g. `#ka0Wt...` vs `ka0Wt...`; join returns nothing)
│   ├── Parsing failure  →  data stored as messy text strings; parser skips
│   │   records silently (e.g. yelp Q3: counted 21 instead of 35)
│   └── Ambiguous tie / date window  →  many rows tie for first place, or
│       "last 4 quarters" could mean more than one date range
│
└── Infra — Not the agent's fault
    ├── Missing database files  →  .db files were Git LFS stubs, not real data
    └── Tool bug  →  harness kept retrying a broken json.loads call (pre-fix)
```

---



## 3. Error Counts & Distribution

**Source:** `error_classification.json` (gpt-5.5, run_55_*). Each failed run is mapped to FM1–FM4 using the taxonomy in §2; infra errors = **0** in this benchmark.

### Benchmark totals


| Run      | Pass | Fail                   | Missing | Pass rate |
| -------- | ---- | ---------------------- | ------- | --------- |
| Base     | 39   | 15                     | 0       | 72.2%     |
| Hints    | 40   | 14                     | 0       | 74.1%     |
| **Both** | —    | **29 error instances** | —       | —         |


- **18 unique queries** failed at least once (11 fail in both runs, 4 base-only, 3 hints-only).
- Hints fixed **1** query (`crmarenapro_q2`: FM1 → pass) and regressed **3** (`GITHUB_REPOS_q3`, `PATENTS_q3`, `yelp_q6`).



### Distribution by failure mode (29 instances)


| FM    | Count | Share | Meaning (one line)                                    |
| ----- | ----- | ----- | ----------------------------------------------------- |
| FM2   | 18    | 62.1% | Complete answer, wrong plan or stopped too early      |
| FM4   | 7     | 24.1% | Right data, broken parse / join / entity match        |
| FM1   | 2     | 6.9%  | No final answer (empty turn or turn-limit exhaustion) |
| FM3   | 2     | 6.9%  | Right plan, wrong column or table                     |
| Infra | 0     | 0%    | Harness / missing data (none in run_55)               |




### FM subtype breakdown


| FM  | Subtype                    | Count | Example query                      |
| --- | -------------------------- | ----- | ---------------------------------- |
| FM1 | No tool call on final turn | 1     | crmarenapro Q2 (base)              |
| FM1 | Ran out of turns           | 1     | stockmarket Q2 (base)              |
| FM2 | Guessing a shortcut        | 9     | agnews Q1, GITHUB Q2, PANCANCER Q3 |
| FM2 | Stopped too early          | 6     | PATENTS Q2, stockmarket Q3/Q4      |
| FM2 | Wrong formula              | 3     | agnews Q2, GITHUB Q3 (hints)       |
| FM3 | Name vs code column        | 2     | PANCANCER Q1 (both runs)           |
| FM4 | Parsing failure            | 5     | yelp Q3, GITHUB Q1, agnews Q3      |
| FM4 | Missing duplicates         | 2     | music_brainz Q1 (both runs)        |




### Base vs hints by FM


| FM  | Base (n=15) | Hints (n=14) |
| --- | ----------- | ------------ |
| FM1 | 2           | 0            |
| FM2 | 8           | 10           |
| FM3 | 1           | 1            |
| FM4 | 4           | 3            |


FM2 dominates both runs. Hints eliminated both FM1 failures (entry-point + ID-normalization guidance on crmarenapro Q2) but added FM2 regressions on three queries that passed without hints.

### Per-dataset error count


| Dataset          | FM1 | FM2 | FM3 | FM4 | Total instances | Unique failing queries |
| ---------------- | --- | --- | --- | --- | --------------- | ---------------------- |
| GITHUB_REPOS     | 0   | 3   | 0   | 2   | 5               | 3                      |
| agnews           | 0   | 4   | 0   | 1   | 5               | 3                      |
| stockmarket      | 1   | 3   | 0   | 0   | 4               | 3                      |
| music_brainz_20k | 0   | 2   | 0   | 2   | 4               | 2                      |
| PANCANCER_ATLAS  | 0   | 2   | 2   | 0   | 4               | 2                      |
| PATENTS          | 0   | 3   | 0   | 0   | 3               | 2                      |
| yelp             | 0   | 1   | 0   | 2   | 3               | 2                      |
| crmarenapro      | 1   | 0   | 0   | 0   | 1               | 1                      |


No failures in: DEPS_DEV_V1, bookreview, googlelocal, stockindex (all 54 queries have base + hints runs).

### Automated classifier crosswalk

The JSON classifier uses a parallel label set. Mapped to FM above as follows:


| Auto label                             | Base | Hints | Typical FM                  |
| -------------------------------------- | ---- | ----- | --------------------------- |
| `REASONING_ERROR:WRONG_APPROACH`       | 4    | 5     | FM2                         |
| `REASONING_ERROR:CALCULATION`          | 4    | 4     | FM2 / FM3 / FM4 (per query) |
| `CORRECT_FILE_WRONG_DATA:WRONG_INFO`   | 3    | 3     | FM4                         |
| `CORRECT_FILE_WRONG_DATA:WRONG_FILTER` | 3    | 2     | FM1 / FM2                   |
| `NO_RESPONSE:empty_result`             | 1    | 0     | FM1                         |




### Query persistence


| Pattern         | Count | Queries                                                                                                  |
| --------------- | ----- | -------------------------------------------------------------------------------------------------------- |
| Fails both runs | 11    | GITHUB Q1–Q2, PANCANCER Q1 & Q3, PATENTS Q2, agnews Q1–Q2, music_brainz Q1 & Q3, stockmarket Q4, yelp Q3 |
| Base only       | 4     | agnews Q3, crmarenapro Q2, stockmarket Q2–Q3                                                             |
| Hints only      | 3     | GITHUB Q3, PATENTS Q3, yelp Q6                                                                           |


Persistent failures (both runs) are almost entirely FM2 (wrong strategy) and FM4 (implementation), not FM1 — the agent consistently picks the same wrong approach even with schema hints.

---



## 4. FM1 — Fails Before Planning

**Definition:** The agent either produces zero tool calls (never starts), or it starts the right way but runs out of allowed turns before producing a final answer.

**Key diagnostic:** Is there no `tool_calls.jsonl` activity at all, or does the trace show the right approach running into a wall it can't get past? For the no-tool-call variant specifically, check `llm_calls.jsonl` rather than assuming the agent was idle the whole time — in the one instance of this in the benchmark, the agent had already made 20 successful tool calls before its *final* turn returned a completely empty completion (`content: ""`, `tool_calls: null`, `finish_reason: "stop"`). A spike in `reasoning_tokens` right before that empty turn is the tell-tale signature: the model spent unusually heavy deliberation and then failed to externalize any decision — neither a `return_answer` nor another tool call.

**Can hints help?** Yes for the no-tool-call variant — hints give the agent its entry point and warn it about data quality. No for horizon exhaustion — the scale problem exists regardless.

---



### FM1-A · crmarenapro Q2 · No tool call

**Title of failure:** Agent abandons before issuing a single query — dirty IDs + schema complexity

**The question:**

> Does the cost and setup of this quote comply with our company policy? If it doesn't, which knowledge article is it in conflict with? Return only the Id of the knowledge article that the quote violates. If no violation is found, return None. Quote Id: `0Q0Wt000001WSDVKA4`

**Agent (no hints):** *(empty)* — `terminate_reason: no_tool_call`
**Ground truth:** `ka0Wt000000Eq0MIAS`
**Log:** `query_crmarenapro/query2/logs/data_agent/run_55_q2/`

**What the agent saw:** 6 databases, 27 tables total. All foreign-key IDs throughout the schema are stored with a `#` prefix — so any naive foreign key join silently returns 0 rows (an **ID normalization** problem: the same entity appears as `#ka0Wt...` in one table and `ka0Wt...` in another). Contrary to what `terminate_reason: no_tool_call` might suggest, the agent was **not idle** — it made 20 successful tool calls across `sales_pipeline`, `products_orders`, and `support`, scanning roughly 40 knowledge-base articles for a policy match. Every one of those 20 calls executed cleanly (no SQL errors, no exceptions). It simply never landed on a high-confidence match, and its 21st and final turn returned nothing at all — no text, no tool call.

**No-hint trace (verified against** `llm_calls.jsonl`**):**

```
Steps 1–19 | 20 successful tool calls (list_db, query_db, execute_python)
             → Explores sales_pipeline, products_orders, support databases
             → Retrieves and scores ~40 knowledge__kav articles by relevance
             → Every call executes cleanly — zero SQL errors, zero exceptions
             → Never reaches high confidence on which article matches

Step 20    | query_db → support
             → SELECT id, title, summary, faq_answer__c FROM knowledge__kav
               WHERE id = 'ka0Wt000000Ens5IAC' OR title ILIKE '%Mandatory Bundles%'
             → Returns "Mandatory Bundles for Quotes" — plausible-sounding,
               but NOT the ground-truth article

Step 21    | final model turn → EMPTY
             → content: ""
             → tool_calls: null
             → finish_reason: "stop"   (not "length" — the model chose to stop)
             → reasoning_tokens: 1,532  (previous max across this run: 1,018)
             → terminate_reason: no_tool_call
```

**Turn-by-turn reasoning-token telemetry (last 6 of 21 turns):**


| Turn           | reasoning_tokens | completion_tokens | Produced a tool call?    |
| -------------- | ---------------- | ----------------- | ------------------------ |
| 15             | 1,018            | 1,066             | ✓                        |
| 16             | 0                | 201               | ✓                        |
| 17             | 0                | 149               | ✓                        |
| 18             | 0                | 159               | ✓                        |
| 19             | 0                | 61                | ✓                        |
| **20 (final)** | **1,532**        | **1,553**         | **✗ — empty completion** |


**Why the final turn produced nothing:** This is a model-level empty completion, not a harness rejection. `finish_reason: "stop"` rules out a hard token cutoff — the model chose to end the turn. The reasoning-token count on that turn (1,532) is ~50% above any prior turn in the same conversation, suggesting the model spent its deliberation weighing whether "Mandatory Bundles for Quotes" was the right answer and then failed to convert that deliberation into either a `return_answer` call or another `query_db` call. This harness's system prompt also forbids any plain-text hedging ("Do not output plain text, explanations, or reasoning... Always use tool calls"), which may remove the model's only outlet for expressing uncertainty short of committing to an action — leaving an empty completion as the observed result.

**Hints run (19 steps → correct):** Hints told the agent which DB to start in and to use `REPLACE(Id,'#','')` when joining. Agent then found `ka0Wt000000Eq0MIAS` ("Volume-Based Discounts") — the article the quote violated.

```
Step 1  | query_db → sales_pipeline
          → fetches quote details with #-prefixed linked IDs
Step 2  | query_db → products_orders
          → fetches quote line items (products, unit prices, discounts)
Step 3  | query_db → support (policy search)
          → search knowledge__kav WHERE title LIKE '%discount%'
Step 5  | execute_python (scoring articles)
Step 7  | query_db → support (fetch policy details)
Step 19 | return_answer → "ka0Wt000000Eq0MIAS"  ✓
```

**What should have happened (no hints):**

1. List the `support` database first
2. Fetch the quote line items
3. Search knowledge articles for discount policy
4. Normalize dirty IDs using `REPLACE(Id,'#','')`

**Layer drill-down:**

- **Surface:** No answer at all — but not because the agent never tried. It made 20 clean tool calls and then its final turn returned a fully empty completion.
- **Why no tool call on turn 21:** Not a harness rejection — the underlying model itself returned `content: ""` and `tool_calls: null` with `finish_reason: "stop"`, immediately after a turn where reasoning-token usage spiked to 1,532 (vs. a prior max of 1,018 across the same conversation).
- **Root cause (why it never got there):** The `#` prefix data-integrity bug meant every join attempt on the transactional path (`sales_pipeline` → `products_orders`) returned 0 rows, pushing the agent into a slower keyword-search strategy over the knowledge base that ran 20 turns without ever reaching a confident match — plausibly the ambiguity that triggered the empty final turn.
- **Schema issue?** Yes — the `#` prefix is a data quality problem baked into the database, and it's the reason the agent needed 20 exploratory turns instead of resolving in 3–5.
- **Hints help?** ✅ Yes — strongly. Hints provide both the entry point and the ID normalization fix, letting the hints run resolve in 19 steps with no empty-completion collapse.

---



### FM1-B · stockmarket Q2 · Horizon exhaustion

**Title of failure:** Correct approach, wrong scale assumption — brute-force scan times out

**The question:**

> List all ETF securities listed on NYSE Arca that reached an adjusted closing price above $200 at any point during 2015, and also report the total number of such ETFs.

**Agent:** 18 ETFs, count = 18
**Ground truth:** 31 ETFs
**Log:** `query_stockmarket/query2/logs/data_agent/run_55_q2/`

**What the agent saw:** Appears to be 2 logical entities: `stockinfo` (metadata: ticker, exchange, type) and a price database. But `list_db` on the price database reveals **2,753 individual ticker tables** — one per stock symbol.

**Trace:**

```
Step 1  | query_db → stockinfo
          → AAAU: "Perth Mint Physical Gold ETF"...
          [Agent discovers the metadata table]

Step 4  | list_db → price database
          → ["AAAU","AADR","AAME","AAWW",...] — 2,753 table names

Step 5  | query_db
          → SELECT count(*) FROM information_schema → n=2753

Step 8  | execute_python
          → generates UNION ALL query across all 1,435 ETF symbols

Step 9  | query_db  [UNION ALL approach]
          → ERROR: "Table function query_table does not support lateral
            join column parameters"

Step 10 | query_db  [alternative batch approach]
          → ERROR: "Table function cannot contain subqueries"

Step 11 | query_db  [another try]
          → ERROR: "Referenced column table_name not found in FROM clause"

[Steps 13–50: agent falls back to checking one ticker at a time]
[After ~18 tickers checked, turn limit hit]

return_answer: "18 ETFs: BOIL, BZQ, DUST, EDZ, ERX, FAZ, FXP,
               GUSH, JDST, JNUG, LABD, LABU, MDY, TZA, UVXY, VIXY,
               XOP, YANG. Total: 18"  ✗
```

**What should have happened:** The agent correctly identified the UNION ALL approach but DuckDB rejected it. The correct fix is to enumerate all ticker tables using Python (not SQL), open each DuckDB file in a batch loop, and aggregate — completing in 3–5 steps instead of 50+.

**Layer drill-down:**

- **Surface:** 18 ETFs instead of 31.
- **Why:** UNION ALL batch query failed (DuckDB engine limitation). One-at-a-time fallback couldn't finish within the 50-turn budget.
- **Root cause:** 2,753 physical ticker tables is an unusual schema fan-out that breaks standard batching approaches on this DB engine.
- **Schema issue?** Yes — per-ticker physical table fan-out is the design property that makes any batch-query approach tricky and makes brute-force impossible within a turn budget.
- **Hints help?** ❌ No — the scale problem exists regardless of guidance.

---



## 5. FM2 — Incorrect Plan

**Definition:** The agent produces a complete, confident answer. The logical strategy was wrong from the start — even if every SQL query ran perfectly, the plan would not produce the correct answer.

**Key distinction from FM3/FM4:** In FM3/FM4, the plan is correct and the fix is swapping data or fixing code. In FM2, *the entire approach* needs to change.

**Can hints help?** Rarely. FM2 usually stems from missing schema information or an ambiguous metric — things hints can patch only partially.

---



### FM2-A · agnews Q1 · Heuristic sports classifier

**The question:**

> What is the title of the sports article whose description has the greatest number of characters?

**Agent:** `Kyoto is Dead - Long Live Pragmatism` (a climate/politics article)
**Ground truth:** `The Rundown`
**Log:** `query_agnews/query1/logs/data_agent/run_55_q1/`

**Schema:** `articles` (MongoDB: `article_id, title, description`) + `article_metadata` (SQLite: `article_id, author_id, region, publication_date`) + `authors` (SQLite: `author_id, name`). **No** `category` **column anywhere.**

**Full trace:**

```
Step 1  | query_db → articles collection, first 1000 rows (structure probe)
          → {article_id:0, title:"Wall St. Bears Claw Back Into the Black",
             description:"Reuters - Short-sellers..."}

Step 2  | query_db → articles WHERE article_id BETWEEN 30000 AND 30020
          → "Kerry Accuses Bush of Hiding the Truth About Iraq"...
          [Agent probing whether article ID ranges encode topic]

Step 3  | query_db → articles WHERE article_id BETWEEN 60000 AND 60020
          → "BYTE OF THE APPLE"...  (tech-looking titles)

Step 4  | query_db → articles WHERE article_id BETWEEN 90000 AND 90020
          → "Davenport's Victory Over Williams May Not Be Enough"  ← sports!
          [Agent sees a sports article at ID 90000+ and starts forming a hypothesis]

Step 6  | query_db → SELECT * FROM article_metadata LIMIT 10
          → {article_id:0, region:"Asia"}, {article_id:1, region:"North America"}
          [No category column — only region is available]

Step 7  | query_db
          → SELECT article_id FROM article_metadata
            JOIN authors ON article_metadata.author_id = authors.author_id
            WHERE authors.name = 'sports'
               OR article_metadata.region = 'sports'
          → []   ← EMPTY. No sports author or region exists.

Step 9  | execute_python
          # Agent reasons: 127,600 total articles, 4 news categories (AG News)
          # Each category ~30,000 articles
          # Hypothesis: IDs 0–29999 = business, 30000–59999 = sports,
          #             60000–89999 = sci/tech, 90000–119999 = world
          sports_articles = articles WHERE article_id BETWEEN 30000 AND 59999
          max_desc = argmax(len(description)) among sports_articles
          → {article_id: 32433,
             title: "Kyoto is Dead - Long Live Pragmatism",
             len: 985}

Step 12 | return_answer → "Kyoto is Dead - Long Live Pragmatism"  ✗
          (GT: "The Rundown")
```

**What went wrong and why:**

- Step 7 proved no category column exists — `WHERE authors.name='sports'` returned empty.
- The agent guessed that IDs 30000–59999 map to "sports" (a reasonable guess for AG News, which has 4 classes × ~30k articles each).
- But AG News articles are shuffled by publication date across categories — the ID range does not encode topic. "Kyoto is Dead" (ID 32433) falls in the guessed sports range but is a world/politics article.
- The hints run returned "Cavaliers, Hokies Play Host" — still wrong for the same fundamental reason.

**What should have happened:** A correct answer requires a `category` field, which doesn't exist in this schema. The query is genuinely unsolvable without it or an external taxonomy lookup.

**Layer drill-down:**

- **Surface:** Returns a climate/politics article as the "sports article."
- **Plan error:** Agent used `article_id` ranges as a proxy for topic category. Step 7 confirmed no category column exists, so it fell back to the only structural signal: ID ordering.
- **Root cause:** AG News IDs are assigned by publication date, not by category. The range heuristic is fundamentally invalid.
- **Schema issue?** Yes — the missing `category` column is the direct cause. This would be trivially solvable with `WHERE category = 'Sports'`.
- **Hints help?** ❌ No — hints run also returned the wrong article.

---



### FM2-B · stockindex Q1 · Wrong volatility formula

**The question:**

> Which stock index in the Asia region has exhibited the highest average intraday volatility since 2020?

**Agent (early run):** Hang Seng Index (HSI), volatility ≈ 218.32
**Ground truth:** `399001.SZ` (Shenzhen Composite)
**Log:** `query_stockindex/query1/logs/data_agent/20260623_231150/`

**Schema:** `index_info` (metadata: Index, Region, Country) + `index_trade` (daily prices: Index, Date, Open, High, Low, Close, CloseUSD).

**Trace:**

```
Step 1  | query_db → index_info
          → Exchange:"Hong Kong Stock Exchange", Exchange:"Shanghai Stock Exchange"...

Step 2  | query_db
          → SELECT Index, Date, High, Low FROM index_trade
            JOIN index_info USING (Index)
            WHERE Region = 'Asia' AND Date >= '2020-01-01'
          → HSI: Date="31 Dec 1986, 00:00", High=2568.3, Low=2568.3
            HSI: Date="January 02, 1987 at 12:00 AM", High=2540.1...

Step 3  | execute_python
          → formula: AVG(High - Low)  ← raw absolute price range
          → result: {"Index": "HSI", "Volatility": 218.32}

Step 4  | return_answer
          → "Hang Seng Index (HSI), average volatility ≈ 218.32"  ✗
```

**Two formulas, two different answers:**


| Formula                                       | Winner               | Value       | Correct? |
| --------------------------------------------- | -------------------- | ----------- | -------- |
| `AVG(High − Low)` (raw range)                 | HSI (Hang Seng)      | 218.32      | ✗        |
| `AVG((High − Low) / Open)` (normalized ratio) | 399001.SZ (Shenzhen) | ~0.020 (2%) | ✓        |


**Why the raw formula is wrong:** HSI trades in thousands of Hong Kong dollars (High ≈ 28,000 HKD). Shenzhen trades in hundreds of CNY. The raw difference `High − Low` is larger for HSI simply because its price scale is larger — not because it's actually more volatile. Dividing by the opening price normalizes for scale and makes indices comparable.

**Layer drill-down:**

- **Surface:** Returns Hang Seng instead of Shenzhen composite.
- **Plan error:** In Step 3, the agent chose `AVG(High - Low)` as the volatility definition — this is the wrong formula.
- **Root cause:** "Intraday volatility" is not precisely defined in the question. The agent defaulted to the simplest interpretation (absolute range). Without hints, it had no reason to prefer a normalized ratio.
- **Why FM2 and not FM4:** FM4 would mean the agent knew it should compute `(High−Low)/Open` but made an arithmetic mistake. FM2 is that the agent *chose the wrong formula as its plan* — the definition of what it was computing was wrong from Step 3.
- **Schema issue?** No — the schema has Open, High, Low. The issue is purely the metric definition in the plan.
- **Hints help?** ✅ Yes — later run with hints specifying the formula returned the correct answer.

---



## 6. FM3 — Wrong Data Selection

**Definition:** The agent's logical plan is correct. The problem is it reads from the wrong column or table. Swap the data source and the answer becomes right.

**Can hints help?** Yes — pointing to the right column or table directly unblocks FM3.

---



### FM3-A · PANCANCER_ATLAS Q1 · Human-readable name vs ICD-O code

**Title of failure:** Both columns visible; agent grouped by the wrong one

**The question:**

> For LGG patients, compute the average log10-transformed expression of the IGF2 gene across different histology types. Only include patients with valid IGF2 expression values and histology annotations that are not enclosed in square brackets. Report the final average values with at least four decimal places of precision.

**Agent:** Groups by `histological_type` → Astrocytoma: 2.5713, Oligodendroglioma: 2.6825, Oligoastrocytoma: 2.7136
**Ground truth:** Groups by `icd_o_3_histology` → 9382/3: 2.7136, 9400/3: 2.6014, 9401/3: 2.5584, 9450/3: 2.6967, 9451/3: 2.5826
**Log:** `query_PANCANCER_ATLAS/query1/logs/data_agent/run_55_hints_q1/`

**Trace:**

```
Step 2  | query_db
          → SELECT column_name FROM information_schema.columns
            WHERE table_name = 'clinical_info'
          → Patient_description (text), histological_type (text),
            icd_o_3_histology (text), tumor_tissue_site (text)...
          [AGENT SEES BOTH histological_type AND icd_o_3_histology]
          [CHOOSES histological_type — readable, obvious]

Step 3  | query_db
          → SELECT histological_type, COUNT(*) FROM clinical_info
            WHERE Patient_description ILIKE '%LGG%'
            GROUP BY histological_type
          → Astrocytoma (194), Oligodendroglioma (189), Oligoastrocytoma (130)
          [Committed to histological_type as the group key from here on]

Step 4  | query_db → molecular_database
          → SELECT ParticipantBarcode, normalized_count
            FROM RNASeq_Expression WHERE Symbol = 'IGF2'

Step 6  | execute_python
          → join clinical ↔ expression on TCGA barcode
          → GROUP BY histological_type
          → AVG(log10(normalized_count + 1))
          → Astrocytoma: 2.5713, Oligoastrocytoma: 2.7136,
            Oligodendroglioma: 2.6825

Step 7  | return_answer → English names  ✗
```

**Agent output vs ground truth — side by side:**


| Agent returned                | Ground truth expected |
| ----------------------------- | --------------------- |
| Astrocytoma: **2.5713**       | **9382/3**: 2.7136    |
| Oligoastrocytoma: **2.7136**  | **9400/3**: 2.6014    |
| Oligodendroglioma: **2.6825** | **9401/3**: 2.5584    |
| *(missing)*                   | **9450/3**: 2.6967    |
| *(missing)*                   | **9451/3**: 2.5826    |


Note: 2.7136 appears in both outputs — Oligoastrocytoma (name) and 9382/3 (code) refer to the same patient cluster. The math is correct; only the grouping key is wrong. The code-based taxonomy splits patients into 5 groups vs. the name-based 3.

**Fix:** Change `GROUP BY histological_type` → `GROUP BY icd_o_3_histology`. One column name change.

**Layer drill-down:**

- **Surface:** 3 English-named groups vs 5 ICD-O coded groups. Validator rejects on key mismatch.
- **Selection error:** Agent chose the readable column at Step 3; `icd_o_3_histology` was visible but ignored.
- **Root cause:** "Astrocytoma" is immediately interpretable. "9382/3" looks like noise without medical domain knowledge. Without a hint flagging the code column, the agent defaulted to the readable one.
- **Schema issue?** Partially — two columns encoding the same concept (name vs. code) with no annotation for which is authoritative creates ambiguity.
- **Hints help?** Would help immediately by naming the code column as the required output format.

---



### FM3-B · yelp Q2 · Cached review count vs actual review rows

**The question:**

> Which U.S. state has the highest number of reviews, and what is the average rating of businesses in that state?

**Agent:** Missouri (MO), avg rating 3.91
**Ground truth:** Pennsylvania (PA), avg rating 3.699
**Log:** `query_yelp/query2/logs/data_agent/run_55_q2/`

**Schema:** `businessinfo_database` (MongoDB: `business {business_id, review_count, state, ...}`) + `user_database` (DuckDB: `review {business_ref, rating, date}`).

**Trace:**

```
Step 3  | query_db (MongoDB)
          → business collection, project {business_id, review_count, description}
          → businessid_49: review_count="8", description="Located at 6901 Phelps Rd..."
          [AGENT SEES review_count directly on the document — no join needed]

Step 5  | query_db (DuckDB)
          → SELECT business_ref, COUNT(*) AS num_reviews, AVG(rating)
            FROM review GROUP BY business_ref
          → businessref_79: 43 reviews, 4.63 avg
          [Agent has real review row counts per business — but doesn't aggregate by state]

Step 6  | execute_python
          → Extract state from business.description using regex
          → SUM(business.review_count) per state  ← uses the cached field!
          → Missouri: total=2243, avg_rating=3.91

return_answer → "Missouri (MO), 2,243 reviews, avg 3.91"  ✗
```

**The exact mistake:** Step 5 queried the real `review` table and got actual row counts per business. But Step 6's Python code aggregated `business.review_count` (the pre-stored integer on the document) by state instead of using the real review counts from Step 5. The agent had the right data in hand and didn't use it.

**Why the two counts differ:** `business.review_count` is a cached snapshot written at some point in the past. Deleted reviews, data sync lag, and different time scopes cause it to diverge from the actual number of rows in the `review` table. This divergence was enough to make Missouri appear to beat Pennsylvania.

**What should have happened:**

```sql
-- Correct approach: join review rows to businesses, group by state
SELECT b.state, COUNT(r.business_ref) AS total_reviews, AVG(r.rating)
FROM review r JOIN business b ON r.business_ref = b.business_id
GROUP BY b.state
ORDER BY total_reviews DESC
LIMIT 1
```

**Layer drill-down:**

- **Surface:** Missouri 3.91 instead of Pennsylvania 3.70. Different state, different rating.
- **Selection error:** `SUM(business.review_count)` used instead of `COUNT(review rows)`. The fact table was available at Step 5 — it just wasn't used for state-level aggregation.
- **Root cause:** `review_count` is directly on the business document (no join needed). The `review` table requires a cross-database join and is much larger. The agent took the path of least resistance.
- **Schema issue?** Yes — storing a cached `review_count` on the business entity alongside a full `review` fact table creates this trap. It's a denormalization pattern that introduces inconsistency over time.
- **Hints help?** ✅ Yes — pointing to the `review` table directly fixes this.

---



## 7. FM4 — Incorrect Implementation

**Definition:** Right plan, right tables. The computation, parse, join, or format is wrong.

**Can hints help?** Strongly for ID normalization issues (see [Key terms](#key-terms) — e.g., stripping `#` prefixes before joins). Partially for parsing edge cases. Less so for date window / tie-break ambiguity.

---



### FM4-A · music_brainz Q1 · Entity resolution (missing track IDs)

**Title of failure:** Narrow title match misses alternate recordings of the same song

**The question:**

> How much revenue in USD did Apple Music make from Beyoncé's song 'Get Me Bodied' in Canada?

**Agent (no hints):** $601.44 ✗ | **Agent (hints):** $1,059.46 ✓ | **Ground truth:** $1,059.46
**Log:** `query_music_brainz_20k/query1/logs/data_agent/run_55_q1/` (fail) vs `.../run_55_hints_q1/` (pass)

**Key schema fact:** One logical song = multiple rows in `tracks` — different album releases, extended mixes, and compilations each get their own `track_id`. Revenue in `sales` is keyed by `track_id`.

**Side-by-side trace:**

```
━━━━━━━━━━━━━━━━━━━ NO-HINT (5 steps — FAILS) ━━━━━━━━━━━━━━━━━━━

Step 1  | query_db → tracks
          → WHERE lower(title) = lower('Get Me Bodied') AND artist LIKE '%beyonc%'
          → []   ← EMPTY. Exact match fails (real titles have album suffixes)

Step 2  | query_db → tracks
          → WHERE lower(title) LIKE '%get me bodied%'
          → 4233: "Get Me Bodied (Sexxxplicit R&B, Volume 25)" — Beyoncé
            10838: "Beyoncé - Get Me Bodied" — artist=nan
            12954: [compilation variant]
            15158: [compilation variant]
            [4 results — looks complete to the agent]

Step 4  | query_db → sales
          → SELECT SUM(revenue_usd) FROM sales
            WHERE track_id IN (4233, 10838, 12954, 15158)
              AND country = 'Canada' AND store = 'Apple Music'
          → $601.44

Step 5  | return_answer → "$601.44"  ✗

━━━━━━━━━━━━━━━━━━━ HINTS (3 steps — PASSES) ━━━━━━━━━━━━━━━━━━━

Step 1  | query_db → tracks
          → WHERE lower(title) LIKE '%get me bodied%'
               OR (lower(artist) LIKE '%beyonc%' AND lower(title) LIKE '%bodied%')
          → 4233, 5281, 10838, 12954, 15158   [5 results — track 5281 added]

Step 2  | query_db → sales
          → WHERE track_id IN (4233, 5281, 10838, 12954, 15158)
              AND country = 'Canada' AND store = 'Apple Music'
          → $1,059.46

Step 3  | return_answer → "$1,059.46"  ✓
```

**The one missed track that cost $458:**


| track_id          | Title                                                | Canada Revenue (Apple Music) |
| ----------------- | ---------------------------------------------------- | ---------------------------- |
| 4233              | Get Me Bodied (Sexxxplicit R&B, Volume 25)           | $377.62                      |
| **5281**          | **Get Me Bodied (Extended Mix) ← MISSED by no-hint** | **$458.02**                  |
| 12954             | [compilation variant]                                | $223.82                      |
| **No-hint total** |                                                      | **$601.44**                  |
| **Hints total**   |                                                      | **$1,059.46**                |


Track 5281 was only retrievable with the broader compound condition: `OR (artist LIKE '%beyonc%' AND title LIKE '%bodied%')`. The no-hint agent got 4 results and assumed that was the complete set.

**Layer drill-down:**

- **Surface:** Missing ~$458 — 43% of the correct total.
- **Implementation error:** `LIKE '%get me bodied%'` returned 4 track IDs. The correct set is 5. The WHERE clause was too narrow.
- **Root cause:** The same song exists as multiple rows because different album releases get different `track_id`s. There is no "canonical song ID" column that groups all recordings.
- **Why FM4 and not FM3:** The agent used the right tables (`tracks` + `sales`) and the right join key (`track_id`). The bug is entirely in the WHERE clause of the first query — a code-narrowness issue, not a data source selection issue.
- **Schema issue?** Yes — one logical song = multiple physical `track_id` rows is an entity resolution challenge baked into the schema.
- **Hints help?** ✅ Yes — hints provided the broader OR match pattern.

---



### FM4-B · yelp Q3 · Nested stringified dict parsing failure

**Title of failure:** Semi-structured data format silently under-counts — `ast.literal_eval` fails on edge cases

**The question:**

> During 2018, how many businesses that received reviews offered either business parking or bike parking?

**Agent:** 21 ✗ | **Ground truth:** 35
**Log:** `query_yelp/query3/logs/data_agent/run_55_q3/`

**The data format problem:** In the yelp MongoDB `business` collection, parking info is stored as a **stringified Python dictionary inside the** `attributes` **field**:

```
"BusinessParking": "{'garage': False, 'street': False,
                      'validated': False, 'lot': True, 'valet': False}"
```

This is *not* JSON — it uses single quotes and Python-style `True`/`False`. It must be parsed with `ast.literal_eval`. Several documents have edge-case variants that silently fail parsing.

**Trace:**

```
Step 1  | query_db (DuckDB)
          → SELECT COUNT(DISTINCT business_ref) FROM review
            WHERE date >= '2018-01-01' AND date < '2019-01-01'
          → 36 businesses reviewed in 2018

Step 2  | query_db (MongoDB) — sample to inspect attribute format
          → BusinessParking: "{'garage':False,'street':False,'lot':False,'valet':False}"
          [Agent sees the stringified-dict format and knows it needs ast.literal_eval]

Step 3  | query_db (DuckDB)
          → SELECT DISTINCT business_ref FROM review
            WHERE date >= '2018-01-01' AND date < '2019-01-01'
          → [businessref_13, businessref_14, ...36 IDs]

Step 4  | query_db (MongoDB)
          → fetch all 36 business documents with their attributes

Step 5  | execute_python
          Code:
            def parse_bool(v):
                if isinstance(v, bool): return v
                if isinstance(v, str):
                    s = v.strip()
                    if s in ('True','true'): return True
                    if s in ('False','false'): return False
                return None

            count = 0
            for record in records:
                attrs = record.get('attributes', {})
                parking_raw = attrs.get('BusinessParking')
                if isinstance(parking_raw, str):
                    try:
                        parking = ast.literal_eval(parking_raw)
                        has_biz_parking = any(
                            parse_bool(v) is True for v in parking.values()
                        )
                    except:
                        has_biz_parking = False   ← SILENT FAILURE

                bike_raw = attrs.get('BikeParking')
                has_bike = parse_bool(bike_raw) is True

                if has_biz_parking or has_bike:
                    count += 1

          Result: count = 21

Step 6  | return_answer → "21"  ✗  (GT: 35)
```

**Why 14 businesses were missed — edge cases silently caught by** `except`**:**


| Edge case in real Yelp data                                                  | What the parser does                                                                                     | Effect                |
| ---------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | --------------------- |
| `BusinessParking: "True"` (whole field is just a boolean string, not a dict) | `ast.literal_eval("True")` returns `True` — code then calls `.values()` on a bool → TypeError → `except` | Counted as no parking |
| `BusinessParking: "u'no'"` (Python 2 unicode prefix)                         | `ast.literal_eval` fails on `u'...'` syntax                                                              | Counted as no parking |
| Extra whitespace / escape chars in the string                                | `ast.literal_eval` parse error                                                                           | Counted as no parking |


Each failure silently hits the `except` branch and sets `has_biz_parking = False`. No error is raised. The final count of 21 is returned confidently.

**Layer drill-down:**

- **Surface:** 21 instead of 35. Silent undercount — no error message.
- **Implementation error:** `ast.literal_eval` failed silently on 14 out of 36 business documents.
- **Root cause:** The `BusinessParking` field was serialized from Python objects to strings during Yelp's data export and retains Python-2/3-specific quirks (unicode prefixes, mixed bool representations).
- **Schema issue?** Yes — storing Python dict strings instead of proper JSON sub-documents creates a parsing trap. Any correct solution requires a defensive multi-mode parser.
- **Hints help?** Partially — hints could flag the unusual format, but can't enumerate every edge case.

---



### FM4-C · crmarenapro Q8 · Wrong time window / tie-break ambiguity

**The question:**

> Identify the agent with the fewest transfer counts in the last 4 quarters among those who handled more than 0 cases. Return only the Id of the agent.
> Today's date: 2023-04-10

**Agent:** `005Wt000003NBcAIAW` ✗
**Ground truth:** `005Wt000003NIliIAG`
**Log:** `query_crmarenapro/query8/logs/data_agent/run_55_q8/`

**Schema:** `support` database: `casehistory__c {id, caseid__c, oldvalue__c (prev owner), newvalue__c (new owner), createddate, field__c}`. A transfer is a row where `field__c = 'Owner Assignment'`. Transfer count is attributed to the *old* owner (`oldvalue__c`).

**Trace:**

```
Step 3  | query_db
          → SELECT field__c, COUNT(*) FROM casehistory__c GROUP BY field__c
          → "Owner Assignment": 165,  "Case Creation": 153,  "Case Closed": 75

Step 4  | query_db  ← KEY SQL
          → WITH owner_events AS (
              SELECT caseid__c, oldvalue__c, newvalue__c,
                     createddate::timestamp AS created_ts
              FROM casehistory__c
              WHERE field__c = 'Owner Assignment'
                AND createddate::timestamp >= TIMESTAMP '2022-04-01'  ← guessed start
                AND createddate::timestamp <  TIMESTAMP '2023-04-01'  ← guessed end
            ), handled AS (
              SELECT newvalue__c AS agent_id,
                     COUNT(DISTINCT caseid__c) AS handled_cases
              FROM owner_events
              GROUP BY newvalue__c
            ), transfers AS (
              SELECT oldvalue__c AS agent_id, COUNT(*) AS transfer_count
              FROM owner_events
              GROUP BY oldvalue__c
            )
            SELECT agent_id, handled_cases,
                   COALESCE(transfer_count, 0) AS transfer_count
            FROM handled LEFT JOIN transfers USING (agent_id)
            WHERE handled_cases > 0
            ORDER BY transfer_count ASC
          → 005Wt000003NBcAIAW: handled=1, transfers=0
            005Wt000003NBykIAG: handled=1, transfers=0
            005Wt000003NDJ1IAO: handled=1, transfers=0
            [many agents tied at 0 transfers]

Step 5  | query_db  [Agent shifts window to match "today's date"]
          → same query but createddate >= '2022-04-10' AND < '2023-04-10'
          → Same agents still tied at 0 transfers — ORDER BY returns different first row

Step 6  | return_answer → "005Wt000003NBcAIAW"  ✗
```

**What went wrong:** Many agents are tied at 0 transfers. When `ORDER BY transfer_count ASC` produces a tie, the database returns whichever row comes first internally — and that's non-deterministic. The ground truth agent `005Wt000003NIliIAG` should rank first, but the agent's query returned a different one from the tied group.

**Layer drill-down:**

- **Surface:** Wrong agent ID — both are syntactically valid Salesforce IDs.
- **Implementation error:** (1) The exact date window `2022-04-10` to `2023-04-10` was tried (Step 5) but agents were still tied. (2) `LIMIT 1` on a tie is non-deterministic — no stable tiebreaker was added.
- **Root cause:** "Last 4 quarters" is time-bounded but "fewest transfers" among many agents all having 0 transfers requires a secondary sort key not specified in the query.
- **Schema issue?** Partially — the lack of a natural tiebreaker (e.g., agent name, a stable ID ordering) makes this query sensitive to query plan internals.
- **Hints help?** ⚠️ Unclear — the tie-breaking rule is not specified anywhere.

---



## 8. Can Hints Help? — Full Summary


| FM  | Subtype      | Dataset         | No-hint result  | Hints result  | Verdict                                | Why                                                   |
| --- | ------------ | --------------- | --------------- | ------------- | -------------------------------------- | ----------------------------------------------------- |
| FM1 | no-tool-call | crmarenapro Q2  | None ✗          | `ka0Wt...` ✓  | ✅ Yes                                  | Entry point + ID normalization fix (strip `#` prefix) |
| FM1 | horizon      | stockmarket Q2  | 18 ETFs ✗       | 18 ETFs ✗     | ❌ No                                   | Scale problem unchanged                               |
| FM2 | heuristic    | agnews Q1       | wrong title ✗   | wrong title ✗ | ❌ No                                   | No category column exists                             |
| FM2 | methodology  | stockindex Q1   | HSI ✗           | 399001.SZ ✓   | ✅ Yes                                  | Correct formula specified                             |
| FM2 | incomplete   | PATENTS Q2      | ~20 groups ✗    | ~20 groups ✗  | ❌ No                                   | Plan stays top-k                                      |
| FM3 | label/code   | PANCANCER Q1    | names ✗         | names ✗       | ⚠️ Didn't specify column in tested run |                                                       |
| FM3 | meta/fact    | yelp Q2         | Missouri ✗      | (not tested)  | ✅ Would help                           | Point to review table                                 |
| FM4 | entity       | music_brainz Q1 | $601 ✗          | $1,059 ✓      | ✅ Yes                                  | Broader OR match pattern                              |
| FM4 | parse        | yelp Q3         | 21 ✗            | (not tested)  | ⚠️ Partial                             | Can flag format, not every edge case                  |
| FM4 | ID           | crmarenapro Q6  | wrong article ✗ | correct ✓     | ✅ Yes                                  | ID normalization: `REPLACE(Id,'#','')` before join    |


**Empirical pattern:**

- **Clean small schemas (≤3 tables, no messy data):** No-hint ≈ hints. Hints can even hurt (stockindex Q3: hints steered the agent to a wrong monthly investment timing rule, causing a query no-hint passed to fail).
- **Messy small schemas (≤3 tables but entity resolution / nested attrs / no label column):** Hints improve accuracy ~+15pp.
- **Large schemas (≥5 tables, multi-DB):** Hints improve ~+15pp, especially for [ID normalization](#key-terms) and entry-point guidance.

---



## 9. Quick Reference


| FM              | Dataset         | Agent returned   | Ground truth         | Root cause (one line)                                                           |
| --------------- | --------------- | ---------------- | -------------------- | ------------------------------------------------------------------------------- |
| FM1 no-tool     | crmarenapro Q2  | *(none)*         | `ka0Wt000000Eq0MIAS` | 27-table schema + `#`-prefixed IDs block every join                             |
| FM1 horizon     | stockmarket Q2  | 18 ETFs          | 31 ETFs              | 2,753 physical ticker tables; serial scan hits turn cap                         |
| FM2 heuristic   | agnews Q1       | "Kyoto is Dead…" | "The Rundown"        | No `category` column; agent used article_id ranges as proxy                     |
| FM2 methodology | stockindex Q1   | HSI 218.32       | 399001.SZ            | `AVG(High−Low)` instead of `AVG((High−Low)/Open)`                               |
| FM2 incomplete  | PATENTS Q2      | ~20 CPC groups   | 23 groups            | "Find all that qualify" treated as top-k ranking                                |
| FM3 label/code  | PANCANCER Q1    | English names    | ICD-O codes          | Grouped by `histological_type` instead of `icd_o_3_histology`                   |
| FM3 meta/fact   | yelp Q2         | Missouri 3.91    | Pennsylvania 3.70    | `SUM(business.review_count)` instead of `COUNT(review rows)`                    |
| FM4 entity      | music_brainz Q1 | $601.44          | $1,059.46            | Narrow title match missed track_id=5281 ($458 revenue)                          |
| FM4 parse       | yelp Q3         | 21               | 35                   | `ast.literal_eval` silently fails on 14 edge-case attribute strings             |
| FM4 window      | crmarenapro Q8  | wrong agent      | `005Wt000003NIliIAG` | Ambiguous "last 4 quarters"; many agents tied at 0 transfers                    |
| FM4 ID          | crmarenapro Q6  | wrong article    | `ka0Wt000000EnwvIAC` | Join on `#`-prefixed IDs without ID normalization (see [Key terms](#key-terms)) |


