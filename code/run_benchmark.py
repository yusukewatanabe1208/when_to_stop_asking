#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run the determinability benchmark against an LLM.

Reads ``data/benchmark_1080.csv``, sends the ``prompt`` column to the model, and
writes one row per item to the output CSV. Already-answered rows are skipped, so
the script can be interrupted and resumed.

Usage
-----
    cp .env.example .env             # then put your keys in .env
    python run_benchmark.py --model gpt-5.5 --reasoning high --out results_gpt55_high.csv

    # a quick smoke test on 10 items
    python run_benchmark.py --model gpt-5.5 --limit 10 --out smoke.csv

Keys are read from ``.env`` in the repository root; environment variables take
precedence. Only the provider you actually call needs a key.

The prompts are fixed: the same template is used for every item and every model,
sent as a single user message with no system prompt. Do not edit the prompt
column if you want results comparable with the paper.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
DEFAULT_BENCHMARK = os.path.join(ROOT, "data", "benchmark_1080.csv")


def load_dotenv(path: str | None = None) -> list[str]:
    """Read KEY=VALUE lines from .env into os.environ without overwriting existing vars.

    Kept dependency-free on purpose: this is the only setup step the scripts need.
    Lines that are blank or start with '#' are ignored; surrounding quotes and an
    optional leading 'export ' are stripped.
    """
    path = path or os.path.join(ROOT, ".env")
    loaded = []
    if not os.path.exists(path):
        return loaded
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.removeprefix("export ").partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and value and key not in os.environ:
                os.environ[key] = value
                loaded.append(key)
    return loaded


KEY_FOR = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY",
           "openrouter": "OPENROUTER_API_KEY"}

# The answer is a single letter; anything else is normalised by extract_answer().
_ONLY_AB = re.compile(r"^\W*(?:case\s*)?([ab])\W*$", re.I)
_BOXED = re.compile(r"\\boxed\{\s*(?:case\s*)?([ab])\s*\}", re.I)


def extract_answer(text: str) -> str | None:
    """Return 'A' / 'B' if the reply commits to one case, else None."""
    t = str(text).strip()
    m = _ONLY_AB.match(t)
    if m:
        return m.group(1).upper()
    m = _BOXED.findall(t)
    if m:
        return m[-1].upper()
    m = re.match(r"^\W*([AB])\b", t)          # falls back to a leading letter
    return m.group(1).upper() if m else None


# --------------------------------------------------------------------------- #
# Providers. Each returns (text, usage dict). Add your own here if needed.
# --------------------------------------------------------------------------- #
def call_openai(prompt: str, model: str, reasoning: str | None):
    from openai import OpenAI

    client = OpenAI()
    kwargs = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    if reasoning and reasoning != "off":
        kwargs["reasoning_effort"] = reasoning
    r = client.chat.completions.create(**kwargs)
    u = r.usage
    return r.choices[0].message.content, {
        "input_tokens": getattr(u, "prompt_tokens", None),
        "output_tokens": getattr(u, "completion_tokens", None),
        "reasoning_tokens": getattr(getattr(u, "completion_tokens_details", None),
                                    "reasoning_tokens", None),
    }


def call_anthropic(prompt: str, model: str, reasoning: str | None):
    import anthropic

    client = anthropic.Anthropic()
    kwargs = {"model": model, "max_tokens": 4096,
              "messages": [{"role": "user", "content": prompt}]}
    budget = {"low": 1024, "medium": 4096, "high": 16384}.get(reasoning or "")
    if budget:
        kwargs["thinking"] = {"type": "enabled", "budget_tokens": budget}
        kwargs["max_tokens"] = budget + 1024
    r = client.messages.create(**kwargs)
    text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
    return text, {"input_tokens": r.usage.input_tokens,
                  "output_tokens": r.usage.output_tokens,
                  "reasoning_tokens": None}


def call_openrouter(prompt: str, model: str, reasoning: str | None):
    from openai import OpenAI

    client = OpenAI(base_url="https://openrouter.ai/api/v1",
                    api_key=os.environ["OPENROUTER_API_KEY"])
    kwargs = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    if reasoning and reasoning != "off":
        kwargs["extra_body"] = {"reasoning": {"enabled": True}}
    r = client.chat.completions.create(**kwargs)
    u = r.usage
    return r.choices[0].message.content, {
        "input_tokens": getattr(u, "prompt_tokens", None),
        "output_tokens": getattr(u, "completion_tokens", None),
        "reasoning_tokens": getattr(getattr(u, "completion_tokens_details", None),
                                    "reasoning_tokens", None),
    }


