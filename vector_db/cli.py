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
    args = parser.parse_args(argv); settings = Settings.from_env(); provider = SentenceTransformerProvider(settings.model_name)
    store = IncidentStore(settings.qdrant_path, settings.collection, provider.dimension)
    try:
        if args.command == 'status': store.ensure_collection(); print(f'collection={settings.collection} dimension={provider.dimension} points={store.count()}'); return
        with psycopg.connect(**settings.psycopg_kwargs()) as connection:
            if args.command == 'index':
                indexed, failures = index_incidents(connection, store, provider); print(f'indexed={indexed} failures={failures} points={store.count()}')
            else:
                for result in search_incidents(connection, store, provider, args.query, args.limit): print(result)
    finally: store.close()
if __name__ == '__main__': main()
