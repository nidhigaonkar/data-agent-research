# LLM cost estimation

```
cost = (input_token_count * input_token_cost) + (output_token_count * output_token_cost)
```

- Ignore caching; use total input tokens only.
- Source tokens from logs (`prompt_tokens` / `input_tokens` and `completion_tokens` / `output_tokens`).
- Use the model's published per-token pricing. State the rate source.
- Estimates for relative comparison, not invoices.

Example (per query):

```python
input_tokens = sum(call["response"]["usage"]["prompt_tokens"] for call in llm_calls)
output_tokens = sum(call["response"]["usage"]["completion_tokens"] for call in llm_calls)
cost = (input_tokens / 1_000_000) * input_rate_per_million + (output_tokens / 1_000_000) * output_rate_per_million
```
