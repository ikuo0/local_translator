"""
SR1000 Pipeline: PDF to Japanese HTML/PDF translation
Orchestrates SF001-SF004 steps with progress management.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from impl_translator.src.libs.batch_splitter import split_text_into_batches
from impl_translator.src.libs.docling_converter import convert_pdf_to_html
from impl_translator.src.libs.html_preproc import preprocess_html
from impl_translator.src.libs.html_text_extractor import extract_tag_text
from impl_translator.src.libs.translation_formatter import translate_batches
from impl_translator.src.libs.translation_restorer import restore_translations_to_html


class SR1000Pipeline:
    """
    SR1000 Pipeline for PDF to Japanese translation.

    Workflow:
    SF001: PDF → 1ページごと HTML（Docling）
    SF002: HTML → スタイルタグ削除 + ID付与
    SF003-1: HTML → タグ単位テキスト抽出
    SF003-2: テキスト → 1500文字バッチ化
    SF003-3: バッチ → Ollama で翻訳
    SF004: 翻訳 → HTML復元
    """

    def __init__(
        self,
        working_dir: Path,
        logger: Optional[logging.Logger] = None,
    ):
        self.working_dir = Path(working_dir)
        self.logger = logger or logging.getLogger("SR1000Pipeline")
        self.working_dir.mkdir(parents=True, exist_ok=True)

    def _log(self, level: str, message: str):
        """Log message."""
        if level == "info":
            self.logger.info(message)
        elif level == "warning":
            self.logger.warning(message)
        elif level == "error":
            self.logger.error(message)

    def _get_page_state_file(self, page_id: str) -> Path:
        """Get state file for a specific page."""
        return self.working_dir / "states" / f"{page_id}.json"

    def _load_page_state(self, page_id: str) -> Dict[str, Any]:
        """Load page processing state."""
        state_file = self._get_page_state_file(page_id)
        if state_file.exists():
            with open(state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "page_id": page_id,
            "status": "pending",  # pending/sf001/sf002/sf003/sf004/completed/failed
            "steps": {
                "sf001": {"status": "pending", "output": None},
                "sf002": {"status": "pending", "output": None},
                "sf003": {"status": "pending", "output": None},
                "sf004": {"status": "pending", "output": None},
            },
        }

    def _save_page_state(self, page_id: str, state: Dict[str, Any]):
        """Save page processing state."""
        state_file = self._get_page_state_file(page_id)
        state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def process_page(
        self,
        page_id: str,
        input_pdf: Path,
        page_number: int,
        ollama_host: str = "http://localhost:11434",
        ollama_model: str = "qwen3:8b",
        temperature: float = 0.3,
        resume: bool = False,
    ) -> bool:
        """
        Process a single PDF page through SF001-SF004.

        Returns:
            True if successful, False if failed
        """
        state = self._load_page_state(page_id)
        step_base_dir = self.working_dir / page_id
        step_base_dir.mkdir(parents=True, exist_ok=True)

        try:
            # SF001: PDF → HTML
            if state["steps"]["sf001"]["status"] != "completed" or not resume:
                self._log(
                    "info",
                    f"[{page_id}] SF001: Converting PDF to HTML...",
                )
                # Docling converter: split single page from PDF
                html_file = step_base_dir / "sf001_page.html"

                # Note: docling_converter expects full PDF, we extract single page
                # Using pymupdf to extract page first
                import pymupdf

                with pymupdf.open(input_pdf) as pdf:
                    if page_number > len(pdf):
                        raise ValueError(f"Page {page_number} out of range")

                    # Extract single page as temporary PDF
                    temp_pdf = step_base_dir / "temp_page.pdf"
                    with pymupdf.open() as single_page_doc:
                        single_page_doc.insert_pdf(pdf, from_page=page_number - 1, to_page=page_number - 1)
                        single_page_doc.save(temp_pdf)

                # Convert to HTML
                convert_pdf_to_html(
                    input_pdf=temp_pdf,
                    working_dir=step_base_dir / "sf001_work",
                    split_pages=False,  # Already single page
                )

                # Find generated HTML
                html_files = list((step_base_dir / "sf001_work" / "input_pages").glob("*.html"))
                if not html_files:
                    raise FileNotFoundError("No HTML generated from PDF")

                html_file.write_text(html_files[0].read_text(encoding="utf-8"), encoding="utf-8")
                temp_pdf.unlink()

                state["steps"]["sf001"]["status"] = "completed"
                state["steps"]["sf001"]["output"] = str(html_file)
                self._save_page_state(page_id, state)
                self._log("info", f"[{page_id}] SF001: Completed")

            html_file = Path(state["steps"]["sf001"]["output"])

            # SF002: HTML → Preprocess
            if state["steps"]["sf002"]["status"] != "completed" or not resume:
                self._log(
                    "info",
                    f"[{page_id}] SF002: Preprocessing HTML...",
                )
                html_preproc_file = step_base_dir / "sf002_preproc.html"
                preprocess_html(
                    input_html=html_file,
                    output_html=html_preproc_file,
                )
                state["steps"]["sf002"]["status"] = "completed"
                state["steps"]["sf002"]["output"] = str(html_preproc_file)
                self._save_page_state(page_id, state)
                self._log("info", f"[{page_id}] SF002: Completed")

            html_preproc_file = Path(state["steps"]["sf002"]["output"])

            # SF003: Translate
            if state["steps"]["sf003"]["status"] != "completed" or not resume:
                self._log(
                    "info",
                    f"[{page_id}] SF003: Extracting text and translating...",
                )

                # SF003-1: Extract text
                text_lines = extract_tag_text(html_preproc_file)
                text_file = step_base_dir / "sf003_1_extracted.txt"
                with open(text_file, "w", encoding="utf-8") as f:
                    for line in text_lines:
                        f.write(f"{{ID={line['id']}}} {line['text']}\n")
                self._log("info", f"[{page_id}] SF003-1: Extracted {len(text_lines)} tags")

                # SF003-2: Split into batches
                batches = split_text_into_batches(text_file, max_chars=1500)
                batches_file = step_base_dir / "sf003_2_batches.json"
                with open(batches_file, "w", encoding="utf-8") as f:
                    json.dump(batches, f, ensure_ascii=False, indent=2)
                self._log("info", f"[{page_id}] SF003-2: Split into {len(batches)} batches")

                # SF003-3: Translate batches
                translations_file = step_base_dir / "sf003_3_translations.json"
                self._log("info", f"[{page_id}] SF003-3: Translating {len(batches)} batches...")
                translate_batches(
                    input_batches_json=batches_file,
                    output_translations_json=translations_file,
                    ollama_host=ollama_host,
                    model=ollama_model,
                    temperature=temperature,
                    page_id=page_id,
                    logger=self,
                )
                self._log("info", f"[{page_id}] SF003-3: All {len(batches)} batches translated")

                state["steps"]["sf003"]["status"] = "completed"
                state["steps"]["sf003"]["output"] = str(translations_file)
                self._save_page_state(page_id, state)
                self._log("info", f"[{page_id}] SF003: Completed")

            translations_file = Path(state["steps"]["sf003"]["output"])

            # SF004: Restore to HTML
            if state["steps"]["sf004"]["status"] != "completed" or not resume:
                self._log(
                    "info",
                    f"[{page_id}] SF004: Restoring translations to HTML...",
                )
                html_translated_file = step_base_dir / "sf004_translated.html"
                restore_translations_to_html(
                    input_html=html_preproc_file,
                    translations_json=translations_file,
                    output_html=html_translated_file,
                )
                state["steps"]["sf004"]["status"] = "completed"
                state["steps"]["sf004"]["output"] = str(html_translated_file)
                self._save_page_state(page_id, state)
                self._log("info", f"[{page_id}] SF004: Completed")

            state["status"] = "completed"
            self._save_page_state(page_id, state)
            self._log("info", f"[{page_id}] All steps completed successfully")
            return True

        except Exception as e:
            state["status"] = "failed"
            state["error"] = str(e)
            self._save_page_state(page_id, state)
            self._log("error", f"[{page_id}] Processing failed: {e}")
            return False

    def get_page_status(self, page_id: str) -> Dict[str, Any]:
        """Get current status of a page."""
        return self._load_page_state(page_id)

    def list_page_states(self) -> Dict[str, Dict[str, Any]]:
        """List all page states."""
        states_dir = self.working_dir / "states"
        result = {}
        if states_dir.exists():
            for state_file in states_dir.glob("*.json"):
                with open(state_file, "r", encoding="utf-8") as f:
                    result[state_file.stem] = json.load(f)
        return result
