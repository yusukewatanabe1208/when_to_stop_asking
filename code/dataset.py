# -*- coding: utf-8 -*-
"""Standardised access to the benchmark and to the released model responses.

    from dataset import load_benchmark, iter_items, load_outputs, score

    for item in iter_items(condition="baseline"):
        print(item.item_id, item.determinable_case)
        print(item.prompt)

Every loader returns plain pandas objects, so anything not covered here is one
``.query()`` away.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterator

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
DATA = os.path.join(ROOT, "data")

#: The nine conditions, in the order used throughout the paper.
CONDITIONS = ["baseline",
              "rel_to_det", "rel_to_und",
              "irr_to_det_matched", "irr_to_und_matched",
              "irr_to_det_2x", "irr_to_und_2x",
              "irr_to_det_4x", "irr_to_und_4x"]



@dataclass(frozen=True)
class Item:
    """One prompt: two cases, the scoring rule, and the ground-truth answer."""

    item_id: str
    scoring_system: str
    condition: str
    threshold: int
    positive_when: str
    score_range: str
    case_A: str
    case_B: str
    case_A_score_min: int
    case_A_score_max: int
    case_B_score_min: int
    case_B_score_max: int
    determinable_case: str          # "A" or "B" — the ground-truth answer
    added_to: str                   # "determinable", "undeterminable", or ""
    added_content: str
    prompt: str                     # the exact string sent to the API

    def check_label(self) -> bool:
        """Re-derive the label from the score ranges. True if it matches.

        A case is determinable when its achievable total cannot cross the
        threshold: either the minimum already reaches it, or the maximum still
        falls short. Which side counts as "positive" (``positive_when``) decides
        what the verdict is, not whether it is determined, so the same test
        applies to every scoring system.
        """
        th = self.threshold
        det = lambda lo, hi: lo >= th or hi < th          # noqa: E731
        det_a = det(self.case_A_score_min, self.case_A_score_max)
        det_b = det(self.case_B_score_min, self.case_B_score_max)
        return det_a != det_b and (self.determinable_case == "A") == det_a


def load_benchmark(condition: str | None = None,
                   scoring_system: str | None = None) -> pd.DataFrame:
    """Return ``data/benchmark_1080.csv``, optionally filtered."""
    df = pd.read_csv(os.path.join(DATA, "benchmark_1080.csv"))
    if condition is not None:
        df = df[df.condition == condition]
    if scoring_system is not None:
        df = df[df.scoring_system == scoring_system]
    return df.reset_index(drop=True)


def iter_items(condition: str | None = None,
               scoring_system: str | None = None) -> Iterator[Item]:
    """Yield one :class:`Item` per row of the benchmark."""
    fields = Item.__dataclass_fields__
    for row in load_benchmark(condition, scoring_system).itertuples(index=False):
        d = row._asdict()
        yield Item(**{k: ("" if pd.isna(d[k]) else d[k]) for k in fields})


def load_outputs(model: str | None = None,
                 reasoning: str | None = None) -> pd.DataFrame:
    """Return ``data/model_outputs.csv``, optionally filtered."""
    df = pd.read_csv(os.path.join(DATA, "model_outputs.csv"))
    if model is not None:
        df = df[df.model == model]
    if reasoning is not None:
        df = df[df.reasoning == reasoning]
    return df.reset_index(drop=True)


def score(outputs: pd.DataFrame | None = None) -> pd.DataFrame:
    """Accuracy and error rate per run and condition.

    This is the correctness check, not the paper's analysis: it only compares
    ``parsed_answer`` with the ground-truth ``determinable_case``.
    """
    o = load_outputs() if outputs is None else outputs
    acc = (o.assign(run=o.model + " (" + o.reasoning.astype(str) + ")")
             .groupby(["run", "condition"])["correct"].mean()
             .unstack("condition")
             .reindex(columns=CONDITIONS))
    return pd.concat({"accuracy": acc.round(3), "error_rate": (1 - acc).round(3)},
                     names=["metric"])


if __name__ == "__main__":          # small self-check
    bench = load_benchmark()
    print(f"benchmark: {len(bench):,} rows "
          f"({bench.item_id.nunique()} pairs x {bench.condition.nunique()} conditions)")
    bad = [i.item_id for i in iter_items() if not i.check_label()]
    print(f"labels re-derived from the score ranges: "
          f"{len(bench) - len(bad):,}/{len(bench):,} match")
    out = load_outputs()
    print(f"model outputs: {len(out):,} rows "
          f"({out.groupby(['model', 'reasoning']).ngroups} runs)")
    ok = int(out.correct.sum())
    print(f"correct: {ok:,}/{len(out):,} ({ok / len(out):.1%})")
    print("\nerror rate by run and condition:")
    print(score().loc["error_rate"].to_string())
