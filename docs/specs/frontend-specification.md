# フロントエンドアプリケーション仕様書

## 1. アプリケーション概要

### 1.1 概要
Azure OpenAI Realtime APIを利用したリアルタイム音声通信WebアプリケーションのReactフロントエンドです。WebRTC技術を使用してブラウザから直接Azure OpenAI Realtime APIとの音声通信を実現し、AIアシスタントとの自然な会話を可能にします。

### 1.2 主要機能
- **リアルタイム音声通信**: WebRTCによるAzure OpenAIとの双方向音声通信
- **AIセッション管理**: Azure OpenAI Realtime APIセッションの作成・管理
- **音声録音・保存**: MediaRecorder APIによるリアルタイム音声録音とBlob Storage保存
- **関数呼び出し**: AI応答による動的なWebページ操作
- **リアルタイムログ**: セッションの詳細な状態表示とデバッグ情報
- **会話応答速度計測**: AIの発話完了からユーザー発話開始までの反応時間測定・統計表示
- **リアルタイムテキスト表示**: AI応答の音声と同期したテキスト表示
- **環境設定管理**: 設定可能な環境変数による柔軟な接続設定

### 1.3 技術スタック
- **フレームワーク**: React 19.1.0
- **言語**: JavaScript (ES6+)
- **ビルドツール**: Create React App (react-scripts 5.0.1)
- **WebRTC**: ブラウザネイティブのWebRTC API
- **Audio**: Web Audio API & MediaDevices API
- **音声録音**: MediaRecorder API（WebM/Opus形式）
- **ファイルアップロード**: Fetch API（multipart/form-data）
- **テスト**: React Testing Library, Jest

### 1.4 対象ブラウザ
- **Chrome**: 最新バージョン
- **Firefox**: 最新バージョン
- **Safari**: 最新バージョン
- **WebRTC対応**: 必須

## 2. アーキテクチャ設計

### 2.1 コンポーネント構成
```
src/
├── App.js                 # メインアプリケーションコンポーネント
├── App.css               # アプリケーションスタイル
├── index.js              # アプリケーションエントリーポイント
├── index.css             # グローバルスタイル
├── reportWebVitals.js    # パフォーマンス測定
└── setupTests.js         # テスト設定
```

### 2.2 データフロー
```
[ユーザー操作] 
    ↓
[React State Management] 
    ↓
[WebRTC Session Management] ←→ [MediaRecorder Recording]
    ↓                              ↓
[Azure OpenAI Realtime API]     [Audio Upload API]
    ↓                              ↓
[Audio Stream & Data Channel]   [Blob Storage]
    ↓
[UI Update & Function Execution]
```

### 2.3 状態管理
- **React Hooks**: useState, useEffect, useRef
- **セッション状態**: sessionActive (boolean)
- **録音状態**: isRecording (boolean), recordingData (Blob)
- **ログ管理**: logMessages (array)
- **会話履歴**: conversationHistory (array), currentTranscript (string)
- **応答時間**: responseTimings (array)
- **WebRTC参照**: peerConnectionRef, dataChannelRef, audioElementRef
- **録音参照**: mediaRecorderRef, recordedChunksRef
- **タイミング参照**: avatarSpeechEndTimeRef

## 3. 機能仕様

### 3.1 セッション管理機能

#### 3.1.1 セッション作成
**機能概要**: Azure OpenAI Realtime APIセッションの初期化

**処理フロー**:
1. 環境変数の検証
2. Azure Sessions APIへのリクエスト送信
3. Ephemeral keyの取得
4. セッションIDの記録
5. WebRTC接続の初期化

**API通信**:
```javascript
// セッション作成リクエスト
const response = await fetch(process.env.REACT_APP_SESSIONS_URL, {
  method: "POST",
  headers: {
    "api-key": process.env.REACT_APP_API_KEY,
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    model: process.env.REACT_APP_DEPLOYMENT,
    voice: process.env.REACT_APP_VOICE
  })
});
```

**エラーハンドリング**:
- API レスポンスエラー（ステータスコード、レスポンス内容）
- 必須フィールド不足（session ID, ephemeral key）
- ネットワークエラー

#### 3.1.2 セッション終了
**機能概要**: アクティブセッションの安全な終了

**処理フロー**:
1. データチャネルのクローズ
2. WebRTC接続の終了
3. 音声要素の削除
4. 参照の初期化
5. セッション状態の更新

### 3.2 WebRTC通信機能

#### 3.2.1 WebRTC接続初期化
**機能概要**: Azure OpenAI Realtime APIとのWebRTC接続確立

**処理フロー**:
1. RTCPeerConnection作成
2. 接続状態監視設定
3. マイクロフォンアクセス取得
4. 音声トラック追加
5. データチャネル作成
6. SDP Offer作成・送信
7. SDP Answer受信・設定

