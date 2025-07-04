#!/bin/bash

# 開発環境用の起動スクリプト
echo "Starting Azure OpenAI Realtime API Proxy in development mode..."

# 仮想環境の確認とアクティベート
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment with uv..."
  uv venv
fi

source .venv/bin/activate

# 依存関係のインストール
echo "Installing dependencies with uv..."
uv pip install -e ".[dev]"

# アプリケーションの起動
echo "Starting FastAPI application..."
cd src
python main.py
