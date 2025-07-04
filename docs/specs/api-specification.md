# API 仕様書

## 1. 概要

### 1.1 API 概要
本APIは、React WebアプリケーションとAzure OpenAI Realtime APIを仲介するプロキシサーバーです。フロントエンドからのリクエストを安全にAzure OpenAI Realtime APIにプロキシし、WebRTCによるリアルタイム音声通信とユーザー発話音声データの自動保存機能を提供します。

### 1.2 ベースURL
```
http://localhost:8000
```

### 1.3 認証方式
- **プロキシ認証**: APIキーはバックエンドで管理（フロントエンドには露出しない）
- **セッション認証**: プロキシが生成したephemeral keyによる認証
- **セキュア設計**: Azure APIキーをフロントエンドから隠蔽

### 1.4 レスポンス形式
- **Content-Type**: `application/json`
- **文字エンコーディング**: UTF-8
- **日時形式**: ISO 8601 (例: `2024-01-01T00:00:00Z`)

## 2. プロキシ API

### 2.1 セッション管理プロキシ

#### 2.1.1 セッション作成プロキシ

**エンドポイント**
```
POST /sessions
```

**説明**
フロントエンドからのリクエストをAzure OpenAI Realtime Sessions APIにプロキシし、安全にephemeral keyを取得します。

**リクエスト**
```json
{
  "model": "gpt-4o-realtime-preview",
  "voice": "alloy"
}
```

**フィールド説明**
- `model` (string, required): 使用するAIモデル名
  - 利用可能値: `gpt-4o-realtime-preview`
- `voice` (string, required): AI音声の種類
  - 利用可能値: `alloy`, `shimmer`, `nova`, `echo`, `fable`, `onyx`

**レスポンス**
```json
{
  "id": "azure_session_id",
  "client_secret": {
    "value": "ephemeral_key_value"
  },
  "created_at": "2024-01-01T00:00:00Z",
  "expires_at": "2024-01-01T01:00:00Z"
}
```

**フィールド説明**
- `id` (string): Azure OpenAIから取得したセッション識別子
- `client_secret.value` (string): Azure OpenAIから取得したephemeral key
- `created_at` (string): セッション作成日時
- `expires_at` (string): セッション有効期限

**ステータスコード**
- `201`: セッション作成成功
- `400`: リクエスト形式エラー
- `429`: レート制限超過
- `500`: Azure OpenAI APIエラー
- `503`: プロキシサーバーエラー

#### 2.1.2 WebRTC SDP プロキシ

**エンドポイント**
```
POST /realtime?model={model}
```

**説明**
フロントエンドからのSDP OfferをAzure OpenAI WebRTC エンドポイントにプロキシします。

**クエリパラメータ**
- `model` (string, required): 使用するAIモデル名

**ヘッダー**
- `Authorization: Bearer {ephemeral_key}` (required)
- `Content-Type: application/sdp` (required)

**リクエストボディ（SDP Offer）**
```
v=0
o=- 1234567890 1234567890 IN IP4 127.0.0.1
s=session
c=IN IP4 127.0.0.1
t=0 0
m=audio 9 UDP/TLS/RTP/SAVPF 111
a=rtpmap:111 opus/48000/2
a=fmtp:111 minptime=10;useinbandfec=1
...
```

**レスポンス（SDP Answer）**
```
v=0
o=- 9876543210 9876543210 IN IP4 127.0.0.1
s=session
c=IN IP4 127.0.0.1
t=0 0
m=audio 9 UDP/TLS/RTP/SAVPF 111
a=rtpmap:111 opus/48000/2
a=fmtp:111 minptime=10;useinbandfec=1
...
```

**プロキシ処理フロー**
1. フロントエンドからSDP Offer受信
2. ephemeral key検証
3. Azure OpenAI WebRTC エンドポイントに転送
4. Azure OpenAIからSDP Answer受信
5. フロントエンドにレスポンス返却

**ステータスコード**
- `200`: SDP交換成功
- `400`: 不正なSDP形式
- `401`: 認証エラー（ephemeral key無効）
- `422`: SDP処理エラー
- `500`: Azure OpenAI APIエラー
- `503`: プロキシサーバーエラー
### 2.2 データチャネルプロキシ（WebRTC）

