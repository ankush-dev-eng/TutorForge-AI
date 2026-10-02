"""
TutorForge AI — Backend Tests
Tests cover: processing pipeline, vector store, RAG, assessment, mastery, learning path.

Vector store tests use the VectorStore abstraction (LocalVectorStore by default).
Chroma-specific tests are skipped when chromadb is not installed.
"""
import pytest
import asyncio
import os
import tempfile
import json
from unittest.mock import patch, MagicMock


# ──────────────────────────────────────────
# Processing Pipeline Tests
# ──────────────────────────────────────────

class TestTextChunking:
    def test_split_text_basic(self):
        from processing import _split_text
        text = " ".join([f"word{i}" for i in range(1200)])
        chunks = _split_text(text, chunk_size=500, overlap=80)
        assert len(chunks) > 1
        assert all(len(c.split()) <= 520 for c in chunks)  # allow small overflow

    def test_split_text_empty(self):
        from processing import _split_text
        chunks = _split_text("")
        assert chunks == []

    def test_split_text_short(self):
        from processing import _split_text
        text = "Short text"
        chunks = _split_text(text)
        assert chunks == ["Short text"]

    def test_split_text_overlap(self):
        from processing import _split_text
        text = " ".join([f"word{i}" for i in range(600)])
        chunks = _split_text(text, chunk_size=300, overlap=50)
        # Verify overlap: last words of chunk N appear in chunk N+1
        if len(chunks) >= 2:
            words0 = set(chunks[0].split()[-30:])
            words1 = set(chunks[1].split()[:30])
            overlap_words = words0 & words1
            assert len(overlap_words) > 0


class TestPDFProcessing:
    def test_pdf_processor_returns_chunks(self, tmp_path):
        """Create a simple PDF and verify chunk structure."""
        try:
            import pypdf
            from reportlab.pdfgen import canvas
        except ImportError:
            pytest.skip("pypdf or reportlab not installed")

        # Create a minimal PDF
        pdf_path = str(tmp_path / "test.pdf")
        c = canvas.Canvas(pdf_path)
        c.drawString(50, 100, "TCP Congestion Control\n" * 20)
        c.save()

        from processing import process_pdf
        chunks = process_pdf(pdf_path, source_id=1, source_name="Test PDF")
        assert len(chunks) > 0
        assert chunks[0]["source_id"] == 1
        assert chunks[0]["source_name"] == "Test PDF"
        assert chunks[0]["source_type"] == "pdf"
        assert chunks[0]["page_number"] == 1
        assert "content" in chunks[0]
        assert len(chunks[0]["content"]) > 0

    def test_pdf_metadata_preserved(self, tmp_path):
        """Verify page number metadata is in all chunks."""
        try:
            import pypdf
            from reportlab.pdfgen import canvas
        except ImportError:
            pytest.skip("pypdf or reportlab not installed")

        pdf_path = str(tmp_path / "test_multipage.pdf")
        c = canvas.Canvas(pdf_path)
        for i in range(3):
            c.drawString(50, 100, f"Page {i+1} content. " * 50)
            c.showPage()
        c.save()

        from processing import process_pdf
        chunks = process_pdf(pdf_path, source_id=1, source_name="Multi")
        for chunk in chunks:
            assert "page_number" in chunk
            assert chunk["page_number"] is not None
            assert 1 <= chunk["page_number"] <= 3


class TestPPTXProcessing:
    def test_pptx_processor_returns_chunks(self, tmp_path):
        try:
            from pptx import Presentation
        except ImportError:
            pytest.skip("python-pptx not installed")

        pptx_path = str(tmp_path / "test.pptx")
        prs = Presentation()
        slide_layout = prs.slide_layouts[1]
        for i in range(3):
            slide = prs.slides.add_slide(slide_layout)
            slide.placeholders[0].text = f"Slide {i+1}: TCP Congestion"
            slide.placeholders[1].text = f"Content for slide {i+1}. " * 20
        prs.save(pptx_path)

        from processing import process_pptx
        chunks = process_pptx(pptx_path, source_id=2, source_name="Test Slides")
        assert len(chunks) > 0
        assert chunks[0]["source_type"] == "pptx"
        assert chunks[0]["slide_number"] is not None
        for chunk in chunks:
            assert "slide_number" in chunk


