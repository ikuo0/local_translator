"""
SR1000 integrated command: PDF to Japanese HTML/PDF translation
Combines all libs modules (docling_converter, html_preproc, html_text_extractor,
batch_splitter, translation_formatter, translation_restorer)
"""

import argparse
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from threading import Lock

from impl_translator.src.features.SR1000 import sf001
from impl_translator.src.features.SR1000.sr1000_pipeline import SR1000Pipeline
from impl_translator.src.libs import job
from impl_translator.src.libs.ai_client.ollama import OllamaClient


def setup_logging(log_file: Path | None = None) -> logging.Logger:
    """Configure logging."""
    logger = logging.getLogger("SR1000")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    # Console handler (for real-time display)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(
        logging.Formatter("[%(levelname)s] %(message)s")
    )
    logger.addHandler(console_handler)

    if log_file is not None:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        logger.addHandler(file_handler)

    return logger


def translate_pdf(
    input_pdf: Path,
    working_dir: Path,
    ollama_host: str = "http://localhost:11434",
    ollama_model: str = "qwen3:8b",
    temperature: float = 0.3,
    resume: bool = False,
    job_id: str | None = None,
    start_page: int = -1,
    end_page: int = -1,
    debug_ollama_cache: bool = False,
    parallel_count: int = 1,
    system_prompt: str | None = None,
) -> int:
    """
    Translate a PDF document page by page.

    Args:
        input_pdf: Path to input PDF file
        working_dir: Working directory for intermediate files
        ollama_host: Ollama host URL
        ollama_model: Ollama model name
        temperature: Translation temperature
        resume: Resume from previous progress
        job_id: Existing job ID when resuming
        start_page: Starting page number (1-indexed, -1 means 1)
        end_page: Ending page number (1-indexed, -1 means last page)
        debug_ollama_cache: Send a diagnostic request before processing pages
        parallel_count: Maximum number of concurrent page workers
        system_prompt: Extra translation context, reused on resume if omitted

    Returns:
        0 if successful, 1 if any page failed
    """
    logger = setup_logging()
    try:
        working_dir = working_dir.resolve()
        input_pdf = input_pdf.resolve()
    except (OSError, RuntimeError) as error:
        logger.error("Unable to resolve input or working directory: %s", error)
        return 1

    if parallel_count < 1:
        logger.error("--parallel-count must be at least 1")
        return 1

    if resume != (job_id is not None):
        logger.error("--resume and --job-id must be supplied together")
        return 1

    if not input_pdf.exists():
        logger.error(f"Input PDF not found: {input_pdf}")
        return 1

    try:
        page_count = sf001.count_pages(input_pdf)
    except Exception as e:
        logger.error(f"Failed to read PDF: {e}")
        return 1

    use_default_start = start_page == -1
    use_default_end = end_page == -1

    # Resolve page range: -1 means first/last page
    if start_page == -1:
        start_page = 1
    if end_page == -1:
        end_page = page_count

    # Validate page range
    if start_page < 1 or end_page < 1 or start_page > end_page:
        logger.error(f"Invalid page range: {start_page} to {end_page} (PDF has {page_count} pages)")
        return 1

    if end_page > page_count:
        logger.warning(f"End page {end_page} exceeds page count {page_count}, using {page_count}")
        end_page = page_count

    if start_page > page_count:
        logger.error(f"Start page {start_page} exceeds page count {page_count}")
        return 1

    try:
        if job_id is None:
            job_id = job.create(working_dir, {"input_pdf": str(input_pdf)})

        with job.lock(working_dir, job_id):
            job_dir = job.job_directory(working_dir, job_id)
            logger = setup_logging(job_dir / "log.txt")
            logger.info("Job ID: %s", job_id)
            logger.info("Job directory: %s", job_dir)
            job_state = job.load(working_dir, job_id)
            data = job_state["data"]
            saved_input = data.get("input_pdf")
            if saved_input != str(input_pdf):
                logger.error("Input PDF does not match the PDF registered for job %s", job_id)
                return 1

            if system_prompt is None:
                system_prompt = data.get("system_prompt")
            else:
                data["system_prompt"] = system_prompt

            selection = data.get("selection", {})
            if use_default_start:
                start_page = selection.get("start_page", start_page)
            if use_default_end:
                end_page = selection.get("end_page", end_page)
            if not 1 <= start_page <= end_page <= page_count:
                logger.error("Invalid page range: %s to %s", start_page, end_page)
                return 1

            logger.info("Input PDF: %s", input_pdf)
            logger.info("Processing pages %s to %s out of %s", start_page, end_page, page_count)

            pipeline = SR1000Pipeline(
                working_dir=working_dir,
                logger=logger,
                job_id=job_id,
            )
            data["selection"] = {
                "document_page_count": page_count,
                "start_page": start_page,
                "end_page": end_page,
                "selected_page_count": end_page - start_page + 1,
            }
            data["pages"] = {
                number: page_progress(pipeline.get_page_status(f"page_{number:06d}"))
                for number in range(start_page, end_page + 1)
            }
            data["sf005"] = {"status": "pending"}
            save_job_progress(working_dir, job_state)

            if debug_ollama_cache:
                logger.info("Ollama cache probe: prompt=Hello, stream=false, keep_alive=0")
                OllamaClient(host=ollama_host, model=ollama_model).generate(
                    prompt="Hello", stream=False, keep_alive="0", log_cache_metrics=True,
                )

            return _process_pages(
                pipeline, logger, input_pdf, start_page, end_page,
                ollama_host, ollama_model, temperature, resume, job_state, parallel_count,
                system_prompt,
            )
    except (OSError, RuntimeError, ValueError) as error:
        logger.error("Unable to use SR1000 job %s: %s", job_id, error)
        return 1


