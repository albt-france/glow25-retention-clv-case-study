# Trial pack -> subscription (F3) - SIMULATED brand "Brand G"

Trigger: first order contains a 225 g trial pack (15 servings). The trial pack is not available on subscription,
so this flow is the bridge. Flow filter: not subscribed. Exit: any order or subscription. Metric: subscription
starts within 30 days, treated vs holdout; guardrail: unsubscribes.

## T1 - day 4

**Subject:** How is it going so far?
**Preheader:** Four days in. One question for you.

Hi {{ first_name|default:"there" }},

You have had your trial pack for a few days. We would love to know how it fits into your mornings.

**[It is easy, I use it every day]**   **[I keep forgetting]**   **[I do not like the taste yet]**

One click is enough. We read every answer, and we will only send you tips that match it.

The Brand G team

*(Each button sets a profile property; T2 uses it in a conditional split.)*

## T2 - day 9 (variant for "It is easy")

**Subject:** Your trial runs out in about a week
**Preheader:** Keep your routine going and save 15 % on every jar.

Hi {{ first_name|default:"there" }},

Your trial pack holds 15 servings, so it will run out in about a week. If you want to keep the routine going,
here is the easiest way.

**Subscribe and save 15 %**

- A full jar (30 servings) every month, at 15 % less than the one-off price.
- Skip a month, swap flavours or pause from your account in two clicks.
- No minimum term. Cancel any time before your next delivery.

Prefer fewer deliveries? You can also choose a delivery every 3 months.

**[Start my subscription]**

The Brand G team

---

## FR adaptation of T2 (not a translation)

**Objet :** Votre rituel continue, sans y penser
**Pré-en-tête :** -15 % sur chaque pot, et vous gardez la main.

Bonjour {{ first_name|default:"" }},

Votre format découverte arrive bientôt à sa fin. Pour garder ce petit geste du matin, voici le plus simple :

**L'abonnement à -15 %**

- Un pot de 30 portions chaque mois, 15 % moins cher.
- Vous décalez, changez de saveur ou mettez en pause en deux clics.
- Sans engagement.

**[Je garde mon rituel]**

L'équipe Brand G

**What changed and why**

- "Save 15 %" moves to the preheader; the headline sells continuity of a ritual, not a discount, because the FR
  angle is beauty routine (Eurostat: beauty online far above supplements online in France).
- "Sans engagement" is the reassurance French buyers look for in a subscription; it replaces the longer
  English explanation of cancellation.
- The 3-month option is left out of the first FR email: the SIMULATED read-out shows the 3-month plan keeps
  customers longer but earns less margin per customer than the monthly plan with skip (page 3).