**WebRTC設定**:
```javascript
const peerConnection = new RTCPeerConnection();

// 接続状態監視
peerConnection.onconnectionstatechange = () => {
  console.log("WebRTC connection state:", peerConnection.connectionState);
};

peerConnection.oniceconnectionstatechange = () => {
  console.log("ICE connection state:", peerConnection.iceConnectionState);
};
```

#### 3.2.2 音声ストリーム管理
**機能概要**: 双方向音声ストリームの管理

**入力音声処理**:
- `getUserMedia()`による音声取得
- 音声トラックのWebRTC接続への追加
- リアルタイム音声送信

**出力音声処理**:
- リモート音声ストリームの受信
- 動的audio要素の作成
- 自動再生設定

```javascript
// 音声出力設定
const audioElement = document.createElement('audio');
audioElement.autoplay = true;
document.body.appendChild(audioElement);

peerConnection.ontrack = (event) => {
  audioElement.srcObject = event.streams[0];
};
```

#### 3.2.3 SDP交換処理
**機能概要**: WebRTC接続のためのSDP (Session Description Protocol) 交換

**SDP Offer作成**:
```javascript
const offer = await peerConnection.createOffer();
await peerConnection.setLocalDescription(offer);
```

**SDP送信・応答**:
```javascript
const sdpResponse = await fetch(`${process.env.REACT_APP_WEBRTC_URL}?model=${process.env.REACT_APP_DEPLOYMENT}`, {
  method: "POST",
  body: offer.sdp,
  headers: {
    Authorization: `Bearer ${ephemeralKey}`,
    "Content-Type": "application/sdp",
  },
});
```

**SDP検証**:
- 必須フィールドの存在確認（v=, o=, s=, t=, m=）
- フォーマットの妥当性検証
- デバッグ情報の出力

### 3.3 データチャネル通信

#### 3.3.1 データチャネル設定
**機能概要**: Azure OpenAI Realtime APIとのメッセージ通信

**チャネル作成**:
```javascript
const dataChannel = peerConnection.createDataChannel('realtime-channel');
```

**イベントハンドリング**:
- `open`: セッション更新の送信
- `message`: サーバーイベントの処理
- `close`: セッション状態の更新

#### 3.3.2 Realtime APIメッセージ処理
**機能概要**: Azure OpenAI Realtime APIイベントの送受信

**送信メッセージ例（セッション更新）**:
```javascript
const event = {
  type: "session.update",
  session: {
    instructions: "あなたはとても優秀なAIアシスタントです。会話内容に対して、非常にナチュラルな返事をします。",
    modalities: ['text', 'audio'],
    tools: [/* 関数定義 */]
  }
};
dataChannel.send(JSON.stringify(event));
```

**受信メッセージ処理**:
- `session.update`: セッション設定の確認
- `session.error`: エラー情報の表示
- `session.end`: セッション終了処理
- `response.function_call_arguments.done`: 関数呼び出し実行

### 3.4 音声録音・アップロード機能

#### 3.4.1 MediaRecorder音声録音
**機能概要**: WebRTCセッション中の同時音声録音

**録音仕様**:
- **フォーマット**: WebM/Opus（ブラウザ標準対応）
- **サンプルレート**: 48kHz
- **チャンネル数**: 1（モノラル）
- **ビットレート**: 32kbps（音声品質とファイルサイズのバランス）

**実装フロー**:
1. セッション開始時に録音開始
2. マイクロフォンストリームの複製取得
3. MediaRecorderによる連続録音
4. データ取得イベントでチャンク蓄積
5. セッション終了時に録音停止・アップロード

```javascript
// 録音開始処理
const startRecording = async (stream) => {
  const options = {
    mimeType: 'audio/webm;codecs=opus',
    audioBitsPerSecond: 32000
  };
  
  mediaRecorderRef.current = new MediaRecorder(stream, options);
  recordedChunksRef.current = [];
  
  mediaRecorderRef.current.ondataavailable = (event) => {
    if (event.data.size > 0) {
      recordedChunksRef.current.push(event.data);
    }
  };
  
  mediaRecorderRef.current.onstop = () => {
    uploadRecordedAudio();
  };
  
  mediaRecorderRef.current.start(1000); // 1秒間隔でデータ取得
  setIsRecording(true);
  addLogMessage("🎤 Recording started");
};
```

#### 3.4.2 音声ファイルアップロード
**機能概要**: 録音データのBlobストレージへのアップロード

