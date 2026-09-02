import os

os.environ.setdefault("LLM_MODE", "stub")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://steh:steh@localhost:5433/steh",
)
os.environ.setdefault(
    "LANGGRAPH_DATABASE_URL",
    "postgresql://steh:steh@localhost:5433/steh?sslmode=disable",
)
os.environ.setdefault(
    "POLICY_FILE",
    "policies/quality-gates.yaml",
)