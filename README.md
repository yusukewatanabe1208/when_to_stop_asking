# When to Stop Asking

This repository provides the benchmark, the prompts exactly as they were sent,
the ground-truth labels, and the raw model responses with their correctness,
for the paper **"When to stop asking: do large language models judge whether
the information in front of them is sufficient?"**

It is the dataset release only: the figures and statistics reported in the paper
are produced elsewhere and are not part of this repository.

```bibtex
@misc{whentostopasking2026,
  title  = {When to stop asking: do large language models judge whether
            the information in front of them is sufficient?},
  year   = {2026},
  note   = {Author and affiliation withheld for anonymous review}
}
```

This guide has four parts: **Installation**, **Quickstart**, **Benchmark
Dataset** (what the items are and how to read them), and **Running a model**
(how to evaluate a model of your own on the benchmark).

## Installation

```bash
git clone <repository-url>
cd when_to_stop_asking
pip install -r code/requirements.txt
```

Reading the data needs only `pandas`. Running the benchmark against a model
additionally needs the client for whichever provider you call (`openai`,
`anthropic`).

To call models, copy the key template and fill in the providers you will use:

```bash
cp .env.example .env
```

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=sk-or-...
```

`.env` is git-ignored. Environment variables override it. Only the provider you
actually call needs a key, and the scripts stop with a clear message before
making any request if the key is missing.

## Quickstart

Inspect the data and check that every label re-derives from the score ranges:

```bash
python code/dataset.py
```

Run the benchmark on a model of your own (ten items first, then the full set):

```bash
python code/run_benchmark.py --model gpt-5.5 --limit 10 --out smoke.csv
python code/run_benchmark.py --model gpt-5.5 --reasoning high --out my_results.csv
```

## Benchmark Dataset

### The task

Each item shows two clinical vignettes, Case A and Case B, scored with the same
clinical scoring system. Both are missing some scored items.

* In one case the missing items **cannot change the verdict**: whatever values
  they take, the total stays on one side of the threshold. That case is
  **determinable**.
* In the other the missing items **can change the verdict**: the achievable
  totals straddle the threshold. That case is **undeterminable**.

The model is asked which case has sufficient information and answers with a
single letter. Because the verdict follows from the item values and the
threshold, labels are constructed by rule, with no human annotation.

```
Two cases are presented below.

Case A:
An 80-year-old patient with atrial fibrillation was evaluated for stroke risk to guide anticoagulation. The patient had a history of congestive heart failure and no history of diabetes mellitus.

Case B:
A patient with atrial fibrillation was evaluated for stroke risk to guide anticoagulation. The patient had no history of congestive heart failure, a history of hypertension, and no history of diabetes mellitus.

Based on the CHADS2 Score, which case has sufficient information to determine whether the patient is at high stroke risk and needs anticoagulation?
Answer with a single letter, "A" or "B". Output only that letter and nothing else.
```

CHADS₂ has a threshold of 2. Case A already scores 2 from what is stated (age
≥ 75, heart failure), so its achievable range is 2–5 and the verdict is fixed:
determinable. Case B scores 1 from what is stated and can reach 1–4, straddling
the threshold: undeterminable. **The answer is A.**

Every row carries those numbers (`threshold`, `case_A_score_min`,
`case_A_score_max`, and so on), so the label can be re-derived and checked row
by row — `code/dataset.py` does exactly that for all 1,080 rows.

### Conditions

Each of the 120 pairs appears in nine conditions. **The correct answer never
changes.**

| Condition | What is added | Added to |
|---|---|---|
| `baseline` | nothing | — |
| `rel_to_det` / `rel_to_und` | one missing **scored item**, chosen so the verdict still does not change | determinable / undeterminable |
| `irr_to_det_matched` / `irr_to_und_matched` | **irrelevant text** of about the same length as the relevant item (~8 tokens) | determinable / undeterminable |
| `irr_to_det_2x` / `irr_to_und_2x` | irrelevant text until the case is ~2× longer | determinable / undeterminable |
| `irr_to_det_4x` / `irr_to_und_4x` | irrelevant text until the case is ~4× longer | determinable / undeterminable |

The irrelevant text is medically ordinary content — drug allergies, current
medications, family history — that never states, negates, or implies any scored
item. Adding text to **both** sides is what separates a pull toward the edited
case from plain degradation: a pull flips sign depending on which side was
edited, whereas noise hurts both sides alike.

The headline measure is

```
attraction = Err(added to undeterminable) − Err(added to determinable)
```

Positive means the judgment was pulled toward whichever case received the
addition; negative means that case was avoided; zero means no directional
effect. Baseline error cancels in the difference, so the measure does not depend
on a model's overall accuracy.

### Files

```
data/
  benchmark_1080.csv          120 pairs x 9 conditions, with the exact prompt sent
  model_outputs.csv           15,120 responses (5 models x reasoning levels)
  irrelevant_texts_45.csv     the 45 irrelevant texts (15 scoring systems x 3 doses)
