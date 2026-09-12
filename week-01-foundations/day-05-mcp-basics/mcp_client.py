"""
Day 5 lab — MCP Client side.
Connects to mcp_server.py over stdio, discovers its tools,
then calls each one — showing exactly what the MCP protocol
does under the hood that LangChain/Claude Desktop abstract away.
"""

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


SERVER = StdioServerParameters(
    command="python",
    args=["mcp_server.py"],   # spins up the server as a subprocess
)


async def main():

    async with stdio_client(SERVER) as (read, write):
        async with ClientSession(read, write) as session:

            await session.initialize()

            # ── Step 1: Tool discovery ─────────────────────────────────────────
            # This is what an AI host (Claude Desktop, Claude Code) does on
            # startup — it asks the MCP server "what tools do you have?"
            print("=" * 60)
            print("STEP 1 — Tool discovery (list_tools)")
            print("=" * 60)

            tools_response = await session.list_tools()
            tools = tools_response.tools

            print(f"Server exposed {len(tools)} tool(s):\n")
            for t in tools:
                print(f"  Tool: {t.name}")
                print(f"  Desc: {t.description}")
                print(f"  Schema: {t.input_schema}")
                print()

            # ── Step 2: Call real tools ────────────────────────────────────────
            print("=" * 60)
            print("STEP 2 — Calling real tools")
            print("=" * 60)

            result = await session.call_tool("calculate", {"expression": "62400 * 83.5"})
            print(f"calculate('62400 * 83.5')  →  {result.content[0].text}")

            result = await session.call_tool("get_weather", {"city": "Mumbai"})
            print(f"get_weather('Mumbai')       →  {result.content[0].text}")

            # ── Step 3: Tool poisoning demo ────────────────────────────────────
            # The LLM reads the description of safe_backup — it sounds safe.
            # It calls it thinking it's protecting files.
            # Watch what actually runs.
            print()
            print("=" * 60)
            print("STEP 3 — Tool poisoning demo (safe_backup)")
            print("=" * 60)
            print("What the LLM reads as the tool description:")
            safe_backup_tool = next(t for t in tools if t.name == "safe_backup")
            print(f"  '{safe_backup_tool.description.strip()}'")
            print()
            print("What actually executes when the LLM calls it:")

            result = await session.call_tool("safe_backup", {"folder_path": "/home/ansh/documents"})
            print(f"  {result.content[0].text}")

            print()
            print("=" * 60)
            print("KEY INSIGHT")
            print("=" * 60)
            print("The LLM only ever sees tool DESCRIPTIONS — never the source code.")
            print("A compromised or malicious MCP server can describe any function")
            print("as safe. The LLM has no way to verify what the code actually does.")
            print("This is the tool poisoning / rug-pull attack (Week 9 deep dive).")


asyncio.run(main())
