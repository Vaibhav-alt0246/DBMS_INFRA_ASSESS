from dataclasses import dataclass
import os
from pathlib import Path

@dataclass(frozen=True)
class Settings:
    database_url: str | None
    qdrant_path: Path
    collection: str = "infra_incidents"
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"

    @classmethod
    def from_env(cls):
        project_root = Path(__file__).resolve().parents[1]
        configured_path = Path(os.getenv("QDRANT_PATH", "data/qdrant_storage"))
        qdrant_path = configured_path if configured_path.is_absolute() else project_root / configured_path
        return cls(os.getenv("DATABASE_URL"), qdrant_path)

    def psycopg_kwargs(self):
        if self.database_url: return {"conninfo": self.database_url}
        env = {"host":"PGHOST", "port":"PGPORT", "dbname":"PGDATABASE", "user":"PGUSER", "password":"PGPASSWORD"}
        result = {key: os.environ[name] for key, name in env.items() if os.environ.get(name)}
        result.setdefault("dbname", "infraassess_test")
        return result
