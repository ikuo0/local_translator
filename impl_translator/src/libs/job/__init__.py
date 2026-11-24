"""File-based job state management."""

import fcntl
import os
import re
import tempfile
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


def now() -> str:
    return datetime.now(UTC).isoformat()


def job_directory(working_dir: Path, job_id: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{32}", job_id):
        raise ValueError(f"Invalid job ID: {job_id}")
    return working_dir / job_id


def create(working_dir: Path, data: dict[str, Any] | None = None) -> str:
    working_dir.mkdir(parents=True, exist_ok=True)
    job_id = uuid.uuid4().hex
    directory = job_directory(working_dir, job_id)
    directory.mkdir()
    state = {
        "job_id": job_id,
        "created_at": now(),
        "updated_at": now(),
        "data": data or {},
    }
    save(working_dir, job_id, state)
    return job_id


def load(working_dir: Path, job_id: str) -> dict[str, Any]:
    path = job_directory(working_dir, job_id) / "job.yaml"
    with path.open(encoding="utf-8") as file:
        state = yaml.safe_load(file)
    if not isinstance(state, dict) or state.get("job_id") != job_id:
        raise ValueError(f"Invalid job state: {path}")
    return state


def save(working_dir: Path, job_id: str, state: dict[str, Any]) -> None:
    directory = job_directory(working_dir, job_id)
    state["updated_at"] = now()
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=directory, delete=False
        ) as file:
            temporary_path = Path(file.name)
            yaml.safe_dump(state, file, allow_unicode=True, sort_keys=False)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, directory / "job.yaml")
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def update(working_dir: Path, job_id: str, sub_key: str, data: Any) -> None:
    with lock(working_dir, job_id):
        state = load(working_dir, job_id)
        state["data"][sub_key] = data
        save(working_dir, job_id, state)


@contextmanager
def lock(working_dir: Path, job_id: str) -> Generator[None]:
    directory = job_directory(working_dir, job_id)
    if not directory.is_dir():
        raise FileNotFoundError(f"Job does not exist: {job_id}")
    with (directory / ".lock").open("a") as file:
        try:
            fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError(f"Job is already running: {job_id}") from error
        try:
            yield
        finally:
            fcntl.flock(file, fcntl.LOCK_UN)
