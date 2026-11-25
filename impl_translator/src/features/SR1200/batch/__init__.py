"""Shared SR1200 conversation processing."""

import requests

DEFAULT_OLLAMA_HOST = "http://ollama:11434"
DEFAULT_OLLAMA_MODEL = "qwen3:8b"
DEFAULT_CONTEXT_TOKENS = 32768


def _chat(host: str, payload: dict) -> dict:
    response = requests.post(f"{host.rstrip('/')}/api/chat", json=payload, timeout=600)
    response.raise_for_status()
    try:
        result = response.json()
    except ValueError as error:
        raise RuntimeError("Ollama の応答形式が不正です。") from error
    if not isinstance(result, dict) or result.get("error"):
        raise RuntimeError("Ollama から有効な応答が返りませんでした。")
    return result


def _history_messages(history: list | None) -> list[dict]:
    if history is None:
        return []
    if not isinstance(history, list) or len(history) % 2:
        raise ValueError("履歴には質問と回答の組を指定してください。")

    messages = []
    for index, item in enumerate(history):
        role = ("user", "assistant")[index % 2]
        if not isinstance(item, dict) or item.get("role") != role:
            raise ValueError("履歴には質問と回答を交互に指定してください。")
        content = item.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("履歴の各発言には文章が必要です。")
        messages.append({"role": role, "content": content})
    return messages


def ask(
    text: str,
    *,
    keep_history: bool = False,
    history: list | None = None,
    context_tokens: int = DEFAULT_CONTEXT_TOKENS,
    ollama_host: str = DEFAULT_OLLAMA_HOST,
    model: str = DEFAULT_OLLAMA_MODEL,
) -> dict:
    """Answer a question, optionally carrying recent user/assistant turns forward."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("質問を入力してください。")
    if type(keep_history) is not bool:
        raise ValueError("keep_history には true または false を指定してください。")
    if type(context_tokens) is not int or context_tokens < 128:
        raise ValueError("コンテキスト上限は128以上の整数で指定してください。")

    previous = []
    if keep_history:
        previous = _history_messages(history)
    question = {"role": "user", "content": text}
    payload = {"model": model, "stream": False, "think": False, "keep_alive": "0"}

    prompt_tokens = None
    dropped_turns = 0
    if keep_history:
        payload.update(keep_alive="30m", truncate=False, shift=False)
        reserve = min(1024, context_tokens // 4)
        while True:
            payload["messages"] = previous + [question]
            try:
                probe = _chat(ollama_host, {
                    **payload, "options": {"num_ctx": context_tokens, "num_predict": 1},
                })
            except requests.HTTPError as error:
                response = error.response
                details = response.text.lower()
                if response.status_code != 413 and not (
                    "context length" in details and ("exceed" in details or "too long" in details)
                ):
                    raise
            else:
                prompt_tokens = probe.get("prompt_eval_count")
                if type(prompt_tokens) is not int or prompt_tokens <= 0:
                    raise RuntimeError("Ollama からプロンプトのトークン数を取得できませんでした。")
                if prompt_tokens <= context_tokens - reserve:
                    break

            if not previous:
                raise ValueError(f"質問が長すぎます。コンテキスト上限は {context_tokens:,} トークンです。")
            previous = previous[2:]
            dropped_turns += 1

        payload["options"] = {
            "num_ctx": context_tokens,
            "num_predict": context_tokens - prompt_tokens,
        }
    else:
        payload["messages"] = [question]

    result = _chat(ollama_host, payload)
    message = result.get("message")
    answer = message.get("content") if isinstance(message, dict) else None
    if not isinstance(answer, str) or not answer.strip():
        raise RuntimeError("Ollama から回答が返りませんでした。")

    updated_history = []
    if keep_history:
        updated_history = payload["messages"] + [{"role": "assistant", "content": answer}]
    return {
        "answer": answer,
        "history": updated_history,
        "prompt_tokens": result.get("prompt_eval_count", prompt_tokens),
        "context_tokens": context_tokens if keep_history else None,
        "dropped_turns": dropped_turns,
    }
