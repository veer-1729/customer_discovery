# Demo prompt: founding engineer incident debug

Use this to verify outreach skills in Cursor Agent.

## Prompt

```text
Read .cursor/skills/cold-email/SKILL.md and LOCAL-OVERLAY.md first.

Draft a short customer discovery email to a founding engineer at a Seed-stage B2B SaaS company about how they debug production incidents after deploys, without pitching the product.

Context (minimal):
- Company: example B2B SaaS, ~15 engineers, public API docs, careers page mentions on-call rotation
- Recipient: founding engineer / head of platform
- Goal: learn their post-deploy incident workflow, not sell

Deliver: subject line (2–3 variants) + email body (~120–180 words) + one discovery question.
```

## Second pass (optional)

```text
Read .cursor/skills/cold-email-rewrite/SKILL.md and LOCAL-OVERLAY.md.

Rewrite the email above. Compare original vs rewrite in a short table: opener, length, salesiness, discovery question quality.
```

## Sequence variant (optional)

```text
Read .cursor/skills/cold-outreach-sequence/SKILL.md and LOCAL-OVERLAY.md (standard mode).

Using the same context, produce: LinkedIn connection request (≤300 chars), first message after accept, and one follow-up. No product pitch.
```

## Success criteria

- Agent reads skill + overlay before drafting
- No Emergent Delta pitch unless you add it to the prompt
- Email sounds peer-to-peer, not marketing
- Personalization tied to on-call / deploy context, not generic flattery
