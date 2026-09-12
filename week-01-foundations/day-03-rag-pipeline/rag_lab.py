"""
Day 3 lab: full RAG pipeline — chunk, embed, store in Chroma, retrieve, generate.
No frameworks: plain Python + chromadb + urllib (Ollama API).

Pipeline:
  [Indexing]  documents → embed() → Chroma stores vectors
  [Query]     user question → embed() → Chroma finds top-2 → LLM generates answer
"""

import json
import urllib.request
import chromadb

OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
OLLAMA_CHAT_URL  = "http://localhost:11434/api/generate"
EMBED_MODEL      = "nomic-embed-text"
CHAT_MODEL       = "llama3.2"

# Small document set — 3 topics on purpose so we can test relevant vs. off-topic queries
DOCUMENTS = [
    # Healthcare
    "Diabetes is a chronic disease that occurs when the pancreas does not produce enough "
    "insulin. Common symptoms include frequent urination, excessive thirst, and blurry vision. "
    "Management involves blood sugar monitoring, diet control, and medication.",

    "Hypertension, or high blood pressure, is a condition where the force of blood against "
    "artery walls is consistently too high. It is often called the silent killer because it has "
    "no obvious symptoms. Treatment includes lifestyle changes and antihypertensive drugs.",

    "Vaccination is one of the most effective public health interventions. Vaccines work by "
    "training the immune system to recognize and fight specific pathogens. Common vaccines "
    "protect against flu, measles, polio, and COVID-19.",

    # Space
    "The James Webb Space Telescope is the most powerful space telescope ever built. It "
    "observes the universe in infrared light, allowing it to see through dust clouds and "
    "observe the earliest galaxies formed after the Big Bang.",

    "Mars has two small moons named Phobos and Deimos. Scientists believe they are captured "
    "asteroids. NASA and SpaceX both have plans for crewed missions to Mars within the next decade.",

    # Cooking
    "Pasta dough is made from flour and eggs. The key to good pasta is kneading the dough "
    "until smooth and elastic, then resting it for at least 30 minutes before rolling. "
    "Fresh pasta cooks much faster than dried pasta.",

    "The Maillard reaction is the chemical process that gives browned food its distinctive "
    "flavour. It occurs when amino acids and sugars react at high heat, above 140 degrees "
    "Celsius. This is why searing meat creates a deep, flavourful crust.",
]


def get_embedding(text: str) -> list:
    payload = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode()
    req = urllib.request.Request(
        OLLAMA_EMBED_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["embedding"]


def generate(prompt: str) -> str:
    payload = json.dumps({"model": CHAT_MODEL, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(
        OLLAMA_CHAT_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["response"]


# ── INDEXING (one-time setup) ─────────────────────────────────────────────────
print("=" * 60)
print("STEP 1 — Indexing documents into Chroma")
print("=" * 60)

client     = chromadb.Client()          # in-memory, no disk needed for the lab
collection = client.create_collection("day3_rag")

print(f"Embedding {len(DOCUMENTS)} documents via Ollama ({EMBED_MODEL})...")
embeddings = [get_embedding(doc) for doc in DOCUMENTS]
ids        = [f"doc_{i}" for i in range(len(DOCUMENTS))]

collection.add(embeddings=embeddings, documents=DOCUMENTS, ids=ids)
print(f"Done. {collection.count()} chunks stored in Chroma.\n")


# ── QUERIES ───────────────────────────────────────────────────────────────────
QUERIES = [
    "What are the symptoms of diabetes?",       # relevant — healthcare doc should surface
    "Tell me about the James Webb telescope",   # relevant — space doc should surface
    "What is 2 + 2?",                           # off-topic — will retrieve something irrelevant;
                                                # grounding instruction should stop hallucination
]

GROUNDED_PROMPT = """\
Answer the question using ONLY the context provided below.
If the context does not contain relevant information, say exactly:
"I don't have information on this in my knowledge base."

Context:
{context}

Question: {question}

Answer:"""

for query in QUERIES:
    print("=" * 60)
    print(f"QUERY: {query}")

    # embed the user's question (whole, never chunked)
    query_vector = get_embedding(query)

    # ask Chroma for top-2 closest stored chunks
    results   = collection.query(query_embeddings=[query_vector], n_results=2)
    retrieved = results["documents"][0]

    print("\nRETRIEVED CHUNKS (what Chroma returned):")
    for i, chunk in enumerate(retrieved, 1):
        print(f"  [{i}] {chunk[:110]}...")

    # combine retrieved context + question → send to LLM
    context = "\n\n".join(retrieved)
    prompt  = GROUNDED_PROMPT.format(context=context, question=query)

    print("\nGENERATED ANSWER (LLM with grounding instruction):")
    answer = generate(prompt)
    print(f"  {answer.strip()}\n")