#### 2.2.1 データチャネル通信の透過的プロキシ

**説明**
WebRTC接続確立後、フロントエンドとAzure OpenAI間のデータチャネル通信を透過的にプロキシします。プロキシサーバーは通信内容を監視し、音声データの自動保存機能を提供します。

**通信フロー**
```
Frontend ←→ Proxy Server ←→ Azure OpenAI
```

**プロキシ機能**
1. **メッセージ転送**: フロントエンド ↔ Azure OpenAI間の双方向メッセージ転送
2. **音声監視**: ユーザー発話イベントの検知と音声データ保存
3. **ログ記録**: 通信ログの構造化記録
4. **エラーハンドリング**: 接続エラー時の適切なエラー処理

**対象メッセージタイプ**
- `session.update`: セッション設定更新
- `input_audio_buffer.speech_started`: ユーザー発話開始
- `input_audio_buffer.speech_stopped`: ユーザー発話終了
- `response.audio.delta`: AI音声レスポンス
- `response.function_call_arguments.done`: 関数呼び出し完了
- `conversation.item.create`: 会話アイテム作成

**音声データ自動保存**
- **トリガー**: `input_audio_buffer.speech_stopped` イベント
- **保存先**: Azure Blob Storage
- **形式**: Opus/WebM（WebRTC標準）
- **メタデータ**: 発話時間、セッションID、音声品質情報

## 3. 音声データ管理 API

### 3.1 自動保存された音声ファイル管理

#### 3.1.1 セッション音声ファイル一覧

**エンドポイント**
```
GET /audio/session/{session_id}
```

**説明**
指定セッションで自動保存された音声ファイルの一覧を取得します。

**パスパラメータ**
- `session_id` (string, required): Azure OpenAIセッション識別子

**クエリパラメータ**
- `audio_type` (string, optional): 音声タイプでフィルタ
  - 利用可能値: `user_speech`, `ai_response`
- `limit` (number, optional): 取得件数制限（デフォルト: 50, 最大: 200）
- `offset` (number, optional): オフセット（デフォルト: 0）

**レスポンス**
```json
{
  "session_id": "azure_session_id",
  "summary": {
    "total_count": 15,
    "total_duration": 450.5,
    "total_size_bytes": 14400000,
    "user_speech_count": 10,
    "ai_response_count": 5,
    "average_duration": 30.03
  },
  "audio_files": [
    {
      "audio_id": "uuid",
      "audio_type": "user_speech",
      "blob_url": "https://storage.blob.core.windows.net/...",
      "sas_url": "https://storage.blob.core.windows.net/...?sv=...",
      "sas_expires_at": "2024-01-01T01:00:00Z",
      "size_bytes": 960000,
      "metadata": {
        "duration": 30.0,
        "format": "opus",
        "sample_rate": 48000,
        "channels": 1,
        "speaker": "user",
        "timestamp_start": "2024-01-01T00:00:00.000Z",
        "timestamp_end": "2024-01-01T00:00:30.000Z",
        "language": "ja-JP"
      },
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "pagination": {
    "limit": 50,
    "offset": 0,
    "has_more": false
  }
}
```

**ステータスコード**
- `200`: 取得成功
- `404`: セッション未発見
- `500`: サーバーエラー

#### 3.1.2 音声ファイル取得

**エンドポイント**
```
GET /audio/{audio_id}
```

**説明**
指定された音声ファイルの詳細情報とアクセス用URLを取得します。

**パスパラメータ**
- `audio_id` (string, required): 音声ファイル識別子

**クエリパラメータ**
- `include_sas` (boolean, optional): SAS URL生成フラグ（デフォルト: true）
- `sas_expiry_hours` (number, optional): SAS URL有効期限（時間、1-24、デフォルト: 1）

**レスポンス**
```json
{
  "audio_id": "uuid",
  "session_id": "azure_session_id",
  "audio_type": "user_speech",
  "blob_url": "https://storage.blob.core.windows.net/...",
  "sas_url": "https://storage.blob.core.windows.net/...?sv=2023-01-03&se=...",
  "sas_expires_at": "2024-01-01T01:00:00Z",
  "size_bytes": 960000,
  "metadata": {
    "duration": 30.0,
    "format": "opus",
    "sample_rate": 48000,
    "channels": 1,
    "speaker": "user",
    "timestamp_start": "2024-01-01T00:00:00.000Z",
    "timestamp_end": "2024-01-01T00:00:30.000Z",
    "language": "ja-JP"
  },
  "created_at": "2024-01-01T00:00:00Z",
  "last_accessed": "2024-01-01T00:05:00Z"
}
```

