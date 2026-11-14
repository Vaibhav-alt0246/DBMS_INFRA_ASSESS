"""Per-user bearer credentials. Store SHA-256 token digests, never plaintext tokens."""
import hashlib
import hmac
import json
import logging
import os
import time
from collections import OrderedDict
from contextvars import ContextVar
from threading import Lock
from fastapi import Request
from fastapi.responses import JSONResponse

actor = ContextVar('actor', default='system')
log = logging.getLogger('infraassess.access')
log.setLevel(logging.INFO)
if not log.handlers:
    log.addHandler(logging.StreamHandler())
log.propagate = False
_buckets = OrderedDict()
_lock = Lock()

async def authorize(request: Request, call_next):
    if request.url.path in ('/api/health', '/api/live', '/api/ready') or request.method == 'OPTIONS':
        return await call_next(request)
    try:
        credentials = json.loads(os.getenv('INFRAASSESS_CREDENTIALS', '{}'))
    except (ValueError, TypeError):
        return JSONResponse(status_code=503, content={'detail': 'Authentication configuration invalid.'})
    authorization = request.headers.get('Authorization', '')
    if not isinstance(credentials, dict) or any(not isinstance(u, dict) for u in credentials.values()):
        return JSONResponse(status_code=503, content={'detail': 'Authentication configuration invalid.'})
    token = authorization[7:] if authorization.startswith('Bearer ') else ''
    digest = hashlib.sha256(token.encode()).hexdigest()
    identity = next((u for hashed, u in credentials.items() if hmac.compare_digest(hashed, digest)), None)
    if not identity or not token:
        return JSONResponse(status_code=401, content={'detail': 'A valid bearer token is required.'}, headers={'WWW-Authenticate': 'Bearer'})
    role = identity.get('role')
    user = identity.get('name', '')
    if role not in ('viewer', 'operator', 'admin') or not user or len(user) > 120:
        return JSONResponse(status_code=403, content={'detail': 'Invalid account permissions.'})
    path = request.url.path
    if (request.method not in ('GET', 'HEAD') and role == 'viewer') or (request.method == 'DELETE' and role != 'admin') or (path.startswith('/api/audit-logs') and role != 'admin') or (path.startswith('/api/sensor-thresholds') and request.method != 'GET' and role != 'admin'):
        return JSONResponse(status_code=403, content={'detail': 'Your role does not permit this operation.'})
    now = time.monotonic()
    with _lock:
        start, count = _buckets.get(digest, (now, 0))
        if now - start >= 60: start, count = now, 0
        _buckets[digest] = (start, count + 1)
        _buckets.move_to_end(digest)
        while len(_buckets) > 10000: _buckets.popitem(last=False)
    if count >= int(os.getenv('API_REQUESTS_PER_MINUTE', '300')):
        return JSONResponse(status_code=429, content={'detail': 'Request limit exceeded.'}, headers={'Retry-After': '60'})
    context = actor.set(user)
    try:
        response = await call_next(request)
        log.info('actor=%s method=%s path=%s status=%s', user, request.method, path, response.status_code)
        return response
    finally:
        actor.reset(context)
