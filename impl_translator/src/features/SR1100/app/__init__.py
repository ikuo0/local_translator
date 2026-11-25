"""HTTP API for SR1100 translation."""

from flask import Blueprint, current_app, jsonify, request
from requests import RequestException, Timeout

from impl_translator.src.features.SR1100 import batch

bp = Blueprint("sr1100", __name__, url_prefix="/sr1100/api")


@bp.post("/translate")
def translate():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="JSON オブジェクトを送信してください。"), 400

    try:
        translation = batch.translate_text(
            payload.get("text"),
            payload.get("direction"),
            ollama_host=current_app.config.get("SR1100_OLLAMA_HOST", batch.DEFAULT_OLLAMA_HOST),
            model=current_app.config.get("SR1100_OLLAMA_MODEL", batch.DEFAULT_OLLAMA_MODEL),
        )
    except Timeout:
        current_app.logger.exception("SR1100 Ollama request timed out")
        return jsonify(error="Ollama の応答がタイムアウトしました。"), 504
    except (RuntimeError, RequestException):
        current_app.logger.exception("SR1100 Ollama translation failed")
        return jsonify(error="Ollama で翻訳を実行できませんでした。"), 502
    except ValueError as error:
        return jsonify(error=str(error)), 400

    return jsonify(translation=translation)
