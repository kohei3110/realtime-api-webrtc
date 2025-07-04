# バックエンドアプリケーション仕様書

## 1. システム概要

### 1.1 アーキテクチャ概要
本バックエンドアプリケーションは、React Webアプリケーションと Azure OpenAI Realtime API を仲介する Python FastAPI アプリケーションです。WebRTC接続のシグナリングサーバーとして機能し、リアルタイム音声通信を実現します。

### 1.2 主要機能
- WebRTC シグナリングサーバー
- Azure OpenAI Realtime API プロキシ
- **ユーザー発話音声データの Azure Blob Storage への永続化**
- **音声データの自動分割・メタデータ管理**
- リアルタイム音声ストリーミング処理
- セッション管理とユーザー認証

### 1.3 技術スタック
- **ランタイム**: Python 3.13
- **フレームワーク**: Python FastAPI
- **WebSocket**: FastAPI WebSocket support
- **WebRTC**: aiortc (Python WebRTC library)
- **Azure SDK**: azure-storage-blob, azure-openai
- **コンテナ**: Docker
- **非同期処理**: asyncio, uvloop
- **パッケージ管理**: uv (Python package manager)

## 2. システム要件

### 2.1 ランタイム要件
- **Python**: 3.13以上
- **OS**: Linux (推奨: Ubuntu 22.04 LTS)
- **メモリ**: 最小2GB、推奨4GB以上
- **CPU**: 最小2コア、推奨4コア以上

### 2.2 機能要件
- リアルタイム双方向音声通信
- WebRTC P2P接続のシグナリング
- Azure OpenAI APIとの統合
- ユーザー発話音声データの自動保存
- 音声データの時系列管理
- セッション管理
- エラーハンドリングとログ記録

### 2.3 非機能要件
- **可用性**: 99.9%
- **レスポンス時間**: WebRTC シグナリング < 100ms
- **スループット**: 同時接続数 1000セッション
- **セキュリティ**: HTTPS/WSS、認証・認可
- **スケーラビリティ**: 水平スケーリング対応

## 3. API 仕様

### 3.1 WebRTC シグナリング API（Azure OpenAI Realtime API プロキシ）

#### 3.1.1 セッション初期化
**POST** `/api/v1/realtime/sessions`
```json
{
  "user_id": "string",
  "model": "gpt-4o-realtime-preview",
  "voice": "alloy",
  "instructions": "あなたはとても優秀なAIアシスタントです。",
  "modalities": ["text", "audio"],
  "tools": [
    {
      "type": "function",
      "name": "function_name",
      "description": "Function description",
      "parameters": {...}
    }
  ]
}
```

**Response**:
```json
{
  "session_id": "uuid",
  "ephemeral_key": "string",
  "webrtc_endpoint": "wss://localhost:8000/api/v1/realtime/webrtc/{session_id}",
  "created_at": "2024-01-01T00:00:00Z",
  "expires_at": "2024-01-01T01:00:00Z"
}
```

#### 3.1.2 WebRTC SDP 交換エンドポイント
**POST** `/api/v1/realtime/webrtc/{session_id}/offer`
```
Content-Type: application/sdp
Authorization: Bearer {ephemeral_key}

v=0
o=- 1234567890 1234567890 IN IP4 127.0.0.1
s=session
...
```

**Response**:
```
Content-Type: application/sdp

v=0
o=- 9876543210 9876543210 IN IP4 127.0.0.1
s=session
...
```

#### 3.1.3 WebSocket プロキシエンドポイント
```
wss://localhost:8000/api/v1/realtime/webrtc/{session_id}
```

**接続時認証**:
- QueryパラメータまたはWebSocketヘッダーでephemeral_keyを送信
- セッションの有効性とキーの妥当性を検証

**メッセージ型定義**:
```python
class RealtimeMessage(BaseModel):
    type: str  # Azure OpenAI Realtime API イベントタイプ
    payload: dict  # イベント固有のデータ
    timestamp: datetime
    session_id: str
    direction: str  # "client_to_azure", "azure_to_client"
```

**プロキシメッセージフロー**:
1. クライアント → バックエンド → Azure OpenAI（WebSocket経由）
2. データチャネルメッセージの透過的転送
3. 音声データの自動保存（ユーザー発話時）
4. Azure OpenAI → バックエンド → クライアント

#### 3.1.4 セッション管理 API

**GET** `/api/v1/realtime/sessions/{session_id}`
```json
{
  "session_id": "uuid",
  "status": "active|inactive|terminated|expired",
  "created_at": "2024-01-01T00:00:00Z",
  "expires_at": "2024-01-01T01:00:00Z",
  "user_id": "string",
  "model": "gpt-4o-realtime-preview",
  "voice": "alloy",
  "connection_state": "connected|disconnected|connecting|failed",
  "audio_files_count": 5,
  "total_duration": 120.5,
  "last_activity": "2024-01-01T00:05:00Z"
}
```

**DELETE** `/api/v1/realtime/sessions/{session_id}`
```json
{
  "session_id": "uuid",
  "status": "terminated",
  "terminated_at": "2024-01-01T00:00:00Z",
  "cleanup_completed": true,
  "final_stats": {
    "total_duration": 1800.5,
    "audio_files_saved": 25,
    "total_audio_size": 15728640
  }
}
```

**GET** `/api/v1/realtime/sessions`
```json
{
  "sessions": [
    {
      "session_id": "uuid",
      "status": "active",
      "created_at": "2024-01-01T00:00:00Z",
      "user_id": "string",
      "model": "gpt-4o-realtime-preview",
      "voice": "alloy",
      "connection_state": "connected",
      "audio_files_count": 5,
      "total_duration": 120.5
    }
  ],
  "pagination": {
    "total_count": 1,
    "active_count": 1,
    "limit": 20,
    "offset": 0,
    "has_more": false
  }
}
```

