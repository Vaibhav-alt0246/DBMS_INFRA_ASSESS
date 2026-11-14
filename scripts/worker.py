"""Single scheduled worker for alerts and vector synchronization (server Qdrant in production)."""
import logging
import os
import time
from backend.app.db import connection
from vector_db.config import Settings
from vector_db.embeddings import SentenceTransformerProvider
from vector_db.indexer import index_incidents
from vector_db.qdrant_store import IncidentStore


def main():
    logging.basicConfig(level=logging.INFO)
    settings = Settings.from_env()
    provider = None
    while True:
        try:
            with connection() as conn:
                conn.execute('SELECT fn_refresh_alerts()')
        except Exception:
            logging.exception('Alert reconciliation failed; retrying next interval')
        try:
            provider = provider or SentenceTransformerProvider(settings.model_name)
            store = IncidentStore(settings.qdrant_path, settings.collection, provider.dimension)
            try:
                with connection() as conn:
                    logging.info('Index sync: %s', index_incidents(conn, store, provider))
            finally:
                store.close()
        except Exception:
            logging.exception('Vector sync failed; retrying next interval')
        time.sleep(max(10, int(os.getenv('SYNC_INTERVAL_SECONDS', '60'))))

if __name__ == '__main__': main()