**ステータスコード**
- `200`: 取得成功
- `404`: 音声ファイル未発見
- `500`: サーバーエラー

## 4. ヘルスチェック・監視 API

### 4.1 システム状態

#### 4.1.1 ヘルスチェック

**エンドポイント**
```
GET /health
```

**説明**
プロキシサーバーとAzure OpenAI接続の健全性をチェックします。

**レスポンス**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "version": "1.0.0",
  "uptime_seconds": 86400,
  "proxy_services": {
    "azure_openai_sessions": {
      "status": "healthy",
      "response_time_ms": 120,
      "last_check": "2024-01-01T00:00:00Z"
    },
    "azure_openai_webrtc": {
      "status": "healthy",
      "response_time_ms": 85,
      "last_check": "2024-01-01T00:00:00Z"
    },
    "blob_storage": {
      "status": "healthy",
      "response_time_ms": 45,
      "last_check": "2024-01-01T00:00:00Z"
    }
  },
  "metrics": {
    "active_proxy_sessions": 12,
    "total_sessions_today": 89,
    "audio_files_saved_today": 345,
    "average_proxy_latency_ms": 15
  }
}
```

**ステータスコード**
- `200`: システム正常
- `503`: システム異常

## 5. エラーレスポンス仕様

### 5.1 共通エラー形式

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {
      "azure_error": "Azure OpenAI specific error details",
      "timestamp": "2024-01-01T00:00:00Z",
      "request_id": "uuid"
    }
  }
}
```

### 5.2 プロキシエラーコード一覧

#### 5.2.1 Azure OpenAI プロキシエラー (502, 503)
- `AZURE_SESSIONS_API_ERROR`: Azure OpenAI Sessions API呼び出しエラー
- `AZURE_WEBRTC_API_ERROR`: Azure OpenAI WebRTC API呼び出しエラー
- `AZURE_API_TIMEOUT`: Azure OpenAI API タイムアウト
- `AZURE_API_RATE_LIMITED`: Azure OpenAI API レート制限

#### 5.2.2 プロキシサーバーエラー (500)
- `PROXY_INTERNAL_ERROR`: プロキシサーバー内部エラー
- `SDP_PROXY_ERROR`: SDP プロキシ処理エラー
- `DATACHANNEL_PROXY_ERROR`: データチャネルプロキシエラー
- `AUDIO_SAVE_ERROR`: 音声データ保存エラー

#### 5.2.3 認証・リクエストエラー (400, 401)
- `INVALID_EPHEMERAL_KEY`: 不正なephemeral key
- `MISSING_MODEL_PARAMETER`: modelパラメータ不足
- `INVALID_SDP_FORMAT`: SDP形式エラー

#### 3.1.2 音声ファイル取得

**エンドポイント**
```
GET /audio/{audio_id}
```

**パスパラメータ**
- `audio_id` (string, required): 音声ファイル識別子

**クエリパラメータ**
- `include_sas` (boolean, optional): SAS URL生成フラグ（デフォルト: true）
- `sas_expiry_hours` (number, optional): SAS URL有効期限（時間、1-24、デフォルト: 1）

**レスポンス**
```json
{
  "audio_id": "uuid",
  "session_id": "uuid",
  "audio_type": "user_speech",
  "blob_url": "https://storage.blob.core.windows.net/...",
  "sas_url": "https://storage.blob.core.windows.net/...?sv=2023-01-03&se=...",
  "sas_expires_at": "2024-01-01T01:00:00Z",
  "size_bytes": 1440000,
  "metadata": {
    "duration": 30.5,
    "format": "wav",
    "sample_rate": 48000,
    "channels": 1,
    "speaker": "user",
    "timestamp_start": "2024-01-01T00:00:00.000Z",
    "timestamp_end": "2024-01-01T00:00:30.500Z",
    "confidence_score": 0.95,
    "language": "ja-JP",
    "transcription": "こんにちは、今日はいい天気ですね。"
  },
  "created_at": "2024-01-01T00:00:00Z",
  "last_accessed": "2024-01-01T00:05:00Z"
}
```

