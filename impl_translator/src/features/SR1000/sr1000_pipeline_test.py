"""
Standalone test for SR1000 Pipeline
"""

import json
import logging
import tempfile
from pathlib import Path

from impl_translator.src.features.SR1000.sr1000_pipeline import SR1000Pipeline


def setup_test_logger():
    """Setup test logger."""
    logger = logging.getLogger("SR1000Test")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if logger.handlers:
        logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(handler)

    return logger


def test_pipeline_initialization():
    """Test pipeline initialization."""
    print("\n" + "=" * 70)
    print("TEST 1: Pipeline Initialization")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        logger = setup_test_logger()
        pipeline = SR1000Pipeline(working_dir=Path(tmpdir), logger=logger)

        assert pipeline.working_dir.exists()
        print("✓ Pipeline initialized successfully")

        # Test state management
        page_id = "page_000001"
        state = pipeline._load_page_state(page_id)
        assert state["page_id"] == page_id
        assert state["status"] == "pending"
        assert all(step["status"] == "pending" for step in state["steps"].values())
        print("✓ Initial state created correctly")

        # Test save and load
        state["status"] = "sf001"
        pipeline._save_page_state(page_id, state)

        loaded_state = pipeline._load_page_state(page_id)
        assert loaded_state["status"] == "sf001"
        print("✓ State save/load works correctly")


def test_pipeline_state_management():
    """Test state management."""
    print("\n" + "=" * 70)
    print("TEST 2: State Management")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        logger = setup_test_logger()
        pipeline = SR1000Pipeline(working_dir=Path(tmpdir), logger=logger)

        # Create multiple pages
        for i in range(1, 4):
            page_id = f"page_{i:06d}"
            state = pipeline._load_page_state(page_id)
            state["status"] = "pending"
            pipeline._save_page_state(page_id, state)

        # List all states
        states = pipeline.list_page_states()
        assert len(states) == 3
        print(f"✓ Created 3 page states")

        # Check status
        for i in range(1, 4):
            page_id = f"page_{i:06d}"
            status = pipeline.get_page_status(page_id)
            assert status["page_id"] == page_id
            assert status["status"] == "pending"

        print("✓ State listing works correctly")


def test_step_tracking():
    """Test step tracking."""
    print("\n" + "=" * 70)
    print("TEST 3: Step Tracking")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        logger = setup_test_logger()
        pipeline = SR1000Pipeline(working_dir=Path(tmpdir), logger=logger)

        page_id = "page_000001"
        state = pipeline._load_page_state(page_id)

        # Simulate step progress
        steps = ["sf001", "sf002", "sf003", "sf004"]
        for step in steps:
            state["steps"][step]["status"] = "completed"
            state["steps"][step]["output"] = f"/path/to/{step}_output.txt"
            pipeline._save_page_state(page_id, state)

            loaded = pipeline._load_page_state(page_id)
            assert loaded["steps"][step]["status"] == "completed"
            assert loaded["steps"][step]["output"] == f"/path/to/{step}_output.txt"
            print(f"✓ Step {step} tracked correctly")


def test_state_persistence():
    """Test state persistence across sessions."""
    print("\n" + "=" * 70)
    print("TEST 4: State Persistence")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Session 1
        logger = setup_test_logger()
        pipeline1 = SR1000Pipeline(working_dir=tmpdir, logger=logger)

        page_id = "page_000001"
        state = pipeline1._load_page_state(page_id)
        state["status"] = "sf002"
        state["steps"]["sf001"]["status"] = "completed"
        state["steps"]["sf001"]["output"] = "/path/to/sf001.html"
        pipeline1._save_page_state(page_id, state)

        print("✓ Session 1: Saved state with SF001 completed")

        # Session 2 (new instance, same directory)
        pipeline2 = SR1000Pipeline(working_dir=tmpdir, logger=logger, job_id=pipeline1.job_id)
        loaded_state = pipeline2._load_page_state(page_id)

        assert loaded_state["status"] == "sf002"
        assert loaded_state["steps"]["sf001"]["status"] == "completed"
        assert loaded_state["steps"]["sf001"]["output"] == "/path/to/sf001.html"

        print("✓ Session 2: Loaded state correctly")
        print("✓ State persists across sessions")


def test_pipeline_structure():
    """Test pipeline directory structure."""
    print("\n" + "=" * 70)
    print("TEST 5: Directory Structure")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        logger = setup_test_logger()
        pipeline = SR1000Pipeline(working_dir=tmpdir, logger=logger)

        # Create some states
        for i in range(1, 3):
            page_id = f"page_{i:06d}"
            pipeline._load_page_state(page_id)
            pipeline._save_page_state(page_id, {})

        assert pipeline.job_dir == tmpdir / pipeline.job_id
        assert (pipeline.job_dir / "job.yaml").is_file()
        assert pipeline._get_phase_dir("page_000001", "SF001_to_html") == (
            pipeline.job_dir / "SF001_to_html" / "page_000001"
        )
        assert SR1000Pipeline(working_dir=tmpdir).job_id != pipeline.job_id

        # Check structure under job_dir
        assert (pipeline.job_dir / "states").is_dir()
        state_files = list((pipeline.job_dir / "states").glob("*.json"))
        assert len(state_files) == 2

        print(f"✓ Working directory structure created")
        print(f"✓ States directory contains {len(state_files)} state files")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("SR1000 PIPELINE - UNIT TESTS")
    print("=" * 70)

    try:
        test_pipeline_initialization()
        test_pipeline_state_management()
        test_step_tracking()
        test_state_persistence()
        test_pipeline_structure()

        print("\n" + "=" * 70)
        print("ALL TESTS PASSED ✓")
        print("=" * 70)
        print()
        print("SR1000 Pipeline is ready for use!")
        print()
        print("To translate a PDF:")
        print("  python -m impl_translator.src.features.SR1000.sr1000_main \\")
        print("    --input-pdf input.pdf \\")
        print("    --working-dir ./work \\")
        print("    --ollama-host http://localhost:11434 \\")
        print("    --ollama-model qwen3:8b")

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
