"""
Day 4 lab: ReAct agent loop.
LLM decides which tool to call → framework runs it → result fed back → LLM loops.
Plain Python + urllib (Ollama /api/chat with tools). No LangChain.

Tools:
  calculate  — real (Python eval, math only)
  get_weather — mock (fake data, no API key needed)
  search      — mock (fake data for a few known queries)
"""

import json
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2"
MAX_LOOPS = 10  # safety cap — infinite agent loops are a real DoS risk


# ── Tool implementations (the actual Python functions) ────────────────────────

def calculate(expression: str) -> str:
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Error: {e}"


def get_weather(city: str) -> str:
    # mock — real version calls a weather API
    data = {
        "mumbai":   "28°C, humid, partly cloudy",
        "delhi":    "35°C, sunny, air quality moderate",
        "london":   "14°C, overcast, light rain expected",
        "new york": "22°C, clear skies",
        "pune":     "26°C, pleasant, light breeze",
    }
    return data.get(city.lower(), f"No weather data for '{city}'")


def search(query: str) -> str:
    # mock — real version calls Google/Bing API
    results = {
        "bitcoin price":  "Bitcoin (BTC) is currently $62,400 USD.",
        "usd to inr":     "1 USD = 83.5 INR as of today.",
        "usd to pkr":     "1 USD = 278 PKR as of today.",
        "python inventor": "Python was created by Guido van Rossum, first released in 1991.",
        "who is elon musk": "Elon Musk is CEO of Tesla and SpaceX, owner of X (formerly Twitter).",
    }
    for key, value in results.items():
        if key in query.lower():
            return value
    return f"No results found for: {query}"


# ── Tool registry — what the LLM sees (descriptions, not code) ───────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate a mathematical expression. Use for any arithmetic or unit conversion math.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Math expression, e.g. '62400 * 83.5' or '15 / 100 * 84500'"
                    }
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name, e.g. 'Mumbai' or 'Delhi'"
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": "Search for real-time or factual information such as prices, exchange rates, or people.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query, e.g. 'Bitcoin price' or 'USD to INR'"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

TOOL_FUNCTIONS = {
    "calculate":   calculate,
    "get_weather": get_weather,
    "search":      search,
}


# ── Agent loop ────────────────────────────────────────────────────────────────

def call_ollama(messages: list) -> dict:
    payload = json.dumps({
        "model":   MODEL,
        "messages": messages,
        "tools":   TOOLS,
        "stream":  False
    }).encode()
    req = urllib.request.Request(
        OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def run_agent(user_query: str):
    print(f"\n{'='*60}")
    print(f"USER: {user_query}")
    print(f"{'='*60}")

    messages  = [{"role": "user", "content": user_query}]
    loop_num  = 0

    while loop_num < MAX_LOOPS:
        loop_num += 1
        response = call_ollama(messages)
        message  = response["message"]
        messages.append(message)

        tool_calls = message.get("tool_calls")

        if tool_calls:
            for tc in tool_calls:
                name = tc["function"]["name"]
                args = tc["function"]["arguments"]

                print(f"\n  [Loop {loop_num}] TOOL CALL  → {name}({args})")

                # framework executes the real function
                result = TOOL_FUNCTIONS[name](**args)

                print(f"  [Loop {loop_num}] OBSERVATION → {result}")

                # feed result back so LLM can continue reasoning
                messages.append({"role": "tool", "content": result})
        else:
            # LLM decided it has enough — prints final answer
            print(f"\nANSWER: {message['content']}")
            break

    if loop_num == MAX_LOOPS:
        print("[WARNING] Hit max loop limit — agent stopped.")

    print(f"\n  ({loop_num} loop(s) total)\n")


# ── Test queries ──────────────────────────────────────────────────────────────

# needs search + calculate (2 tool calls, 2 loops)
run_agent("What is the current price of Bitcoin in INR?")

# needs 2 weather calls (might run in 1 or 2 loops depending on model)
run_agent("What is the weather in Mumbai and Delhi right now?")

# pure math — should answer directly or use calculate (1 loop)
run_agent("What is 15% of 84500?")
