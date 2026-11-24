# Claims guardrail (food supplements, EU)

Not legal advice. This is a working filter so that no email reaches a legal or human review with an obvious
problem. The final check is always a person, and for new claims the brand's regulatory or legal adviser.

## The rule that matters for collagen

Regulation (EU) No 432/2012 (list of permitted health claims for foods) contains **no claim for collagen itself**.
The word "collagen" appears in authorised claims only through **vitamin C**, in six wordings (read on
2026-11-24 from the Publications Office copy of the regulation, EN and FR versions in
`data/public/eu_432_2012_collagen_claims.csv`):

- Vitamin C contributes to normal collagen formation for the normal function of blood vessels
- Vitamin C contributes to normal collagen formation for the normal function of bones
- Vitamin C contributes to normal collagen formation for the normal function of cartilage
- Vitamin C contributes to normal collagen formation for the normal function of gums
- Vitamin C contributes to normal collagen formation for the normal function of skin
- Vitamin C contributes to normal collagen formation for the normal function of teeth

This is why a collagen product "with vitamin C" can carry a claim at all. The claim may only be used for a
product that contains vitamin C in the quantity the regulation requires (conditions of use: to be checked on
the product sheet by a person).

## What `src/claims_check.py` does

| Rule | Result |
|---|---|
| A sentence links a body function (skin, hair, nails, joints, energy, ...) to an effect (supports, improves, boosts, contributes, ...) and is **not** one of the authorised wordings, word for word | BLOCK | <!-- claims-check: ignore -->
| Banned wording, EN or FR: `anti-aging`, `heals`, `cures`, `treats`, `wrinkles disappear`, `reverses`, `younger-looking`, `detox`, `miracle`, `guaranteed results`, `before/after`, `prevents`, `anti-rides`, `guérit`, `soigne`, `rajeunit`, ... | BLOCK |
| `clinically proven`, `studies show` and similar without a `[source: ...]` marker | BLOCK |
| An authorised wording found, word for word | PASS, with a reminder to check vitamin C content |
| Anything else | PASS (not checked for claims) - still read by a person |

Text inside backticks and lines marked `claims-check: ignore` are treated as mentions, not claims, so that
documentation like this page can list banned words.

## Human validation (mandatory)

1. The person who wrote the email is never the only reviewer.
2. Checklist: claim wording verbatim; product contains vitamin C; no dosage advice beyond what the label says;
   no `before/after` stories or images; no implied health effect in images or subject lines; offer terms and
   cancellation terms correct; FR version reviewed by a native speaker.
3. Every new claim, testimonial or "study" goes to the legal or regulatory adviser before use.

## What this guardrail cannot do

- It does not understand images, emojis or implied claims ("the secret of radiant 50-year-olds").
- It only knows the collagen-related vitamin C claims; other nutrients need their own list.
- It does not replace national rules (for example on testimonials) or a legal opinion.