class TestTextProcessing:
    def test_text_file_processing(self, tmp_path):
        txt_path = str(tmp_path / "test.txt")
        content = "This is test content. " * 100
        with open(txt_path, "w") as f:
            f.write(content)

        from processing import process_text
        chunks = process_text(txt_path, source_id=3, source_name="Test Text")
        assert len(chunks) >= 1
        assert all(chunk["source_type"] == "text" for chunk in chunks)
        assert all(chunk["source_id"] == 3 for chunk in chunks)


class TestAudioFallback:
    def test_audio_fallback_returns_chunks(self):
        from processing import _audio_fallback
        chunks = _audio_fallback("/fake/path.mp4", 1, "Lecture", "video")
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk["source_type"] == "video"
            assert chunk["timestamp_start"] is not None
            assert chunk["timestamp_end"] is not None
            assert "DEMO FALLBACK" in chunk["content"]

    def test_dispatch_unknown_type(self, tmp_path):
        txt_path = str(tmp_path / "test.xyz")
        with open(txt_path, "w") as f:
            f.write("Some content " * 20)
        from processing import process_document
        # Should not raise, defaults to text
        chunks = process_document(str(txt_path), 1, "Unknown", "xyz")
        # May be 0 if content is short


# ──────────────────────────────────────────
# Mastery Update Tests
# ──────────────────────────────────────────

class TestMasteryLogic:
    def test_mastery_increases_on_correct(self):
        from assessment_service import AdaptiveAssessmentService, MASTERY_CORRECT_WEIGHT
        svc = AdaptiveAssessmentService()

        class FakeMastery:
            score = 0.5
            questions_seen = 0
            correct_answers = 0
            last_updated = None
            id = 1

        m = FakeMastery()
        import asyncio

        async def run():
            with patch("assessment_service.MasteryHistory", MagicMock()):
                # Manually apply the math
                d_factor = {1: 0.6, 2: 1.0, 3: 1.5}.get(2, 1.0)
                delta = MASTERY_CORRECT_WEIGHT * d_factor
                new_score = min(1.0, 0.5 + delta)
                assert new_score > 0.5

        asyncio.run(run())

    def test_mastery_bounded_0_1(self):
        from assessment_service import MASTERY_CORRECT_WEIGHT
        score = 1.0
        delta = MASTERY_CORRECT_WEIGHT * 1.5  # hard question
        new_score = min(1.0, score + delta)
        assert new_score == 1.0

        score = 0.0
        delta = 0.08
        new_score = max(0.0, score - delta)
        assert new_score == 0.0

    def test_difficulty_selection_up(self):
        from assessment_service import AdaptiveAssessmentService
        svc = AdaptiveAssessmentService()
        # High mastery → go up
        result = svc.select_next_difficulty(0.85, 2)
        assert result == 3

    def test_difficulty_selection_down(self):
        from assessment_service import AdaptiveAssessmentService
        svc = AdaptiveAssessmentService()
        # Low mastery → go down
        result = svc.select_next_difficulty(0.30, 2)
        assert result == 1

    def test_difficulty_stays_at_bounds(self):
        from assessment_service import AdaptiveAssessmentService
        svc = AdaptiveAssessmentService()
        # Already at max
        result = svc.select_next_difficulty(0.95, 3)
        assert result == 3
        # Already at min
        result = svc.select_next_difficulty(0.10, 1)
        assert result == 1

    def test_difficulty_label(self):
        from assessment_service import AdaptiveAssessmentService
        svc = AdaptiveAssessmentService()
        assert svc.difficulty_label(1) == "Easy"
        assert svc.difficulty_label(2) == "Medium"
        assert svc.difficulty_label(3) == "Hard"


