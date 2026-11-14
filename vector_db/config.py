from dataclasses import dataclass
import os
import hashlib
from pathlib import Path
from dotenv import load_dotenv
from psycopg.conninfo import conninfo_to_dict

@dataclass(frozen=True)
class Settings:
    database_url: str | None
    qdrant_path: Path
    collection: str = "infra_incidents"
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    dimension: int = 384
    qdrant_url: str | None = None

    @classmethod
    def from_env(cls):
        project_root = Path(__file__).resolve().parents[1]
        load_dotenv(project_root / '.env', override=False)
        configured_path = Path(os.getenv("QDRANT_PATH", "data/qdrant_storage"))
        qdrant_path = configured_path if configured_path.is_absolute() else project_root / configured_path
        return cls(os.getenv("DATABASE_URL"), qdrant_path,
                   collection=os.getenv('QDRANT_COLLECTION', 'infra_incidents') + '_' + hashlib.sha256(os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2').encode()).hexdigest()[:12],
                   model_name=os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2'),
                   dimension=int(os.getenv('EMBEDDING_DIMENSION', '384')),
                   qdrant_url=os.getenv('QDRANT_URL'))

    def psycopg_kwargs(self):
        if self.database_url:
            result = conninfo_to_dict(self.database_url)
        else:
            env = {"host":"PGHOST", "port":"PGPORT", "dbname":"PGDATABASE", "user":"PGUSER", "password":"PGPASSWORD"}
            result = {key: os.environ[name] for key, name in env.items() if os.environ.get(name)}
            result.setdefault("dbname", "infraassess_test")
        result.setdefault('connect_timeout', os.getenv('PGCONNECT_TIMEOUT') or '5')
        return result