**アップロード処理**:
```javascript
const uploadRecordedAudio = async () => {
  try {
    const audioBlob = new Blob(recordedChunksRef.current, {
      type: 'audio/webm;codecs=opus'
    });
    
    const formData = new FormData();
    formData.append('audio_file', audioBlob, `recording_${Date.now()}.webm`);
    
    const metadata = {
      audio_type: 'user_speech',
      format: 'webm',
      duration: recordingDuration,
      sample_rate: 48000,
      channels: 1,
      timestamp_start: recordingStartTime,
      timestamp_end: new Date().toISOString(),
      language: 'ja-JP'
    };
    formData.append('metadata', JSON.stringify(metadata));
    
    const response = await fetch(process.env.REACT_APP_AUDIO_UPLOAD_URL, {
      method: 'POST',
      headers: {
        'session-id': sessionId
      },
      body: formData
    });
    
    if (response.ok) {
      const result = await response.json();
      addLogMessage(`✅ Audio uploaded: ${result.audio_id}`);
      addLogMessage(`📁 Blob URL: ${result.blob_url}`);
    } else {
      addLogMessage(`❌ Upload failed: ${response.status}`);
    }
  } catch (error) {
    addLogMessage(`❌ Upload error: ${error.message}`);
  }
};
```

**エラーハンドリング**:
- ネットワークエラー時の再試行
- ファイルサイズ制限チェック
- フォーマット対応チェック
- アップロード進捗表示

### 3.5 関数呼び出し機能

#### 3.5.1 利用可能な関数
**機能一覧**:

1. **getPageHTML**
   - 機能: 現在のページHTMLの取得
   - 戻り値: `{ success: true, html: string }`

2. **changeBackgroundColor**
   - 機能: ページ背景色の変更
   - パラメータ: `{ color: string }` (16進カラーコード)
   - 戻り値: `{ success: true, color: string }`

3. **changeTextColor**
   - 機能: ページテキスト色の変更
   - パラメータ: `{ color: string }` (16進カラーコード)
   - 戻り値: `{ success: true, color: string }`

#### 3.5.2 関数実行フロー
**処理手順**:
1. AI応答による関数呼び出し指示受信
2. 関数名と引数の解析
3. ローカル関数の実行
4. 実行結果のデータチャネル送信

```javascript
// 関数呼び出し処理
if (realtimeEvent.type === "response.function_call_arguments.done") {
  const fn = fns[realtimeEvent.name];
  if (fn !== undefined) {
    const args = JSON.parse(realtimeEvent.arguments);
    const result = await fn(args);
    const functionEvent = {
      type: "conversation.item.create",
      item: {
        type: "function_call_output",
        call_id: realtimeEvent.call_id,
        output: JSON.stringify(result),
      }
    };
    dataChannel.send(JSON.stringify(functionEvent));
  }
}
```

### 3.6 ログ・デバッグ機能

#### 3.6.1 リアルタイムログ表示
**機能概要**: セッションの状態とイベントのリアルタイム表示

**ログレベル**:
- 情報ログ: セッション状態、接続状態
- デバッグログ: WebRTCイベント、メッセージ交換
- エラーログ: 接続エラー、API エラー

**ログ形式**:
- プレーンテキスト（ユーザー向け）
- JSON形式（開発者向け、詳細データ）

#### 3.5.2 環境変数デバッグ
**機能概要**: 設定の妥当性確認

**検証項目**:
- 必須環境変数の存在確認
- セキュリティ配慮（APIキーのマスク表示）
- 設定値のコンソール出力

```javascript
const requiredVars = [
  'REACT_APP_WEBRTC_URL',
  'REACT_APP_SESSIONS_URL',
  'REACT_APP_AUDIO_UPLOAD_URL',
  'REACT_APP_API_KEY',
  'REACT_APP_DEPLOYMENT',
  'REACT_APP_VOICE'
];

const missingVars = requiredVars.filter(varName => !process.env[varName]);
if (missingVars.length > 0) {
  console.error('Missing environment variables:', missingVars);
}
```

### 3.7 会話応答速度計測機能

#### 3.7.1 応答時間測定
**機能概要**: AIの発話完了からユーザーの発話開始までの反応時間を自動測定

**測定対象**:
- **開始点**: `response.audio.done` イベント受信時（AI発話完了）
- **終了点**: `input_audio_buffer.speech_started` イベント受信時（ユーザー発話開始）
- **精度**: ミリ秒単位（`Date.now()`を使用）

**計測データ構造**:
```javascript
const timingData = {
  avatarEndTime: 1673123456789,    // AI発話完了時刻（Unix timestamp）
  userStartTime: 1673123458234,    // ユーザー発話開始時刻（Unix timestamp）
  responseTimeMs: 2445,            // 応答時間（ミリ秒）
  responseTimeSec: "2.45",         // 応答時間（秒、表示用）
  timestamp: "14:30:15"            // 記録時刻（HH:MM:SS）
};
```

