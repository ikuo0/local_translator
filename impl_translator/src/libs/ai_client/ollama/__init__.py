"""Ollama API client - main implementation."""

import json
import logging
from typing import Optional

import requests


logger = logging.getLogger("SR1000.ollama")
_TOKEN_REPEAT_ERROR = "prediction aborted, token repeat limit reached"
_TOKEN_REPEAT_RETRIES = 3


class OllamaClient:
    """Client for interacting with Ollama API."""

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "qwen3:8b",
        timeout: int = 600,
    ):
        """
        Initialize Ollama client.

        Args:
            host: Ollama server URL (default: http://localhost:11434)
            model: Model name (default: qwen3:8b)
            timeout: Connection and read timeout in seconds (default: 600)
        """
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._base_url = f"{self.host}/api"

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        keep_alive: str = "5m",
        stream: bool = False,
        think: Optional[bool] = None,
        log_cache_metrics: bool = False,
        repeat_penalty: float = 1.0,
    ) -> str:
        """
        Generate text using Ollama.

        Args:
            prompt: Input prompt text
            system: System prompt (optional)
            temperature: Temperature for generation (0.0-2.0)
            keep_alive: How long to keep model loaded (e.g., "5m", "1h")
            stream: Whether to stream response (default: False)
            think: Whether to enable thinking (None uses the model default)
            log_cache_metrics: Log cache metrics for a nonstreaming diagnostic request
            repeat_penalty: Initial repetition penalty. Increases by 0.1 per token-repeat retry.

        Returns:
            Generated text response

        Raises:
            requests.RequestException: If API request fails
            ValueError: If response is invalid
        """
        url = f"{self._base_url}/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "repeat_penalty": repeat_penalty,
            },
        }

        if system:
            payload["system"] = system

        if think is not None:
            payload["think"] = think

        if keep_alive:
            payload["keep_alive"] = keep_alive

        for attempt in range(_TOKEN_REPEAT_RETRIES + 1):
            response = requests.post(url, json=payload, timeout=self.timeout)
            try:
                response.raise_for_status()
                break
            except requests.HTTPError as exc:
                body = response.text.strip()
                if _TOKEN_REPEAT_ERROR in body and attempt < _TOKEN_REPEAT_RETRIES:
                    retry_number = attempt + 1
                    payload["options"] = {
                        "temperature": round(temperature + 0.1 * retry_number, 10),
                        "repeat_penalty": round(repeat_penalty + 0.1 * retry_number, 10),
                    }
                    logger.warning(
                        "Ollama token repeat limit reached, retry %d/%d "
                        "(temperature=%g, repeat_penalty=%g)",
                        retry_number,
                        _TOKEN_REPEAT_RETRIES,
                        payload["options"]["temperature"],
                        payload["options"]["repeat_penalty"],
                    )
                    continue
                if not body:
                    raise
                raise requests.HTTPError(
                    f"{exc} | Ollama response: {body}",
                    response=response,
                    request=exc.request,
                ) from exc

        if stream:
            # Collect all streamed responses
            full_response = ""
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    if "response" in data:
                        full_response += data["response"]
            return full_response
        else:
            data = response.json()
            if log_cache_metrics:
                cached_tokens = data.get("prompt_eval_cached_count")
                if type(cached_tokens) is not int or cached_tokens < 0:
                    cache_status = "unknown"
                else:
                    cache_status = "not_used" if cached_tokens == 0 else "used"
                logger.info(
                    "Ollama /api/generate model=%s keep_alive=%s prompt_eval_cached_count=%s "
                    "prompt_eval_count=%s cache=%s",
                    self.model, keep_alive, cached_tokens,
                    data.get("prompt_eval_count"), cache_status,
                )
            if "response" not in data:
                raise ValueError("Invalid response: missing 'response' field")
            return data["response"]

    def chat(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        temperature: float = 0.7,
        keep_alive: str = "5m",
    ) -> str:
        """
        Chat with Ollama using messages format.

        Args:
            messages: List of message dicts with 'role' and 'content'
                      (e.g., [{"role": "user", "content": "..."}])
            system: System prompt (optional)
            temperature: Temperature for generation (0.0-2.0)
            keep_alive: How long to keep model loaded (e.g., "5m", "1h")

        Returns:
            Generated text response

        Raises:
            requests.RequestException: If API request fails
            ValueError: If response is invalid
        """
        url = f"{self._base_url}/chat"

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        if system:
            payload["system"] = system

        if keep_alive:
            payload["keep_alive"] = keep_alive

        response = requests.post(
            url,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()

        data = response.json()
        if "message" not in data or "content" not in data["message"]:
            raise ValueError("Invalid response: missing 'message.content' field")
        return data["message"]["content"]

    def unload_model(self) -> None:
        """
        Unload model from memory to free GPU resources.

        This sends an empty request with keep_alive=0 to unload the model.
        """
        url = f"{self._base_url}/generate"
        payload = {
            "model": self.model,
            "keep_alive": 0,
        }
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            # Unload is best-effort; don't fail if it doesn't work
            print(f"Warning: Failed to unload model: {e}")

    def get_model_info(self) -> dict:
        """
        Get information about the model.

        Returns:
            Dictionary with model information

        Raises:
            requests.RequestException: If API request fails
        """
        url = f"{self._base_url}/show"
        payload = {"name": self.model}

        response = requests.post(
            url,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def list_models(self) -> list[dict]:
        """
        List all available models.

        Returns:
            List of model information dictionaries

        Raises:
            requests.RequestException: If API request fails
        """
        url = f"{self._base_url}/tags"

        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        return data.get("models", [])
