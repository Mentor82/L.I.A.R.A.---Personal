"""
Unit tests for EmbeddingService
===============================
Backend selection, the LiNeP EMBED path (fake trunk connection, no network)
and cosine_similarity's handling of vectors from different models.
"""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from linep.v0_2.constants import EventType, RuntimeProfile

from services.embedding_service import (
    BACKEND_LINEP,
    EmbeddingError,
    EmbeddingService,
)


def _event(event_type, embedding=None, error=None):
    return SimpleNamespace(event_type=event_type, embedding=embedding, error=error)


def _embedding(model_id, vector):
    return SimpleNamespace(space=SimpleNamespace(model_id=model_id, dimensions=len(vector)), vector=vector)


class FakeTrunk:
    """Answers every EMBED request with the next scripted event list."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []
        self.closed = False

    def execute_stream(self, request):
        self.requests.append(request)
        yield from self.replies.pop(0)

    def close(self):
        self.closed = True


def _ok(model_id, vector):
    return [_event(EventType.EMBEDDING_RESULT, _embedding(model_id, vector)), _event(EventType.COMPLETED)]


def _linep_service():
    return EmbeddingService(model_name="bge-m3", dimension=4, version=2, backend=BACKEND_LINEP)


class TestEmbeddingServiceLinep(unittest.TestCase):

    def test_single_embedding_sends_embed_request(self):
        service = _linep_service()
        trunk = FakeTrunk([_ok("bge-m3", [0.5, 0.5, 0.5, 0.5])])
        with patch.object(service, "_connect_linep", return_value=trunk):
            vector = service.generate_embedding("Backup-Strategie")
        self.assertEqual(vector, [0.5, 0.5, 0.5, 0.5])
        self.assertEqual(trunk.requests[0].profile, RuntimeProfile.EMBED)
        self.assertEqual(trunk.requests[0].model_id, "task:embed-bge")
        self.assertEqual(trunk.requests[0].payload, "Backup-Strategie")
        self.assertTrue(trunk.closed)

    def test_batch_uses_one_connection(self):
        service = _linep_service()
        trunk = FakeTrunk([_ok("bge-m3", [1.0, 0, 0, 0]), _ok("bge-m3", [0, 1.0, 0, 0])])
        with patch.object(service, "_connect_linep", return_value=trunk) as connect:
            vectors = service.generate_embeddings_batch(["a", "b"])
        self.assertEqual(connect.call_count, 1)
        self.assertEqual(vectors, [[1.0, 0, 0, 0], [0, 1.0, 0, 0]])
        ids = {r.stream.request_id for r in trunk.requests}
        self.assertEqual(len(ids), 2)

    def test_other_model_is_rejected(self):
        service = _linep_service()
        trunk = FakeTrunk([_ok("nomic-embed-text", [0.5, 0.5, 0.5, 0.5])])
        with patch.object(service, "_connect_linep", return_value=trunk):
            with self.assertRaisesRegex(EmbeddingError, "nomic-embed-text"):
                service.generate_embedding("x")

    def test_wrong_dimension_is_rejected(self):
        service = _linep_service()
        trunk = FakeTrunk([_ok("bge-m3", [0.5] * 3)])
        with patch.object(service, "_connect_linep", return_value=trunk):
            with self.assertRaisesRegex(EmbeddingError, "3 dims, expected 4"):
                service.generate_embedding("x")

    def test_runtime_failure_raises(self):
        service = _linep_service()
        failed = [_event(EventType.FAILED, error=SimpleNamespace(message="no runtime for task:embed-bge"))]
        trunk = FakeTrunk([failed])
        with patch.object(service, "_connect_linep", return_value=trunk):
            with self.assertRaisesRegex(EmbeddingError, "no runtime"):
                service.generate_embedding("x")
        self.assertTrue(trunk.closed)

    def test_stream_without_embedding_raises(self):
        service = _linep_service()
        trunk = FakeTrunk([[_event(EventType.COMPLETED)]])
        with patch.object(service, "_connect_linep", return_value=trunk):
            with self.assertRaisesRegex(EmbeddingError, "without an embedding"):
                service.generate_embedding("x")

    def test_transport_error_becomes_embedding_error(self):
        service = _linep_service()
        with patch.object(service, "_connect_linep", side_effect=ConnectionRefusedError("trunk down")):
            with self.assertRaisesRegex(EmbeddingError, "trunk down"):
                service.generate_embedding("x")

    def test_linep_backend_never_loads_a_local_model(self):
        with self.assertRaises(EmbeddingError):
            _linep_service().model

    def test_unknown_backend_is_refused(self):
        with self.assertRaises(ValueError):
            EmbeddingService(backend="ollama")


class TestCosineSimilarity(unittest.TestCase):

    def setUp(self):
        self.service = EmbeddingService()

    def test_identical_vectors(self):
        self.assertAlmostEqual(self.service.cosine_similarity([1.0, 2.0], [1.0, 2.0]), 1.0)

    def test_zero_vector_scores_zero(self):
        self.assertEqual(self.service.cosine_similarity([0.0, 0.0], [1.0, 2.0]), 0.0)

    def test_different_dimensions_raise(self):
        with self.assertRaisesRegex(ValueError, "dimensions differ"):
            self.service.cosine_similarity([0.1] * 384, [0.1] * 1024)


if __name__ == "__main__":
    unittest.main()
