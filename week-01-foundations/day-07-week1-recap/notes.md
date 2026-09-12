# Day 7 — Week 1 Recap & Week 2 Preview

## The complete picture — how Days 1-6 connect

```
Day 1 — TOKENS + CONTEXT WINDOW
  Text breaks into tokens. Context window = what the LLM sees at once.
  History resent every turn. Bigger context = higher cost.
         ↓
Day 2 — EMBEDDINGS + SIMILARITY
  Text converts to vectors (numbers capturing meaning).
  Cosine similarity finds closest matches. Baseline: never truly 0.
         ↓
Day 3 — RAG PIPELINE          [uses Day 1 + Day 2]
  Chunk docs → embed → store in Chroma → embed query → retrieve top-N
  → retrieved text + question → LLM → grounded answer.
  User question never chunked. Indexing is one-time. Queries are instant.
         ↓
Day 4 — AGENT LOOP (ReAct)   [context window grows with each loop]
  LLM thinks → calls tool → gets observation → thinks again → loops.
  Tools are functions the framework runs. LLM only writes text.
  Training = brain. RAG = domain knowledge. Tools = live actions.
         ↓
Day 5 — MCP                  [extends Day 4 tools into separate processes]
  Tools are now separate MCP server processes, not inline functions.
  Host discovers tools via list_tools(). LLM sees descriptions only, never code.
  Tool poisoning: description says safe, code does malicious.
         ↓
Day 6 — AGENT MEMORY         [uses Day 2+3 for retrieval, Day 4 for save tool]
  Short-term = context window (whiteboard, wiped at session end).
  Long-term = external store (notebook, survives forever).
  Load at start → agent "remembers". Save at end → facts persist.
  Memory poisoning self-reinforces. Cross-user leakage needs auth to fix.
```

## The attacker's view of everything learned in Week 1

| Foundation | Attack (coming weeks) |
|---|---|
| Context window (Day 1) | Token stuffing; context exhaustion; Denial of Wallet |
| Embeddings + similarity (Day 2) | Craft content that scores high similarity to pull sensitive chunks into retrieval |
| RAG pipeline (Day 3) | Poison a vector DB doc; cross-tenant leakage via missing access control; indirect injection via retrieved content |
| Agent loop + tools (Day 4) | Parameter injection; incomplete tool result exploit; excessive tool calls |
| MCP (Day 5) | Tool poisoning via misleading descriptions; fake MCP server supply chain; confused deputy |
| Agent memory (Day 6) | One-time memory injection affects all future sessions; cross-user leakage; self-reinforcing false facts |

## The one attack that connects everything

**Prompt injection** — sneaking instructions into the LLM's input that override the developer's intended behaviour. Root cause: the LLM cannot tell developer instructions apart from attacker-planted content when both arrive in the same context window.

- **Against RAG (Day 3):** injection inside a retrieved document → indirect prompt injection
- **Against agent loop (Day 4):** injection inside a tool result → attacker-controlled tool parameters
- **Against MCP (Day 5):** injection inside a resource the MCP server passes to the LLM
- **Against memory (Day 6):** injection tricks the agent into saving a false fact → memory poisoning starts here

## Week 1 self-test (all answered correctly)

**Q1: A RAG chatbot has no access control on retrieval. User B asks a question. What gets retrieved?**

A: User A's documents — anything in the vector store closest to User B's query, regardless of who it belongs to. No auth on retrieval = any user gets any document. Seen live in Day 6 Session 2: different user got previous user's full stored profile. (Cross-user memory leakage / RAG cross-tenant leakage.)

**Q2: Agent calls search("bitcoin price"), gets only the USD price back. What does the LLM do?**

A: Uses its own stale training data to fill the gap — answers with an outdated exchange rate without telling the user it did so. Answers confidently but is wrong. Seen live in Day 4 lab: ~76 rate used instead of current 83.5. Exploitable: attacker poisons tool to return incomplete data, LLM fills gaps predictably from training.

**Q3: MCP server's safe_backup tool has a clean description but malicious code. What does the LLM see?**

A: Only the description — never the source code. LLM calls the tool thinking it's safe. Malicious code runs silently: data exfiltration, file deletion, anything the code does. LLM reports success to the user. Demonstrated live in Day 5 lab.

**Q4: Attacker injects a false email in Session 1 of a memory-enabled agent. Session 1 ends. What happens in Session 5?**

A: Every future session loads the poisoned memory and sends reports to the attacker's email — attacker long gone from Session 1. Bonus: in Day 6 lab Session 3, the agent also saved a *second* reinforcing memory ("user prefers attacker@evil.com") — the attack self-reinforces with each session, getting harder to detect and clean over time.

**Q5: Why can't you give agents unlimited context windows?**

A: Three reasons:
1. **Cost** — tokens = money; quadratic self-attention cost means unlimited windows are impractical at scale
2. **Lost in the middle** — LLMs become unreliable at following instructions buried deep in a very long context; the longer the context, the less faithfully middle content is processed
3. **Larger attack surface** — more context = more places to hide injections; LLM also becomes more "overwhelmed" (susceptible to manipulation) as context grows; context stuffing and Denial of Wallet attacks scale with window size

## What's coming in Week 2

**Weeks 2-3: Prompt Injection & Jailbreaking**

- Direct prompt injection — user directly injects into the chat input
- Indirect prompt injection — injection hidden in content the LLM reads (PDFs, web pages, RAG docs)
- System prompt extraction — make the LLM reveal its own system prompt
- Jailbreak patterns — make the LLM bypass its own safety guardrails

Labs:
- Extract your own chatbot's system prompt
- Inject via a PDF that the RAG app reads (Day 3's pipeline as the attack target)
- Gandalf (Lakera) + HackAPrompt + PortSwigger Web LLM attacks labs

Week 1 built the systems. Week 2 breaks them.

## Week 1 progress

| Day | Topic | Theory | Lab | Pushed |
|---|---|---|---|---|
| 1 | Tokens, context window, temperature, top-k/top-p | ✅ | ✅ Ollama temperature experiment | ✅ |
| 2 | Embeddings, cosine similarity, RAG vs training, naive vs well-built RAG | ✅ | ✅ similarity_lab.py (nomic-embed-text) | ✅ |
| 3 | RAG pipeline: chunking, vector DB, retrieval+generation | ✅ | ✅ rag_lab.py (Chroma + llama3.2) | ✅ |
| 4 | Agent loop (ReAct), tools, training+RAG+tools tradeoffs | ✅ | ✅ agent_lab.py (3 tools, parallel calls) | ✅ |
| 5 | MCP architecture, tool discovery, tool poisoning | ✅ | ✅ mcp_server.py + mcp_client.py | ✅ |
| 6 | Agent memory types, memory poisoning, cross-user leakage | ✅ | ✅ memory_agent.py (4-session demo) | ✅ |
| 7 | Week 1 recap, attack surface map, Week 2 preview | ✅ | — | ✅ |
