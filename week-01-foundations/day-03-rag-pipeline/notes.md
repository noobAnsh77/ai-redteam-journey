# Day 3 — RAG Pipeline: Chunking, Vector DB, Retrieval & Generation

## What I set out to learn

How a full RAG pipeline actually works end-to-end — the 4 steps a developer builds, how they connect, and where the attack surface lives before we exploit any of it in Weeks 5-6.

## Core concepts

**The 4-step RAG pipeline**

```
[Indexing — one-time setup, no user involved]
Document → Chunker → Chunks → embed() → Vectors → Vector DB stores them

[Query — happens every time a user asks something]
User question → embed() → query vector → Vector DB finds top-N closest chunks
→ chunk text retrieved → combined with question → LLM generates grounded answer
```

**Step 1 — Chunking**

Splitting a large document into smaller pieces before embedding. Done once during indexing, never at query time, and never on the user's question.

- Why: embedding a whole document as one vector loses specific detail (back to Day 2 — one big blob dilutes meaning). Each chunk needs to be small enough that its embedding actually represents a specific idea, not a mix of 50 ideas.
- Chunk size sweet spot: ~200-500 words (~300 is common). Too small (single sentences) = too many chunks, fragmented context, huge API call count. Too large = back to the dilution problem.
- Real scale: a 1000-page document at ~500 words/page = ~500,000 words → ~1,700 chunks at 300 words each.
- Embedding all 1,700 chunks takes ~10-15 minutes locally (one API call per chunk, ~0.4s each). Production systems use batch embedding — hundreds of chunks per call — cutting this to a few minutes.
- **Key point:** this is a one-time background job done by the developer. It does not happen per user query. Zero impact on live query speed.

**Step 2 — Embedding (covered in depth Day 2)**

Each chunk runs through `embed()` once → stored as a vector in the vector DB. Same `embed()` API used at query time for the user's question. Never chunked, never embedded more than once (unless the document changes).

**Step 3 — Vector Database (Chroma)**

A specialized database built for one job: store many vectors and answer "given this new vector, which stored vectors are closest?" extremely fast.

- Normal SQL databases can't do this — "find nearest vector" isn't a SQL operation.
- Chroma uses approximate nearest neighbor (ANN) search algorithms (HNSW / IVF) — pre-organizes vectors into a graph/cluster structure during insertion so it can skip most stored vectors at search time and jump to the likely neighborhood.
- Tradeoff: approximate (might miss the single best match by a tiny margin) but returns top candidates in milliseconds. For RAG, "very close" is good enough.
- What Chroma stores per chunk:
  ```
  chunk_id → {
    embedding: [0.023, -0.41, 0.88, ...],  # 768 numbers
    document: "...original chunk text...",
    metadata: {source: "policy.pdf", page: 42}
  }
  ```

**Step 4 — Retrieval + Generation**

- User's question gets embedded (once, whole — never chunked)
- Vector DB returns top-N chunks by similarity
- Retrieved chunk text + original question combined into one prompt
- LLM generates a grounded answer using both

Example for "what is 2+2" hitting a healthcare RAG:
```
embed("what is 2+2") → query vector
→ Vector DB returns top-3 "closest" healthcare chunks (likely something vague
  like "dosage: 2mg + 2mg = 4mg" — closest available, not actually relevant)
→ Prompt: "Answer: what is 2+2. Context: [chunk1] [chunk2] [chunk3]"
→ LLM replies: "4" (math is in training, ignores irrelevant context)
```

## Questions I asked today

**Q: "in chunking, if a developer builds a healthcare RAG with a 1000-page document and chunks it sentence-by-sentence, how long would that take?"**

A: First correction — real systems don't chunk sentence-by-sentence. That creates too many tiny, fragmented pieces that lose surrounding context. Typical chunk size is ~200-500 words. At that size, 1000 pages → ~1,700 chunks (vs. tens of thousands for sentence-level, which is why chunk size matters practically, not just theoretically).

Time to embed 1,700 chunks locally: ~10-15 minutes one-time. Production speeds this up using batch embedding. More importantly — this is a one-time background indexing job done before any user arrives, completely invisible to people chatting with the app. The "slow part" doesn't affect live query speed at all.

**Q: "vector DB understood — so retrieval+generation means: RAG is already updated in chunks, user asks, AI replies by checking closest similarity (like top-k/top-p from Day 1) — and if user sends 'what is 2+2', does it get broken into chunks and sent with the RAG chunks to the chat model?"**

A: Almost exactly right, one correction: the user's question is never chunked. Only documents get chunked during indexing. The user's question gets embedded as a single whole unit, used as the search query. The retrieved chunk text (which was already chunked during indexing) + the original user question together get sent to the LLM. So yes — top-k/top-p from Day 1 applies at the generation step, and cosine similarity from Day 2 is the retrieval step. Everything connects.

## Security angles worth remembering

- **Vector DB has no native access control** — by default it finds the nearest vectors across everything stored, with no concept of who owns which document. A multi-tenant app storing all customers' documents in one collection without metadata filtering = User A's query retrieves User B's private documents. This is the cross-tenant data leakage attack (Weeks 5-6).

- **Malicious content in the vector DB persists across sessions** — unlike injecting something into one conversation's context window, a poisoned chunk stored in the vector DB gets retrieved every time a query is close enough. One successful RAG poisoning = persistent attack on every future user whose query matches.

- **The retrieval step is blind to intent** — the vector DB doesn't know if a user's query is legitimate, adversarial, or off-topic. It just returns "nearest." An attacker who knows what's indexed can craft queries designed to pull specific sensitive chunks, even ones that weren't meant to be surfaced.

- **Approximate search = fuzzy attack surface** — because ANN search is approximate and picks up surface-level patterns (we saw this in Day 2: finance vs. weather scored 0.588 due to incidental word overlap), a malicious document doesn't need to be a strong topical match to get retrieved — just close enough in the embedding space.

## Lab — upcoming

- [ ] Build end-to-end RAG pipeline: Chroma vector DB + LangChain + actual retrieval + generation
- [ ] Index a small document set
- [ ] Test with relevant and irrelevant queries
- [ ] Confirm retrieval + grounded generation works
- [ ] Test what happens with no-match queries (naive vs. threshold behaviour)
