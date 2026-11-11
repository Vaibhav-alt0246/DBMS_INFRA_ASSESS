from vector_db.embeddings import SentenceTransformerProvider


class FakeNumpyArray:
    def tolist(self):
        return [[0.6, 0.8], [1.0, 0.0]]


class FakeModel:
    def get_sentence_embedding_dimension(self):
        return 2

    def encode(self, texts, *, normalize_embeddings, convert_to_numpy):
        assert texts == ["first", "second"]
        assert normalize_embeddings is True
        assert convert_to_numpy is True
        return FakeNumpyArray()


def test_embed_converts_explicit_numpy_output_to_float_lists():
    provider = object.__new__(SentenceTransformerProvider)
    provider.model = FakeModel()
    provider._dimension = 2

    result = provider.embed((text for text in ("first", "second")))

    assert result == [[0.6, 0.8], [1.0, 0.0]]
    assert isinstance(result, list)
    assert all(isinstance(vector, list) for vector in result)
    assert all(isinstance(value, float) for vector in result for value in vector)


def test_embed_empty_input_returns_empty_list_without_model_call():
    provider = object.__new__(SentenceTransformerProvider)
    provider.model = None
    provider._dimension = 2

    assert provider.embed([]) == []
