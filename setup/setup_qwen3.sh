#!/usr/bin/env bash

# Windows11 ホスト、devcontainer開発の場合を想定している
# 本スクリプトはWSL側で実行する

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

if ! command -v docker >/dev/null 2>&1; then
    echo "Error: docker is not installed or is not on PATH." >&2
    exit 1
fi

echo "Starting the Ollama service..."
docker compose up -d ollama

echo "Downloading Qwen3 8B from the Ollama Library..."
docker compose exec ollama ollama pull qwen3:8b

echo "Running a translation test..."
docker compose exec -T ollama ollama run qwen3:8b \
    "Translate into Japanese: The surface consists of multiple polygons."

echo "Checking the running model..."
docker compose exec ollama ollama ps

echo "Setup complete. The model is stored in the Docker ollama_data volume."
