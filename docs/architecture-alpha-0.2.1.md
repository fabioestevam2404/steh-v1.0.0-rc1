# Alpha 0.2.1 Architecture

```text
FastAPI
  |
Task Service
  |
  +--> Structured Logs
  |
  +--> Audit Events
  |
  v
LangGraph StateGraph
  |
  +--> PostgresSaver
  |
  +--> Requirements Agent
  |      |
  |      +--> Policy Engine
  |
  +--> Architecture Agent
         |
         +--> Policy Engine

PostgreSQL
  |
  +--> Application schema
  |     tasks
  |     agent_runs
  |     audit_events
  |
  +--> LangGraph checkpoint schema
```