**イベントハンドリング**:
```javascript
// AI発話完了時
if (realtimeEvent.type === "response.audio.done") {
  avatarSpeechEndTimeRef.current = Date.now();
}

// ユーザー発話開始時
if (realtimeEvent.type === "input_audio_buffer.speech_started") {
  if (avatarSpeechEndTimeRef.current) {
    const responseTime = Date.now() - avatarSpeechEndTimeRef.current;
    // 統計データに追加
    setResponseTimings(prev => [...prev, timingData]);
  }
}
```

#### 3.7.2 統計情報表示
**機能概要**: 測定した応答時間の統計情報をリアルタイム表示

**表示項目**:
- **平均応答時間**: 全計測値の算術平均（秒）
- **最短応答時間**: 最小値（秒）
- **最長応答時間**: 最大値（秒）
- **応答回数**: 計測されたターン数

**統計計算**:
```javascript
const avgResponseTime = responseTimings.reduce((sum, timing) => 
  sum + timing.responseTimeMs, 0) / responseTimings.length / 1000;

const minResponseTime = Math.min(...responseTimings.map(timing => 
  timing.responseTimeMs)) / 1000;

const maxResponseTime = Math.max(...responseTimings.map(timing => 
  timing.responseTimeMs)) / 1000;
```

#### 3.7.3 詳細履歴表示
**機能概要**: 個別の応答時間を時系列で表示

**表示形式**:
- **時刻**: 記録された時刻（HH:MM:SS）
- **応答時間**: 秒単位で小数点以下2桁まで
- **パフォーマンス指標**: 視覚的フィードバック

**パフォーマンス評価基準**:
- 🚀 **優秀** (緑色): 2秒未満
- **普通** (黄色): 2秒以上5秒未満  
- 🐌 **要改善** (赤色): 5秒以上

**UI実装**:
```javascript
<div style={{
  backgroundColor: timing.responseTimeMs < 2000 ? '#e8f5e8' : 
                   timing.responseTimeMs < 5000 ? '#fff3cd' : '#f8d7da',
  // その他のスタイル...
}}>
  <span>{timing.timestamp}</span>: {timing.responseTimeSec}秒
  {timing.responseTimeMs < 2000 && ' 🚀'}
  {timing.responseTimeMs >= 5000 && ' 🐌'}
</div>
```

#### 3.7.4 リアルタイムテキスト表示
**機能概要**: AI応答の音声と同期したテキスト表示

**実装機能**:
- **リアルタイム更新**: `response.audio_transcript.delta` イベントによる逐次表示
- **タイピングエフェクト**: 点滅カーソル表示
- **完成時処理**: `response.audio_transcript.done` イベントで履歴に保存

**状態管理**:
```javascript
const [currentTranscript, setCurrentTranscript] = useState('');
const [conversationHistory, setConversationHistory] = useState([]);

// リアルタイム更新
if (realtimeEvent.type === "response.audio_transcript.delta") {
  setCurrentTranscript(prev => prev + realtimeEvent.delta);
}

// 完成時処理
if (realtimeEvent.type === "response.audio_transcript.done") {
  setConversationHistory(prev => [...prev, {
    role: 'assistant',
    content: realtimeEvent.transcript,
    timestamp: new Date().toLocaleTimeString()
  }]);
  setCurrentTranscript('');
}
```

#### 3.7.5 高齢者向け最適化
**設計理念**: 高齢者にとって使いやすい会話体験の実現

**UXの考慮事項**:
- **視認性**: 大きな文字、高コントラスト配色
- **理解しやすさ**: 専門用語を避けた表示
- **フィードバック**: 応答性の可視化による安心感の提供

**評価基準**:
- **理想的な応答時間**: 1-2秒（自然な会話のペース）
- **許容範囲**: 3秒以内（ストレスを感じない範囲）
- **改善必要**: 5秒以上（会話の自然さが損なわれる）

### 3.8 リアルタイムテキスト表示機能

#### 3.8.1 会話履歴管理
**機能概要**: AI応答のテキストを会話履歴として保存・表示

**データ構造**:
```javascript
const messageData = {
  role: 'assistant',           // 発話者（'assistant' 固定）
  content: 'こんにちは...',    // 発話内容
  timestamp: '14:30:15'        // 発話時刻
};
```

**表示仕様**:
- **発話者表示**: 「AI」として表示
- **時刻表示**: HH:MM:SS形式
- **スタイリング**: AI応答は青系統の背景色

#### 3.8.2 エラーハンドリング
**対象エラー**:
- 音声認識失敗時の対応
- ネットワーク切断時のデータ保持
- 不正なイベント受信時の処理

