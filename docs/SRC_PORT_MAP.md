# NYRA v13 source-port map

The supplied `src.zip` is a large TypeScript/TSX codebase, not a drop-in Python Telegram backend. NYRA uses its relevant architectural ideas rather than copying the whole tree.

| Supplied source concept | NYRA implementation |
|---|---|
| AgentTool / runAgent | `src/agent/agent.py`, bounded planner/executor |
| agentMemory / session memory | `src/memory/store.py`, active recall, SQLite |
| autoDream / consolidation | `src/agent/reflection.py`, scheduler |
| Task / tasks | `src/agent/goals.py`, `src/agent/planner.py` |
| tool orchestration | `src/tools/registry.py` |
| context / queued input | `src/agent/context.py` |
| image attachment handling | Telegram media metadata + ephemeral inspection |
| provider abstraction | `src/providers/` |

The goal is to preserve the useful cognitive architecture while keeping the runtime small enough for Pydroid3/Termux.
