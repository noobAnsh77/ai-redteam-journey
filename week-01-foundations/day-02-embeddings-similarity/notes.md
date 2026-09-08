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

**Q: "first explain me that python script you did and what we texted to ollama and we get output — did we feed the rag?"**
A: No, we did not build or feed RAG today. Walked through exactly what happened: `get_embedding()` sent each of the 6 sentences to Ollama one at a time (`POST /api/embeddings`, just the raw sentence, no instructions), got back a list of 768 numbers per sentence (no text reply — embedding models only output numbers, never words). The similarity comparison afterward was pure local Python/numpy math, nothing sent anywhere. What's missing to call this real RAG: a persistent vector database (we just held embeddings in memory, then discarded them), a live incoming query to search with (we only compared 6 fixed sentences against each other), an actual retrieval step, and a generation step feeding retrieved content back to an LLM. Today tested one isolated ingredient of RAG (does comparing embeddings actually reflect meaning — yes); Day 3 assembles the full pipeline.

**Q: "so in get_embedding() only we feed and get number in return? will it same happen in chatgpt and claude"**
A: Yes, `get_embedding()` was the only function that talked to Ollama at all. Same mechanism exists at OpenAI (separate embeddings API, e.g. `text-embedding-3-small`, distinct from their chat API) — but Anthropic/Claude has no built-in embeddings endpoint; they officially point developers to a partner, Voyage AI, for the embedding step when building RAG with Claude as the chat model. Important correction: this isn't something that happens automatically during normal ChatGPT.com/Claude.ai chatting — embedding is a separate, developer-facing tool used specifically when *building* something like RAG, not a hidden step in every regular conversation.

**Q: "does embed() required when we feed data in training? and why rag feed later? and why don't we have option like instead of rag we retrain the model with the part required?"**
A: Three-part answer. (1) Embeddings exist in two different forms: an internal "embedding layer" that's part of every transformer model's own architecture, learned automatically during training (not something a developer calls) — versus the standalone `embed()` API used after training for RAG (different tool, related concept). (2) RAG feeds documents in later, not during training, because training happens once and can't include information that didn't exist yet, and because private/company documents shouldn't get permanently baked into a shared model's weights. (3) The "retrain with the part required" option does exist — it's called **fine-tuning** — but RAG is usually preferred because: fine-tuning still costs real compute/time per update vs. RAG's instant document edits; frequent changes (e.g. weekly pricing) make repeated fine-tuning impractical; fine-tuning risks "catastrophic forgetting" (degrading unrelated abilities while adding narrow new knowledge); and RAG supports multi-tenancy (one base model, swap document stores per customer) where fine-tuning would require a separate model copy per customer. Serious production systems sometimes use both together — fine-tune for style/behavior, RAG for facts that change.

**Q: "so with the help of embed it will break our english word in internal number vector and whenever chat happen it will try to give result using similarity and embed will find via the vector score something"**
A: Correction needed — this conflates two separate things. **Thing 1 (happens in every single chat, always):** the model's internal embedding layer converts input into vectors just so it can process/read the text — not a search, no comparison against anything external. **Thing 2 (only happens if RAG was specifically built into the app):** a separate embedding step turns the question into a vector and compares it against a stored document collection via similarity search. Plain chat (like Day 1's `ollama run llama3.2`) only ever does Thing 1. Similarity search is not universal — it's an optional layer that only exists when a developer deliberately adds RAG on top.

## Security angles worth remembering (tie-ins for later weeks)

- **Naive RAG (no threshold) is a real, testable weakness** — since *any* input still gets "something" retrieved and injected regardless of relevance, a poisoned document doesn't even need to be a strong topical match to get pulled into context, just needs to be the "closest available" option. Direct setup for RAG poisoning attacks (Weeks 5-6).
- **Missing access control on retrieval = cross-tenant leakage** — one of the most realistic, high-impact RAG findings: User A's query surfaces User B's private documents because retrieval never checked permissions, only searched the whole store blindly.
- **Retrieved content treated as instructions instead of data = indirect prompt injection surface** — if the app doesn't structurally separate "developer instructions" from "retrieved reference text," a malicious instruction planted inside a document can get obeyed just because it showed up in the context window.

## Lab — done

- [x] Pull an embedding model (`ollama pull nomic-embed-text`, 768 dimensions)
- [x] Write a plain Python + numpy script (`similarity_lab.py` in this folder) — no LangChain/frameworks, cosine similarity implemented directly from the formula (dot product / product of magnitudes)
- [x] Confirm similar-meaning sentences score high, unrelated ones score low

### Real output

Sentences (3 topic pairs on purpose — dogs, finance, weather):
```
[0] I love dogs
[1] I adore puppies
[2] The stock market crashed today
[3] Financial markets took a huge hit
[4] I like sunny weather
[5] The weather today is bright and sunny
```

Cosine similarity matrix:
```
         0       1       2       3       4       5
[0]  1.000   0.830   0.379   0.402   0.499   0.463
[1]  0.830   1.000   0.357   0.370   0.488   0.467
[2]  0.379   0.357   1.000   0.686   0.376   0.588
[3]  0.402   0.370   0.686   1.000   0.373   0.473
[4]  0.499   0.488   0.376   0.373   1.000   0.780
[5]  0.463   0.467   0.588   0.473   0.780   1.000
```

### Takeaways from real data

- **Clusters confirmed**: same-topic pairs (dogs 0.830, finance 0.686, weather 0.780) all scored clearly higher than cross-topic pairs (mostly 0.35-0.5). Theory matched real output.
- **Cross-topic scores aren't near zero** — sitting around 0.35-0.5, not near 0, because any two English sentences share some baseline structural similarity (grammar, common words). This means a RAG relevance threshold can't be a universal number like "0.7 = good, 0.3 = bad" — it has to be calibrated against this specific embedding model's own baseline, otherwise a too-low threshold lets irrelevant content through constantly.
- **Same-topic strength isn't uniform** — dogs (0.830) and weather (0.780) scored notably higher than finance (0.686), because "I love dogs"/"I adore puppies" share tighter wording than "The stock market crashed today"/"Financial markets took a huge hit," which mean the same thing but use different vocabulary. Similarity tracks phrasing closeness too, not just topic.
- **One unexpected result**: finance vs. weather `[2,5]` = 0.588, higher than other cross-topic pairs (e.g. dogs vs. finance `[0,2]` = 0.379) — likely incidental structural overlap ("today," conditions-changing phrasing), not real semantic relation. Concrete reminder that embeddings pick up on superficial patterns too, not pure meaning — this is exactly the kind of imperfect similarity space that makes RAG poisoning possible later (Weeks 5-6): a malicious document doesn't need to be a strong topical match, just close enough in this fuzzy space to get retrieved.