**ステータスコード**
- `200`: 取得成功
- `404`: 音声ファイル未発見
- `500`: サーバーエラー

#### 3.1.3 セッション音声ファイル一覧

**エンドポイント**
```
GET /audio/session/{session_id}
```

**パスパラメータ**
- `session_id` (string, required): セッション識別子

**クエリパラメータ**
- `audio_type` (string, optional): 音声タイプでフィルタ
- `speaker` (string, optional): 話者でフィルタ
- `start_time` (string, optional): 開始時間でフィルタ（ISO 8601）
- `end_time` (string, optional): 終了時間でフィルタ（ISO 8601）
- `min_duration` (number, optional): 最小時間でフィルタ（秒）
- `max_duration` (number, optional): 最大時間でフィルタ（秒）
- `limit` (number, optional): 取得件数制限（デフォルト: 50, 最大: 200）
- `offset` (number, optional): オフセット（デフォルト: 0）
- `sort_by` (string, optional): ソート順
  - 利用可能値: `created_at`, `duration`, `timestamp_start`
- `sort_order` (string, optional): ソート方向
  - 利用可能値: `asc`, `desc`（デフォルト: `desc`）

**レスポンス**
```json
{
  "session_id": "uuid",
  "summary": {
    "total_count": 25,
    "total_duration": 1800.5,
    "total_size_bytes": 57600000,
    "user_speech_count": 15,
    "ai_response_count": 10,
    "average_duration": 72.02
  },
  "audio_files": [
    {
      "audio_id": "uuid",
      "audio_type": "user_speech",
      "blob_url": "https://storage.blob.core.windows.net/...",
      "sas_url": "https://storage.blob.core.windows.net/...?sv=...",
      "sas_expires_at": "2024-01-01T01:00:00Z",
      "size_bytes": 1440000,
      "metadata": {
        "duration": 30.5,
        "format": "wav",
        "speaker": "user",
        "timestamp_start": "2024-01-01T00:00:00.000Z",
        "timestamp_end": "2024-01-01T00:00:30.500Z",
        "language": "ja-JP"
      },
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "pagination": {
    "limit": 50,
    "offset": 0,
    "has_more": false
  }
}
```

**ステータスコード**
- `200`: 取得成功
- `400`: クエリパラメータエラー
- `404`: セッション未発見
- `500`: サーバーエラー

#### 3.1.4 音声ファイル削除

**エンドポイント**
```
DELETE /audio/{audio_id}
```

**パスパラメータ**
- `audio_id` (string, required): 音声ファイル識別子

**ヘッダー**
- `Authorization: Bearer {ephemeral_key}` (optional)

**レスポンス**
```json
{
  "audio_id": "uuid",
  "deletion_status": "completed",
  "deleted_at": "2024-01-01T00:30:00Z"
}
```

**ステータスコード**
- `200`: 削除成功
- `404`: 音声ファイル未発見
- `500`: サーバーエラー

#### 3.1.5 セッション音声ファイル一括削除

**エンドポイント**
```
DELETE /audio/session/{session_id}
```

**パスパラメータ**
- `session_id` (string, required): セッション識別子

**ヘッダー**
- `Authorization: Bearer {ephemeral_key}` (required)

**クエリパラメータ**
- `audio_type` (string, optional): 削除対象の音声タイプ指定
- `confirm` (boolean, required): 削除確認フラグ（trueが必須）

**レスポンス**
```json
{
  "session_id": "uuid",
  "deletion_status": "completed",
  "deleted_count": 25,
  "deleted_size_bytes": 57600000,
  "failed_deletions": [],
  "deleted_at": "2024-01-01T00:30:00Z"
}
```

**フィールド説明**
- `failed_deletions` (array): 削除に失敗した音声ファイルのリスト

**ステータスコード**
- `200`: 削除成功
- `400`: confirmパラメータ未指定
- `401`: 認証エラー
- `404`: セッション未発見
- `500`: サーバーエラー

### 3.2 音声データ分析

#### 3.2.1 音声ファイル統計

**エンドポイント**
```
GET /audio/stats
```

