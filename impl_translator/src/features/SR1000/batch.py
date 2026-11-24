"""Translate a PDF one page at a time, retaining resumable job state."""

import argparse
import hashlib
import logging
import os
import signal
import sys
import tempfile
import time
from pathlib import Path

import pymupdf
import yaml

from impl_translator.src.libs import job, translator


class InterruptionHandler:
    """Graceful interruption handler for CTRL+C."""

    def __init__(self):
        self.interrupted = False
        self._previous_handler = None

    def __enter__(self):
        self._previous_handler = signal.signal(signal.SIGINT, self._handle_interrupt)
        return self

    def __exit__(self, *args):
        signal.signal(signal.SIGINT, self._previous_handler)

    def _handle_interrupt(self, signum, frame):
        self.interrupted = True

    def check(self):
        """Check if interruption was requested; raises KeyboardInterrupt if so."""
        if self.interrupted:
            raise KeyboardInterrupt("Interrupted by user")


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def configure_logging(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("SR1000")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    return logger


def validate_paths(
    input_pdf: Path, output_pdf: Path, output_text: Path, log_file: Path
) -> None:
    paths = [input_pdf, output_pdf, output_text, log_file]
    if len(set(paths)) != len(paths):
        raise ValueError("Input, outputs and log must be distinct files")
    if not input_pdf.is_file():
        raise FileNotFoundError(f"Input PDF not found: {input_pdf}")


def build_outputs(directory: Path, state: dict) -> None:
    data = state["data"]
    output_pdf = Path(data["output_pdf"])
    output_text = Path(data["output_text"])
    pdf_temp = None
    text_temp = None
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    output_text.parent.mkdir(parents=True, exist_ok=True)
    try:
        with pymupdf.open() as merged:
            texts = []
            with pymupdf.open(data["input_pdf"]) as original:
                for page_number in range(1, data["page_count"] + 1):
                    page_info = data["pages"][str(page_number)]
                    if page_info["status"] == "completed":
                        page_pdf = directory / "pages" / f"{page_number:06}.pdf"
                        with pymupdf.open(page_pdf) as page_document:
                            if len(page_document) != 1:
                                raise ValueError(f"Invalid page artifact: {page_pdf}")
                            texts.append(
                                page_document[0]
                                .get_textpage()
                                .extractText(sort=True)
                                .strip()
                            )
                            merged.insert_pdf(page_document)
                    elif page_info["status"] == "failed":
                        source_page = original[page_number - 1]
                        page = merged.new_page(
                            width=source_page.rect.width, height=source_page.rect.height
                        )
                        message = f"翻訳に失敗しました（ページ {page_number}）"
                        font_size = min(
                            12.0,
                            page.rect.width * 0.9 / len(message),
                            page.rect.height * 0.6,
                        )
                        page.insert_text(
                            (page.rect.width * 0.05, page.rect.height * 0.7),
                            message,
                            fontname="japan",
                            fontsize=font_size,
                        )
                        texts.append(message)
                    else:
                        raise ValueError(f"Page {page_number} has not finished")
            with tempfile.NamedTemporaryFile(
                dir=output_pdf.parent, suffix=".pdf", delete=False
            ) as file:
                pdf_temp = Path(file.name)
            merged.save(pdf_temp)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=output_text.parent, delete=False
        ) as file:
            text_temp = Path(file.name)
            file.write("\n\n".join(texts) + "\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(pdf_temp, output_pdf)
        os.replace(text_temp, output_text)
    finally:
        if pdf_temp is not None:
            pdf_temp.unlink(missing_ok=True)
        if text_temp is not None:
            text_temp.unlink(missing_ok=True)


def run_job(
    working_dir: Path,
    job_id: str,
    host: str | None,
    model: str | None,
    qps: int = 4,
    pool_max_workers: int = 2,
    primary_font_family: str | None = "serif",
) -> int:
    directory = job.job_directory(working_dir, job_id)
    with job.lock(working_dir, job_id):
        state = job.load(working_dir, job_id)
        data = state["data"]
        print(
            f"Job ID: {job_id}\nJob directory: {directory}\nLog: {data['log_file']}",
            flush=True,
        )
        input_pdf = Path(data["input_pdf"])
        if file_hash(input_pdf) != data["input_sha256"]:
            raise ValueError("Input PDF has changed since the job was created")
        if host is not None:
            data["ollama_host"] = host
        if model is not None:
            data["ollama_model"] = model
        if primary_font_family is not None:
            data["primary_font_family"] = primary_font_family
        logger = configure_logging(Path(data["log_file"]))
        logger.info("Job %s started or resumed", job_id)
        data["status"] = "running"
        data.setdefault("started_at", job.now())
        run_started = time.monotonic()
        job.save(working_dir, job_id, state)
        with InterruptionHandler() as interrupt_handler:
            try:
                with pymupdf.open(input_pdf) as source:
                    if len(source) != data["page_count"]:
                        raise ValueError("Input PDF page count has changed")
                    pages_dir = directory / "pages"
                    pages_dir.mkdir(exist_ok=True)
                    for page_number in range(1, len(source) + 1):
                        interrupt_handler.check()
                        key = str(page_number)
                        previous = data["pages"].get(key, {})
                        destination = pages_dir / f"{page_number:06}.pdf"
                        if previous.get("status") == "completed":
                            if not destination.is_file():
                                raise FileNotFoundError(
                                    f"Completed page artifact missing: {destination}"
                                )
                            logger.info(
                                "Job %s: Page %s/%s already completed",
                                job_id,
                                page_number,
                                len(source),
                            )
                            continue
                        start = time.monotonic()
                        source_text = source[page_number - 1].get_textpage().extractText()
                        page_info = {
                            "page": page_number,
                            "status": "running",
                            "started_at": job.now(),
                            "model": data["ollama_model"],
                            "ollama_host": data["ollama_host"],
                            "input_characters": len(source_text),
                        }
                        data["pages"][key] = page_info
                        job.save(working_dir, job_id, state)
                        logger.info(
                            "Job %s: Page %s/%s started", job_id, page_number, len(source)
                        )
                        try:
                            with tempfile.TemporaryDirectory(
                                dir=directory, prefix="page-"
                            ) as temp:
                                temporary = Path(temp)
                                page_input = temporary / "input.pdf"
                                with pymupdf.open() as one_page:
                                    one_page.insert_pdf(
                                        source,
                                        from_page=page_number - 1,
                                        to_page=page_number - 1,
                                    )
                                    one_page.save(page_input)
                                if source_text.strip():
                                    translated = translator.translate_page(
                                        page_input,
                                        temporary / "translated",
                                        data["ollama_host"],
                                        data["ollama_model"],
                                        interrupt_handler,
                                        qps=qps,
                                        pool_max_workers=pool_max_workers,
                                        primary_font_family=data.get("primary_font_family", "serif"),
                                    )
                                    page_info["llm_status"] = "completed"
                                else:
                                    translated = page_input
                                    page_info["llm_status"] = "not_required"
                                interrupt_handler.check()
                                with pymupdf.open(translated) as result:
                                    if len(result) != 1:
                                        raise ValueError(
                                            f"Expected one translated page, got {len(result)}"
                                        )
                                    page_info["output_characters"] = len(
                                        result[0].get_text()
                                    )
                                os.replace(translated, destination)
                            page_info["status"] = "completed"
                            logger.info(
                                "Job %s: Page %s/%s completed",
                                job_id,
                                page_number,
                                len(source),
                            )
                        except KeyboardInterrupt:
                            page_info["status"] = "interrupted"
                            page_info["elapsed_seconds"] = round(
                                time.monotonic() - start, 3
                            )
                            page_info["finished_at"] = job.now()
                            job.save(working_dir, job_id, state)
                            raise
                        except (OSError, ValueError, RuntimeError) as error:
                            page_info["status"] = "failed"
                            page_info["llm_status"] = "error_or_unavailable"
                            page_info["error"] = f"{type(error).__name__}: {error}"
                            logger.exception(
                                "Job %s: Page %s/%s failed",
                                job_id,
                                page_number,
                                len(source),
                            )
                        finally:
                            page_info["elapsed_seconds"] = round(
                                time.monotonic() - start, 3
                            )
                            page_info["finished_at"] = job.now()
                            job.save(working_dir, job_id, state)
                interrupt_handler.check()
                build_outputs(directory, state)
                failed = sum(
                    1 for page in data["pages"].values() if page["status"] == "failed"
                )
                data["status"] = "completed"
                if failed:
                    data["status"] = "completed_with_errors"
                data["finished_at"] = job.now()
                job.save(working_dir, job_id, state)
                logger.info("Job %s finished; failed pages: %s", job_id, failed)
                print(
                    f"Job {job_id}: {data['status']}; output: {data['output_pdf']}",
                    flush=True,
                )
                if failed:
                    return 1
                return 0
            except KeyboardInterrupt:
                data["status"] = "interrupted"
                job.save(working_dir, job_id, state)
                logger.warning("Job %s interrupted", job_id)
                print(
                    f"Job {job_id} interrupted; job directory: {directory}",
                    file=sys.stderr,
                    flush=True,
                )
                return 130
            except Exception:
                data["status"] = "error"
                logger.exception("Job %s failed", job_id)
                raise
            finally:
                data["elapsed_seconds"] = round(
                    data.get("elapsed_seconds", 0) + time.monotonic() - run_started, 3
                )
                job.save(working_dir, job_id, state)
                for handler in logger.handlers[:]:
                    handler.close()
                    logger.removeHandler(handler)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Translate an English PDF into Japanese"
    )
    parser.add_argument("--working-dir", required=True, type=Path)
    parser.add_argument("--log-file", type=Path)
    parser.add_argument("--input-pdf", type=Path)
    parser.add_argument("--output-pdf", type=Path)
    parser.add_argument("--output-text", type=Path)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--job-id")
    parser.add_argument("--ollama-host")
    parser.add_argument("--ollama-model")
    parser.add_argument(
        "--qps",
        type=int,
        default=4,
        help="Queries per second for LLM requests (default: 4, was: 1)",
    )
    parser.add_argument(
        "--pool-max-workers",
        type=int,
        default=2,
        help="Max worker threads for parallel translation (default: 2, was: 1)",
    )
    parser.add_argument(
        "--primary-font-family",
        type=str,
        default="serif",
        choices=["serif", "sans-serif", "script", "None"],
        help="Font family for translated text (default: serif). Options: serif, sans-serif, script, or None for system fonts. Reduces file size by ~70%%.",
    )
    args = parser.parse_args()
    if args.resume:
        if not args.job_id:
            parser.error("--resume requires --job-id")
        if any((args.input_pdf, args.output_pdf, args.output_text, args.log_file)):
            parser.error(
                "Input, output and log paths are restored from the job when resuming"
            )
    else:
        if args.job_id or not all(
            (args.input_pdf, args.output_pdf, args.output_text, args.log_file)
        ):
            parser.error(
                "A new job requires --input-pdf, --output-pdf, --output-text and --log-file"
            )
    working_dir = args.working_dir.resolve()
    try:
        if args.resume:
            job_id = args.job_id
        else:
            input_pdf = args.input_pdf.resolve()
            output_pdf = args.output_pdf.resolve()
            output_text = args.output_text.resolve()
            log_file = args.log_file.resolve()
            validate_paths(input_pdf, output_pdf, output_text, log_file)
            with pymupdf.open(input_pdf) as pdf:
                if len(pdf) == 0:
                    raise ValueError("Input PDF contains no pages")
                page_count = len(pdf)
            stat = input_pdf.stat()
            data = {
                "status": "created",
                "input_pdf": str(input_pdf),
                "input_size": stat.st_size,
                "input_modified_at": stat.st_mtime,
                "input_sha256": file_hash(input_pdf),
                "output_pdf": str(output_pdf),
                "output_text": str(output_text),
                "log_file": str(log_file),
                "page_count": page_count,
                "ollama_host": args.ollama_host or "http://ollama:11434",
                "ollama_model": args.ollama_model or "qwen3:8b",
                "pages": {},
            }
            job_id = job.create(working_dir, data)
        return run_job(
            working_dir,
            job_id,
            args.ollama_host,
            args.ollama_model,
            qps=args.qps,
            pool_max_workers=args.pool_max_workers,
            primary_font_family=args.primary_font_family if args.primary_font_family != "None" else None,
        )
    except (OSError, ValueError, RuntimeError, yaml.YAMLError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
