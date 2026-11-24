# Localisation playbook: one brand voice, seven markets

Glow25 declares seven markets in its public `hreflang` tags (DE, BE, ES, FR, GB, IT, NL; country domains
glow25.fr, .it, .nl, .es, .co.uk, with Belgium served by glow25.nl) and publishes the same 120-article magazine
in each domain's sitemap (read 2026-11-24). Eurostat `isoc_ec_ibgs` (2024, women aged 25-54, % who bought online
in the last 3 months) gives the starting angle per market.

| Market | Supplements online | Beauty online | Angle | Moments | Offer style | Tone |
|---|---|---|---|---|---|---|
| DE | 28.6 % | 34.4 % | Supplement + routine, product facts | January, Black Friday, Muttertag (May) | Subscription saving | Factual, "du" or "Sie" per brand voice |
| BE | 28.6 % | 33.9 % | Same as NL (Dutch) and FR (French) by language | January, Moederdag / Fête des mères | Subscription saving | Bilingual: never mix NL and FR in one email |
| NL | 31.1 % | 50.9 % | Beauty routine and convenience, highest online beauty share | January, Moederdag (May) | Free shipping thresholds, subscription | Direct, informal |
| FR | 11.8 % | 29.1 % | **Beauty ritual, texture, gesture** - not "supplement" | Janvier, Fête des mères (end of May / June), soldes | Ritual continuity, "sans engagement" | Warm, "vous", short |
| IT | 14.3 % | 21.1 % | Beauty and quality of ingredients; trust first | Gennaio, Festa della mamma (May) | Bundles, gifts | Warm, personal |
| ES | 17.4 % | 34.7 % | Beauty routine | Enero, Día de la Madre (first Sunday of May), rebajas | Bundles, seasonal | Friendly, energetic |
| GB | n/a (not in the 2024 EU table) | n/a | Routine and convenience | January, Mother's Day (March), Black Friday | Subscribe & save | Plain English, light humour |

DE and BE show exactly the same supplement value (28.56 %); this was checked with two separate single-country
queries to Eurostat and is a genuine equality in the published table.

## Rules

1. **Adapt the story, keep the voice.** Same values (plain, no promises), different reasons to care.
2. **Claims are never adapted.** Only the official wording of an authorised claim in that language
   (e.g. FR: "La vitamine C contribue à la formation normale de collagène pour assurer la fonction normale
   de la peau"). Every version passes `src/claims_check.py`.
3. **Local moments, local dates.** Public holidays from Nager.Date (data/public/public_holidays.csv); Mother's
   Day differs by country.
4. **Prices and currency.** GB in GBP (ECB reference rate in data/public/ecb_eur_gbp_monthly.csv for reporting).
5. **Native review.** A native speaker reads every adapted email before it is scheduled.
6. **Test the adaptation, not the translation.** SIMULATED: in France a rewritten welcome (ritual angle) earned
   EUR 1.90 per recipient in 14 days vs EUR 1.37 for the version translated from German (interval includes
   zero), and had about 40 % fewer unsubscribes.
