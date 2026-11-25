"""
SR1000 Pipeline: PDF to Japanese HTML/PDF translation
Orchestrates SF001-SF005 with progress management.
"""

import json
import logging
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import Event, Lock
from typing import Any, Dict, Optional

from impl_translator.src.features.SR1000 import sf001, sf002, sf003, sf004, sf005
from impl_translator.src.libs import job


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
    SF005: PDF・テキスト・Markdown出力
    """

    def __init__(
        self,
        working_dir: Path,
        logger: Optional[logging.Logger] = None,
        job_id: Optional[str] = None,
    ):
        self.working_dir = Path(working_dir).resolve()
        self.job_id = job_id if job_id is not None else job.create(self.working_dir)
        self.job_dir = job.job_directory(self.working_dir, self.job_id)
        self.logger = logger or logging.getLogger("SR1000Pipeline")
        self.metadata_file = self.job_dir / "metadata.json"
        if not self.job_dir.is_dir():
            raise FileNotFoundError(f"Job does not exist: {self.job_id}")
        self.metadata = self._load_metadata()
        self._metadata_lock = Lock()
        self._ollama_lock = Lock()
        self.stop_requested = Event()

    def _log(self, level: str, message: str):
        """Log message."""
        if level == "info":
            self.logger.info(message)
        elif level == "warning":
            self.logger.warning(message)
        elif level == "error":
            self.logger.error(message)

    def _load_metadata(self) -> Dict[str, Any]:
        """Load metadata from file."""
        if self.metadata_file.exists():
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_metadata(self):
        """Save metadata to file."""
        self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

    def _record_phase_metadata(self, page_id: str, phase: str, duration_sec: float, success: bool, output_path: Optional[str] = None):
        """Record phase execution metadata."""
        with self._metadata_lock:
            if page_id not in self.metadata:
                self.metadata[page_id] = {"phases": {}}

            self.metadata[page_id]["phases"][phase] = {
                "duration_sec": duration_sec,
                "success": success,
                "output": output_path,
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            }
            self._save_metadata()

    def _get_page_state_file(self, page_id: str) -> Path:
        """Get state file for a specific page."""
        return self.job_dir / "states" / f"{page_id}.json"

    def _load_page_state(self, page_id: str) -> Dict[str, Any]:
        """Load page processing state."""
        state_file = self._get_page_state_file(page_id)
        try:
            with state_file.open(encoding="utf-8") as file:
                state = json.load(file)
        except FileNotFoundError:
            return self._new_page_state(page_id)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._log("warning", f"[{page_id}] Invalid state file, processing page again")
            return self._new_page_state(page_id)
        if isinstance(state, dict) and state.get("page_id") == page_id and "status" in state:
            return state
        self._log("warning", f"[{page_id}] Invalid state file, processing page again")
        return self._new_page_state(page_id)

    @staticmethod
    def _new_page_state(page_id: str) -> Dict[str, Any]:
        return {
            "page_id": page_id,
            "status": "pending",
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

    def _get_phase_dir(self, page_id: str, phase: str) -> Path:
        """Get directory for a specific phase."""
        # phase: sf001_to_html, sf002_preproc, sf003_translate, sf004_restore
        phase_base_dir = self.job_dir / f"{phase}"
        page_phase_dir = phase_base_dir / page_id
        page_phase_dir.mkdir(parents=True, exist_ok=True)
        return page_phase_dir

    @contextmanager
    def _track_step(self, page_id: str, state: dict, step_name: str):
        if self.stop_requested.is_set():
            raise KeyboardInterrupt
        step = state["steps"][step_name]
        stats = {"started_at": job.now(), "finished_at": None, "duration_sec": None}
        step.update(status="running", output=None, stats=stats)
        state["status"] = "running"
        started = time.monotonic()

        def finish():
            stats["finished_at"] = job.now()
            stats["duration_sec"] = time.monotonic() - started

        self._save_page_state(page_id, state)
        try:
            yield finish
        except KeyboardInterrupt:
            step["status"] = "interrupted"
            state["status"] = "interrupted"
            raise
        except Exception:
            step["status"] = "failed"
            raise
        finally:
            if stats["finished_at"] is None:
                finish()
            self._save_page_state(page_id, state)

    def process_page(
        self,
        page_id: str,
        input_pdf: Path,
        page_number: int,
        ollama_host: str = "http://localhost:11434",
        ollama_model: str = "qwen3:8b",
        temperature: float = 0.3,
        resume: bool = False,
        system_prompt: str | None = None,
    ) -> bool:
        """
        Process a single PDF page through SF001-SF004.

        Returns:
            True if successful, False if failed
        """
        if resume and self._load_page_state(page_id)["status"] == "completed":
            return True
        state = self._new_page_state(page_id)

        try:
            with self._metadata_lock:
                if self.metadata.pop(page_id, None) is not None:
                    self._save_metadata()

            # SF001: PDF → HTML
            self._log(
                "info",
                f"[{page_id}] SF001: Converting PDF to HTML...",
            )
            with self._track_step(page_id, state, "sf001") as finish:
                sf001_dir = self._get_phase_dir(page_id, "SF001_to_html")
                html_file = sf001.convert_page_to_html(input_pdf, page_number, sf001_dir)

                finish()
                duration = state["steps"]["sf001"]["stats"]["duration_sec"]
                self._record_phase_metadata(page_id, "SF001_to_html", duration, True, str(html_file))

                state["steps"]["sf001"]["status"] = "completed"
                state["steps"]["sf001"]["output"] = str(html_file)
                self._log("info", f"[{page_id}] SF001: Completed ({duration:.2f}s)")

            # SF002: HTML → Preprocess
            self._log(
                "info",
                f"[{page_id}] SF002: Preprocessing HTML...",
            )
            with self._track_step(page_id, state, "sf002") as finish:
                sf002_dir = self._get_phase_dir(page_id, "SF002_preproc")
                html_preproc_file = sf002.prepare_html(html_file, sf002_dir)

                finish()
                duration = state["steps"]["sf002"]["stats"]["duration_sec"]
                self._record_phase_metadata(page_id, "SF002_preproc", duration, True, str(html_preproc_file))

                state["steps"]["sf002"]["status"] = "completed"
                state["steps"]["sf002"]["output"] = str(html_preproc_file)
                self._log("info", f"[{page_id}] SF002: Completed ({duration:.2f}s)")

            # SF003: Translate
            self._log(
                "info",
                f"[{page_id}] SF003: Extracting text and translating...",
            )
            with self._track_step(page_id, state, "sf003") as finish:
                sf003_dir = self._get_phase_dir(page_id, "SF003_translate")

                translations_file = sf003.translate_page(
                    html_preproc_file,
                    sf003_dir,
                    page_id=page_id,
                    ollama_host=ollama_host,
                    model=ollama_model,
                    temperature=temperature,
                    system_prompt=system_prompt,
                    logger=self.logger,
                    ollama_lock=self._ollama_lock,
                    stop_requested=self.stop_requested,
                )

                finish()
                duration = state["steps"]["sf003"]["stats"]["duration_sec"]
                self._record_phase_metadata(page_id, "SF003_translate", duration, True, str(translations_file))

                state["steps"]["sf003"]["status"] = "completed"
                state["steps"]["sf003"]["output"] = str(translations_file)
                self._log("info", f"[{page_id}] SF003: Completed ({duration:.2f}s)")

            # SF004: Restore to HTML
            self._log(
                "info",
                f"[{page_id}] SF004: Restoring translations to HTML...",
            )
            with self._track_step(page_id, state, "sf004") as finish:
                sf004_dir = self._get_phase_dir(page_id, "SF004_restore")
                html_translated_file = sf004.restore_page_html(
                    html_preproc_file, translations_file, sf004_dir,
                )

                finish()
                duration = state["steps"]["sf004"]["stats"]["duration_sec"]
                self._record_phase_metadata(page_id, "SF004_restore", duration, True, str(html_translated_file))

                state["steps"]["sf004"]["status"] = "completed"
                state["steps"]["sf004"]["output"] = str(html_translated_file)
                self._log("info", f"[{page_id}] SF004: Completed ({duration:.2f}s)")

            state["status"] = "completed"
            state.pop("error", None)
            self._save_page_state(page_id, state)
            self._log("info", f"[{page_id}] All steps completed successfully")
            return True

        except Exception as e:
            state["status"] = "failed"
            state["error"] = str(e)
            self._save_page_state(page_id, state)
            self._log("error", f"[{page_id}] Processing failed: {e}")
            return False

    def export_job(
        self, input_pdf: Path, start_page: int, end_page: int, job_state: dict,
        fallback_pages: list[int] | None = None,
    ) -> bool:
        """Run SF005 and persist the export result in the job state."""
        phase_dir = self.job_dir / "SF005"
        html_pages = (
            (
                self.job_dir / "SF001_to_html" / page_id / "page.html",
                self.job_dir / "SF004_restore" / page_id / "translated.html",
            )
            for page_id in (f"page_{number:06d}" for number in range(start_page, end_page + 1))
        )
        self.logger.info("SF005: Exporting PDF, text, and Markdown")
        export_state = {"status": "progress", "stats": {"started_at": job.now()}}
        job_state["data"]["sf005"] = export_state
        started = time.monotonic()
        job.save(self.working_dir, self.job_id, job_state)
        try:
            output_pdf = sf005.export_translated_pages(
                html_pages, phase_dir, f"{input_pdf.stem}jpn.pdf",
                source_pdf=input_pdf, fallback_pages=fallback_pages,
            )
            export_state.update(status="complete", outputs={
                "pdf": str(output_pdf.relative_to(self.job_dir)),
                "text": "SF005/text",
                "md_en": "SF005/md_en",
                "md_jp": "SF005/md_jp",
            })
            if fallback_pages:
                export_state["fallback_pages"] = fallback_pages
        except KeyboardInterrupt:
            export_state.update(status="error", error="Interrupted")
            raise
        except Exception as error:
            export_state.update(status="error", error=str(error))
            self.logger.error("SF005: Export failed: %s", error)
            return False
        finally:
            export_state["stats"].update(
                finished_at=job.now(),
                duration_sec=time.monotonic() - started,
            )
            job.save(self.working_dir, self.job_id, job_state)
        self.logger.info("SF005: Saved %s", output_pdf)
        self.logger.info("SF005: Saved page text in %s", phase_dir / "text")
        self.logger.info("SF005: Saved original and translated Markdown in %s and %s", phase_dir / "md_en", phase_dir / "md_jp")
        return True

    def get_page_status(self, page_id: str) -> Dict[str, Any]:
        """Get current status of a page."""
        return self._load_page_state(page_id)

    def list_page_states(self) -> Dict[str, Dict[str, Any]]:
        """List all page states."""
        states_dir = self.job_dir / "states"
        result = {}
        if states_dir.exists():
            for state_file in states_dir.glob("*.json"):
                with open(state_file, "r", encoding="utf-8") as f:
                    result[state_file.stem] = json.load(f)
        return result