**復旧処理**:
- タイムアウト時の自動リセット
- 状態の初期化処理
- エラーメッセージの適切な表示

## 4. ユーザーインターフェース仕様

### 4.1 レイアウト構成

#### 4.1.1 全体レイアウト
```
┌─────────────────────────────────────┐
│ Azure OpenAI Realtime Session       │
├─────────────────────────────────────┤
│ ⚠️ WARNING: セキュリティ警告          │
├─────────────────────────────────────┤
│ [Start Session] / [Close Session]   │
├─────────────────────────────────────┤
│ ┌─ Log Container ─────────────────┐ │
│ │ > Starting session...           │ │
│ │ > Ephemeral Key Received: ***   │ │
│ │ > WebRTC connection state: ...  │ │
│ │ │                               │ │
│ │ │ (スクロール可能)                │ │
│ │ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

#### 4.1.2 レスポンシブ対応
- **最大幅**: 800px（中央配置）
- **パディング**: 20px
- **モバイル対応**: ビューポート設定済み

### 4.2 UI コンポーネント

#### 4.2.1 メインヘッダー
- **タイトル**: "Azure OpenAI Realtime Session"
- **色**: #0078d4 (Microsoft Azure Blue)
- **フォント**: Arial, sans-serif

#### 4.2.2 警告メッセージ
- **背景色**: #fffacd (薄い黄色)
- **テキスト色**: #8b0000 (暗い赤)
- **ボーダー**: #ffb6c1 (薄いピンク)
- **内容**: 本番環境でのAPIキー露出に関する警告

#### 4.2.3 セッション制御ボタン
**デザイン仕様**:
- **背景色**: #0078d4 (通常) / #005a9e (ホバー)
- **テキスト色**: 白
- **パディング**: 10px 20px
- **フォントサイズ**: 16px
- **ボーダー**: なし
- **角丸**: 5px

**状態別表示**:
- セッション非活性時: "Start Session"
- セッション活性時: "Close Session"

#### 4.2.4 ログコンテナ
**デザイン仕様**:
- **背景色**: #f5f5f5 (薄いグレー)
- **ボーダー**: 1px solid #ddd
- **高さ**: 400px (固定)
- **オーバーフロー**: 縦スクロール対応
- **フォント**: monospace (等幅フォント)

**ログメッセージスタイル**:
- **マージン**: 5px 0
- **改行**: 自動折り返し (word-break: break-word)
- **空白**: 保持 (white-space: pre-wrap)

#### 4.2.5 応答時間統計コンポーネント
**表示条件**: セッション活性時かつ応答データ有り時のみ表示

**デザイン仕様**:
- **背景色**: #f9f9f9 (薄いグレー)
- **ボーダー**: 1px solid #ddd
- **角丸**: 10px
- **パディング**: 15px
- **マージン**: 20px 0

**統計情報表示**:
- **背景色**: #f5f5f5
- **パディング**: 10px
- **角丸**: 8px
- **フォント**: 標準サイズ、太字（項目名）

**詳細履歴表示**:
- **最大高さ**: 200px
- **オーバーフロー**: 縦スクロール
- **項目マージン**: 2px 0
- **項目パディング**: 5px 10px
- **フォントサイズ**: 0.9em

**パフォーマンス色分け**:
- **優秀（2秒未満）**: #e8f5e8 (薄い緑) + 🚀
- **普通（2-5秒）**: #fff3cd (薄い黄)
- **要改善（5秒以上）**: #f8d7da (薄い赤) + 🐌

#### 4.2.6 会話履歴コンポーネント
**表示条件**: セッション活性時のみ表示

**コンテナ仕様**:
- **背景色**: #ffffff (白)
- **ボーダー**: 1px solid #ddd
- **角丸**: 8px
- **パディング**: 15px
- **最大高さ**: 400px
- **オーバーフロー**: 縦スクロール

**メッセージスタイル**:
- **マージン**: 10px 0
- **パディング**: 10px
- **角丸**: 8px
- **フォントサイズ**: 14px
- **行間**: 1.4

**AI応答メッセージ**:
- **背景色**: #e3f2fd (薄い青)
- **左ボーダー**: 4px solid #2196f3 (青)

**リアルタイム表示（入力中）**:
- **背景色**: #e8f5e8 (薄い緑)
- **ボーダー**: 2px dashed #4caf50 (緑の点線)
- **アニメーション**: fadeIn (0.3s ease-in)

**タイピングインジケーター**:
- **文字**: | (パイプ文字)
- **アニメーション**: 1秒間隔の点滅
- **色**: #4caf50 (緑)

**ヘッダー情報**:
- **フォント**: 太字
- **フォントサイズ**: 0.9em
- **色**: #666 (グレー)
- **内容**: "AI - HH:MM:SS"

#### 4.2.7 録音インジケーター
**表示条件**: 録音中のみ表示

**デザイン仕様**:
- **色**: #ff4444 (赤)
- **フォント**: 太字
- **マージン**: 10px (左)
- **アニメーション**: 1.5秒間隔のパルス効果

**表示内容**: " 🎤 Recording..."

### 4.3 アクセシビリティ

#### 4.3.1 セマンティック HTML
- 適切な見出しタグ（h1）の使用
- ボタン要素の適切な使用
- ラベルとコントロールの関連付け

#### 4.3.2 キーボード操作
- Tabキーによるフォーカス移動
- Enterキーによるボタン実行
- Escapeキーによるセッション終了（実装推奨）

#### 4.3.3 スクリーンリーダー対応
- 状態変化の通知
- ログメッセージの読み上げ対応
- ARIA属性の適切な使用（実装推奨）

## 5. 設定・環境変数

### 5.1 必須環境変数

#### 5.1.1 Azure OpenAI 接続設定
```bash
# WebRTC エンドポイント URL
REACT_APP_WEBRTC_URL=https://region.realtimeapi-preview.ai.azure.com/v1/realtimertc

