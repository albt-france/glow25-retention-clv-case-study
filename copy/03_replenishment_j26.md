# Replenishment, day 26 + branch (F4) - SIMULATED brand "Brand G"

Trigger: one-off order of a 30-serving jar (450 g; 15 g per serving on the trial pack label, so about 30 days).
Flow filters: no order since the trigger, not subscribed. Smart sending on; skipped if a campaign went out in the
last 24 hours. Exit on order.

Why day 26: in the SIMULATED order history most one-off buyers reorder around day 32-34, and only a few percent
before day 21. A reminder on day 21 arrives while the jar is still half full. In a concurrent A/B test,
day 26 + a "still have some?" branch beat day 21 on 60-day repurchase (report, page 4).

## R1 - day 26

**Subject:** About 4 servings left?
**Preheader:** Reorder now and it arrives before your jar is empty.

Hi {{ first_name|default:"there" }},

If you have used your jar most mornings, you have about four servings left. Delivery takes 2-3 working days,
so today is the day to reorder if you do not want a gap in your routine.

**[Reorder my jar]**

Still have plenty left? Tell us and we will remind you later instead:

**[I still have some - remind me in a week]**

Want to stop thinking about it? Subscribers save 15 % and can skip a month at any time.

The Brand G team

*(Conditional split: "still have some" sets a date property; R2 goes out 7 days later only to them.)*

## R2 - day 33, only for "I still have some"

**Subject:** Your reminder, as promised
**Preheader:** One click and your next jar is on its way.

Hi {{ first_name|default:"there" }},

A week ago you told us you still had some powder left. This is the reminder you asked for.

**[Reorder my jar]**

If the timing never fits, a subscription delivers every month and you can move a delivery whenever you like.

The Brand G team

---

## FR adaptation of R1 (not a translation)

**Objet :** Plus que quelques cuillères ?
**Pré-en-tête :** Recommandez maintenant, votre rituel continue sans pause.

Bonjour {{ first_name|default:"" }},

Votre pot touche bientôt à sa fin. Pour ne pas interrompre votre rituel du matin, c'est le bon moment pour le
recommander : la livraison prend 2 à 3 jours ouvrés.

**[Je recommande mon pot]**

Il vous en reste encore ? **[Rappelez-moi dans une semaine]**

L'équipe Brand G

**What changed and why**

- The English version counts servings ("about 4 left"); the French one talks about the ritual not being
  interrupted, in line with the beauty-ritual angle used across the FR flows.
- The subscription line is removed from the FR R1: one clear action per email, the subscription offer comes
  in R2 for French recipients.

## What I would test next

- Subject line with the number ("About 4 servings left?") vs without, read on **click rate and revenue per
  recipient**, never on opens (machine opens inflate them since September 2025 in the SIMULATED data).
- Day 26 vs day 28 for customers whose previous reorder gap was longer than 35 days (personalised timing from
  their own history).
- A "reorder 2 jars, free shipping" block vs the subscription line, judged on contribution margin per recipient.
