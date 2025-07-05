#!/bin/bash

# プロジェクト全体の起動スクリプト
echo "Starting Azure OpenAI Realtime API WebRTC Project..."

# .envファイルが存在するか確認
if [ ! -f ".env" ]; then
  echo "Warning: .env file not found. Creating from sample..."
  if [ -f "./backend/.env.sample" ]; then
    cp ./backend/.env.sample .env
    echo "Please update the .env file with your API credentials before continuing."
  else
    echo "Error: No .env.sample file found. Please create a .env file manually."
    exit 1
  fi
fi

# Dockerコンテナのビルドと起動
docker compose up --build

echo "Services started. Use Ctrl+C to stop."
