import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf
import yaml

from impl_translator.src.features.SR1000 import batch
from impl_translator.src.libs import job


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.working = self.root / "jobs"
        self.input_pdf = self.root / "input.pdf"
        self.output_pdf = self.root / "output.pdf"
        self.output_text = self.root / "output.txt"
        self.log_file = self.root / "progress.log"
        with pymupdf.open() as pdf:
            for text in ("First page", "Second page"):
                page = pdf.new_page()
                page.insert_text((72, 72), text)
            pdf.save(self.input_pdf)

    def tearDown(self):
        self.temporary.cleanup()

    def new_job(self):
        return job.create(
            self.working,
            {
                "status": "created",
                "input_pdf": str(self.input_pdf),
                "input_sha256": batch.file_hash(self.input_pdf),
                "output_pdf": str(self.output_pdf),
                "output_text": str(self.output_text),
                "log_file": str(self.log_file),
                "page_count": 2,
                "ollama_host": "http://ollama:11434",
                "ollama_model": "qwen3:8b",
                "pages": {},
            },
        )

    def translated_copy(self, input_pdf, output_dir, host, model):
        output_dir.mkdir(parents=True, exist_ok=True)
        target = output_dir / "input.ja.mono.pdf"
        with pymupdf.open(input_pdf) as pdf:
            pdf.save(target)
        return target

    def test_failed_page_is_retried_and_successful_page_is_reused(self):
        job_id = self.new_job()
        calls = []

        def translate(input_pdf, output_dir, host, model):
            with pymupdf.open(input_pdf) as pdf:
                text = pdf[0].get_text()
            calls.append(text)
            if "Second" in text and model == "qwen3:8b":
                raise RuntimeError("translation failed")
            return self.translated_copy(input_pdf, output_dir, host, model)

        with (
            patch.object(batch.translator, "translate_page", side_effect=translate),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(batch.run_job(self.working, job_id, None, None), 1)
            self.assertEqual(batch.run_job(self.working, job_id, None, "new-model"), 0)
        self.assertEqual(len(calls), 3)
        self.assertEqual(sum("First" in text for text in calls), 1)
        state = job.load(self.working, job_id)["data"]
        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["pages"]["1"]["model"], "qwen3:8b")
        self.assertEqual(state["pages"]["2"]["model"], "new-model")
        with pymupdf.open(self.output_pdf) as pdf:
            self.assertEqual(len(pdf), 2)
            self.assertIn("First page", pdf[0].get_text())
            self.assertIn("Second page", pdf[1].get_text())
        self.assertIn("Second page", self.output_text.read_text(encoding="utf-8"))
        self.assertIn("Page 2/2 failed", self.log_file.read_text(encoding="utf-8"))

    def test_failure_page_and_job_status(self):
        job_id = self.new_job()
        with (
            patch.object(
                batch.translator, "translate_page", side_effect=RuntimeError("offline")
            ),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(batch.run_job(self.working, job_id, None, None), 1)
        state = job.load(self.working, job_id)["data"]
        self.assertEqual(state["status"], "completed_with_errors")
        self.assertEqual(state["pages"]["1"]["status"], "failed")
        with pymupdf.open(self.output_pdf) as pdf:
            self.assertEqual(len(pdf), 2)
            self.assertIn("翻訳に失敗しました", pdf[0].get_text())
        self.assertIn(
            "翻訳に失敗しました", self.output_text.read_text(encoding="utf-8")
        )

    def test_interrupted_page_is_retried(self):
        job_id = self.new_job()
        with (
            patch.object(
                batch.translator, "translate_page", side_effect=KeyboardInterrupt
            ),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(batch.run_job(self.working, job_id, None, None), 130)
        state = job.load(self.working, job_id)["data"]
        self.assertEqual(state["status"], "interrupted")
        self.assertEqual(state["pages"]["1"]["status"], "running")
        with (
            patch.object(
                batch.translator, "translate_page", side_effect=self.translated_copy
            ),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(batch.run_job(self.working, job_id, None, None), 0)

    def test_changed_input_is_rejected(self):
        job_id = self.new_job()
        self.input_pdf.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "changed"):
            batch.run_job(self.working, job_id, None, None)

    def test_textless_page_is_preserved_without_translation(self):
        blank_input = self.root / "blank.pdf"
        with pymupdf.open() as pdf:
            page = pdf.new_page(width=200, height=300)
            page.draw_rect(pymupdf.Rect(20, 20, 80, 80), color=(1, 0, 0))
            pdf.save(blank_input)
        self.input_pdf = blank_input
        job_id = self.new_job()
        state = job.load(self.working, job_id)
        state["data"]["page_count"] = 1
        job.save(self.working, job_id, state)
        with (
            patch.object(batch.translator, "translate_page") as translate,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(batch.run_job(self.working, job_id, None, None), 0)
        translate.assert_not_called()
        state = job.load(self.working, job_id)["data"]
        self.assertEqual(state["pages"]["1"]["llm_status"], "not_required")
        with pymupdf.open(self.output_pdf) as pdf:
            self.assertEqual(len(pdf), 1)
            self.assertEqual(pdf[0].rect.width, 200)
            self.assertEqual(len(pdf[0].get_drawings()), 1)

    def test_job_update_and_invalid_id(self):
        job_id = job.create(self.working)
        job.update(self.working, job_id, "progress", {"done": 2})
        self.assertEqual(
            job.load(self.working, job_id)["data"]["progress"], {"done": 2}
        )
        with self.assertRaises(ValueError):
            job.load(self.working, "../outside")

    def test_job_lock_prevents_concurrent_updates(self):
        job_id = job.create(self.working)
        with (
            job.lock(self.working, job_id),
            self.assertRaisesRegex(RuntimeError, "already running"),
        ):
            job.update(self.working, job_id, "progress", 1)

    def test_job_cli_create_update_and_get(self):
        command = [
            sys.executable,
            "-m",
            "impl_translator.src.libs.job",
            "--working-dir",
            str(self.working),
        ]
        job_id = subprocess.check_output([*command, "--create"], text=True).strip()
        subprocess.run(
            [
                *command,
                "--update",
                "--job-id",
                job_id,
                "--sub-key",
                "progress",
                "--data",
                "{done: 2}",
            ],
            check=True,
        )
        result = subprocess.check_output(
            [*command, "--get", "--job-id", job_id, "--sub-key", "progress"],
            text=True,
        )
        self.assertEqual(yaml.safe_load(result)["progress"], {"done": 2})


if __name__ == "__main__":
    unittest.main()