# Sessions API エンドポイント URL
REACT_APP_SESSIONS_URL=https://your-resource-name.openai.azure.com/openai/realtimeapi/sessions?api-version=2025-04-01-preview

# 音声アップロード エンドポイント URL
REACT_APP_AUDIO_UPLOAD_URL=http://localhost:8000/audio/upload

# Azure OpenAI API キー
REACT_APP_API_KEY=your-api-key-here
```

#### 5.1.2 モデル設定
```bash
# デプロイメント名（モデル名と異なる場合がある）
REACT_APP_DEPLOYMENT=gpt-4o-realtime-preview

# 使用する音声タイプ
REACT_APP_VOICE=alloy
```

### 5.2 音声設定オプション

#### 5.2.1 利用可能な音声タイプ
- `alloy`: バランスの取れた中性的な声
- `shimmer`: 明るく親しみやすい声
- `nova`: 若々しくエネルギッシュな声
- `echo`: 落ち着いた深みのある声
- `fable`: 表現豊かでストーリーテリング向け
- `onyx`: 力強く権威的な声

### 5.3 セキュリティ設定

#### 5.3.1 API キー管理
**現在の実装**:
- フロントエンドで直接API キーを使用（開発・検証用途のみ）
- 環境変数による設定
- ログでのマスク表示

**本番環境推奨設定**:
- バックエンドプロキシによるAPI キー管理
- Ephemeral keyのみフロントエンドで使用
- HTTPS必須

#### 5.3.2 CORS設定
- Azure OpenAI エンドポイントでのCORS設定が必要
- 開発環境: localhost:3000
- 本番環境: 実際のドメイン

## 6. パフォーマンス・最適化

### 6.1 React最適化

#### 6.1.1 レンダリング最適化
- `useEffect`依存配列の適切な設定
- `useRef`による参照管理（再レンダリング回避）
- ログメッセージの効率的な更新

#### 6.1.2 メモリ管理
- WebRTC接続のクリーンアップ
- Audio要素の適切な削除
- イベントリスナーの削除

### 6.2 WebRTC最適化

#### 6.2.1 接続性能
- ICE候補の効率的な処理
- 接続状態の適切な監視
- エラー時の自動復旧（実装推奨）

#### 6.2.2 音声品質
- Opusコーデックの使用
- 適切なサンプリングレート（48kHz）
- エコーキャンセレーション設定

### 6.3 ネットワーク最適化

#### 6.3.1 通信効率
- データチャネルメッセージの最適化
- 不要なログの削減
- 接続プールの効果的な利用

### 6.4 会話応答速度要件

#### 6.4.1 パフォーマンス基準
**測定対象**: AI発話完了からユーザー発話開始までの時間

**品質基準**:
- **🚀 優秀**: 2秒未満
  - 自然な会話のペース
  - 高齢者にとってストレスのない応答速度
  - システムの理想的な動作状態

- **普通**: 2秒以上5秒未満
  - 許容範囲内の応答速度
  - 軽微な遅延だが会話継続可能
  - ネットワーク状況による一時的な遅延

- **🐌 要改善**: 5秒以上
  - 会話の自然さが損なわれる
  - ユーザビリティの問題あり
  - システム・ネットワークの最適化が必要

#### 6.4.2 高齢者向けUX考慮事項
**設計目標**:
- **認知負荷の軽減**: 遅延による混乱を避ける
- **安心感の提供**: 視覚的フィードバックによる状況把握
- **継続的な改善**: 統計データによる品質向上

**実装要件**:
- リアルタイム応答時間表示
- 統計情報の分かりやすい可視化
- パフォーマンス悪化時の視覚的警告

#### 6.4.3 技術的制約
**計測精度**:
- **タイムスタンプ精度**: ミリ秒単位（Date.now()使用）
- **イベント依存性**: WebRTC DataChannelの安定性に依存
- **ブラウザ差異**: 実装によるタイミング誤差の可能性

**制限事項**:
- ネットワーク遅延による影響
- ブラウザのオーディオ処理遅延
- デバイス性能による処理時間差異

#### 6.4.4 データ保持・プライバシー
**統計データ管理**:
- **保存場所**: ブラウザメモリのみ（永続化なし）
- **セッション範囲**: セッション終了時に自動削除
- **プライバシー**: 個人識別情報の収集なし

**データ活用**:
- リアルタイム品質監視
- システム性能の可視化
- 開発・デバッグ用途の統計情報

## 7. エラーハンドリング

### 7.1 WebRTC エラー

#### 7.1.1 接続エラー
**エラータイプ**:
- `failed`: 接続失敗
- `disconnected`: 接続切断
- `closed`: 接続終了

**ハンドリング**:
```javascript
peerConnection.onconnectionstatechange = () => {
  const state = peerConnection.connectionState;
  if (state === 'failed') {
    logMessage('WebRTC connection failed');
    // 再接続ロジック（実装推奨）
  }
};
```

#### 7.1.2 メディアエラー
**エラータイプ**:
- `NotAllowedError`: マイクロフォンアクセス拒否
- `NotFoundError`: マイクロフォンデバイス未発見
- `NotReadableError`: デバイス使用中

### 7.2 API エラー

#### 7.2.1 Sessions API エラー
**HTTP ステータスコード**:
- `400`: リクエスト形式エラー
- `401`: 認証エラー
- `429`: レート制限
- `500`: サーバーエラー

**エラー処理**:
```javascript
if (!response.ok) {
  const errorText = await response.text();
  throw new Error(`API request failed: ${response.status} ${response.statusText}. Response: ${errorText}`);
}
```

#### 7.2.2 WebRTC API エラー
**SDP関連エラー**:
- 空のSDP
- 不正なSDP形式
- 必須フィールド不足

### 7.3 環境設定エラー

#### 7.3.1 環境変数エラー
**検証項目**:
- 必須変数の存在
- URL形式の妥当性
- APIキーの形式

**エラー表示**:
- コンソールログ
- UI上のエラーメッセージ
- 詳細なデバッグ情報

## 8. テスト仕様

### 8.1 テスト構成

#### 8.1.1 テストライブラリ
- **React Testing Library**: DOM テスト
- **Jest**: テストランナー・アサーション
- **@testing-library/jest-dom**: DOM マッチャー
- **@testing-library/user-event**: ユーザーインタラクション

#### 8.1.2 テスト分類
- **単体テスト**: コンポーネント単位
- **統合テスト**: WebRTC機能
- **E2Eテスト**: 完全なユーザーフロー（実装推奨）

### 8.2 テストケース

#### 8.2.1 UI テスト
```javascript
// コンポーネントレンダリングテスト
test('renders Azure OpenAI Realtime Session title', () => {
  render(<App />);
  const titleElement = screen.getByText(/Azure OpenAI Realtime Session/i);
  expect(titleElement).toBeInTheDocument();
});