code/
  dataset.py                  loaders, iterators, and the correctness check
  run_benchmark.py            run the benchmark against a model
  requirements.txt
docs/
  DATA.md                     column-by-column description of every file
  PROMPTS.md                  one full prompt per condition, as sent
```

`docs/DATA.md` documents every column. `docs/PROMPTS.md` shows one pair through
five conditions with the prompts in full.

### Accessing the data

`code/dataset.py` provides loaders and an iterator over the items in a
standardised format:

```python
from dataset import load_benchmark, iter_items, load_outputs, score

for item in iter_items(condition="baseline"):
    print(item.item_id, item.scoring_system, item.determinable_case)
    print(item.prompt)
    assert item.check_label()        # re-derives the label from the score ranges

bench = load_benchmark(scoring_system="CHADS2 Score")
outputs = load_outputs(model="GPT-5.5", reasoning="max")
print(score())                       # accuracy and error rate per run and condition
```

Running the module prints a self-check:

```bash
python code/dataset.py
```

### Released responses

`data/model_outputs.csv` has one row per (item, condition, model, reasoning
level): the reply verbatim in `raw_output`, the extracted letter in
`parsed_answer`, and `correct` against the ground truth. All 15,120 cells are
filled and every reply parsed to A or B.

| Model | Reasoning settings |
|---|---|
| Claude Opus 4.5 | off, low, medium, high |
| GPT-5.5 | off, low, high, max |
| Qwen3.5-9B | off, on |
| Qwen3.5-27B | off, on |
| Qwen3.6-35B-A3B | off, on |

Claude and GPT were called through their own APIs; the three Qwen models through
OpenRouter, which does not expose a reasoning budget for them, so only the
on/off toggle was varied. Responses were collected in August–September 2026.

## Running a model

```bash
python code/run_benchmark.py --model gpt-5.5 --reasoning high --out my_results.csv
```

The provider is inferred from the model id (`gpt*` → OpenAI, `claude*` →
Anthropic, anything else → OpenRouter) and can be overridden with `--provider`.
`--limit N` runs the first N items as a smoke test, `--workers` sets the number
of parallel requests, and rows already present in the output file are skipped,
so an interrupted run can be resumed by repeating the command.

Send the `prompt` column unchanged if you want results comparable with ours.
Reasoning-level names differ between providers: `run_benchmark.py` maps `low` /
`medium` / `high` to thinking budgets for Anthropic and passes
`reasoning_effort` through for OpenAI.

The output has the same columns as `data/model_outputs.csv`, so it can be read
back with `load_outputs` and summarised with `score`:

```python
import pandas as pd
from dataset import score

print(score(pd.read_csv("my_results.csv")))
```

## How the data was built

The vignettes are assembled mechanically from per-item text chunks, so wording
never drifts between conditions. Fifteen clinical scoring systems are used
(4–9 scored items each), and 120 pairs were drawn — 8 per scoring system, with
the correct answer balanced between A and B. The label comes from comparing the
achievable score range against the threshold.

A board-certified internal medicine physician (one of the authors) checked that
each chunk matches its scored item's definition. The irrelevant texts were generated with an LLM
and then screened twice, by two different models, for whether they leak any
scored item and whether they read as natural clinical prose; the same physician
reviewed the final set. Details are in `docs/DATA.md`.

## Limitations

* The vignettes are synthetic and short. They are built to isolate a single
  judgment, not to look like real clinical notes.
* Fifteen scoring systems, 8 pairs each. Per-scoring-system estimates rest on 8
  pairs and are noisy; we report them only as a robustness check.
* The prompt fixes the answer format to one letter, which suppresses hedging. A
  model allowed to abstain might behave differently.
* Model versions and provider defaults move. Re-running later may not reproduce
  the same numbers.

## License

Code (`code/`) is MIT; data (`data/`) is CC BY 4.0. See `LICENSE`. The clinical scoring systems are published clinical tools; only their
thresholds and item definitions are used here.
