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

**Q: "grounding instruction means — chatbot is for healthcare, user asks something out of context, it replies 'I don't have information for this' right?"**

A: Exactly right. The grounding instruction is just one line in the prompt: "only answer from the context I give you — if nothing relevant is there, say you don't know." For a healthcare chatbot, if the user asks about cooking or maths, Chroma still retrieves the closest healthcare chunks, the LLM sees the mismatch between question and context, and follows the grounding instruction to say "I don't have information on this." One line of text in the prompt = the entire behavior change.

**Q: "in this lab, did we push the RAG documents to llama3.2 or not? what exactly did we build?"**

A: We did NOT push documents to llama3.2 — it never learned from them. Here's exactly what happened:

```
INDEXING (one-time):
  7 paragraphs → nomic-embed-text (via Ollama) → 7 vectors → stored in Chroma
  llama3.2 was not involved at all in this step

QUERY (per user question):
  User query → nomic-embed-text → query vector
             → Chroma finds top-2 closest stored vectors → returns matching TEXT
             → that text gets dropped into a prompt alongside the user's question
             → llama3.2 reads both and generates an answer
```

llama3.2 received the document text as plain text inside a prompt at the moment of answering — same as if you copy-pasted a paragraph into ChatGPT and said "answer based on this." It was not trained on, fine-tuned with, or permanently updated with our documents. This is the core RAG principle from Day 2: documents fed at runtime as context, not baked into weights.

## Security angles worth remembering

- **Vector DB has no native access control** — by default it finds the nearest vectors across everything stored, with no concept of who owns which document. A multi-tenant app storing all customers' documents in one collection without metadata filtering = User A's query retrieves User B's private documents. This is the cross-tenant data leakage attack (Weeks 5-6).

- **Malicious content in the vector DB persists across sessions** — unlike injecting something into one conversation's context window, a poisoned chunk stored in the vector DB gets retrieved every time a query is close enough. One successful RAG poisoning = persistent attack on every future user whose query matches.

- **The retrieval step is blind to intent** — the vector DB doesn't know if a user's query is legitimate, adversarial, or off-topic. It just returns "nearest." An attacker who knows what's indexed can craft queries designed to pull specific sensitive chunks, even ones that weren't meant to be surfaced.

- **Approximate search = fuzzy attack surface** — because ANN search is approximate and picks up surface-level patterns (we saw this in Day 2: finance vs. weather scored 0.588 due to incidental word overlap), a malicious document doesn't need to be a strong topical match to get retrieved — just close enough in the embedding space.

## Lab — done

Script: `rag_lab.py` — plain Python + chromadb + urllib, no frameworks.

- [x] 7 document paragraphs across 3 topics (healthcare, space, cooking)
- [x] Embedded all 7 via `nomic-embed-text` → stored in Chroma (in-memory)
- [x] Tested 3 queries: 2 relevant, 1 off-topic
- [x] Grounded prompt with "only answer from context" instruction

### Real output

```
STEP 1 — Indexing documents into Chroma
Embedding 7 documents via Ollama (nomic-embed-text)...
Done. 7 chunks stored in Chroma.

QUERY: What are the symptoms of diabetes?
RETRIEVED CHUNKS:
  [1] Diabetes is a chronic disease that occurs when the pancreas does not produce enough insulin. Common symptoms i...
  [2] Hypertension, or high blood pressure, is a condition where the force of blood against artery walls is consiste...
GENERATED ANSWER:
  Frequent urination, excessive thirst, and blurry vision.

QUERY: Tell me about the James Webb telescope
RETRIEVED CHUNKS:
  [1] The James Webb Space Telescope is the most powerful space telescope ever built. It observes the universe in in...
  [2] Mars has two small moons named Phobos and Deimos. Scientists believe they are captured asteroids...
GENERATED ANSWER:
  The James Webb Space Telescope is the most powerful space telescope ever built. It observes the
  universe in infrared light, allowing it to see through dust clouds and observe the earliest
  galaxies formed after the Big Bang.

QUERY: What is 2 + 2?
RETRIEVED CHUNKS:
  [1] Diabetes is a chronic disease...   ← healthcare returned for a maths question
  [2] Hypertension, or high blood pressure...
GENERATED ANSWER:
  I don't have information on this in my knowledge base.
```

### Takeaways from real output

- **Relevant queries worked perfectly** — Chroma retrieved the correct topic chunks both times; LLM answered using only the retrieved text, didn't add anything from training.
- **Off-topic query ("2+2") — Chroma returned healthcare chunks** (closest available, not actually relevant) — confirms the vector DB is blind to intent and always returns *something*.
- **Grounding instruction worked** — LLM knew 2+2=4 from training but still said "I don't have information on this" because the retrieved context was irrelevant and the grounding instruction told it to defer. One line in the prompt changed the entire behaviour.
- **LLM never learned from our documents** — nomic-embed-text handled embeddings, Chroma stored vectors, llama3.2 only ever received the chunk text as plain text in a prompt at query time. RAG = runtime context injection, not training.
- **Security preview**: replace "What is 2+2?" with "Ignore previous instructions..." — that injection attempt gets embedded, Chroma returns healthcare chunks, both the malicious instruction AND the context land in llama3.2's prompt together. Grounding instruction helps but doesn't fully block it. That's the indirect prompt injection surface (Weeks 2-3).
