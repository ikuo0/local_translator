"""HTTP API for SR1200."""

import os

from flask import Blueprint, current_app, jsonify, request
from requests import RequestException, Timeout

from impl_translator.src.features.SR1200 import batch

bp = Blueprint("sr1200", __name__, url_prefix="/sr1200/api")


@bp.post("/ask")
def ask():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="JSON オブジェクトを送信してください。"), 400

    try:
        context_tokens = int(current_app.config.get(
            "SR1200_CONTEXT_TOKENS", os.environ.get("SR1200_CONTEXT_TOKENS", batch.DEFAULT_CONTEXT_TOKENS),
        ))
        if context_tokens < 128:
            raise ValueError("SR1200_CONTEXT_TOKENS must be at least 128")
    except (TypeError, ValueError):
        current_app.logger.exception("Invalid SR1200 context limit")
        return jsonify(error="SR1200 のコンテキスト設定が不正です。"), 500

    try:
        result = batch.ask(
            payload.get("text"),
            keep_history=payload.get("keep_history", False),
            history=payload.get("history"),
            context_tokens=context_tokens,
            ollama_host=current_app.config.get("SR1200_OLLAMA_HOST", batch.DEFAULT_OLLAMA_HOST),
            model=current_app.config.get("SR1200_OLLAMA_MODEL", batch.DEFAULT_OLLAMA_MODEL),
        )
    except Timeout:
        current_app.logger.exception("SR1200 Ollama request timed out")
        return jsonify(error="Ollama の応答がタイムアウトしました。"), 504
    except (RuntimeError, RequestException):
        current_app.logger.exception("SR1200 Ollama request failed")
        return jsonify(error="Ollama で回答を生成できませんでした。"), 502
    except ValueError as error:
        return jsonify(error=str(error)), 400

    return jsonify(result)
