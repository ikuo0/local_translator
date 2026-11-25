"""SR1001: Job progress monitoring UI via Flask."""

import os
from pathlib import Path

import yaml
from flask import Blueprint, Flask, jsonify, send_from_directory

from impl_translator.src.features.SR1001 import batch

bp = Blueprint("sr1001", __name__, url_prefix="/sr1001")


def get_working_dir() -> Path:
    return Path(os.environ.get("IMPL_TRANSLATOR_WORKING_DIR", "output/job")).resolve()


@bp.route("/")
def index():
    return send_from_directory(Path(__file__).parent.parent / "html", "index.html")


@bp.route("/api/job/<job_id>", defaults={"view": "status"})
@bp.route("/api/job/<job_id>/<any(pages,summary,metrics):view>")
def get_job_status(job_id: str, view: str = "status"):
    try:
        report = batch.load_report(get_working_dir(), job_id)
    except FileNotFoundError:
        return jsonify({"error": f"Job not found: {job_id}"}), 404
    except (ValueError, yaml.YAMLError) as error:
        return jsonify({"error": str(error)}), 400
    except OSError as error:
        return jsonify({"error": str(error)}), 500

    if view == "pages":
        return jsonify(job_id=job_id, pages=report["pages"])
    if view == "summary":
        return jsonify(job_id=job_id, sf005=report["sf005"], **report["summary"])
    if view == "metrics":
        return jsonify(job_id=job_id, metrics=batch.page_metrics(report))
    return jsonify(report)


def create_app():
    app = Flask(__name__)
    app.register_blueprint(bp)
    return app
