from .postgres import fetch_incidents_by_ids

def search_incidents(connection, store, embedder, query, limit):
    query = ' '.join(query.split())
    if not query: raise ValueError('query must not be empty')
    if limit < 1 or limit > 100: raise ValueError('limit must be between 1 and 100')
    hits = store.search(embedder.embed([query])[0], limit); ids = [int(hit.id) for hit in hits]
    rows = fetch_incidents_by_ids(connection, ids)
    return [{'score': float(hit.score), **rows[int(hit.id)]} for hit in hits if int(hit.id) in rows]
