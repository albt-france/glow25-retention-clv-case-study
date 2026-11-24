# AI-assisted copy workflow (language-model step optional)

Goal: use a language model where it saves time (reading many customer answers, drafting variants) and keep
people responsible for what is true, what is allowed and what is sent.

## Steps

| # | Step | Who / what | Output |
|---|---|---|---|
| 1 | Customer research: group cancel reasons and free-text answers into themes | `src/copy_lab.py` - rule-based grouping by default; language-model step (optional) to name themes and pull example phrases | theme table with counts and example phrases (SIMULATED cancel reasons in this repo) |
| 2 | Brief: pick one theme, one audience, one action | Person | brief: audience, insight, offer, single call to action |
| 3 | Variant exploration: 6-10 subject lines and openings | Template variants by default; language-model step (optional) | candidate list |
| 4 | Claims check | `src/claims_check.py` (rules, EN + FR) | blocked lines removed |
| 5 | Human edit and validation | Person: claims, tone, brand voice, offer terms, local adaptation | final copy |
| 6 | Test | Holdout or A/B, judged on clicks, revenue per recipient and margin, never on opens | read-out in the weekly update |

## What stays human

- Every claim and every number in the final copy.
- The choice of the angle per market (adaptation, not translation).
- The offer and its margin (no discount is proposed by a model).
- The decision to scale, stop or re-test.

## Fallback without a model (the version used in this repository)

`python src/copy_lab.py` runs without any key: themes come from keyword rules on the cancel reasons and subject
lines come from templates filled with the theme, the product and the action. The optional language-model step
is switched on only if `.env` sets `LLM_PROVIDER` and `LLM_API_KEY`; whatever it returns goes through the same
claims check and the same human review. Only aggregated, anonymous inputs are sent (theme counts, no customer
data).

## Guardrails

- Inputs: aggregates only, no names, no emails, no order ids.
- Outputs: never sent automatically; every line passes `claims_check.py` and a person.
- Logging: the variant list and the check result are saved in `data/processed/copy_lab_variants.csv`.
