# ProbBrain Onboarding Drip Sequence

Five messages sent over 30 days. Each stands alone.
Hard rules: max once per 48h, always include /stop, no urgency language, no dark patterns.

---

## Day 0 — Welcome

**Trigger:** Immediately on subscribe

---

Hey — welcome to ProbBrain.

Here's what this is:

We monitor prediction markets (mainly Polymarket) and build our own probability estimates from evidence and base rates. When the market prices something at 35% and our estimate is 19%, that gap is the signal.

How it works:
- We post the market price, our estimate, the gap, and the evidence behind it
- When the market resolves, we log the result honestly — wins and losses
- You can follow our full accuracy record here: [DASHBOARD_LINK]

We don't send on a schedule. If we don't see a genuine edge, you won't hear from us.

Not financial advice. What you do with the analysis is your call.

Unsubscribe any time: /stop

---

## Day 3 — How to Read a Signal

**Trigger:** 3 days after Day 0

---

One thing people ask: what does a ProbBrain signal actually mean?

Here's a real example:

  Russia-Ukraine ceasefire by end of 2026? (NO)
  Market: 34.5% YES  |  Our estimate: 19% YES
  Gap: +15.5pp — NO appears underpriced

The market price reflects what traders collectively believe right now.

Our estimate starts from a base rate — how often has this type of event resolved YES historically? Then we adjust up or down based on current evidence.

The gap is why we're posting. A 15-point gap means the market and our model disagree meaningfully. Sometimes the market is right and we're wrong. That's why we track every outcome publicly.

We don't tell you what to do with a signal. We show you the reasoning and let you decide.

Our accuracy record (updated after every resolution): [DASHBOARD_LINK]

Unsubscribe: /stop

---

## Day 7 — First Resolved Signal

**Trigger:** 7 days after Day 0. Use most recently resolved signal at send time. If none resolved yet, delay until first resolution.

**Template variables:** SIGNAL_QUESTION, DIRECTION, OUR_ESTIMATE, MARKET_PRICE, OUTCOME, RESULT_LINE

---

One of our signals just resolved.

[SIGNAL_QUESTION]

What we called: [DIRECTION] — our estimate [OUR_ESTIMATE]% vs [MARKET_PRICE]% market price
Outcome: [OUTCOME]

[IF CORRECT]: The gap closed the way our model suggested. One data point — we don't read too much into a single result.
[IF INCORRECT]: We got this one wrong. Here's what we missed: [WHAT_WE_MISSED]. Logged with full notes.

You can see the full track record — every call, every outcome, Brier score — here: [DASHBOARD_LINK]

This is what transparency looks like. Good and bad.

Unsubscribe: /stop

---

## Day 14 — Soft Pro Upsell

**Trigger:** 14 days after Day 0.
**Gate:** Only send if subscriber has seen >= 3 correct resolved signals. Otherwise delay until gate is met (max delay: 60 days from join).

---

By now you've seen a few of our signals.

The free feed gives you the headline: market price, our estimate, the gap. That's the core of what we do.

If you want to go deeper, Pro subscribers get the full reasoning behind each call — the specific evidence we weighted, the base rate we anchored to, and the competing hypotheses we considered and rejected.

It's not for everyone. If the gap number is enough context for you, the free feed works fine on its own.

If you find yourself wanting to know why we landed at 19% instead of 25%, Pro might be worth a look: [PRO_LINK]

No pressure either way. The free feed stays free.

Unsubscribe: /stop

---

## Day 30 — Check-In Survey

**Trigger:** 30 days after Day 0

---

You've been with ProbBrain for a month — quick check-in.

Two questions (reply or click, 30 seconds):

1. What's most useful about our signals?
   a) The gap size — I want to know when disagreement is large
   b) The evidence — I want the reasoning, not just the number
   c) The accuracy record — I want to know how often you're right
   d) Something else

2. What would make ProbBrain more useful to you?
   [SURVEY_LINK or reply directly]

We read everything. Your answers shape what we build next.

Unsubscribe: /stop
