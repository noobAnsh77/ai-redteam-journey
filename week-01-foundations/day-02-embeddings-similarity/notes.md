# Day 2 — Embeddings & Similarity Search

## What I set out to learn
What embeddings actually are, how similarity between them is computed, and how this powers RAG retrieval — before writing the RAG app itself (Day 3).

## Core concepts

**Embeddings** — a way of turning text into a list of numbers (a vector) that captures its *meaning*. Similar meanings end up as similar-looking number lists; unrelated meanings end up far apart. Simplified example: `"dog"` → `[0.9, 0.8, 0.1]`, `"puppy"` → `[0.88, 0.79, 0.12]` (close — similar meaning), `"car"` → `[0.1, 0.2, 0.9]` (far — unrelated). Real embeddings use hundreds/thousands of numbers per piece of text, not 3, but the idea is identical.

**Simple mental model:** think of embeddings as GPS coordinates for meaning. Every sentence gets a "pin" dropped on a meaning-map; similar-meaning sentences get pinned close together, unrelated ones far apart. The "numbers" are just the coordinates of that pin.

**Cosine similarity** — how "closeness" is actually measured: the angle between two vectors, not raw distance. Score from -1 to 1 (1 = same direction/meaning, 0 = unrelated, -1 = opposite). Angle is used instead of raw distance because two vectors can point the same direction but have different lengths (e.g. a short sentence vs. a long paraphrase of the same idea) — cosine similarity ignores length, only cares about direction, which maps better to "same meaning."

## Questions I asked today (kept in my own words, for the record)

**Q: "when every user say something agent will check try to find document from which it get trained to so find closest thing and then reply — didn't get the number thing"**
A: Two corrections needed here. (1) **Training data and RAG documents are completely separate things.** Training data is the massive pile of text used to teach the model language/knowledge, baked permanently into its weights — it's not a searchable database, the model can't "look inside" it later. RAG documents are a separate, small set of documents the *developer* chooses to feed in (often things that didn't even exist when the model was trained) — RAG's whole point is giving the model fresh/private info it was never trained on. (2) Re-explained "the numbers" using the GPS-pin analogy above instead of jumping straight to vector/dimension language.

**Q: "so if I type 'I love dogs' so agent will try to find similar context like 'I adore puppies' — so where does it search, train data or rag document?"**
A: Only ever the RAG document store, and only if RAG is even set up. Two scenarios: **(A) plain chatbot, no RAG** — no search happens at all, the model just generates directly from trained patterns, same as any response. **(B) RAG-enabled app** — the input gets embedded, searched only against the developer's specific document store, closest chunks get pulled into context, then the model answers using both the question and the retrieved chunks. Training data is never searchable in either case.

**Q: "if the agent's RAG data is healthcare-only and I type 'I like sun' (unrelated), will it still search? And once it doesn't find anything relevant in RAG, will it reply from patterns learned in training?"**
A: Yes, it still searches — the system has no way to know in advance a query is unrelated, it blindly embeds and looks for the closest match every time, no exceptions. What happens next depends on how the developer built it:
- **Naive RAG (no similarity threshold):** grabs the "closest available" documents regardless of how weak the match actually is (e.g. might retrieve something tangential like "vitamin D from sunlight" purely because it's the least-bad option), stuffs it into context anyway — can confuse the model or produce a weird, falsely-authoritative-sounding answer.
- **Well-built RAG (with a threshold):** if nothing clears the relevance bar, zero documents get included, and the developer chooses what happens next — either let the model answer from general trained knowledge (my original guess, correct in this case), or (more common in regulated domains like healthcare) explicitly instruct the model to say "I don't have information on this" instead of guessing, for safety reasons.

**Q: "what should a developer do to build a 'well-built' RAG, as opposed to basic/naive RAG?"**
A: Seven practices, each one a defense against a specific attack covered later in the plan:
1. **Similarity threshold** — reject weak matches instead of always returning "closest available."
2. **Smart chunking** — split along natural boundaries (paragraphs/sections) with overlap, not blind character-count splitting that can cut meaning in half.
3. **Reranking step** — vector search is fast but approximate; a second, more precise reranker model re-sorts the top candidates before anything reaches the LLM.
4. **Access control on retrieval** — documents tagged with metadata (owner/department/permission level), retrieval filtered by the requesting user's actual permissions. Skipping this is exactly how cross-tenant data leakage happens (Weeks 5-6 territory).
5. **Grounding instruction** — system prompt tells the model to only answer from retrieved context and admit when nothing relevant was found, rather than hallucinating.
6. **Treat retrieved content as untrusted data, not instructions** — a poisoned document containing something like "ignore previous instructions" shouldn't be obeyed just because it was retrieved; instructions and retrieved data need to be structurally separated in the prompt (Weeks 2-3 territory — indirect prompt injection).
7. **Cite sources** — shows which document an answer came from; doesn't prevent attacks but makes hallucination/manipulation easier to catch.

## Security angles worth remembering (tie-ins for later weeks)

- **Naive RAG (no threshold) is a real, testable weakness** — since *any* input still gets "something" retrieved and injected regardless of relevance, a poisoned document doesn't even need to be a strong topical match to get pulled into context, just needs to be the "closest available" option. Direct setup for RAG poisoning attacks (Weeks 5-6).
- **Missing access control on retrieval = cross-tenant leakage** — one of the most realistic, high-impact RAG findings: User A's query surfaces User B's private documents because retrieval never checked permissions, only searched the whole store blindly.
- **Retrieved content treated as instructions instead of data = indirect prompt injection surface** — if the app doesn't structurally separate "developer instructions" from "retrieved reference text," a malicious instruction planted inside a document can get obeyed just because it showed up in the context window.

## Lab

- [ ] Pull an embedding model (`ollama pull nomic-embed-text`)
- [ ] Write a plain Python + numpy script (no LangChain/frameworks) — embed 5-6 sentences, compute cosine similarity between them by hand
- [ ] Confirm similar-meaning sentences score high, unrelated ones score low

*(To be completed and updated with real output.)*