def pick_provider(model: str) -> str:
    m = model.lower()
    if m.startswith(("gpt", "o1", "o3", "o4")):
        return "openai"
    if m.startswith("claude"):
        return "anthropic"
    return "openrouter"          # qwen/..., google/..., meta-llama/... etc.


CALLERS = {"openai": call_openai, "anthropic": call_anthropic,
           "openrouter": call_openrouter}


def ask(prompt: str, model: str, reasoning: str | None, provider: str, retries: int = 3):
    for attempt in range(retries):
        try:
            return CALLERS[provider](prompt, model, reasoning)
        except Exception as exc:                       # noqa: BLE001
            if attempt == retries - 1:
                return f"[ERROR] {exc!r}", {}
            time.sleep(5 * (attempt + 1))
    return "[ERROR] unreachable", {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True,
                    help="model id, e.g. gpt-5.5 / claude-opus-4-5 / qwen/qwen3.5-27b")
    ap.add_argument("--reasoning", default="off",
                    help="off / low / medium / high / max / on (provider-dependent)")
    ap.add_argument("--out", required=True, help="output CSV path")
    ap.add_argument("--benchmark", default=DEFAULT_BENCHMARK)
    ap.add_argument("--provider", choices=list(CALLERS),
                    help="override the provider inferred from --model")
    ap.add_argument("--workers", type=int, default=8, help="parallel requests")
    ap.add_argument("--limit", type=int, help="only run the first N items (smoke test)")
    args = ap.parse_args()

    loaded = load_dotenv()
    if loaded:
        print(f".env: loaded {', '.join(loaded)}")

    bench = pd.read_csv(args.benchmark)
    if args.limit:
        bench = bench.head(args.limit)
    provider = args.provider or pick_provider(args.model)

    key = KEY_FOR[provider]
    if not os.environ.get(key):
        print(f"error: {key} is not set.\n"
              f"       Put it in .env at the repository root (see .env.example),\n"
              f"       or export it in your shell before running.", file=sys.stderr)
        return 1

    print(f"model={args.model} reasoning={args.reasoning} provider={provider} "
          f"items={len(bench)}")

    done = {}
    if os.path.exists(args.out):                       # resume
        prev = pd.read_csv(args.out)
        done = {(r.item_id, r.condition): r for r in prev.itertuples()}
        print(f"resuming: {len(done)} rows already in {args.out}")

    todo = [r for r in bench.itertuples() if (r.item_id, r.condition) not in done]
    print(f"to run: {len(todo)}")
    rows = [vars(r) for r in done.values()] if done else []

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(ask, r.prompt, args.model, args.reasoning, provider): r
                for r in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            r = futs[fut]
            text, usage = fut.result()
            parsed = extract_answer(text)
            rows.append({"item_id": r.item_id, "scoring_system": r.scoring_system,
                         "condition": r.condition, "model": args.model,
                         "reasoning": args.reasoning, "raw_output": text,
                         "parsed_answer": parsed,
                         "determinable_case": r.determinable_case,
                         "correct": int(parsed == r.determinable_case) if parsed else 0,
                         "input_tokens": usage.get("input_tokens"),
                         "output_tokens": usage.get("output_tokens"),
                         "reasoning_tokens": usage.get("reasoning_tokens")})
            if i % 25 == 0 or i == len(todo):
                pd.DataFrame(rows).to_csv(args.out, index=False)
                print(f"  {i}/{len(todo)} saved")

    df = pd.DataFrame(rows)
    df = df[[c for c in ("item_id", "scoring_system", "condition", "model", "reasoning",
                         "raw_output", "parsed_answer", "determinable_case", "correct",
                         "input_tokens", "output_tokens", "reasoning_tokens")
             if c in df.columns]]
    df.to_csv(args.out, index=False)

    n_bad = int(df.parsed_answer.isna().sum())
    print(f"\nsaved: {args.out}  ({len(df)} rows)")
    print(f"unparsed replies: {n_bad}")
    print(f"error rate (all conditions): {1 - df.correct.mean():.3f}")
    print("\nerror rate by condition:")
    print((1 - df.groupby('condition').correct.mean()).round(3).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
