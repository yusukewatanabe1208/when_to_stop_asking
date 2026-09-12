# Prompts

Every prompt below is the exact string sent to the API: a single user message,
no system prompt, no temperature set. The same template is used for every item
and every model.

```
Two cases are presented below.

Case A:
{case_A}

Case B:
{case_B}

Based on the {scoring_system}, which case has sufficient information to determine whether {decision_target}?
Answer with a single letter, "A" or "B". Output only that letter and nothing else.
```

## One pair through five conditions (`IT162`, CHADS2 Score)

The answer is **Case A** in all of them. Only the undeterminable case (Case B here)
is edited; the conditions that edit the determinable case are built the same way, with
the roles of the two cases swapped.

| Condition | Case A | Case B | Whole prompt | Added to Case B |
|---|---|---|---|---|
| Baseline | 39 tok | 41 tok | 142 tok | — |
| Relevant item added | 39 tok | 45 tok | 146 tok | A 68-year-old |
| Irrelevant text (token-matched) | 39 tok | 48 tok | 149 tok | Family history included maternal osteoarthritis. |
| Irrelevant text (2x) | 39 tok | 74 tok | 175 tok | Family history included maternal osteoarthritis. The patient reported a severe allergy to macrolide antibiotics, which historically caused significant gastrointestinal upset and a diffuse skin rash during childhood. |
| Irrelevant text (4x) | 39 tok | 139 tok | 240 tok | Family history included maternal osteoarthritis. The patient reported a severe allergy to macrolide antibiotics, which historically caused significant gastrointestinal upset and a diffuse skin rash during childhood. According to the medical record, the patient took oral levothyroxine each morning to manage a long-standing history of uncomplicated primary hypothyroidism. Current regular medications included a daily oral zinc tablet and a nonprescription antihistamine taken during the spring months for seasonal allergic rhinitis. The patient had a penicillin allergy. |

### Baseline

`condition = baseline` — nothing added. Case A = 39 tokens, Case B = 41 tokens, whole prompt = 142 tokens. Answer: Case A.

```
Two cases are presented below.

Case A:
An 80-year-old patient with atrial fibrillation was evaluated for stroke risk to guide anticoagulation. The patient had a history of congestive heart failure and no history of diabetes mellitus.

Case B:
A patient with atrial fibrillation was evaluated for stroke risk to guide anticoagulation. The patient had no history of congestive heart failure, a history of hypertension, and no history of diabetes mellitus.

Based on the CHADS2 Score, which case has sufficient information to determine whether the patient is at high stroke risk and needs anticoagulation?
Answer with a single letter, "A" or "B". Output only that letter and nothing else.
```

### Relevant item added

`condition = rel_to_und` — one missing scored item, added to the undeterminable case. Case A = 39 tokens, Case B = 45 tokens, whole prompt = 146 tokens. Answer: Case A.

```
Two cases are presented below.

Case A:
An 80-year-old patient with atrial fibrillation was evaluated for stroke risk to guide anticoagulation. The patient had a history of congestive heart failure and no history of diabetes mellitus.

Case B:
A 68-year-old patient with atrial fibrillation was evaluated for stroke risk to guide anticoagulation. The patient had no history of congestive heart failure, a history of hypertension, and no history of diabetes mellitus.

Based on the CHADS2 Score, which case has sufficient information to determine whether the patient is at high stroke risk and needs anticoagulation?
Answer with a single letter, "A" or "B". Output only that letter and nothing else.
```

### Irrelevant text (token-matched)

`condition = irr_to_und_matched` — irrelevant text of about the same length as the relevant item. Case A = 39 tokens, Case B = 48 tokens, whole prompt = 149 tokens. Answer: Case A.

```
Two cases are presented below.

Case A:
An 80-year-old patient with atrial fibrillation was evaluated for stroke risk to guide anticoagulation. The patient had a history of congestive heart failure and no history of diabetes mellitus.

Case B:
A patient with atrial fibrillation was evaluated for stroke risk to guide anticoagulation. The patient had no history of congestive heart failure, a history of hypertension, and no history of diabetes mellitus. Family history included maternal osteoarthritis.

Based on the CHADS2 Score, which case has sufficient information to determine whether the patient is at high stroke risk and needs anticoagulation?
Answer with a single letter, "A" or "B". Output only that letter and nothing else.
```

### Irrelevant text (2x)

`condition = irr_to_und_2x` — irrelevant text until the case is about twice as long. Case A = 39 tokens, Case B = 74 tokens, whole prompt = 175 tokens. Answer: Case A.

```
Two cases are presented below.

Case A:
An 80-year-old patient with atrial fibrillation was evaluated for stroke risk to guide anticoagulation. The patient had a history of congestive heart failure and no history of diabetes mellitus.

Case B:
A patient with atrial fibrillation was evaluated for stroke risk to guide anticoagulation. The patient had no history of congestive heart failure, a history of hypertension, and no history of diabetes mellitus. Family history included maternal osteoarthritis. The patient reported a severe allergy to macrolide antibiotics, which historically caused significant gastrointestinal upset and a diffuse skin rash during childhood.

Based on the CHADS2 Score, which case has sufficient information to determine whether the patient is at high stroke risk and needs anticoagulation?
Answer with a single letter, "A" or "B". Output only that letter and nothing else.
```

### Irrelevant text (4x)

`condition = irr_to_und_4x` — irrelevant text until the case is about four times as long. Case A = 39 tokens, Case B = 139 tokens, whole prompt = 240 tokens. Answer: Case A.

```
Two cases are presented below.

Case A:
An 80-year-old patient with atrial fibrillation was evaluated for stroke risk to guide anticoagulation. The patient had a history of congestive heart failure and no history of diabetes mellitus.

Case B:
A patient with atrial fibrillation was evaluated for stroke risk to guide anticoagulation. The patient had no history of congestive heart failure, a history of hypertension, and no history of diabetes mellitus. Family history included maternal osteoarthritis. The patient reported a severe allergy to macrolide antibiotics, which historically caused significant gastrointestinal upset and a diffuse skin rash during childhood. According to the medical record, the patient took oral levothyroxine each morning to manage a long-standing history of uncomplicated primary hypothyroidism. Current regular medications included a daily oral zinc tablet and a nonprescription antihistamine taken during the spring months for seasonal allergic rhinitis. The patient had a penicillin allergy.

Based on the CHADS2 Score, which case has sufficient information to determine whether the patient is at high stroke risk and needs anticoagulation?
Answer with a single letter, "A" or "B". Output only that letter and nothing else.
```

## All 1,080 prompts

The `prompt` column of `data/benchmark_1080.csv` holds every prompt verbatim.
To read one:

```python
import pandas as pd
b = pd.read_csv("data/benchmark_1080.csv")
print(b.query("item_id == 'IT162' and condition == 'baseline'").prompt.iloc[0])
```
