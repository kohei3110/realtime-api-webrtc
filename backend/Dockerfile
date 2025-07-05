# ベースイメージとしてPython 3.13を使用
FROM python:3.13-slim

# 作業ディレクトリ設定
WORKDIR /app

# 必要なパッケージをインストール
RUN apt-get update && apt-get install -y curl ffmpeg && apt-get clean

# コードをコピー
COPY src/ src/
COPY pyproject.toml ./
COPY requirements.txt ./

# uvをインストール & 依存関係をインストール
RUN pip install --no-cache-dir uv && \
    uv venv /app/venv && \
    . /app/venv/bin/activate && \
    uv pip install --no-cache-dir -r requirements.txt

# 実行時の環境変数設定
ENV HOST=0.0.0.0
ENV PORT=8000
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/venv/bin:$PATH"
ENV PYTHONPATH="/app/src"

# ヘルスチェック設定
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1

# 8000番ポートを開放
EXPOSE 8000

# アプリケーションを実行
CMD ["python", "-m", "main"]