def page_progress(state: dict) -> dict:
    """Project a saved page state into the job progress record."""
    status = state["status"]
    if status == "completed":
        progress = {"status": "complete"}
    elif status in {"failed", "interrupted", "running"}:
        progress = {"status": "error", "error": state.get("error") or "Page processing did not finish"}
    else:
        progress = {"status": "pending"}

    phases = {
        name: step["stats"]
        for name, step in state.get("steps", {}).items()
        if step.get("stats")
    }
    if phases:
        started_at = phases.get("sf001", {}).get("started_at")
        finished_at = next(
            (phases[name].get("finished_at") for name in ("sf004", "sf003", "sf002", "sf001") if name in phases),
            None,
        )
        stats = {"started_at": started_at, "finished_at": finished_at, "phases": phases}
        if started_at and finished_at:
            try:
                started = datetime.fromisoformat(started_at)
                finished = datetime.fromisoformat(finished_at)
                stats["duration_sec"] = (finished - started).total_seconds()
            except (TypeError, ValueError):
                pass
        progress["stats"] = stats
    return progress


def save_job_progress(working_dir: Path, job_state: dict) -> None:
    data = job_state["data"]
    summary = dict.fromkeys(("pending", "progress", "error", "complete"), 0)
    for page in data["pages"].values():
        summary[page["status"]] += 1
    data["summary"] = {"total": len(data["pages"]), **summary}
    job.save(working_dir, job_state["job_id"], job_state)