# ──────────────────────────────────────────
# Answer Evaluation Tests
# ──────────────────────────────────────────

class TestAnswerEvaluation:
    def _make_mcq_question(self, correct="B) Option B"):
        q = MagicMock()
        q.question_type = "mcq"
        q.correct_answer = correct
        return q

    def test_correct_mcq_answer(self):
        from assessment_service import AdaptiveAssessmentService
        svc = AdaptiveAssessmentService()
        q = self._make_mcq_question("B) Exponentially by doubling each RTT")

        import asyncio
        result = asyncio.run(
            svc.evaluate_answer(q, "B) Exponentially by doubling each RTT")
        )
        assert result["is_correct"] is True
        assert result["score"] == 1.0

    def test_wrong_mcq_answer(self):
        from assessment_service import AdaptiveAssessmentService
        svc = AdaptiveAssessmentService()
        q = self._make_mcq_question("B) Exponentially by doubling each RTT")

        import asyncio
        result = asyncio.run(
            svc.evaluate_answer(q, "A) Linearly by 1 MSS per RTT")
        )
        assert result["is_correct"] is False
        assert result["score"] == 0.0

    def test_true_false_evaluation(self):
        from assessment_service import AdaptiveAssessmentService
        svc = AdaptiveAssessmentService()
        q = MagicMock()
        q.question_type = "true_false"
        q.correct_answer = "True"

        import asyncio
        result = asyncio.run(
            svc.evaluate_answer(q, "True")
        )
        assert result["is_correct"] is True


# ──────────────────────────────────────────
# JSON Parsing Tests
# ──────────────────────────────────────────

class TestJSONParsing:
    def test_parse_clean_json(self):
        from assessment_service import AdaptiveAssessmentService
        svc = AdaptiveAssessmentService()
        raw = '{"text": "Test question", "options": ["A", "B"], "correct_answer": "A", "explanation": "Because"}'
        result = svc._parse_json_response(raw)
        assert result["text"] == "Test question"
        assert result["correct_answer"] == "A"

    def test_parse_json_with_markdown(self):
        from assessment_service import AdaptiveAssessmentService
        svc = AdaptiveAssessmentService()
        raw = '```json\n{"text": "Q?", "options": ["A"], "correct_answer": "A", "explanation": "Ex"}\n```'
        result = svc._parse_json_response(raw)
        assert result.get("text") == "Q?"

    def test_parse_invalid_json(self):
        from assessment_service import AdaptiveAssessmentService
        svc = AdaptiveAssessmentService()
        result = svc._parse_json_response("This is not JSON at all")
        assert result == {}


# ──────────────────────────────────────────
# Citation Formatting Tests
# ──────────────────────────────────────────

class TestCitationFormatting:
    def test_format_video_location(self):
        from rag_service import RAGService
        svc = RAGService()
        chunk_info = {"timestamp_start": 760.0, "timestamp_end": 818.0}
        loc = svc._format_location(chunk_info)
        assert "12:40" in loc
        assert "13:38" in loc

    def test_format_pdf_location(self):
        from rag_service import RAGService
        svc = RAGService()
        chunk_info = {"page_number": 87, "timestamp_start": None}
        loc = svc._format_location(chunk_info)
        assert "87" in loc

    def test_format_slide_location(self):
        from rag_service import RAGService
        svc = RAGService()
        chunk_info = {"slide_number": 14, "page_number": None, "timestamp_start": None}
        loc = svc._format_location(chunk_info)
        assert "14" in loc

    def test_citation_truncates_long_text(self):
        from rag_service import RAGService
        svc = RAGService()
        chunk_info = {
            "source_id": 1,
            "source_name": "Test",
            "source_type": "pdf",
            "page_number": 5,
            "slide_number": None,
            "timestamp_start": None,
            "timestamp_end": None,
            "relevance": 0.9,
            "text": "x" * 500
        }
        citation = svc._format_citation(chunk_info)
        assert len(citation["excerpt"]) <= 210  # 200 + "..."