// ボタン状態テスト
test('shows start session button initially', () => {
  render(<App />);
  const buttonElement = screen.getByText(/Start Session/i);
  expect(buttonElement).toBeInTheDocument();
});
```

#### 8.2.2 WebRTC テスト
```javascript
// WebRTC接続テスト（モック使用）
test('initializes WebRTC connection', async () => {
  // RTCPeerConnection をモック
  global.RTCPeerConnection = jest.fn().mockImplementation(() => ({
    createOffer: jest.fn().mockResolvedValue({ sdp: 'mock-sdp' }),
    setLocalDescription: jest.fn(),
    setRemoteDescription: jest.fn(),
    close: jest.fn()
  }));
  
  // テスト実行
});
```

#### 8.2.3 エラーハンドリングテスト
```javascript
// API エラーテスト
test('handles API error gracefully', async () => {
  // fetch をモックしてエラーレスポンスを返す
  global.fetch = jest.fn().mockRejectedValue(new Error('API Error'));
  
  render(<App />);
  const button = screen.getByText(/Start Session/i);
  fireEvent.click(button);
  
  // エラーメッセージの表示確認
});
```

### 8.3 テスト実行

#### 8.3.1 開発時テスト
```bash
# 監視モードでテスト実行
npm test

# カバレッジ付きテスト
npm test -- --coverage
```

#### 8.3.2 CI/CD テスト
```bash
# 一回実行モード
npm test -- --watchAll=false

