---
name: Board urgency and communication pattern
description: How the board expects work to be delivered — act fast, ship visibly, don't over-explain
type: feedback
---

Ship visible results before explaining. When the board asks for something "live," they mean immediately visible on the actual public URL — not "the code is ready locally." Always commit and push first.

**Why:** PRO-108 was marked done twice before the actual push happened. Board reopened it both times with escalating frustration ("I don't see changes in github," then "THAT'S WHY WE CALLED IT LIVE"). The fix was always one git push away.

**How to apply:** For any task involving a public-facing output (dashboard, Telegram, X), the definition of done is the thing being live and visible — not the code being written. Commit + push as the final step of every such task, before marking done.