**クエリパラメータ**
- `session_id` (string, optional): 特定セッションの統計
- `user_id` (string, optional): 特定ユーザーの統計
- `start_date` (string, optional): 集計開始日（YYYY-MM-DD）
- `end_date` (string, optional): 集計終了日（YYYY-MM-DD）
- `group_by` (string, optional): グループ化単位
  - 利用可能値: `day`, `week`, `month`, `session`, `user`

**レスポンス**
```json
{
  "period": {
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "group_by": "day"
  },
  "summary": {
    "total_files": 1250,
    "total_duration": 86400.0,
    "total_size_bytes": 2764800000,
    "unique_sessions": 150,
    "unique_users": 75,
    "average_file_duration": 69.12,
    "average_session_duration": 576.0
  },
  "breakdown": [
    {
      "date": "2024-01-01",
      "file_count": 45,
      "total_duration": 3240.5,
      "total_size_bytes": 103596800,
      "session_count": 8,
      "user_count": 6
    }
  ],
  "audio_type_breakdown": {
    "user_speech": {
      "count": 750,
      "total_duration": 51840.0,
      "percentage": 60.0
    },
    "ai_response": {
      "count": 500,
      "total_duration": 34560.0,
      "percentage": 40.0
    }
  }
}
```

**ステータスコード**
- `200`: 取得成功
- `400`: パラメータエラー
- `500`: サーバーエラー

## 4. ヘルスチェック・監視 API

### 4.1 システム状態

#### 4.1.1 ヘルスチェック

**エンドポイント**
```
GET /health
```

**レスポンス**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "version": "1.0.0",
  "uptime_seconds": 86400,
  "services": {
    "azure_openai": {
      "status": "healthy",
      "response_time_ms": 120,
      "last_check": "2024-01-01T00:00:00Z"
    },
    "blob_storage": {
      "status": "healthy",
      "response_time_ms": 45,
      "last_check": "2024-01-01T00:00:00Z"
    },
    "database": {
      "status": "healthy",
      "response_time_ms": 12,
      "last_check": "2024-01-01T00:00:00Z"
    }
  },
  "metrics": {
    "active_sessions": 25,
    "total_sessions_today": 150,
    "audio_files_processed_today": 1250,
    "storage_usage_percentage": 45.2,
    "average_response_time_ms": 95
  }
}
```

**ステータスコード**
- `200`: システム正常
- `503`: システム異常

#### 4.1.2 詳細メトリクス

**エンドポイント**
```
GET /metrics
```

**クエリパラメータ**
- `timeframe` (string, optional): 集計期間
  - 利用可能値: `1h`, `24h`, `7d`, `30d`（デフォルト: `1h`）

**レスポンス**
```json
{
  "timeframe": "1h",
  "timestamp": "2024-01-01T00:00:00Z",
  "system_metrics": {
    "cpu_usage_percentage": 45.2,
    "memory_usage_percentage": 67.8,
    "disk_usage_percentage": 34.1,
    "network_io_mbps": 125.6
  },
  "application_metrics": {
    "active_sessions": 25,
    "sessions_created": 45,
    "sessions_terminated": 38,
    "webrtc_connections_established": 42,
    "webrtc_connection_failures": 3,
    "audio_files_uploaded": 125,
    "audio_upload_failures": 2,
    "average_session_duration": 420.5,
    "average_audio_processing_time_ms": 250
  },
  "azure_metrics": {
    "openai_api_calls": 1250,
    "openai_api_errors": 15,
    "openai_average_response_time_ms": 180,
    "blob_storage_operations": 250,
    "blob_storage_errors": 2,
    "storage_bandwidth_mbps": 45.2
  },
  "error_metrics": {
    "total_errors": 20,
    "error_rate_percentage": 1.6,
    "error_breakdown": {
      "authentication_errors": 5,
      "azure_api_errors": 10,
      "storage_errors": 3,
      "validation_errors": 2
    }
  }
}
```

**ステータスコード**
- `200`: 取得成功
- `500`: サーバーエラー

## 5. エラーレスポンス仕様

### 5.1 共通エラー形式

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {
      "field": "specific error details",
      "timestamp": "2024-01-01T00:00:00Z",
      "request_id": "uuid"
    }
  }
}
```

### 5.2 エラーコード一覧

