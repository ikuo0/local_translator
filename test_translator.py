import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from pypdf.errors import PdfReadError
import translator


class SplitTextTests(unittest.TestCase):
    def test_chunks_respect_limit_and_preserve_text(self):
        text = "first paragraph\n\nsecond paragraph with more words"
        chunks = translator.split_text(text, 20)

        self.assertEqual("".join(chunks), text)
        self.assertTrue(all(len(chunk) <= 20 for chunk in chunks))
        self.assertEqual(chunks[0], "first paragraph\n\n")

    def test_long_unbroken_text_is_split(self):
        self.assertEqual(translator.split_text("abcdefgh", 3), ["abc", "def", "gh"])

    def test_invalid_chunk_size_is_rejected(self):
        with self.assertRaises(ValueError):
            translator.split_text("text", 0)


class DocumentTests(unittest.TestCase):
    def test_text_file_extraction(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.txt"
            path.write_text("こんにちは", encoding="utf-8")
            self.assertEqual(translator.extract_text(path), "こんにちは")

    def test_pdf_pages_are_joined(self):
        page1, page2 = Mock(), Mock()
        page1.extract_text.return_value = "first"
        page2.extract_text.return_value = "second"
        reader = SimpleNamespace(pages=[page1, page2])
        with patch.object(translator, "PdfReader", return_value=reader):
            self.assertEqual(translator.extract_text("source.pdf"), "first\n\nsecond")

    def test_invalid_pdf_has_readable_error(self):
        with patch.object(
            translator, "PdfReader", side_effect=PdfReadError("invalid PDF")
        ):
            with self.assertRaisesRegex(ValueError, "PDFを読み込めません"):
                translator.extract_text("source.pdf")

    def test_chunks_are_translated_sequentially_with_context(self):
        with patch.object(translator, "translate_chunk", side_effect=["訳1", "訳2"]) as mock:
            result = translator.translate_document("abcdefgh", "model", "url", 4)

        self.assertEqual(result, "訳1訳2")
        self.assertEqual(mock.call_args_list[0].args, ("abcd", "model", "url", ""))
        self.assertEqual(mock.call_args_list[1].args, ("efgh", "model", "url", "訳1"))

    def test_paragraph_break_is_preserved_between_chunks(self):
        with patch.object(translator, "translate_chunk", side_effect=["訳1", "訳2"]):
            result = translator.translate_document(
                "first\n\nsecond", "model", "url", 7
            )

        self.assertEqual(result, "訳1\n\n訳2")

    def test_ollama_request_uses_local_generate_endpoint(self):
        response = io.BytesIO(json.dumps({"response": "翻訳"}).encode("utf-8"))
        with patch.object(translator, "urlopen", return_value=response) as urlopen:
            result = translator.translate_chunk(
                "source", "model", "http://localhost:11434/"
            )

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://localhost:11434/api/generate")
        payload = json.loads(request.data)
        self.assertEqual(payload["model"], "model")
        self.assertFalse(payload["stream"])
        self.assertEqual(result, "翻訳")


if __name__ == "__main__":
    unittest.main()