### 3.2 Azure OpenAI Realtime API プロキシ

#### 3.2.1 プロキシアーキテクチャ
バックエンドは以下の役割でAzure OpenAI Realtime APIをプロキシします：

1. **認証プロキシ**: APIキーを安全に管理し、ephemeral keyを生成
2. **WebRTCプロキシ**: SDP交換とWebSocket通信の中継
3. **音声データ監視**: リアルタイム音声ストリームの自動保存
4. **セッション管理**: ユーザーセッションの状態管理とクリーンアップ

#### 3.2.2 Azure Sessions API プロキシ
**内部実装**: Azure OpenAI `/realtime/sessions` エンドポイントへのプロキシ

```python
class AzureOpenAISessionProxy:
    async def create_session(self, request: SessionCreateRequest) -> SessionResponse:
        """Azure OpenAI Sessions APIへのプロキシ呼び出し"""
        azure_request = {
            "model": request.model,
            "voice": request.voice,
            "instructions": request.instructions,
            "modalities": request.modalities,
            "tools": request.tools
        }
        
        response = await self.azure_client.post(
            f"{self.azure_endpoint}/realtime/sessions",
            headers={
                "api-key": self.api_key,
                "Content-Type": "application/json"
            },
            json=azure_request
        )
        
        azure_session = response.json()
        
        # 内部セッション管理
        session = await self.session_manager.create_session(
            session_id=azure_session["id"],
            ephemeral_key=azure_session["client_secret"]["value"],
            user_id=request.user_id,
            model=request.model,
            voice=request.voice
        )
        
        return SessionResponse(
            session_id=session.session_id,
            ephemeral_key=session.ephemeral_key,
            webrtc_endpoint=f"wss://{self.host}/api/v1/realtime/webrtc/{session.session_id}",
            created_at=session.created_at,
            expires_at=session.expires_at
        )
```

#### 3.2.3 WebRTC SDP プロキシ
```python
class WebRTCSDPProxy:
    async def proxy_sdp_offer(self, session_id: str, offer_sdp: str, ephemeral_key: str) -> str:
        """クライアントのSDP OfferをAzure OpenAIに転送"""
        session = await self.session_manager.get_session(session_id)
        
        if not session or session.ephemeral_key != ephemeral_key:
            raise HTTPException(status_code=401, detail="Invalid session or ephemeral key")
        
        # Azure OpenAI WebRTC エンドポイントにSDP Offerを送信
        response = await self.azure_client.post(
            f"{self.azure_webrtc_endpoint}?model={session.model}",
            headers={
                "Authorization": f"Bearer {ephemeral_key}",
                "Content-Type": "application/sdp"
            },
            data=offer_sdp
        )
        
        answer_sdp = await response.text()
        
        # セッション状態更新
        await self.session_manager.update_connection_state(session_id, "connecting")
        
        return answer_sdp
```

#### 3.2.4 リアルタイムメッセージプロキシ
```python
class RealtimeMessageProxy:
    async def handle_websocket_connection(self, websocket: WebSocket, session_id: str):
        """WebSocketを通じてクライアントとAzure OpenAI間のメッセージをプロキシ"""
        session = await self.session_manager.get_session(session_id)
        
        # Azure OpenAI WebSocketに接続
        azure_ws = await self.connect_to_azure_websocket(session)
        
        # 双方向メッセージ転送
        await asyncio.gather(
            self.client_to_azure_proxy(websocket, azure_ws, session_id),
            self.azure_to_client_proxy(azure_ws, websocket, session_id)
        )
    
    async def client_to_azure_proxy(self, client_ws: WebSocket, azure_ws, session_id: str):
        """クライアント → Azure OpenAI メッセージ転送"""
        async for message in client_ws.iter_text():
            # メッセージログ記録
            await self.log_message(session_id, "client_to_azure", message)
            
            # Azure OpenAIに転送
            await azure_ws.send(message)
    
    async def azure_to_client_proxy(self, azure_ws, client_ws: WebSocket, session_id: str):
        """Azure OpenAI → クライアント メッセージ転送"""
        async for message in azure_ws:
            # メッセージログ記録
            await self.log_message(session_id, "azure_to_client", message)
            
            # 音声データ検出・保存
            await self.process_audio_message(message, session_id)
            
            # クライアントに転送
            await client_ws.send_text(message)
```

### 3.3 音声ストレージ API

#### 3.3.1 音声アップロード
**POST** `/api/v1/audio/upload`
```json
{
  "session_id": "string",
  "audio_data": "base64_encoded_audio",
  "audio_type": "user_speech|ai_response|full_conversation",
  "metadata": {
    "duration": 30.5,
    "format": "wav",
    "sample_rate": 48000,
    "channels": 1,
    "speaker": "user|assistant",
    "timestamp_start": "2024-01-01T00:00:00.000Z",
    "timestamp_end": "2024-01-01T00:00:30.500Z",
    "confidence_score": 0.95,
    "language": "ja-JP",
    "transcription": "こんにちは、今日はいい天気ですね。"
  }
}
```

