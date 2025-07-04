#!/bin/bash

# Docker環境でのバックエンドサービス起動スクリプト
echo "Building and starting Azure OpenAI Realtime API Proxy in Docker..."

# .envファイルが存在するか確認
if [ ! -f ".env" ]; then
  echo "Warning: .env file not found. Creating from sample..."
  cp .env.sample .env
  echo "Please update the .env file with your API credentials before continuing."
  exit 1
fi

# Dockerコンテナのビルドと起動
docker compose up --build -d

echo "Container started in detached mode. Use 'docker compose logs -f' to view logs."