#### 5.2.1 認証・認可エラー (401, 403)
- `INVALID_EPHEMERAL_KEY`: 不正なephemeral key
- `EXPIRED_SESSION`: セッション期限切れ
- `AUTHENTICATION_REQUIRED`: 認証が必要
- `INSUFFICIENT_PERMISSIONS`: 権限不足

#### 5.2.2 リクエストエラー (400, 422)
- `INVALID_REQUEST_FORMAT`: リクエスト形式エラー
- `MISSING_REQUIRED_FIELD`: 必須フィールド不足
- `INVALID_FIELD_VALUE`: フィールド値不正
- `INVALID_AUDIO_FORMAT`: 音声形式不正
- `AUDIO_TOO_LARGE`: 音声ファイルサイズ超過
- `INVALID_SDP_FORMAT`: SDP形式エラー

#### 5.2.3 リソースエラー (404, 409)
- `SESSION_NOT_FOUND`: セッション未発見
- `AUDIO_FILE_NOT_FOUND`: 音声ファイル未発見
- `RESOURCE_CONFLICT`: リソース競合

#### 5.2.4 外部サービスエラー (502, 503)
- `AZURE_OPENAI_ERROR`: Azure OpenAI APIエラー
- `AZURE_STORAGE_ERROR`: Azure Storageエラー
- `WEBRTC_CONNECTION_FAILED`: WebRTC接続エラー
- `EXTERNAL_SERVICE_UNAVAILABLE`: 外部サービス利用不可

#### 5.2.5 サーバーエラー (500)
- `INTERNAL_SERVER_ERROR`: 内部サーバーエラー
- `AUDIO_PROCESSING_ERROR`: 音声処理エラー
- `DATABASE_ERROR`: データベースエラー

#### 5.2.6 制限エラー (429, 507)
- `RATE_LIMIT_EXCEEDED`: レート制限超過
- `STORAGE_QUOTA_EXCEEDED`: ストレージ容量超過
- `CONCURRENT_SESSION_LIMIT`: 同時セッション数制限

### 5.3 エラーレスポンス例

#### 5.3.1 認証エラー
```json
{
  "error": {
    "code": "INVALID_EPHEMERAL_KEY",
    "message": "The provided ephemeral key is invalid or has expired",
    "details": {
      "session_id": "uuid",
      "provided_key": "key_prefix...",
      "timestamp": "2024-01-01T00:00:00Z",
      "request_id": "req_12345"
    }
  }
}
```

#### 5.3.2 バリデーションエラー
```json
{
  "error": {
    "code": "INVALID_REQUEST_FORMAT",
    "message": "Request validation failed",
    "details": {
      "field_errors": [
        {
          "field": "model",
          "message": "model is required",
          "provided_value": null
        },
        {
          "field": "voice",
          "message": "voice must be one of: alloy, shimmer, nova, echo, fable, onyx",
          "provided_value": "invalid_voice"
        }
      ],
      "timestamp": "2024-01-01T00:00:00Z",
      "request_id": "req_12346"
    }
  }
}
```

#### 5.3.3 外部サービスエラー
```json
{
  "error": {
    "code": "AZURE_OPENAI_ERROR",
    "message": "Failed to communicate with Azure OpenAI service",
    "details": {
      "azure_error_code": "RateLimitExceeded",
      "azure_error_message": "Rate limit exceeded. Please retry after 60 seconds",
      "retry_after_seconds": 60,
      "session_id": "uuid",
      "timestamp": "2024-01-01T00:00:00Z",
      "request_id": "req_12347"
    }
  }
}
```

## 6. API制限事項

### 6.1 レート制限

#### 6.1.1 セッション作成
- **制限**: 100回/分/IP
- **ヘッダー**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

#### 6.1.2 音声アップロード
- **制限**: 1000回/時間/セッション
- **ファイルサイズ**: 最大10MB/ファイル

#### 6.1.3 WebSocket接続
- **制限**: 同時接続数1000/サーバー
- **メッセージ**: 10,000回/分/セッション

### 6.2 データ制限

#### 6.2.1 ストレージ制限
- **保存期間**: 30日間（設定可能）
- **総容量**: 100GB/アカウント
- **ファイル数**: 100,000ファイル/アカウント

