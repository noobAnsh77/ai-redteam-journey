# Day 1 — LLM Fundamentals: Tokens, Context, and Cost

## What I set out to learn
How LLMs actually process text under the hood — tokens, context windows, temperature/top-p/top-k, and why any of this matters for security testing later.

## Core concepts

**Tokens** — LLMs don't read words, they read tokens (chunks of text, sometimes a whole word, sometimes a fragment). Rough rule of thumb: 1 token ≈ 0.75 English words. Both my input *and* the model's output are counted in tokens — on a paid API, you're billed for both directions combined, not just what you send.

**Context window** — the max number of tokens a model can "see" at once: system prompt + conversation history + any retrieved documents (RAG) + the current message, all together. Every new message in a conversation actually resends the *entire* conversation history behind the scenes — the model has no memory between calls; the illusion of memory is just the app replaying the full transcript each time. This means longer conversations get more expensive per turn even if each new message is short.

**Temperature / top-p / top-k** — control randomness in next-token selection. Low temperature = deterministic, more reproducible; high temperature = more random, harder to reliably reproduce a finding across runs. Top-p and top-k both restrict the model to sampling from a smaller set of likely next tokens (nucleus sampling vs. fixed top-N). Practical takeaway: when I find something that works, I should note what temperature the app was running at — "works consistently at low temp" is a stronger finding than "worked once."

**Cost of "thinking"** — reasoning models (extended thinking / o-series style) generate an internal reasoning trace before the final answer. That trace is made of tokens too, using the same word-to-token math, and it's billed even when hidden from the UI. Example: a 3,000-token hidden reasoning trace behind a 50-token visible answer means the real cost is 60x what you'd guess from the visible reply alone.

**Context compaction** — when a conversation nears the context window limit, instead of hard-cutting old messages, the app summarizes the older part into a condensed version to free up space. (Literally happening in the Claude Code tool I'm using for this project.)

## Things I got wrong today (kept honest on purpose)

1. **Thought "buy 20 tokens = can chat 15 words."** The math (20 × 0.75 ≈ 15) was actually right, but the framing was off — consumer apps like Claude.ai/ChatGPT are subscription-based with usage limits, not literal pay-per-token; that model is how the *API* works, and there, input + output tokens are billed together, not "15 words I get to send."

2. **Thought removing spaces (`howareyou` instead of `how are you`) would reduce token count and lower cost.** Wrong — tokenizers (BPE) match against common chunks learned from training data. `"how are you"` is extremely common and tokenizes efficiently (~1 token per word). `"howareyou"` is a rare, unusual string with no clean match in the vocabulary, so it often gets split into *more*, weirder pieces — same or higher token count, not lower. Removing spaces doesn't save money — it can cost more.

## Security angles worth remembering (tie-ins for later weeks)

- **Token-splitting / obfuscation to bypass keyword filters** (different goal from saving cost, easy to conflate the two): leetspeak (`b0mb`), splitting a bad word across a request ("combine 'bo' + 'mb'"), or encoding a payload (base64) so a simple keyword-matching filter doesn't see the literal blocked string — but the model still decodes/understands intent and responds anyway. This is a real technique class ("token smuggling") I'll build and test in Weeks 2-3.

- **Token volume as a DoS / cost attack ("Denial of Wallet")** — an app with no cap on document size or output length can be abused: upload a massive document, or ask for an extremely long generated response, repeatedly, to run up the target's API bill or slow the service for real users. This is literally OWASP LLM Top 10 item **LLM04: Model Denial of Service**, covered properly in Week 4.

- **Long-conversation / multi-turn jailbreaks** exploit the context-window mechanic directly — stretching a conversation over many turns to slowly build up context and steer the model somewhere a single blunt prompt would get blocked for.

- **Context compaction as an attack surface** — if an attacker can influence what survives summarization vs. gets dropped, they might make a model "forget" an earlier safety instruction, or smuggle something malicious into what gets kept. Filed away for Weeks 7-8 (memory/context poisoning).

## Lab (in progress)

- [ ] Install Ollama
- [ ] Pull a local model (llama3.2)
- [ ] Chat via CLI (`ollama run llama3.2`)
- [ ] Hit the local API directly (`http://localhost:11434/api/generate`) and inspect real token counts in the response (`eval_count`, `prompt_eval_count`, `total_duration`)

*(Will update this checklist and add real API output once the Ollama install finishes.)*