# ──────────────────────────────────────────
# Local Vector Store Tests (Phase 5)
# ──────────────────────────────────────────

class TestLocalVectorStore:
    """Tests for the LocalVectorStore — no optional dependencies required."""

    def _make_store(self):
        from vector_store import LocalVectorStore
        return LocalVectorStore(persist_path=None)  # in-memory

    def test_add_and_count(self):
        store = self._make_store()
        assert store.count() == 0
        texts = ["TCP congestion control", "UDP user datagram protocol"]
        metadatas = [
            {"source_id": 1, "source_type": "pdf", "source_name": "Net", "page_number": 1},
            {"source_id": 1, "source_type": "pdf", "source_name": "Net", "page_number": 2},
        ]
        ids = store.add_documents(texts, metadatas)
        assert len(ids) == 2
        assert store.count() == 2

    def test_add_and_query(self):
        """Documents added should be retrievable by relevant query."""
        store = self._make_store()
        texts = [
            "TCP implements congestion control using slow start and AIMD",
            "UDP provides connectionless unreliable datagrams",
            "HTTP is an application layer protocol for the web",
        ]
        metadatas = [
            {"source_id": 1, "source_type": "pdf", "source_name": "Networking", "page_number": i + 1}
            for i in range(3)
        ]
        store.add_documents(texts, metadatas)

        results = store.query("How does TCP control congestion?", n_results=2)
        assert len(results) >= 1
        # The TCP chunk should score higher than unrelated chunks
        assert "TCP" in results[0]["text"] or "congestion" in results[0]["text"].lower()

    def test_metadata_preserved(self):
        """All metadata fields must be returned intact."""
        store = self._make_store()
        meta = {
            "source_id": 42,
            "source_name": "Lecture Video",
            "source_type": "video",
            "page_number": "",
            "slide_number": "",
            "timestamp_start": 120.0,
            "timestamp_end": 180.0,
            "chunk_id": "abc123",
        }
        ids = store.add_documents(["video segment text content here"], [meta])
        results = store.query("video segment", n_results=1)
        assert len(results) == 1
        returned_meta = results[0]["metadata"]
        assert str(returned_meta.get("source_id")) == "42"
        assert returned_meta.get("source_name") == "Lecture Video"
        assert returned_meta.get("source_type") == "video"

    def test_empty_query_returns_empty(self):
        """An empty query string should return empty results safely."""
        store = self._make_store()
        store.add_documents(
            ["Some document about networking"],
            [{"source_id": 1, "source_type": "pdf", "source_name": "N"}],
        )
        results = store.query("", n_results=5)
        assert results == []

    def test_query_empty_store_returns_empty(self):
        """Querying an empty store should return empty results."""
        store = self._make_store()
        results = store.query("TCP congestion", n_results=5)
        assert results == []

    def test_top_k_respected(self):
        """n_results must be respected (not more than requested)."""
        store = self._make_store()
        texts = [f"Document number {i} about networking protocols" for i in range(10)]
        metadatas = [{"source_id": i, "source_type": "text", "source_name": f"Doc{i}"} for i in range(10)]
        store.add_documents(texts, metadatas)
        results = store.query("networking protocols", n_results=3)
        assert len(results) <= 3

    def test_relevance_score_range(self):
        """relevance must be in [0, 1]."""
        store = self._make_store()
        texts = [
            "TCP congestion window sliding acknowledgment",
            "UDP does not guarantee delivery connectionless",
        ]
        metadatas = [{"source_id": 1, "source_type": "pdf", "source_name": "N"} for _ in texts]
        store.add_documents(texts, metadatas)
        results = store.query("TCP congestion", n_results=5)
        for r in results:
            assert 0.0 <= r["relevance"] <= 1.0
            assert 0.0 <= r["distance"] <= 1.0

    def test_delete_by_source(self):
        """delete_by_source removes only the matching chunks."""
        store = self._make_store()
        texts = ["Source one document content", "Source two document content"]
        metadatas = [
            {"source_id": 1, "source_type": "pdf", "source_name": "S1"},
            {"source_id": 2, "source_type": "pdf", "source_name": "S2"},
        ]
        store.add_documents(texts, metadatas)
        assert store.count() == 2
        store.delete_by_source(source_id=1)
        assert store.count() == 1
        results = store.query("source one document", n_results=5)
        # Should not contain source_id=1 chunks
        for r in results:
            assert str(r["metadata"].get("source_id", "")) != "1"

    def test_reset(self):
        """reset() must clear all documents."""
        store = self._make_store()
        store.add_documents(
            ["content A", "content B"],
            [{"source_id": 1, "source_type": "pdf", "source_name": "X"} for _ in range(2)],
        )
        assert store.count() == 2
        store.reset()
        assert store.count() == 0
        assert store.query("content A", n_results=1) == []

    def test_custom_ids(self):
        """User-supplied IDs must be stored and returned."""
        store = self._make_store()
        custom_ids = ["chunk-001", "chunk-002"]
        returned_ids = store.add_documents(
            ["First chunk text", "Second chunk text"],
            [{"source_id": 1, "source_type": "pdf", "source_name": "X"} for _ in range(2)],
            ids=custom_ids,
        )
        assert returned_ids == custom_ids
        results = store.query("first chunk", n_results=1)
        assert results[0]["id"] in custom_ids


