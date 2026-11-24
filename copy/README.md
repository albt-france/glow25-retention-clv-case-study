# Email copy samples

Sample copy for **Brand G**, the fictional collagen brand of this case study (SIMULATED context). It shows how I
would write the four flows I would build first; for a real brand it would be rewritten in that brand's voice and
checked against its own product sheets.

| File | Flow | Emails |
|---|---|---|
| [01_welcome.md](01_welcome.md) | Welcome | W1, W2 (EN) + FR adaptation of W1 |
| [02_trial_to_subscription.md](02_trial_to_subscription.md) | Trial pack -> subscription | T1, T2 (EN) + FR adaptation of T2 |
| [03_replenishment_j26.md](03_replenishment_j26.md) | Replenishment, day 26 + branch | R1, R2 (EN) + FR adaptation of R1 |
| [04_cancel_save.md](04_cancel_save.md) | Cancel-save | X1, X2 (EN) + FR adaptation of X1 |

Rules applied to every email:

- the only health claim used is an authorised one, word for word (Regulation (EU) No 432/2012, vitamin C), and
  only for a product that contains vitamin C;
- no dosage advice, no `before/after` images or stories, no promise of results;
- servings are mentioned only to say how long a jar lasts;
- every file passes `python src/claims_check.py copy/` (0 blocked), then a person reads it before anything is scheduled.

French versions are **adaptations, not translations**: Eurostat shows that women aged 25-54 in France buy beauty
products online far more often than supplements (29.1 % vs 11.8 % in 2024), so the French copy leads with the
daily beauty ritual and the texture, not with the supplement.
