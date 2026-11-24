"""SR1001: Job progress monitoring UI via Flask."""

import os
from flask import Blueprint, send_from_directory, jsonify
from pathlib import Path

from impl_translator.src.features.SR1001 import summary

bp = Blueprint("sr1001", __name__, url_prefix="/sr1001")


def get_working_dir() -> Path:
    """Get working directory from environment or default."""
    working_dir = os.environ.get("IMPL_TRANSLATOR_WORKING_DIR", "output/job")
    return Path(working_dir).resolve()


def get_html_dir() -> Path:
    """Get SR1001 html directory."""
    return Path(__file__).parent.parent / "html"


@bp.route("/")
def index():
    """Job progress monitoring dashboard."""
    html_dir = get_html_dir()
    return send_from_directory(html_dir, "index.html")


@bp.route("/api/job/<job_id>")
def get_job_status(job_id: str):
    """Get job status as JSON."""
    
    working_dir = get_working_dir()
    try:
        # Load job state without lock (read-only, safe while job is running)
        state = summary.load_job_state(working_dir, job_id, include_timings=False)
        data = state["data"]
        metrics = summary.calculate_summary(state)
        status = data.get("status")
        if status is None:
            if metrics.running_pages:
                status = "running"
            elif metrics.pending_pages:
                status = "pending"
            elif metrics.failed_pages or metrics.interrupted_pages:
                status = "failed"
            elif metrics.total_pages:
                status = "completed"

        return jsonify({
            "job_id": job_id,
            "status": status,
            "total_pages": metrics.total_pages,
            "completed": metrics.completed_pages,
            "failed": metrics.failed_pages,
            "interrupted": metrics.interrupted_pages,
            "running": metrics.running_pages,
            "progress_percent": metrics.progress_percent,
            "created_at": state.get("created_at"),
            "updated_at": state.get("updated_at"),
            "elapsed_seconds": data.get("elapsed_seconds", 0),
            "log_file": data.get("log_file"),
        })
    except FileNotFoundError:
        return jsonify({"error": f"Job not found: {job_id}"}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as error:
        return jsonify({"error": str(error)}), 500


@bp.route("/api/job/<job_id>/pages")
def get_job_pages(job_id: str):
    """Get detailed page status."""
    
    working_dir = get_working_dir()
    try:
        # Load job state without lock (read-only, safe while job is running)
        state = summary.load_job_state(working_dir, job_id, include_timings=False)
        
        pages = state["data"].get("pages", {})
        return jsonify({
            "job_id": job_id,
            "pages": pages,
        })
    except FileNotFoundError:
        return jsonify({"error": f"Job not found: {job_id}"}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as error:
        return jsonify({"error": str(error)}), 500


@bp.route("/api/job/<job_id>/summary")
def get_job_summary(job_id: str):
    """Get job summary statistics."""
    
    working_dir = get_working_dir()
    try:
        # Load job state without lock (read-only, safe while job is running)
        state = summary.load_job_state(working_dir, job_id)
        
        metrics = summary.calculate_summary(state)
        return jsonify({
            "job_id": job_id,
            **summary.format_summary_json(metrics),
        })
    except FileNotFoundError:
        return jsonify({"error": f"Job not found: {job_id}"}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as error:
        return jsonify({"error": str(error)}), 500


@bp.route("/api/job/<job_id>/metrics")
def get_job_metrics(job_id: str):
    """Get page-by-page metrics."""
    from dataclasses import asdict
    
    working_dir = get_working_dir()
    try:
        # Load job state without lock (read-only, safe while job is running)
        state = summary.load_job_state(working_dir, job_id)
        
        metrics = summary.calculate_page_metrics(state)
        return jsonify({
            "job_id": job_id,
            "metrics": [asdict(m) for m in metrics],
        })
    except FileNotFoundError:
        return jsonify({"error": f"Job not found: {job_id}"}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as error:
        return jsonify({"error": str(error)}), 500


def create_app():
    """Create and configure Flask app."""
    from flask import Flask
    
    app = Flask(__name__)
    app.register_blueprint(bp)
    return app