**Response**:
```json
{
  "audio_id": "uuid",
  "blob_url": "https://storage.blob.core.windows.net/audio-records/user-speech/2024/01/01/{session_id}/{audio_id}.wav",
  "upload_status": "completed",
  "size_bytes": 1440000,
  "sas_url": "https://storage.blob.core.windows.net/audio-records/...?sv=2023-01-03&se=2024-01-01T01%3A00%3A00Z&sr=b&sp=r&sig=...",
  "sas_expires_at": "2024-01-01T01:00:00Z",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### 3.3.2 音声検索・取得
**GET** `/api/v1/audio/{audio_id}`
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

**GET** `/api/v1/audio/session/{session_id}`
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

#### 3.3.3 音声データ削除
**DELETE** `/api/v1/audio/{audio_id}`

**Response**:
```json
{
  "audio_id": "uuid",
  "deletion_status": "completed",
  "deleted_at": "2024-01-01T00:30:00Z"
}
```

**DELETE** `/api/v1/audio/session/{session_id}`

**Response**:
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

#### 3.3.4 音声データ統計・分析
**GET** `/api/v1/audio/stats`

**クエリパラメータ**:
- `session_id` (string, optional): 特定セッションの統計
- `user_id` (string, optional): 特定ユーザーの統計
- `start_date` (string, optional): 集計開始日（YYYY-MM-DD）
- `end_date` (string, optional): 集計終了日（YYYY-MM-DD）
- `group_by` (string, optional): グループ化単位
  - 利用可能値: `day`, `week`, `month`, `session`, `user`

**Response**:
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

### 3.4 ヘルスチェック・監視 API

#### 3.4.1 システム状態
**GET** `/api/v1/health`

**Response**:
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

#### 3.4.2 詳細メトリクス
**GET** `/api/v1/metrics`

**クエリパラメータ**:
- `timeframe` (string, optional): 集計期間
  - 利用可能値: `1h`, `24h`, `7d`, `30d`（デフォルト: `1h`）

**Response**:
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

## 4. WebRTC プロキシ実装詳細

### 4.1 WebRTCプロキシアーキテクチャ
```python
class WebRTCProxyManager:
    def __init__(self):
        self.session_manager = SessionManager()
        self.audio_processor = AudioProcessor()
        self.azure_client = AzureOpenAIClient()
        
    async def create_proxy_session(self, user_id: str, config: SessionConfig) -> ProxySession:
        """プロキシセッションの作成"""
        # Azure OpenAI セッション作成
        azure_session = await self.azure_client.create_session(config)
        
        # 内部セッション管理
        proxy_session = ProxySession(
            session_id=azure_session.id,
            user_id=user_id,
            ephemeral_key=azure_session.client_secret.value,
            azure_session_id=azure_session.id,
            model=config.model,
            voice=config.voice,
            status="created"
        )
        
        await self.session_manager.store_session(proxy_session)
        return proxy_session
        
    async def proxy_webrtc_connection(self, session_id: str, client_offer: str) -> str:
        """WebRTC接続のプロキシ処理"""
        session = await self.session_manager.get_session(session_id)
        
        # Azure OpenAI WebRTCエンドポイントに転送
        azure_answer = await self.azure_client.exchange_sdp(
            session.ephemeral_key,
            session.model,
            client_offer
        )
        
        # セッション状態更新
        await self.session_manager.update_status(session_id, "webrtc_connected")
        
        return azure_answer
```

### 4.2 データチャネルプロキシ
```python
class DataChannelProxy:
    async def setup_proxy_connection(self, session_id: str, client_ws: WebSocket):
        """データチャネルのプロキシ接続セットアップ"""
        session = await self.session_manager.get_session(session_id)
        
        # Azure OpenAI WebSocketへの接続確立
        azure_ws_url = f"{self.azure_webrtc_endpoint}/realtime"
        azure_ws = await websockets.connect(
            azure_ws_url,
            extra_headers={
                "Authorization": f"Bearer {session.ephemeral_key}",
                "Model": session.model
            }
        )
        
        # 双方向プロキシ開始
        await asyncio.gather(
            self.proxy_client_to_azure(client_ws, azure_ws, session_id),
            self.proxy_azure_to_client(azure_ws, client_ws, session_id),
            return_exceptions=True
        )
    
    async def proxy_client_to_azure(self, client_ws: WebSocket, azure_ws, session_id: str):
        """クライアント → Azure OpenAI プロキシ"""
        try:
            async for message in client_ws.iter_text():
                realtime_event = json.loads(message)
                
                # メッセージログ
                logger.info("client_message_proxied", 
                           session_id=session_id,
                           event_type=realtime_event.get("type"),
                           timestamp=datetime.utcnow())
                
                # Azure OpenAIに転送
                await azure_ws.send(message)
                
        except WebSocketDisconnect:
            logger.info("client_disconnected", session_id=session_id)
            await azure_ws.close()
    
    async def proxy_azure_to_client(self, azure_ws, client_ws: WebSocket, session_id: str):
        """Azure OpenAI → クライアント プロキシ"""
        try:
            async for message in azure_ws:
                realtime_event = json.loads(message)
                
                # 音声データ処理（ユーザー発話の自動保存）
                await self.process_realtime_event(realtime_event, session_id)
                
                # メッセージログ
                logger.info("azure_message_proxied",
                           session_id=session_id,
                           event_type=realtime_event.get("type"),
                           timestamp=datetime.utcnow())
                
                # クライアントに転送
                await client_ws.send_text(message)
                
        except Exception as e:
            logger.error("azure_proxy_error", session_id=session_id, error=str(e))
            await client_ws.close()
