# Cancel-save (F6) - SIMULATED brand "Brand G"

Trigger: the subscriber opens "cancel subscription" in the customer portal. Flow filter: active subscriber.
Never sent after a failed payment (that is a dunning flow, not a save flow). The portal shows the same three
options on screen; this email follows up if the subscriber left without choosing. Metric: save rate (no
cancellation within 14 days) vs a 10 % holdout that sees the plain cancel page; guardrail: complaints.

## X1 - immediately

**Subject:** Before you go: three easier options
**Preheader:** Skip, swap or pause. Your subscription, your rhythm.

Hi {{ first_name|default:"there" }},

We saw you were about to cancel. That is completely fine, and it only takes a click. But if the reason is
timing, taste or too much powder in the cupboard, one of these may suit you better:

- **Skip your next delivery** - nothing is charged, and everything restarts the month after.
- **Swap your product** - try another flavour or format on your next delivery.
- **Pause for up to 3 months** - and we remind you a week before it restarts.

**[Skip my next delivery]**   **[Swap my product]**   **[Pause my subscription]**

Still want to cancel? **[Cancel my subscription]** - no questions, no hoops.

The Brand G team

## X2 - day 2, only if the subscriber chose "too expensive" as the reason

**Subject:** A smaller option, if price is the issue
**Preheader:** Same routine, fewer deliveries.

Hi {{ first_name|default:"there" }},

You told us the price was the reason. Thank you for saying it: it helps us.

Two things that lower what you spend without a bigger discount:

- a delivery every 6 weeks instead of every month;
- the 225 g format between two full jars.

**[Change my delivery rhythm]**

If neither fits, your cancellation is confirmed and you can come back any time.

The Brand G team

*(No percentage-off offer here on purpose: in the SIMULATED data a -30 % comeback offer to "too expensive"
cancellers brought people back but lost contribution margin over 6 months; see page 5.)*

---

## FR adaptation of X1 (not a translation)

**Objet :** Une pause plutôt qu'un adieu ?
**Pré-en-tête :** Décalez, changez ou mettez en pause en un clic.

Bonjour {{ first_name|default:"" }},

Vous souhaitez arrêter votre abonnement : c'est possible en un clic. Mais si c'est une question de rythme ou
d'envie de changement, vous avez peut-être une option plus douce :

- **Décaler** votre prochaine livraison ;
- **Changer** de saveur ;
- **Mettre en pause** jusqu'à 3 mois.

**[Décaler]**   **[Changer]**   **[Mettre en pause]**

Vous préférez arrêter ? **[Résilier mon abonnement]**

L'équipe Brand G

**What changed and why**

- "Une pause plutôt qu'un adieu" is a softer opener than a list of options; the FR flows keep a warmer, more
  personal register.
- The cancel link stays as visible as the other options in both versions: in France, cancelling a
  subscription online must stay simple, so the email never hides it (not legal advice: to be checked with the
  legal team).
