from __future__ import annotations

from fastembed import TextEmbedding


class SchemaEmbedder:
    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model = TextEmbedding(model_name=model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings_generator = self._model.embed(texts)
        return [embedding.tolist() for embedding in embeddings_generator]

    def embed_single(self, text: str) -> list[float]:
        return self.embed([text])[0]

    @property
    def model_name(self) -> str:
        return self._model_name