```

### 4.3 リアルタイム音声処理
```python
class RealtimeAudioProcessor:
    def __init__(self):
        self.storage_client = AudioBlobStorageClient()
        self.vad = VoiceActivityDetector()
        
    async def process_realtime_event(self, event: dict, session_id: str):
        """Azure OpenAI Realtimeイベントの処理"""
        event_type = event.get("type")
        
        if event_type == "input_audio_buffer.speech_started":
            # ユーザー発話開始
            await self.start_speech_recording(session_id, event)
            
        elif event_type == "input_audio_buffer.speech_stopped":
            # ユーザー発話終了 - 音声データ保存
            await self.finalize_speech_recording(session_id, event)
            
        elif event_type == "response.audio.delta":
            # AI応答音声 - オプションで保存
            await self.process_ai_audio_response(session_id, event)
            
        elif event_type == "conversation.item.created":
            # 会話アイテム作成時のメタデータ記録
            await self.log_conversation_item(session_id, event)
    
    async def start_speech_recording(self, session_id: str, event: dict):
        """ユーザー発話記録開始"""
        speech_session = {
            "session_id": session_id,
            "start_time": datetime.utcnow(),
            "audio_chunks": [],
            "item_id": event.get("item_id")
        }
        
        # メモリに記録セッション保存
        self.active_recordings[session_id] = speech_session
        
        logger.info("speech_recording_started", session_id=session_id)
    
    async def finalize_speech_recording(self, session_id: str, event: dict):
        """ユーザー発話記録終了・保存"""
        if session_id not in self.active_recordings:
            return
            
        recording = self.active_recordings[session_id]
        end_time = datetime.utcnow()
        duration = (end_time - recording["start_time"]).total_seconds()
        
        # 最小発話時間チェック
        if duration < 0.5:
            del self.active_recordings[session_id]
            return
        
        # 音声データをAzure OpenAIから取得
        # （input_audio_bufferイベントには実際の音声データは含まれないため、
        #  別途WebRTCストリームから抽出する必要があります）
        audio_data = await self.extract_audio_from_buffer(session_id, recording)
        
        if audio_data:
            # Azure Blob Storageに保存
            metadata = {
                "duration": duration,
                "format": "opus",  # WebRTCではOpusが標準
                "sample_rate": 48000,
                "channels": 1,
                "speaker": "user",
                "timestamp_start": recording["start_time"].isoformat(),
                "timestamp_end": end_time.isoformat(),
                "item_id": recording["item_id"],
                "language": "ja-JP"
            }
            
            await self.storage_client.upload_audio(
                audio_data,
                session_id,
                "user_speech",
                metadata
            )
            
            logger.info("user_speech_saved",
                       session_id=session_id,
                       duration=duration,
                       audio_size=len(audio_data))
        
        # 記録セッション削除
        del self.active_recordings[session_id]
```

## 5. Azure OpenAI統合とプロキシ実装

### 5.1 Azure OpenAI Realtime API統合
```python
class AzureOpenAIRealtimeClient:
    def __init__(self):
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_version = "2024-02-15-preview"
        
        # HTTPクライアント設定
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_connections=100)
        )
    
    async def create_session(self, config: SessionConfig) -> AzureSession:
        """Azure OpenAI Realtime Sessions APIへのリクエスト"""
        url = f"{self.endpoint}/openai/realtime/sessions"
        
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": config.model,
            "voice": config.voice,
            "instructions": config.instructions,
            "modalities": config.modalities,
            "tools": config.tools
        }
        
        response = await self.http_client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        session_data = response.json()
        return AzureSession(
            id=session_data["id"],
            ephemeral_key=session_data["client_secret"]["value"],
            expires_at=session_data["expires_at"]
        )
    
    async def exchange_sdp(self, ephemeral_key: str, model: str, offer_sdp: str) -> str:
        """WebRTC SDP交換"""
        url = f"{self.endpoint}/openai/realtime/sessions"
        
        headers = {
            "Authorization": f"Bearer {ephemeral_key}",
            "Content-Type": "application/sdp"
        }
        
        params = {"model": model}
        
        response = await self.http_client.post(
            url, 
            headers=headers, 
            params=params,
            content=offer_sdp
        )
        response.raise_for_status()
        
        return response.text
    
    async def connect_websocket(self, ephemeral_key: str, model: str) -> websockets.WebSocketServerProtocol:
        """Azure OpenAI WebSocket接続"""
        ws_url = f"{self.endpoint.replace('https://', 'wss://')}/openai/realtime"
        
        headers = {
            "Authorization": f"Bearer {ephemeral_key}",
            "Model": model
        }
        
        websocket = await websockets.connect(ws_url, extra_headers=headers)
        return websocket
