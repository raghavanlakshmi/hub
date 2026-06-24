import time
from datetime import datetime
from typing import Any

INPUT_COST_PER_MTOK = 3.0   # Claude Sonnet 4.6 — verify current pricing before reporting real $ figures
OUTPUT_COST_PER_MTOK = 15.0


def compute_cost(input_tokens: int, output_tokens: int) -> float:
    return (
        (input_tokens / 1_000_000) * INPUT_COST_PER_MTOK
        + (output_tokens / 1_000_000) * OUTPUT_COST_PER_MTOK
    )


def tracked_claude_call(client, phase: str, state: dict, **create_kwargs) -> Any:
    """
    Drop-in replacement for client.messages.create(...).
    Logs tokens/cost/latency into state["token_log"], returns the same
    response object messages.create() would have returned.
    """
    start = time.perf_counter()
    response = client.messages.create(**create_kwargs)
    elapsed_ms = (time.perf_counter() - start) * 1000

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost = compute_cost(input_tokens, output_tokens)

    entry = {
        "phase": phase,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost, 6),
        "latency_ms": round(elapsed_ms, 1),
        "timestamp": datetime.now().isoformat(),
    }

    state.setdefault("token_log", []).append(entry)
    print(f"[usage] {phase}: {input_tokens} in / {output_tokens} out "
          f"| ${cost:.4f} | {elapsed_ms:.0f}ms")

    return response


def summarize_usage(state: dict) -> dict:
    """Roll up state['token_log'] into totals — this is what feeds your comparison report."""
    log = state.get("token_log", [])
    total_input = sum(e["input_tokens"] for e in log)
    total_output = sum(e["output_tokens"] for e in log)
    total_cost = sum(e["cost_usd"] for e in log)
    total_latency = sum(e["latency_ms"] for e in log)

    by_phase = {}
    for e in log:
        p = e["phase"]
        by_phase.setdefault(p, {"calls": 0, "input_tokens": 0, "output_tokens": 0,
                                  "cost_usd": 0.0, "latency_ms": 0.0})
        by_phase[p]["calls"] += 1
        by_phase[p]["input_tokens"] += e["input_tokens"]
        by_phase[p]["output_tokens"] += e["output_tokens"]
        by_phase[p]["cost_usd"] += e["cost_usd"]
        by_phase[p]["latency_ms"] += e["latency_ms"]

    return {
        "total_calls": len(log),
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_cost_usd": round(total_cost, 6),
        "total_latency_ms": round(total_latency, 1),
        "by_phase": by_phase,
    }
