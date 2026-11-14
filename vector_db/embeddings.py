from typing import Protocol, Sequence

class EmbeddingProvider(Protocol):
    @property
    def dimension(self) -> int: ...
    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...

class SentenceTransformerProvider:
    def __init__(self, model_name):
        from sentence_transformers import SentenceTransformer
        import os
        self.model_name = model_name
        self.model = SentenceTransformer(model_name, local_files_only=os.getenv('EMBEDDING_OFFLINE', '0') == '1')
        self._dimension = int(self.model.get_sentence_embedding_dimension())
    @property
    def dimension(self): return self._dimension
    def embed(self, texts):
        values = list(texts)
        if not values:
            return []
        return self.model.encode(values, normalize_embeddings=True, convert_to_numpy=True).tolist()