```

### 5.2 セッション管理システム
```python
class RealtimeSessionManager:
    def __init__(self):
        self.sessions: Dict[str, ProxySession] = {}
        self.azure_client = AzureOpenAIRealtimeClient()
        
    async def create_proxy_session(self, request: SessionCreateRequest) -> SessionResponse:
        """プロキシセッション作成"""
        # Azure OpenAIセッション作成
        azure_session = await self.azure_client.create_session(
            SessionConfig(
                model=request.model,
                voice=request.voice,
                instructions=request.instructions,
                modalities=request.modalities,
                tools=request.tools
            )
        )
        
        # 内部セッション作成
        proxy_session = ProxySession(
            session_id=azure_session.id,
            user_id=request.user_id,
            ephemeral_key=azure_session.ephemeral_key,
            model=request.model,
            voice=request.voice,
            status="created",
            created_at=datetime.utcnow(),
            expires_at=azure_session.expires_at,
            last_activity=datetime.utcnow()
        )
        
        self.sessions[azure_session.id] = proxy_session
        
        # セッション有効期限監視
        asyncio.create_task(self.monitor_session_expiry(azure_session.id))
        
        return SessionResponse(
            session_id=azure_session.id,
            ephemeral_key=azure_session.ephemeral_key,
            webrtc_endpoint=f"wss://{os.getenv('HOST', 'localhost:8000')}/api/v1/realtime/webrtc/{azure_session.id}",
            created_at=proxy_session.created_at,
            expires_at=proxy_session.expires_at
        )
    
    async def get_session(self, session_id: str) -> Optional[ProxySession]:
        """セッション取得"""
        return self.sessions.get(session_id)
    
    async def update_connection_state(self, session_id: str, state: str):
        """接続状態更新"""
        if session_id in self.sessions:
            self.sessions[session_id].connection_state = state
            self.sessions[session_id].last_activity = datetime.utcnow()
    
    async def terminate_session(self, session_id: str) -> bool:
        """セッション終了"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.status = "terminated"
            session.terminated_at = datetime.utcnow()
            
            # クリーンアップ
            await self.cleanup_session_resources(session_id)
            del self.sessions[session_id]
            
            return True
        return False
    
    async def monitor_session_expiry(self, session_id: str):
        """セッション有効期限監視"""
        session = self.sessions.get(session_id)
        if not session:
            return
            
        # 有効期限まで待機
        sleep_duration = (session.expires_at - datetime.utcnow()).total_seconds()
        if sleep_duration > 0:
            await asyncio.sleep(sleep_duration)
        
        # 期限切れセッション削除
        await self.terminate_session(session_id)
        logger.info("session_expired", session_id=session_id)
```

### 5.2 Azure Blob Storage 統合

#### 5.2.1 ストレージ構成
```python
class AudioBlobStorageClient:
    def __init__(self):
        self.blob_service_client = BlobServiceClient(
            account_url=os.getenv("AZURE_STORAGE_ACCOUNT_URL"),
            credential=os.getenv("AZURE_STORAGE_KEY")
        )
        self.container_name = "audio-records"
        
    def get_blob_path(self, session_id: str, audio_id: str, audio_type: str, timestamp: datetime) -> str:
        """
        音声ファイルのBlobパスを生成
        パス形式: {audio_type}/{YYYY}/{MM}/{DD}/{session_id}/{audio_id}.wav
        """
        date_path = timestamp.strftime("%Y/%m/%d")
        return f"{audio_type}/{date_path}/{session_id}/{audio_id}.wav"
    
    async def upload_audio(self, audio_data: bytes, session_id: str, audio_type: str, metadata: dict) -> dict:
        """ユーザー発話音声データのアップロード"""
        audio_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        blob_name = self.get_blob_path(session_id, audio_id, audio_type, timestamp)
        
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_name
        )
        
        # メタデータ設定
        blob_metadata = {
            "session_id": session_id,
            "audio_id": audio_id,
            "audio_type": audio_type,
            "upload_timestamp": timestamp.isoformat(),
            "duration": str(metadata.get("duration", 0)),
            "sample_rate": str(metadata.get("sample_rate", 48000)),
            "speaker": metadata.get("speaker", "user"),
            "language": metadata.get("language", "ja-JP"),
            "transcription": metadata.get("transcription", ""),
            "content_type": "audio/wav"
        }
        
        # 音声データアップロード
        await blob_client.upload_blob(
            audio_data, 
            overwrite=True,
            metadata=blob_metadata,
            content_settings=ContentSettings(content_type="audio/wav")
        )
        
        # SAS URL生成
        sas_url = await self.generate_sas_url(blob_name, expiry_hours=1)
        
        return {
            "audio_id": audio_id,
            "blob_url": blob_client.url,
            "sas_url": sas_url,
            "sas_expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "upload_status": "completed",
            "size_bytes": len(audio_data),
            "created_at": timestamp.isoformat()
        }
    
    async def generate_sas_url(self, blob_name: str, expiry_hours: int = 1) -> str:
        """SAS URLの生成"""
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_name
        )
        
        sas_token = generate_blob_sas(
            account_name=blob_client.account_name,
            container_name=blob_client.container_name,
            blob_name=blob_client.blob_name,
            account_key=os.getenv("AZURE_STORAGE_KEY"),
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=expiry_hours)
        )
        
        return f"{blob_client.url}?{sas_token}"
    
    async def get_audio_metadata(self, blob_name: str) -> dict:
        """音声ファイルのメタデータ取得"""
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_name
        )
        
        properties = await blob_client.get_blob_properties()
        return properties.metadata
    
    async def list_session_audio_files(self, session_id: str) -> List[dict]:
        """セッション内の全音声ファイル一覧取得"""
        container_client = self.blob_service_client.get_container_client(self.container_name)
        
        audio_files = []
        async for blob in container_client.list_blobs(name_starts_with=f"user_speech/"):
            if session_id in blob.name:
                metadata = await self.get_audio_metadata(blob.name)
                audio_files.append({
                    "blob_name": blob.name,
                    "blob_url": f"{self.blob_service_client.url}/{self.container_name}/{blob.name}",
                    "size": blob.size,
                    "last_modified": blob.last_modified,
                    "metadata": metadata
                })
        
        return audio_files
    
    async def delete_audio_file(self, blob_name: str) -> bool:
        """音声ファイル削除"""
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_name
        )
        
        try:
            await blob_client.delete_blob()
            return True
        except Exception as e:
            logger.error(f"Failed to delete audio file: {blob_name}", error=str(e))
            return False
```

#### 5.2.2 音声データ処理パイプライン
```python
class AudioProcessingPipeline:
    def __init__(self):
        self.storage_client = AudioBlobStorageClient()
        self.vad = VoiceActivityDetector()  # 発話区間検出
        
    async def process_audio_stream(self, audio_frame: AudioFrame, session_id: str) -> None:
        """リアルタイム音声ストリーム処理"""
        
        # 1. 音声フレーム解析
        audio_data = audio_frame.to_ndarray()
        is_speech = self.vad.detect_speech(audio_data)
        
        if is_speech:
            # 2. 発話区間の音声データを蓄積
            await self._accumulate_speech_data(audio_data, session_id)
        else:
            # 3. 無音区間で発話終了を検出した場合、音声ファイル保存
            await self._finalize_speech_segment(session_id)
    
    async def _accumulate_speech_data(self, audio_data: np.ndarray, session_id: str) -> None:
        """発話区間の音声データ蓄積"""
        # セッションごとの音声バッファに蓄積
        if session_id not in self.speech_buffers:
            self.speech_buffers[session_id] = {
                "data": [],
                "start_time": datetime.utcnow(),
                "last_activity": datetime.utcnow()
            }
        
        self.speech_buffers[session_id]["data"].append(audio_data)
        self.speech_buffers[session_id]["last_activity"] = datetime.utcnow()
    
    async def _finalize_speech_segment(self, session_id: str) -> None:
        """発話区間終了時の音声ファイル保存"""
        if session_id not in self.speech_buffers:
            return
            
        buffer = self.speech_buffers[session_id]
        
        # 最小発話時間チェック（500ms以上）
        duration = (buffer["last_activity"] - buffer["start_time"]).total_seconds()
        if duration < 0.5:
            return
        
        # 音声データを結合してWAVファイル作成
        combined_audio = np.concatenate(buffer["data"])
        wav_data = self._convert_to_wav(combined_audio, sample_rate=48000)
        
        # メタデータ作成
        metadata = {
            "duration": duration,
            "format": "wav",
            "sample_rate": 48000,
            "channels": 1,
            "speaker": "user",
            "timestamp_start": buffer["start_time"].isoformat(),
            "timestamp_end": buffer["last_activity"].isoformat(),
            "language": "ja-JP"
        }
        
        # Azure Blob Storage にアップロード
        await self.storage_client.upload_audio(
            wav_data, 
            session_id, 
            "user_speech", 
            metadata
        )
        
        # バッファクリア
        del self.speech_buffers[session_id]
        
        logger.info("User speech saved", 
                   session_id=session_id, 
                   duration=duration,
                   audio_size=len(wav_data))
```

## 6. Docker コンテナ仕様

### 6.1 Dockerfile
```dockerfile
FROM python:3.13-slim

WORKDIR /app

# システム依存関係
RUN apt-get update && apt-get install -y \
    libopus-dev \
    libvpx-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# uvのインストール
RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--loop", "uvloop"]
```

### 6.2 依存関係 (pyproject.toml)
```toml
[project]
name = "realtime-api-webrtc-backend"
version = "1.0.0"
description = "WebRTC シグナリングサーバー for Azure OpenAI Realtime API"
requires-python = ">=3.13"
dependencies = [
    "fastapi==0.104.1",
    "uvicorn[standard]==0.24.0",
    "websockets==12.0",
    "aiortc==1.6.0",
    "azure-storage-blob==12.19.0",
    "openai==1.3.5",
    "pydantic==2.5.0",
    "python-multipart==0.0.6",
    "uvloop==0.19.0",
]

[project.optional-dependencies]
dev = [
    "pytest==7.4.3",
    "pytest-asyncio==0.21.1",
    "black==23.11.0",
    "flake8==6.1.0",
    "mypy==1.7.1",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
dev-dependencies = [
    "pytest>=7.4.3",
    "pytest-asyncio>=0.21.1",
    "black>=23.11.0",
    "flake8>=6.1.0",
    "mypy>=1.7.1",
]
```

### 6.3 環境変数
```bash
# Azure OpenAI Realtime API
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Azure Storage
AZURE_STORAGE_ACCOUNT_URL=https://yourstorageaccount.blob.core.windows.net/
AZURE_STORAGE_KEY=your_storage_key
AZURE_STORAGE_CONTAINER_NAME=audio-records

# WebRTC Proxy Settings
HOST=localhost:8000
WEBRTC_PROXY_TIMEOUT=30
MAX_WEBSOCKET_CONNECTIONS=1000

# Audio Processing
AUDIO_RETENTION_DAYS=30
AUDIO_ARCHIVE_DAYS=7
MIN_SPEECH_DURATION=0.5
MAX_AUDIO_FILE_SIZE=10485760  # 10MB

# Session Management
SESSION_EXPIRY_HOURS=1
SESSION_CLEANUP_INTERVAL=300  # 5分
MAX_CONCURRENT_SESSIONS=1000

# Application
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

## 7. セキュリティ仕様

### 7.1 認証・認可
- JWT トークンベース認証
- セッション単位のアクセス制御
- Azure AD 統合 (オプション)

### 7.2 通信セキュリティ
- HTTPS/WSS 必須
- WebRTC DTLS/SRTP による暗号化
- API レート制限

### 7.3 データセキュリティ
- 音声データの暗号化保存（Azure Storage Service Encryption）
- 音声ファイルアクセス用SASトークン生成
- ユーザー音声データのプライバシー保護
- Azure Blob Storage アクセス制御
- ログの機密情報マスキング

#### 7.3.1 音声データプライバシー保護
```python
class AudioPrivacyManager:
    def __init__(self):
        self.storage_client = AudioBlobStorageClient()
        
    async def generate_audio_sas_token(self, blob_name: str, expiry_hours: int = 1) -> str:
        """音声ファイルアクセス用の一時SASトークン生成"""
        blob_client = self.storage_client.blob_service_client.get_blob_client(
            container=self.storage_client.container_name,
            blob=blob_name
        )
        
        sas_token = generate_blob_sas(
            account_name=blob_client.account_name,
            container_name=blob_client.container_name,
            blob_name=blob_client.blob_name,
            account_key=os.getenv("AZURE_STORAGE_KEY"),
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=expiry_hours)
        )
        
        return f"{blob_client.url}?{sas_token}"
    
    async def anonymize_audio_metadata(self, session_id: str) -> None:
        """音声メタデータの匿名化"""
        audio_files = await self.storage_client.list_session_audio_files(session_id)
        
        for audio_file in audio_files:
            blob_client = self.storage_client.blob_service_client.get_blob_client(
                container=self.storage_client.container_name,
                blob=audio_file["blob_name"]
            )
            
            # 個人識別可能な情報を削除
            anonymized_metadata = {
                "audio_type": audio_file["metadata"].get("audio_type"),
                "duration": audio_file["metadata"].get("duration"),
                "language": audio_file["metadata"].get("language"),
                "anonymized": "true",
                "anonymized_at": datetime.utcnow().isoformat()
            }
            
            await blob_client.set_blob_metadata(anonymized_metadata)
```

## 8. 監視・ログ

### 8.1 ログ仕様
```python
import logging
import structlog

logger = structlog.get_logger()

# セッション作成ログ
logger.info("session_created", session_id=session_id, user_id=user_id)

# WebRTC 接続ログ
logger.info("webrtc_connected", session_id=session_id, peer_connection_state="connected")

# Azure API 呼び出しログ
logger.info("azure_openai_request", session_id=session_id, request_id=request_id, duration_ms=duration)
```

### 8.2 メトリクス
- アクティブセッション数
- WebRTC 接続成功率
- Azure OpenAI レスポンス時間
- 音声データ処理量・保存容量
- 音声ファイルアップロード成功率
- 発話区間検出精度

### 8.3 音声データ監視
```python
class AudioMetricsCollector:
    async def collect_audio_metrics(self) -> dict:
        """音声データ関連メトリクス収集"""
        return {
            "total_audio_files": await self._count_total_audio_files(),
            "total_storage_size": await self._calculate_total_storage_size(),
            "daily_upload_count": await self._count_daily_uploads(),
            "average_speech_duration": await self._calculate_average_duration(),
            "storage_cost_estimate": await self._estimate_storage_cost()
        }
```

## 9. エラーハンドリング

### 9.1 エラーレスポンス形式
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

### 9.2 エラーコード一覧

#### 9.2.1 認証・認可エラー (401, 403)
- `INVALID_EPHEMERAL_KEY`: 不正なephemeral key
- `EXPIRED_SESSION`: セッション期限切れ
- `AUTHENTICATION_REQUIRED`: 認証が必要
- `INSUFFICIENT_PERMISSIONS`: 権限不足

#### 9.2.2 リクエストエラー (400, 422)
- `INVALID_REQUEST_FORMAT`: リクエスト形式エラー
- `MISSING_REQUIRED_FIELD`: 必須フィールド不足
- `INVALID_FIELD_VALUE`: フィールド値不正
- `INVALID_AUDIO_FORMAT`: 音声形式不正
- `AUDIO_TOO_LARGE`: 音声ファイルサイズ超過
- `INVALID_SDP_FORMAT`: SDP形式エラー

#### 9.2.3 リソースエラー (404, 409)
- `SESSION_NOT_FOUND`: セッション未発見
- `AUDIO_FILE_NOT_FOUND`: 音声ファイル未発見
- `RESOURCE_CONFLICT`: リソース競合

#### 9.2.4 外部サービスエラー (502, 503)
- `AZURE_OPENAI_ERROR`: Azure OpenAI APIエラー
- `AZURE_STORAGE_ERROR`: Azure Storageエラー
- `WEBRTC_CONNECTION_FAILED`: WebRTC接続エラー
- `EXTERNAL_SERVICE_UNAVAILABLE`: 外部サービス利用不可

#### 9.2.5 サーバーエラー (500)
- `INTERNAL_SERVER_ERROR`: 内部サーバーエラー
- `AUDIO_PROCESSING_ERROR`: 音声処理エラー
- `DATABASE_ERROR`: データベースエラー

#### 9.2.6 制限エラー (429, 507)
- `RATE_LIMIT_EXCEEDED`: レート制限超過
- `STORAGE_QUOTA_EXCEEDED`: ストレージ容量超過
- `CONCURRENT_SESSION_LIMIT`: 同時セッション数制限

### 9.3 エラーレスポンス例

#### 9.3.1 認証エラー
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

#### 9.3.2 バリデーションエラー
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

#### 9.3.3 音声ファイルエラー
```json
{
  "error": {
    "code": "AUDIO_UPLOAD_FAILED",
    "message": "Failed to upload audio data to Azure Blob Storage",
    "details": {
      "session_id": "uuid",
      "audio_size": 1440000,
      "error_reason": "Storage account quota exceeded",
      "timestamp": "2024-01-01T00:00:00Z",
      "request_id": "req_12347"
    }
  }
}
```

#### 9.3.4 外部サービスエラー
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
      "request_id": "req_12348"
    }
  }
}
```

## 10. パフォーマンス最適化

### 10.1 非同期処理
- asyncio による非同期I/O
- コネクションプール管理
- バックグラウンドタスクによる音声処理

### 10.2 キャッシュ戦略
- セッション情報のメモリキャッシュ
- Azure OpenAI レスポンスキャッシュ
- Redis クラスター対応

### 10.3 スケーリング
- ステートレス設計
- ロードバランサー対応
- 水平スケーリング

## 11. デプロイメント

### 11.1 AWS ECS/Fargate
```yaml
# docker-compose.yml for local development
version: '3.8'
services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY}
      - AZURE_STORAGE_KEY=${AZURE_STORAGE_KEY}
    volumes:
      - ./logs:/app/logs
```

### 11.2 開発環境セットアップ
```bash
# プロジェクトのクローン
git clone <repository-url>
cd realtime-api-webrtc-backend

# uvでの依存関係インストール
uv sync

# 開発サーバー起動
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# テスト実行
uv run pytest

# コードフォーマット
uv run black .
uv run flake8 .
```

### 11.3 ヘルスチェック実装
```python
@app.get("/api/v1/health")
async def health_check():
    """システムヘルスチェック"""
    azure_openai_health = await check_azure_openai_health()
    blob_storage_health = await check_blob_storage_health()
    
    overall_status = "healthy"
    if not azure_openai_health["status"] == "healthy" or not blob_storage_health["status"] == "healthy":
        overall_status = "unhealthy"
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "uptime_seconds": get_uptime_seconds(),
        "services": {
            "azure_openai": azure_openai_health,
            "blob_storage": blob_storage_health,
            "database": await check_database_health()
        },
        "metrics": {
            "active_sessions": len(session_manager.sessions),
            "total_sessions_today": await get_sessions_count_today(),
            "audio_files_processed_today": await get_audio_files_count_today(),
            "storage_usage_percentage": await get_storage_usage_percentage(),
            "average_response_time_ms": await get_average_response_time()
        }
    }

@app.get("/api/v1/metrics")
async def get_metrics(timeframe: str = "1h"):
    """詳細メトリクス取得"""
    return {
        "timeframe": timeframe,
        "timestamp": datetime.utcnow().isoformat(),
        "system_metrics": await collect_system_metrics(),
        "application_metrics": await collect_application_metrics(timeframe),
        "azure_metrics": await collect_azure_metrics(timeframe),
        "error_metrics": await collect_error_metrics(timeframe)
    }

async def check_azure_openai_health() -> dict:
    """Azure OpenAI APIヘルスチェック"""
    try:
        start_time = time.time()
        # 軽量なAPIコールでヘルスチェック
        response = await azure_client.get_models()
        response_time = (time.time() - start_time) * 1000
        
        return {
            "status": "healthy",
            "response_time_ms": response_time,
            "last_check": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "last_check": datetime.utcnow().isoformat()
        }

async def check_blob_storage_health() -> dict:
    """Azure Blob Storageヘルスチェック"""
    try:
        start_time = time.time()
        # コンテナの存在確認
        container_client = blob_service_client.get_container_client("audio-records")
        await container_client.get_container_properties()
        response_time = (time.time() - start_time) * 1000
        
        return {
            "status": "healthy",
            "response_time_ms": response_time,
            "last_check": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "last_check": datetime.utcnow().isoformat()
        }
```

## 12. 開発・テスト

### 12.1 パッケージ管理 (uv)

#### 12.1.1 uvの特徴
- **高速**: Rustで実装された次世代Pythonパッケージマネージャー
- **決定論的**: uv.lockファイルによる再現可能なビルド
- **pip互換**: 既存のPythonエコシステムとの完全互換
- **仮想環境管理**: プロジェクトごとの独立した環境

#### 12.1.2 基本コマンド
```bash
# プロジェクト初期化
uv init

# 依存関係インストール
uv sync

# パッケージ追加
uv add fastapi
uv add --dev pytest

# パッケージ削除
uv remove package-name

# 仮想環境でコマンド実行
uv run python script.py
uv run pytest

# ロックファイル更新
uv lock

# 本番環境用インストール（開発依存関係除外）
uv sync --no-dev
```

#### 12.1.3 設定ファイル

**pyproject.toml**: メインの設定ファイル
- プロジェクトメタデータ
- 依存関係定義
- ツール設定

**uv.lock**: 決定論的な依存関係ロックファイル
- 正確なバージョン情報
- 依存関係ツリー
- ハッシュによる整合性検証

### 12.2 単体テスト
```python
import pytest
from fastapi.testclient import TestClient

@pytest.mark.asyncio
async def test_webrtc_signaling():
    # WebRTC シグナリングテスト
    
@pytest.mark.asyncio  
async def test_azure_openai_integration():
    # Azure OpenAI 統合テスト
```

### 12.3 統合テスト
- WebRTC E2E テスト
- Azure サービス統合テスト
- 音声データ保存・取得テスト
- 負荷テスト

### 12.4 音声データテスト
```python
@pytest.mark.asyncio
async def test_audio_upload_and_retrieval():
    """音声データアップロード・取得テスト"""
    # テスト用音声データ作成
    test_audio_data = generate_test_audio_wav(duration=5.0, sample_rate=48000)
    
    # アップロードテスト
    storage_client = AudioBlobStorageClient()
    blob_url = await storage_client.upload_audio(
        test_audio_data, 
        "test_session_123", 
        "user_speech",
        {"duration": 5.0, "speaker": "user"}
    )
    
    assert blob_url is not None
    
    # 取得テスト
    audio_files = await storage_client.list_session_audio_files("test_session_123")
    assert len(audio_files) > 0

```

### 12.5 テスト実行
```bash
# 全テスト実行
uv run pytest

# 特定のテストファイル実行
uv run pytest tests/test_audio.py

# カバレッジ付きテスト実行
uv run pytest --cov=src

# 並列テスト実行
uv run pytest -n auto
```

## 13. API制限事項

### 13.1 レート制限

#### 13.1.1 セッション作成
- **制限**: 100回/分/IP
- **ヘッダー**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

#### 13.1.2 音声アップロード
- **制限**: 1000回/時間/セッション
- **ファイルサイズ**: 最大10MB/ファイル

#### 13.1.3 WebSocket接続
- **制限**: 同時接続数1000/サーバー
- **メッセージ**: 10,000回/分/セッション

### 13.2 データ制限

#### 13.2.1 ストレージ制限
- **保存期間**: 30日間（設定可能）
- **総容量**: 100GB/アカウント
- **ファイル数**: 100,000ファイル/アカウント

#### 13.2.2 セッション制限
- **有効期間**: 1時間
- **同時セッション**: 10セッション/ユーザー
- **最大継続時間**: 4時間/セッション

### 13.3 レート制限実装
```python
from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import time
from collections import defaultdict

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, calls_per_minute: int = 100):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute
        self.clients = defaultdict(list)
    
    async def dispatch(self, request, call_next):
        client_ip = request.client.host
        now = time.time()
        
        # 古いエントリを削除
        self.clients[client_ip] = [
            timestamp for timestamp in self.clients[client_ip]
            if now - timestamp < 60
        ]
        
        # レート制限チェック
        if len(self.clients[client_ip]) >= self.calls_per_minute:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={
                    "X-RateLimit-Limit": str(self.calls_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(now + 60))
                }
            )
        
        # リクエストを記録
        self.clients[client_ip].append(now)
        
        response = await call_next(request)
        
        # レート制限ヘッダーを追加
        remaining = self.calls_per_minute - len(self.clients[client_ip])
        response.headers["X-RateLimit-Limit"] = str(self.calls_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now + 60))
        
        return response
```