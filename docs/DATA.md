# Data description

Three files, all UTF-8 CSV with a header row. Values are copied unchanged from the
experiment; nothing is rounded or reformatted except where stated.

## `data/benchmark_1080.csv`

1,080 rows = 120 pairs x 9 conditions.
One row is one prompt.

| Column | Description |
|---|---|
| `item_id` | pair identifier, stable across conditions |
| `scoring_system` | which clinical scoring system the pair is built from (15 in total) |
| `condition` | one of the nine conditions (see README) |
| `added_to` | which case received the addition: `determinable`, `undeterminable`, or empty for baseline |
| `added_content` | the text that was added, without the `[REL]` / `[IRR]` marker |
| `threshold` | the scoring system's decision threshold |
| `positive_when` | the decision rule, e.g. `total >= 7` |
| `score_range` | the totals the scoring system can produce, e.g. `0-10` |
| `case_A`, `case_B` | the two vignettes as they appear in the prompt |
| `case_A_score_min`, `case_A_score_max` | totals Case A can reach once the missing items take their extreme values |
| `case_B_score_min`, `case_B_score_max` | the same for Case B |
| `case_A_tokens`, `case_B_tokens` | token counts (tiktoken `o200k_base`) |
| `determinable_case` | **ground truth**: `A` or `B`, whichever case is determinable |
| `determinable_side_judgment` | whether the determinable case sits `above_threshold` or `below_threshold` |
| `missing_items_determinable`, `missing_items_undeterminable` | number of scored items left out of each case |
| `prompt` | the exact string sent to the API |
| `prompt_tokens` | token count of `prompt` (tiktoken `o200k_base`) |

The ground truth is derived, not annotated. The `score_min` / `score_max` columns make
this checkable row by row: a case is determinable when its whole achievable range sits
on one side of the threshold (`score_min >= threshold`, or `score_max < threshold`), and
undeterminable when the range straddles it (`score_min < threshold <= score_max`). This
holds for all 1,080 rows.

For example, a CHADS2 pair with `threshold = 2`: the determinable case may span 2-5
(always at or above the threshold) while the undeterminable one spans 1-4 (either side
is still possible).

## `data/model_outputs.csv`

15,120 rows = 120 pairs x 9 conditions x 14 runs.

| Column | Description |
|---|---|
| `item_id`, `scoring_system`, `condition` | join keys back to the benchmark |
| `model` | display name of the model |
| `reasoning` | reasoning setting: `off`, `low`, `medium`, `high`, `max`, or `on` |
| `raw_output` | the model's reply, verbatim |
| `parsed_answer` | `A` or `B` extracted from the reply |
| `determinable_case` | ground truth, repeated here so the file stands alone |
| `correct` | 1 if `parsed_answer` equals `determinable_case` |
| `input_tokens`, `output_tokens` | as reported by the provider |
| `reasoning_tokens` | as reported; for Claude the API does not break this out, so it is output tokens minus the visible reply |

All 15,120 cells are filled and every reply parsed to A or B.

### Runs

| Model | Reasoning settings |
|---|---|
| Claude Opus 4.5 | high, low, medium, off |
| GPT-5.5 | high, low, max, off |
| Qwen3.5-27B | off, on |
| Qwen3.5-9B | off, on |
| Qwen3.6-35B-A3B | off, on |

Claude and GPT were called through their own APIs; the three Qwen models through
OpenRouter, which does not expose a reasoning budget for them, so only off/on was varied.
Model names are the display names used throughout the paper (for example
`Opus 4.5`); responses were collected in August-September 2026, so a provider's
current build of a given name may no longer match.

## `data/irrelevant_texts_45.csv`

45 rows = 15 scoring systems x 3 doses. The irrelevant text is fixed per
scoring system and dose, and the doses are nested: the `matched` text is a prefix of
`2x`, which is a prefix of `4x`. The same text is used whichever case receives it.

| Column | Description |
|---|---|
| `scoring_system` | which scoring system the text belongs to |
| `condition` | `matched`, `2x`, or `4x` |
| `n_sentences`, `added_tokens` | size of the added text |
| `irrelevant_text` | the text itself |

Each text covers drug allergies, current medications, or family history, and was
screened so that it does not state, negate, or imply any scored item of that scoring
system — for instance, a diabetes drug is never mentioned for a score that counts
diabetes. Two different LLMs screened every sentence and every assembled text, and a
board-certified internal medicine physician reviewed the final set.

## Joining the files

```python
import pandas as pd
b = pd.read_csv("data/benchmark_1080.csv")
o = pd.read_csv("data/model_outputs.csv")
df = o.merge(b[["item_id", "condition", "prompt", "case_A", "case_B"]],
             on=["item_id", "condition"])
```
