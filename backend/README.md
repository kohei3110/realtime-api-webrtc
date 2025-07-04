# Azure OpenAI Realtime API プロキシサーバー

Azure OpenAI Realtime APIを安全にプロキシするサーバー。WebRTCによるリアルタイム音声通信とセッション管理をサポート。

## 環境構築

### 前提条件
- Python 3.13+
- uv (高速Pythonパッケージマネージャー)

### uvのインストール
まだuvをインストールしていない場合は、以下のコマンドでインストールできます：

```bash
# pipを使用してuvをインストール
pip install uv

# または、公式の方法（Linux/macOS）
curl -sSf https://raw.githubusercontent.com/astral-sh/uv/main/install.sh | bash

# Windows (PowerShell)
# irm https://raw.githubusercontent.com/astral-sh/uv/main/install.ps1 | iex
```

### 環境セットアップ

```bash
# リポジトリのクローン
git clone https://github.com/your-username/azure-openai-realtime-api-proxy.git
cd azure-openai-realtime-api-proxy/backend

# 仮想環境の作成と依存関係のインストール
uv venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 依存関係のインストール
uv pip install -e ".[dev]"
```

## 環境変数設定

`.env`ファイルを作成し、以下の環境変数を設定します：

```bash
# Azure OpenAI API 設定
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_VERSION=2024-10-01-preview

# サーバー設定
HOST=0.0.0.0
PORT=8000
CORS_ORIGINS=http://localhost:3000

# ログレベル
LOG_LEVEL=INFO
```

## アプリケーションの起動

```bash
# 開発環境での起動
cd src
python main.py

# または、uvicornを直接使用
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Dockerを使用した起動
docker compose up --build
```

## コンテナ化

このプロジェクトはDockerコンテナとして実行することができます。コンテナ化により環境依存のない一貫した実行環境が提供され、デプロイが容易になります。

### コンテナの準備

```bash
# イメージのビルド
docker compose build
```

### コンテナの起動方法

```bash
# 対話モードでコンテナを起動（ログが表示される）
docker compose up

# バックグラウンドで実行
docker compose up -d

# 提供されているスクリプトを使用して起動
./run_docker.sh
```

### コンテナの操作

```bash
# コンテナの状態確認
docker compose ps

# ログの確認
docker compose logs -f

# コンテナの停止
docker compose down

# コンテナの再起動
docker compose restart

# コンテナとイメージを全て削除（クリーンアップ）
docker compose down --rmi all --volumes --remove-orphans
```

### コンテナ内のシェルにアクセス

```bash
# コンテナ内でコマンドを実行
docker compose exec api bash

# または、新しいシェルを開始
docker compose run --rm api bash
```

### 複数環境構成

開発環境と本番環境などで異なる設定を使用する場合：

```bash
# 開発環境設定
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# 本番環境設定
docker compose -f docker-compose.yml -f docker-compose.prod.yml up
```

## APIエンドポイント

### ヘルスチェック
- **GET /health**: サービスの稼働状態を確認

### セッション作成プロキシ
- **POST /sessions**: Azure OpenAI Sessionsプロキシエンドポイント

### WebRTC SDP プロキシ
- **POST /realtime**: WebRTC SDP交換プロキシエンドポイント

## 開発ツール

```bash
# テスト実行
uv run pytest

# カバレッジレポート付きテスト
uv run pytest --cov=src

# コードフォーマット
uv run black src tests
uv run isort src tests

# リンター実行
uv run ruff src tests
```