def _process_pages(
    pipeline: SR1000Pipeline,
    logger: logging.Logger,
    input_pdf: Path,
    start_page: int,
    end_page: int,
    ollama_host: str,
    ollama_model: str,
    temperature: float,
    resume: bool,
    job_state: dict,
    parallel_count: int,
    system_prompt: str | None,
) -> int:
    pages = job_state["data"]["pages"]
    progress_lock = Lock()
    pending = []
    for number, page in pages.items():
        if resume and page["status"] == "complete":
            logger.info("[page_%06d] Reusing completed page", number)
        else:
            pending.append(number)

    def update_progress(page_number: int, state: dict) -> None:
        with progress_lock:
            pages[page_number] = state
            save_job_progress(pipeline.working_dir, job_state)

    def process_page(page_number: int) -> None:
        if pipeline.stop_requested.is_set():
            return
        page_id = f"page_{page_number:06d}"
        logger.info("Processing %s (%s/%s)", page_id, page_number - start_page + 1, end_page - start_page + 1)
        update_progress(page_number, {"status": "progress"})

        try:
            success = pipeline.process_page(
                page_id=page_id,
                input_pdf=input_pdf,
                page_number=page_number,
                ollama_host=ollama_host,
                ollama_model=ollama_model,
                temperature=temperature,
                resume=resume,
                system_prompt=system_prompt,
            )
            result = page_progress(pipeline.get_page_status(page_id))
            if success:
                logger.info(f"✓ {page_id} completed")
            else:
                logger.warning(f"✗ {page_id} failed")
        except KeyboardInterrupt:
            result = page_progress(pipeline.get_page_status(page_id))
            result.update(status="error", error="Interrupted")
            update_progress(page_number, result)
            raise
        except Exception as error:
            result = {"status": "error", "error": str(error)}
            logger.error(f"Exception processing {page_id}: {error}")
        update_progress(page_number, result)

    if parallel_count == 1:
        for number in pending:
            process_page(number)
    else:
        with ThreadPoolExecutor(max_workers=parallel_count, thread_name_prefix="sr1000") as pool:
            futures = []
            try:
                for number in pending:
                    futures.append(pool.submit(process_page, number))
                for future in as_completed(futures):
                    future.result()
            except BaseException:
                pipeline.stop_requested.set()
                for future in futures:
                    future.cancel()
                raise

    failed_pages = [number for number, page in pages.items() if page["status"] == "error"]
    completed_count = job_state["data"]["summary"]["complete"]

    # Summary
    logger.info("=" * 60)
    logger.info(f"Processing complete: {completed_count} completed, {len(failed_pages)} failed")

    if failed_pages:
        logger.warning(f"Failed pages: {failed_pages}")
        return 1
    if completed_count != len(pages):
        logger.error("SF005: Export requires all selected pages to be complete")
        return 1

    if not pipeline.export_job(input_pdf, start_page, end_page, job_state):
        return 1
    logger.info("All pages processed successfully!")
    return 0


class SR1000ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stdout)
        print(f"{self.prog}: error: {message}")
        self.exit(2)


def main():
    parser = SR1000ArgumentParser(
        description="SR1000: Translate PDF to Japanese using Ollama"
    )

    parser.add_argument(
        "--input-pdf",
        type=Path,
        required=True,
        help="Input PDF file",
    )
    parser.add_argument(
        "--working-dir",
        type=Path,
        required=True,
        help="Working directory for intermediate files and state",
    )
    parser.add_argument(
        "--ollama-host",
        type=str,
        default="http://localhost:11434",
        help="Ollama host URL (default: http://localhost:11434)",
    )
    parser.add_argument(
        "--ollama-model",
        type=str,
        default="qwen3:8b",
        help="Ollama model name (default: qwen3:8b)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.3,
        help="Translation temperature (default: 0.3)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from previous progress",
    )
    parser.add_argument(
        "--job-id",
        type=str,
        help="Existing job ID to use with --resume",
    )
    parser.add_argument(
        "--start-page",
        type=int,
        default=-1,
        help="Starting page number (1-indexed, -1 means 1, default: -1)",
    )
    parser.add_argument(
        "--end-page",
        type=int,
        default=-1,
        help="Ending page number (1-indexed, -1 means last page, default: -1)",
    )

    parser.add_argument(
        "--debug-ollama-cache",
        action="store_true",
        help="Log cache metrics for a Hello request with keep_alive=0 before translating",
    )

    parser.add_argument(
        "--parallel-count",
        type=int,
        default=1,
        help="Maximum concurrent page workers (default: 1; Ollama requests remain sequential)",
    )

    parser.add_argument(
        "--system-prompt",
        help="Extra context for each translation request (reuses the saved value on resume)",
    )

    args = parser.parse_args()
    if args.parallel_count < 1:
        parser.error("--parallel-count must be at least 1")
    if args.resume != (args.job_id is not None):
        parser.error("--resume and --job-id must be supplied together")

    exit_code = translate_pdf(
        input_pdf=args.input_pdf,
        working_dir=args.working_dir,
        ollama_host=args.ollama_host,
        ollama_model=args.ollama_model,
        temperature=args.temperature,
        resume=args.resume,
        job_id=args.job_id,
        start_page=args.start_page,
        end_page=args.end_page,
        debug_ollama_cache=args.debug_ollama_cache,
        parallel_count=args.parallel_count,
        system_prompt=args.system_prompt,
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
