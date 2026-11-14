import argparse
import psycopg
from .config import Settings
from .embeddings import SentenceTransformerProvider
from .indexer import index_incidents
from .qdrant_store import IncidentStore
from .search import search_incidents

def main(argv=None):
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('index'); sub.add_parser('status')
    s = sub.add_parser('search'); s.add_argument('--query', required=True); s.add_argument('--limit', type=int, default=5)
    args = parser.parse_args(argv); settings = Settings.from_env()
    provider = None if args.command == 'status' else SentenceTransformerProvider(settings.model_name)
    dimension = settings.dimension if provider is None else provider.dimension
    store = IncidentStore(settings.qdrant_path, settings.collection, dimension)
    try:
        if args.command == 'status': store.ensure_collection(); print(f'collection={settings.collection} dimension={dimension} points={store.count()}'); return
        with psycopg.connect(**settings.psycopg_kwargs()) as connection:
            if args.command == 'index':
                stats = index_incidents(connection, store, provider); print(f'scanned={stats.scanned} embedded={stats.embedded} upserted={stats.upserted} removed={stats.removed} failures={stats.failures} points={store.count()}')
            else:
                for result in search_incidents(connection, store, provider, args.query, args.limit): print(result)
    finally: store.close()
if __name__ == '__main__': main()
