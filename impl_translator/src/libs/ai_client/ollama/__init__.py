"""Ollama API client - main implementation."""

import json
from typing import Optional

import requests


class OllamaClient:
    """Client for interacting with Ollama API."""

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "qwen3:8b",
        timeout: int = 300,
    ):
        """
        Initialize Ollama client.

        Args:
            host: Ollama server URL (default: http://localhost:11434)
            model: Model name (default: qwen3:8b)
            timeout: Request timeout in seconds (default: 300)
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
    ) -> str:
        """
        Generate text using Ollama.

        Args:
            prompt: Input prompt text
            system: System prompt (optional)
            temperature: Temperature for generation (0.0-2.0)
            keep_alive: How long to keep model loaded (e.g., "5m", "1h")
            stream: Whether to stream response (default: False)

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
