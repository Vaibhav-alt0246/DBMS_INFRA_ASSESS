from vector_db.config import Settings

settings = Settings.from_env()
FRONTEND_ORIGIN = __import__('os').getenv('FRONTEND_ORIGIN', 'http://localhost:3000')