# JUnit形式レポート出力
npm test -- --reporters=default --reporters=jest-junit
```

## 9. デプロイメント

### 9.1 ビルド設定

#### 9.1.1 本番ビルド
```bash
# 本番用ビルド作成
npm run build

# ビルド結果
build/
├── static/
│   ├── css/
│   ├── js/
│   └── media/
├── index.html
└── manifest.json
```

#### 9.1.2 環境別設定
**開発環境**:
- ソースマップ有効
- デバッグ情報出力
- Hot Reload対応

**本番環境**:
- コード最小化
- ソースマップ削除
- キャッシュ最適化

### 9.2 デプロイ方法

#### 9.2.1 静的ホスティング
**Azure Static Web Apps**:
```yaml
# azure-static-web-apps.yml
name: Azure Static Web Apps CI/CD

on:
  push:
    branches:
      - main

jobs:
  build_and_deploy_job:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build And Deploy
        uses: Azure/static-web-apps-deploy@v1
        with:
          app_location: "/frontend"
          output_location: "build"
```

**その他のオプション**:
- Vercel
- Netlify
- AWS S3 + CloudFront
- GitHub Pages

#### 9.2.2 環境変数設定
**本番環境での注意点**:
- API キーの適切な管理
- CORS設定の確認
- HTTPS必須
- 環境別URL設定

### 9.3 監視・ログ

#### 9.3.1 パフォーマンス監視
```javascript
// Web Vitals測定
import { reportWebVitals } from './reportWebVitals';

// パフォーマンス測定開始
reportWebVitals(console.log);
```

#### 9.3.2 エラー監視
**推奨ツール**:
- Application Insights
- Sentry
- LogRocket
- Google Analytics

## 10. 今後の拡張計画

### 10.1 機能拡張

#### 10.1.1 UI/UX 改善
- **チャット機能**: テキストベースの会話表示
- **音声可視化**: オーディオレベルメーターの追加
- **レスポンシブデザイン**: モバイル最適化
- **多言語対応**: i18n実装

#### 10.1.2 高度な機能
- **会話履歴**: セッション間の会話記録
- **カスタム関数**: 動的な関数登録機能
- **音声設定**: リアルタイム音声パラメータ調整
- **ファイル操作**: 音声ファイルのアップロード・ダウンロード

### 10.2 技術改善

#### 10.2.1 TypeScript移行
- 型安全性の向上
- 開発効率の改善
- エラーの早期発見

#### 10.2.2 状態管理強化
- Redux Toolkit導入
- 複雑な状態の管理改善
- ミドルウェアによるログ管理

#### 10.2.3 テスト強化
- E2Eテストの追加
- WebRTC専用テストユーティリティ
- パフォーマンステスト

### 10.3 セキュリティ強化

#### 10.3.1 認証・認可
- ユーザー認証システム
- セッション管理強化
- アクセス制御

#### 10.3.2 プライバシー保護
- 音声データの暗号化
- ローカルストレージの最小化
- GDPR準拠

## 11. 開発ガイドライン

### 11.1 コーディング規約

#### 11.1.1 JavaScript スタイル
- ES6+構文の使用
- const/let の適切な使い分け
- アロー関数の活用
- 分割代入の使用

#### 11.1.2 React ベストプラクティス
- Functional Componentの使用
- Hooksの適切な使用
- Prop typesの定義（実装推奨）
- 適切なキーの設定

#### 11.1.3 命名規約
- **コンポーネント**: PascalCase (App.js)
- **関数**: camelCase (startSession)
- **定数**: SCREAMING_SNAKE_CASE (API_URL)
- **ファイル**: kebab-case または PascalCase

### 11.2 Git ワークフロー

#### 11.2.1 ブランチ戦略
- `main`: 本番リリース用
- `develop`: 開発統合用
- `feature/*`: 機能開発用
- `hotfix/*`: 緊急修正用

#### 11.2.2 コミットメッセージ
```
feat: add voice selection feature
fix: resolve WebRTC connection issue
docs: update API documentation
style: format code with prettier
refactor: improve error handling logic
test: add WebRTC connection tests
```

### 11.3 開発環境

#### 11.3.1 必須ツール
- **Node.js**: 18.x以上
- **npm**: 9.x以上
- **Azure OpenAI**: アクセス権限
- **Modern Browser**: WebRTC対応

#### 11.3.2 推奨ツール
- **VSCode**: エディタ
- **React Developer Tools**: デバッグ
- **WebRTC Internals**: 接続診断
- **Postman**: API テスト

---

**アプリケーションバージョン**: 0.1.0  
**最終更新**: 2025年7月4日  
**ドキュメントバージョン**: 1.0.0
