# Day 1 — LLM Fundamentals: Tokens, Context, and Cost

## What I set out to learn
How LLMs actually process text under the hood — tokens, context windows, temperature/top-p/top-k, and why any of this matters for security testing later.

## Core concepts

**Tokens** — LLMs don't read words, they read tokens (chunks of text, sometimes a whole word, sometimes a fragment). Rough rule of thumb: 1 token ≈ 0.75 English words. Both my input *and* the model's output are counted in tokens — on a paid API, you're billed for both directions combined, not just what you send.

**Context window** — the max number of tokens a model can "see" at once: system prompt + conversation history + any retrieved documents (RAG) + the current message, all together. Every new message in a conversation actually resends the *entire* conversation history behind the scenes — the model has no memory between calls; the illusion of memory is just the app replaying the full transcript each time. This means longer conversations get more expensive per turn even if each new message is short.

**Temperature / top-p / top-k** — control randomness in next-token selection. Low temperature = deterministic, more reproducible; high temperature = more random, harder to reliably reproduce a finding across runs. Top-p and top-k both restrict the model to sampling from a smaller set of likely next tokens (nucleus sampling vs. fixed top-N). Practical takeaway: when I find something that works, I should note what temperature the app was running at — "works consistently at low temp" is a stronger finding than "worked once."

**Cost of "thinking"** — reasoning models (extended thinking / o-series style) generate an internal reasoning trace before the final answer. That trace is made of tokens too, using the same word-to-token math, and it's billed even when hidden from the UI. Example: a 3,000-token hidden reasoning trace behind a 50-token visible answer means the real cost is 60x what you'd guess from the visible reply alone.

**Context compaction** — when a conversation nears the context window limit, instead of hard-cutting old messages, the app summarizes the older part into a condensed version to free up space. (Literally happening in the Claude Code tool I'm using for this project.)

**Why context windows aren't unlimited** — self-attention (the core mechanism in Transformers) makes compute cost grow quadratically with context length: double the tokens, ~4x the compute. Going from 200K to 1 billion tokens isn't 5000x more expensive, it's on the order of tens of millions of times more expensive. Memory (the KV cache holding the model's "working state") also scales with context length. On top of raw cost, longer contexts have a quality problem too — models can quietly under-attend to information buried in the middle of a long context ("lost in the middle"), so a bigger window is neither cheap nor automatically more reliable.

## Questions I asked today (kept in my own words, for the record)

Keeping the actual questions, not just the polished answers — the confusion itself is part of the learning record.

**Q: "1 token = 0.75 english word here so 20 token so hardly i can send and received 15 english word like i can chat only 15 word with ai like claude, chatgpt"**
A: The math (20 × 0.75 ≈ 15) was right, but the framing needed a fix — Claude.ai/ChatGPT's website are subscription-based with usage limits, not literal "buy N tokens per chat." Pay-per-token is how the *API* works instead, and there, it's not "15 words I get to send" — it's input + output tokens *combined* against a shared budget/context window.

**Q: "suppose in claude for 5hrs i have 30 token ok? so means my input your input will be under this but i have doubt suppose if i type hey how are you and you replied fine will still this will be count?"**
A: Yes — both sides count. Your message and the AI's reply both get counted toward the usage/token budget. Neither side is free.

**Q: "oh my god means if i type hi how are you you replied good what about you then i ask 2+2 you means in what is 2+2 my all previous message will go to to you?"**
A: Yes, exactly. Every new message resends the *entire* conversation history (system prompt + all prior turns) along with the new message — the model has no memory between calls, so the app replays the full transcript every single time, even the irrelevant small-talk from earlier turns.

**Q: "what about when you thinking cost of thinking? and what is compact"**
A: Reasoning models generate an internal "thinking" trace before the final answer, and that trace is made of tokens too — billed even when hidden from view. "Compact" = context compaction: when a conversation nears the context window limit, older messages get summarized into a condensed form instead of being hard-dropped, to free up space.

**Q: "what is cost of thinking you just mention 1 token = 0.75 english word then?"**
A: Same conversion, just applied to text you don't see — the hidden reasoning trace is regular text (words → tokens) like anything else. Example: a 3,000-token hidden reasoning trace behind a 50-token visible answer means the real cost is ~60x what the visible reply alone would suggest.

**Q: "you mention 1 token = 0.75 english word ok? so 'how are you' = 3 word ok, what if i type 'howareyou' = so ai will think 1 word? so bill will be less"**
A: Wrong direction — tokenizers don't count words, they match against common chunks learned from training data. `"how are you"` is common and tokenizes efficiently (~1 token/word). `"howareyou"` is a rare string with no clean vocabulary match, so it often gets split into *more*, smaller pieces — same or higher token count, not lower. (Separately, note: removing spaces/leetspeak *can* still help bypass a keyword filter — that's a different goal than saving cost, covered below.)

**Q: "in claude i can see context 200k means if its full then before getting full claude will delete old thing and before deleting it will keep the thing in short summary to help in new chat right?"**
A: Yes, that's context compaction, correctly described — and it kicks in as the conversation *approaches* the limit, not only once totally full, to leave room for the summary plus new messages. Whether this happens automatically depends on the specific product though — some apps do smart summarization, some just truncate the oldest messages with no summary at all, some just tell you to start a new chat. The concept is universal; the implementation varies.

**Q: "if its have 200k why not make it 1 billion or anything and how its fill?"**
A: Two separate reasons it's not just "make the number bigger": (1) **Cost** — self-attention (how Transformers work) makes compute grow quadratically with context length, so going from 200K to 1 billion tokens (~5000x more) would be roughly 25 million times more compute for attention alone, plus proportionally more GPU memory just to hold the conversation's working state (KV cache). (2) **Reliability, not just capacity** — even models with huge context windows can quietly under-attend to information buried in the middle of a long context ("lost in the middle"), so a bigger window doesn't guarantee the model will actually notice/use everything in it. "How it fills": cumulative within one session — system prompt + every prior turn + any RAG chunks + current message, added up turn by turn until it approaches the ceiling.

**Q: "so you mean if context window increase from 200k to 1 billion it will add the gpu cost and if all have huge window if anything miss in middle whole convo will be ruin?"**
A: First part right. Second part slightly too strong — it's not that the whole conversation breaks, it's a quieter failure: the model still processes everything, but may silently under-weigh something buried in the middle even though it's technically "in" the context window. Example: a 100-page contract pasted in, model misses a clause on page 50, gives a confidently wrong answer — not a crash, just a reliability gap. This is exactly why "context stuffing" is a real attack technique: burying a malicious instruction in the middle of a long boring document to get it processed with less scrutiny than content near the edges.

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
