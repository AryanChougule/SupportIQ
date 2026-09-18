#!/usr/bin/env bash

set -euo pipefail

# Always run from the project directory
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

IMAGE_NAME="supportiq:latest"
CONTAINER_NAME="supportiq"
ENV_FILE="$PROJECT_DIR/.env"
ENV_EXAMPLE="$PROJECT_DIR/.env.example"

echo "Starting SupportIQ deployment..."

# Check Docker
if ! command -v docker >/dev/null 2>&1; then
    echo "Error: Docker is not installed or is not available in PATH."
    exit 1
fi

# Create .env automatically if it does not exist
if [ ! -f "$ENV_FILE" ]; then
    if [ ! -f "$ENV_EXAMPLE" ]; then
        echo "Error: .env.example was not found."
        exit 1
    fi

    cp "$ENV_EXAMPLE" "$ENV_FILE"
    echo "Created .env from .env.example."
fi

# Read the Gemini API key from .env
GEMINI_API_KEY_VALUE="$(
    sed -n 's/^GEMINI_API_KEY=//p' "$ENV_FILE" | head -n 1
)"

# Ask for the API key if the placeholder is still present
case "$GEMINI_API_KEY_VALUE" in
    ""|"your_gemini_api_key_here"|"gemini_api_key"|"your_key_here")
        echo
        echo "A Gemini API key is required for natural-language queries."
        echo "Get one from: https://aistudio.google.com/app/apikey"
        echo

        read -r -s -p "Enter your Gemini API key: " GEMINI_API_KEY_VALUE
        echo

        if [ -z "$GEMINI_API_KEY_VALUE" ]; then
            echo "Error: Gemini API key cannot be empty."
            exit 1
        fi
        ;;
esac

echo
echo "Building SupportIQ Docker image..."

docker build \
    -t "$IMAGE_NAME" \
    "$PROJECT_DIR"

echo "Removing any previous SupportIQ container..."

docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

echo "Starting SupportIQ..."

docker run \
    --name "$CONTAINER_NAME" \
    --env-file "$ENV_FILE" \
    --env "GEMINI_API_KEY=$GEMINI_API_KEY_VALUE" \
    -p 8000:8000 \
    "$IMAGE_NAME"