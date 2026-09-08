"""
Day 2 lab: get real embeddings from a local Ollama model and compute
cosine similarity by hand (no sklearn, no LangChain) to see for real
that similar-meaning sentences score high and unrelated ones score low.
"""

import json
import urllib.request
import numpy as np

OLLAMA_URL = "http://localhost:11434/api/embeddings"
MODEL = "nomic-embed-text"

sentences = [
    "I love dogs",
    "I adore puppies",
    "The stock market crashed today",
    "Financial markets took a huge hit",
    "I like sunny weather",
    "The weather today is bright and sunny",
]


def get_embedding(text: str) -> np.ndarray:
    payload = json.dumps({"model": MODEL, "prompt": text}).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    return np.array(result["embedding"])


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    # the actual formula: dot product of the two vectors, divided by
    # the product of their magnitudes (lengths) -- this is what
    # "angle between two vectors" means in practice.
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


print("Fetching embeddings from Ollama...\n")
embeddings = [get_embedding(s) for s in sentences]
print(f"Embedding dimension: {len(embeddings[0])}\n")

print("Sentences:")
for i, s in enumerate(sentences):
    print(f"  [{i}] {s}")

print("\nCosine similarity matrix (1.0 = identical direction/meaning, 0 = unrelated):\n")
header = "".join(f"{i:>8}" for i in range(len(sentences)))
print(f"{'':6}{header}")
for i in range(len(sentences)):
    row = "".join(
        f"{cosine_similarity(embeddings[i], embeddings[j]):>8.3f}"
        for j in range(len(sentences))
    )
    print(f"[{i}]   {row}")
