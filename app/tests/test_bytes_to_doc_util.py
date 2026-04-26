"""
Unit tests for app/utils/bytes_to_doc_util.py

Covers:
- DocumentChunk metadata with element_type / caption fields
- DataType.get_to_doc_func routing
- Document.to_markdown() — all element types + legacy PyMuPDF chunks
- Document.from_pdf() — regression using a minimal in-memory PDF
"""

import io
from typing import Dict
from unittest.mock import MagicMock, patch

import fitz
import pytest

from app.utils.bytes_to_doc_util import (
    DataType,
    Document,
    DocumentChunk,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_minimal_pdf(text: str = "Hello world") -> bytes:
    """Create a minimal single-page PDF in memory."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 100), text)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def _text_chunk(text: str, element_type=None, page_num=1) -> DocumentChunk:
    meta = {"page_num": [page_num]}
    if element_type is not None:
        meta["element_type"] = element_type
    return DocumentChunk(data_type=DataType.TEXT, content=text.encode(), metadata=meta)


def _image_chunk(caption=None, page_num=1) -> DocumentChunk:
    meta = {"page_num": [page_num], "element_type": "IMAGE"}
    if caption:
        meta["caption"] = caption
    return DocumentChunk(data_type=DataType.PNG, content=b"\x89PNG\r\n\x1a\n", metadata=meta)


# ---------------------------------------------------------------------------
# DocumentChunk metadata
# ---------------------------------------------------------------------------

class TestDocumentChunkMetadata:
    def test_accepts_element_type(self):
        chunk = _text_chunk("Hello", element_type="TITLE")
        assert chunk.metadata["element_type"] == "TITLE"

    def test_accepts_caption(self):
        chunk = DocumentChunk(
            data_type=DataType.PNG,
            content=b"\x89PNG\r\n\x1a\n",
            metadata={"page_num": [1], "element_type": "IMAGE", "caption": "Fig 1"},
        )
        assert chunk.metadata["caption"] == "Fig 1"

    def test_metadata_none_is_allowed(self):
        chunk = DocumentChunk(data_type=DataType.TEXT, content=b"plain text", metadata=None)
        assert chunk.metadata is None

    def test_rejects_non_fundamental_data_type(self):
        with pytest.raises(Exception):
            DocumentChunk(data_type=DataType.PDF, content=b"%PDF", metadata=None)


# ---------------------------------------------------------------------------
# DataType.get_to_doc_func routing
# ---------------------------------------------------------------------------

class TestGetToDocFunc:
    # classmethods create new bound method objects on each access, so compare __func__
    def test_pdf_default_returns_from_pdf(self):
        func = DataType.PDF.get_to_doc_func()
        assert func._call_func_.__func__ is Document.from_pdf.__func__

    def test_all_non_pdf_types_route_correctly(self):
        expected = {
            DataType.PNG: Document.from_png,
            DataType.JPEG: Document.from_jpeg,
            DataType.TEXT: Document.from_txt,
        }
        for dtype, expected_func in expected.items():
            assert dtype.get_to_doc_func()._call_func_.__func__ is expected_func.__func__


# ---------------------------------------------------------------------------
# Document.to_markdown()
# ---------------------------------------------------------------------------

class TestToMarkdown:
    def test_title_renders_as_heading(self):
        doc = Document("f.pdf", {0: _text_chunk("My Title", "TITLE")})
        assert doc.to_markdown().startswith("## My Title")

    def test_text_renders_as_paragraph(self):
        doc = Document("f.pdf", {0: _text_chunk("Body text", "TEXT")})
        assert "Body text\n\n" in doc.to_markdown()

    def test_table_renders_as_code_block(self):
        doc = Document("f.pdf", {0: _text_chunk("col1 col2", "TABLE")})
        md = doc.to_markdown()
        assert "```\ncol1 col2\n```" in md

    def test_equation_renders_with_dollars(self):
        doc = Document("f.pdf", {0: _text_chunk("E=mc^2", "EQUATION")})
        assert "$$ E=mc^2 $$" in doc.to_markdown()

    def test_table_caption_renders_italic(self):
        doc = Document("f.pdf", {0: _text_chunk("Table 1: Results", "TABLE_CAPTION")})
        assert "*Table 1: Results*" in doc.to_markdown()

    def test_image_caption_is_skipped(self):
        doc = Document("f.pdf", {0: _text_chunk("Caption text", "IMAGE_CAPTION")})
        assert doc.to_markdown() == ""

    def test_image_chunk_renders_placeholder(self):
        doc = Document("f.pdf", {0: _image_chunk()})
        assert "![Image](chunk_0)" in doc.to_markdown()

    def test_image_chunk_with_caption(self):
        doc = Document("f.pdf", {0: _image_chunk(caption="Figure 1")})
        assert "![Image](chunk_0) — Figure 1" in doc.to_markdown()

    def test_legacy_chunk_no_element_type_renders_as_paragraph(self):
        chunk = DocumentChunk(
            data_type=DataType.TEXT,
            content=b"Legacy text",
            metadata={"page_num": [1]},
        )
        doc = Document("f.pdf", {0: chunk})
        assert "Legacy text\n\n" in doc.to_markdown()

    def test_legacy_chunk_with_none_metadata(self):
        chunk = DocumentChunk(data_type=DataType.TEXT, content=b"No meta", metadata=None)
        doc = Document("f.pdf", {0: chunk})
        assert "No meta\n\n" in doc.to_markdown()

    def test_chunk_ordering_preserved(self):
        doc = Document("f.pdf", {
            0: _text_chunk("First", "TEXT"),
            1: _text_chunk("Second", "TITLE"),
        })
        md = doc.to_markdown()
        assert md.index("First") < md.index("Second")

    def test_empty_document(self):
        doc = Document("f.pdf", {})
        assert doc.to_markdown() == ""


# ---------------------------------------------------------------------------
# Document.from_pdf() — regression
# ---------------------------------------------------------------------------

class TestFromPdf:
    def test_returns_document(self):
        pdf_bytes = _make_minimal_pdf("Hello world")
        doc = Document.from_pdf("test.pdf", pdf_bytes)
        assert doc is not None
        assert doc.file_name == "test.pdf"

    def test_extracts_text(self):
        pdf_bytes = _make_minimal_pdf("Hello world")
        doc = Document.from_pdf("test.pdf", pdf_bytes)
        all_text = " ".join(
            c.get_as_string() for c in doc.contents.values() if c.data_type == DataType.TEXT
        )
        assert "Hello" in all_text

    def test_chunks_have_page_num(self):
        pdf_bytes = _make_minimal_pdf("Some content")
        doc = Document.from_pdf("test.pdf", pdf_bytes)
        for chunk in doc.contents.values():
            if chunk.data_type == DataType.TEXT:
                assert "page_num" in chunk.metadata

    def test_no_splits(self):
        # With do_splits=False text should not be split
        long_text = " ".join(["word"] * 1000)
        pdf_bytes = _make_minimal_pdf(long_text)
        doc = Document.from_pdf("test.pdf", pdf_bytes, do_splits=False)
        text_chunks = [c for c in doc.contents.values() if c.data_type == DataType.TEXT]
        assert len(text_chunks) == 1

    def test_invalid_bytes_returns_none(self):
        doc = Document.from_pdf("bad.pdf", b"not a pdf")
        assert doc is None

    def test_no_element_type_in_metadata(self):
        # from_pdf chunks should NOT have element_type (legacy format)
        pdf_bytes = _make_minimal_pdf("Hello")
        doc = Document.from_pdf("test.pdf", pdf_bytes)
        for chunk in doc.contents.values():
            if chunk.metadata:
                assert "element_type" not in chunk.metadata