#### 6.2.2 セッション制限
- **有効期間**: 1時間
- **同時セッション**: 10セッション/ユーザー
- **最大継続時間**: 4時間/セッション

## 7. SDK・クライアントライブラリ

### 7.1 JavaScript/TypeScript SDK

```javascript
import { RealtimeAPIClient } from '@azure-openai/realtime-client';

const client = new RealtimeAPIClient({
  apiUrl: 'https://localhost:8000/api/v1',
  apiKey: 'your-api-key' // Optional for client-side
});

// セッション作成
const session = await client.createSession({
  user_id: 'user123',
  model: 'gpt-4o-realtime-preview',
  voice: 'alloy',
  instructions: 'あなたは優秀なアシスタントです。'
});

// WebRTC接続
const webrtc = await client.connectWebRTC(session.session_id, session.ephemeral_key);

// 音声ファイル取得
const audioFiles = await client.getSessionAudioFiles(session.session_id);
```

### 7.2 Python SDK

```python
from azure_openai_realtime import RealtimeAPIClient

client = RealtimeAPIClient(
    api_url="https://localhost:8000/api/v1",
    api_key="your-api-key"
)

# セッション作成
session = await client.create_session(
    user_id="user123",
    model="gpt-4o-realtime-preview",
    voice="alloy",
    instructions="あなたは優秀なアシスタントです。"
)

# WebSocket接続
async with client.connect_websocket(session.session_id, session.ephemeral_key) as ws:
    async for message in ws:
        print(f"Received: {message}")

# 音声ファイル一覧
audio_files = await client.get_session_audio_files(session.session_id)
```

## 8. WebRTC実装ガイド

### 8.1 フロントエンド実装例

```javascript
// セッション作成
const response = await fetch('/api/v1/realtime/sessions', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    user_id: 'user123',
    model: 'gpt-4o-realtime-preview',
    voice: 'alloy',
    instructions: 'あなたは優秀なAIアシスタントです。',
    modalities: ['text', 'audio']
  })
});

const session = await response.json();

// WebRTC接続設定
const peerConnection = new RTCPeerConnection();

// マイクロフォン取得
const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
const audioTrack = stream.getAudioTracks()[0];
peerConnection.addTrack(audioTrack);

// データチャネル作成
const dataChannel = peerConnection.createDataChannel('realtime-channel');

// SDP Offer作成・送信
const offer = await peerConnection.createOffer();
await peerConnection.setLocalDescription(offer);

const sdpResponse = await fetch(`/api/v1/realtime/webrtc/${session.session_id}/offer`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${session.ephemeral_key}`,
    'Content-Type': 'application/sdp'
  },
  body: offer.sdp
});

const answerSdp = await sdpResponse.text();
await peerConnection.setRemoteDescription({
  type: 'answer',
  sdp: answerSdp
});

// WebSocket接続
const ws = new WebSocket(`${session.webrtc_endpoint}?ephemeral_key=${session.ephemeral_key}`);

ws.onmessage = (event) => {
  const realtimeEvent = JSON.parse(event.data);
  console.log('Received:', realtimeEvent);
};

// セッション更新
dataChannel.addEventListener('open', () => {
  const sessionUpdate = {
    type: 'session.update',
    session: {
      instructions: 'あなたは優秀なAIアシスタントです。',
      modalities: ['text', 'audio']
    }
  };
  ws.send(JSON.stringify(sessionUpdate));
});
```

### 8.2 エラーハンドリング例

```javascript
// WebRTC接続エラーハンドリング
peerConnection.onconnectionstatechange = () => {
  const state = peerConnection.connectionState;
  
  switch (state) {
    case 'connected':
      console.log('WebRTC connected successfully');
      break;
    case 'disconnected':
      console.log('WebRTC disconnected');
      // 再接続ロジック
      break;
    case 'failed':
      console.error('WebRTC connection failed');
      // エラー処理とフォールバック
      break;
  }
};

// WebSocketエラーハンドリング
ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = (event) => {
  if (event.code !== 1000) {
    console.error('WebSocket closed unexpectedly:', event.code, event.reason);
    // 再接続ロジック
  }
};
```

---

**API バージョン**: v1  
**最終更新**: 2025年7月4日  
**ドキュメントバージョン**: 1.0.0