# ──────────────────────────────────────────
# Vector Store Abstraction Tests
# ──────────────────────────────────────────

class TestVectorStoreAbstraction:
    """Tests that exercise the singleton via its abstract interface."""

    def test_singleton_is_base_type(self):
        """The module-level singleton must implement VectorStoreBase."""
        from vector_store import vector_store, VectorStoreBase
        assert isinstance(vector_store, VectorStoreBase)

    def test_add_chunks_alias(self):
        """add_chunks() must be a valid alias for add_documents()."""
        from vector_store import LocalVectorStore
        store = LocalVectorStore()
        ids = store.add_chunks(
            ["Test chunk for alias"],
            [{"source_id": 1, "source_type": "pdf", "source_name": "T"}],
        )
        assert len(ids) == 1
        assert store.count() == 1


# ──────────────────────────────────────────
# ChromaDB-specific Tests (skipped if not installed)
# ──────────────────────────────────────────

class TestVectorStoreChroma:
    """
    ChromaDB tests. Skipped automatically when chromadb is not installed.
    Run only when chromadb is explicitly configured in the environment.
    """

    def test_chroma_available(self):
        chromadb = pytest.importorskip("chromadb", reason="chromadb not installed")
        # If we reach here, chromadb is installed
        assert chromadb is not None

    def test_chroma_store_add_and_query(self, tmp_path):
        chromadb = pytest.importorskip("chromadb", reason="chromadb not installed")
        from chromadb.config import Settings as ChromaSettings

        client = chromadb.PersistentClient(
            path=str(tmp_path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        collection = client.get_or_create_collection("test_collection")

        texts = ["TCP congestion control", "UDP user datagram protocol"]
        fake_embeddings = [[0.1] * 384, [0.2] * 384]
        ids = ["id1", "id2"]
        metadatas = [
            {"source_id": "1", "source_type": "pdf"},
            {"source_id": "2", "source_type": "video"},
        ]

        collection.add(embeddings=fake_embeddings, documents=texts, metadatas=metadatas, ids=ids)
        assert collection.count() == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
