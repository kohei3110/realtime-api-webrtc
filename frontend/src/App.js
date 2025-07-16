import React, { useState, useEffect, useRef, useCallback } from 'react';
import './App.css';

function App() {
  const [logMessages, setLogMessages] = useState([]);
  const [sessionActive, setSessionActive] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [currentTranscript, setCurrentTranscript] = useState('');
  const [conversationHistory, setConversationHistory] = useState([]);
  const [responseTimings, setResponseTimings] = useState([]);
  const dataChannelRef = useRef(null);
  const peerConnectionRef = useRef(null);
  const audioElementRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const recordedChunksRef = useRef([]);
  const recordingStartTimeRef = useRef(null);
  const sessionIdRef = useRef(null);
  const aiSpeechEndTimeRef = useRef(null);
  
  // Log environment variables for debugging
  useEffect(() => {
    console.log('Environment Variables:');
    console.log('WEBRTC_URL:', process.env.REACT_APP_WEBRTC_URL);
    console.log('SESSIONS_URL:', process.env.REACT_APP_SESSIONS_URL);
    console.log('DEPLOYMENT:', process.env.REACT_APP_DEPLOYMENT);
    console.log('VOICE:', process.env.REACT_APP_VOICE);
    // Not logging API_KEY for security reasons

    // Validate environment variables
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
      logMessage(`Error: Missing environment variables: ${missingVars.join(', ')}`);
    }
  }, []);

  // Function to log messages to UI
  const logMessage = (message) => {
    setLogMessages(prevMessages => [...prevMessages, message]);
  };

  // Test MediaRecorder capabilities
  const testMediaRecorderSupport = () => {
    const formats = [
      'audio/webm;codecs=opus',
      'audio/webm;codecs=vorbis',
      'audio/webm',
      'audio/ogg;codecs=opus',
      'audio/ogg;codecs=vorbis',
      'audio/ogg',
      'audio/mp4',
      'audio/mpeg',
      'audio/wav'
    ];

    logMessage("🔍 Testing MediaRecorder support:");
    formats.forEach(format => {
      const supported = MediaRecorder.isTypeSupported(format);
      logMessage(`  ${format}: ${supported ? '✅' : '❌'}`);
    });
  };

  // Start recording audio
  const startRecording = async (stream) => {
    try {
      // Check supported audio formats in order of preference
      let mimeType;
      let fileExtension;
      
      // Prioritize formats that work well with ffmpeg
      if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
        mimeType = 'audio/webm;codecs=opus';
        fileExtension = 'webm';
        logMessage("🎵 Using WebM/Opus audio format");
      } else if (MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')) {
        mimeType = 'audio/ogg;codecs=opus';
        fileExtension = 'ogg';
        logMessage("🎵 Using OGG/Opus audio format");
      } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
        mimeType = 'audio/mp4';
        fileExtension = 'mp4';
        logMessage("🎵 Using MP4 audio format");
      } else if (MediaRecorder.isTypeSupported('audio/mpeg')) {
        mimeType = 'audio/mpeg';
        fileExtension = 'mp3';
        logMessage("🎵 Using MP3 audio format");
      } else {
        // Fallback to basic WebM
        mimeType = 'audio/webm';
        fileExtension = 'webm';
        logMessage("⚠️ Using fallback WebM format");
      }

      const options = {
        mimeType: mimeType,
        audioBitsPerSecond: 128000 // Higher quality for better analysis
      };

      // Clone the stream for recording to avoid conflicts with WebRTC
      const recordingStream = stream.clone();
      mediaRecorderRef.current = new MediaRecorder(recordingStream, options);
      recordedChunksRef.current = [];
      recordingStartTimeRef.current = new Date().toISOString();
      
      // Store the file extension and mime type for later use
      mediaRecorderRef.current.fileExtension = fileExtension;
      mediaRecorderRef.current.actualMimeType = mimeType;

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          console.log(`MediaRecorder chunk received: ${event.data.size} bytes, type: ${event.data.type}`);
          recordedChunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = () => {
        console.log(`Recording stopped. Total chunks: ${recordedChunksRef.current.length}`);
        // Add a small delay to ensure all chunks are processed
        setTimeout(() => {
          uploadRecordedAudio();
        }, 100);
      };

      mediaRecorderRef.current.onerror = (event) => {
        console.error('MediaRecorder error:', event.error);
        logMessage(`❌ Recording error: ${event.error.message}`);
        setIsRecording(false);
      };

      mediaRecorderRef.current.onstart = () => {
        console.log('MediaRecorder started successfully');
        logMessage(`🎤 Recording started with ${mimeType}`);
      };

      // Start recording - don't use timeslice to avoid fragmenting the file
      mediaRecorderRef.current.start();
      setIsRecording(true);
    } catch (error) {
      console.error('Error starting recording:', error);
      logMessage(`❌ Failed to start recording: ${error.message}`);
    }
  };

  // Stop recording audio
  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      logMessage("🎤 Recording stopped");
    }
  };

  // Upload recorded audio to backend
  const uploadRecordedAudio = async () => {
    try {
      if (recordedChunksRef.current.length === 0) {
        logMessage("⚠️ No audio data to upload");
        return;
      }

      // Get the actual MIME type and extension used
      const actualMimeType = mediaRecorderRef.current ? mediaRecorderRef.current.actualMimeType : 'audio/webm';
      const fileExtension = mediaRecorderRef.current ? mediaRecorderRef.current.fileExtension : 'webm';
      
      // Log chunk information for debugging
      console.log(`Creating audio blob from ${recordedChunksRef.current.length} chunks`);
      const totalSize = recordedChunksRef.current.reduce((total, chunk) => total + chunk.size, 0);
      console.log(`Total audio data size: ${totalSize} bytes`);
      
      // Create the blob with the correct MIME type
      const audioBlob = new Blob(recordedChunksRef.current, { type: actualMimeType });
      console.log(`Created blob: size=${audioBlob.size}, type=${audioBlob.type}`);
      
      // Validate blob size
      if (audioBlob.size === 0) {
        logMessage("❌ Generated audio blob is empty");
        return;
      }
      
      // Calculate duration approximation
      const recordingDuration = recordingStartTimeRef.current 
        ? (new Date() - new Date(recordingStartTimeRef.current)) / 1000 
        : 0;

      const formData = new FormData();
      const fileName = `recording_${Date.now()}.${fileExtension}`;
      formData.append('audio_file', audioBlob, fileName);
      formData.append('session_id', sessionIdRef.current || '');
      formData.append('audio_format', fileExtension);

      const metadata = {
        audio_type: 'user_speech',
        format: fileExtension,
        duration: recordingDuration,
        sample_rate: 48000,
        channels: 1,
        timestamp_start: recordingStartTimeRef.current,
        timestamp_end: new Date().toISOString(),
        language: 'ja-JP',
        mime_type: actualMimeType,
        original_size: audioBlob.size
      };
      formData.append('metadata', JSON.stringify(metadata));

      logMessage(`📤 Uploading ${fileExtension.toUpperCase()} audio (${(audioBlob.size / 1024).toFixed(1)} KB)...`);
      console.log('Upload metadata:', metadata);

      const response = await fetch(process.env.REACT_APP_AUDIO_UPLOAD_URL, {
        method: 'POST',
        headers: {
          'session-id': sessionIdRef.current || 'no-session'
        },
        body: formData
      });

      if (response.ok) {
        const result = await response.json();
        logMessage(`✅ Audio uploaded successfully`);
        logMessage(`📁 Audio ID: ${result.audio_id}`);
        logMessage(`🔗 Blob URL: ${result.blob_url}`);
        if (result.sas_url) {
          logMessage(`🔑 SAS URL expires: ${new Date(result.sas_expires_at).toLocaleString()}`);
        }
      } else {
        const errorText = await response.text();
        logMessage(`❌ Upload failed: ${response.status} ${response.statusText}`);
        console.error('Upload error response:', errorText);
      }
    } catch (error) {
      console.error('Error uploading audio:', error);
      logMessage(`❌ Upload error: ${error.message}`);
    }
  };

  // Function definitions for tool capabilities
  const fns = {
    getPageHTML: () => {
      return { success: true, html: document.documentElement.outerHTML };
    },
    changeBackgroundColor: ({ color }) => {
      document.body.style.backgroundColor = color;
      return { success: true, color };
    },
    changeTextColor: ({ color }) => {
      document.body.style.color = color;
      return { success: true, color };
    },
  };

  // Start the session
  const startSession = async () => {
    try {
      logMessage("Starting session...");
      
      // WARNING: In production, this should be handled by a secure backend
      // to avoid exposing API keys in the client-side code
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

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API request failed: ${response.status} ${response.statusText}. Response: ${errorText}`);
      }

      const data = await response.json();
      console.log("Session response:", data);

      if (!data.id || !data.client_secret?.value) {
        throw new Error("Invalid session response: missing session ID or client secret");
      }

      const sessionId = data.id;
      const ephemeralKey = data.client_secret?.value;
      console.log("Ephemeral key:", ephemeralKey);

      // Store session ID for audio upload
      sessionIdRef.current = sessionId;

      // Mask the ephemeral key in the log message
      logMessage("Ephemeral Key Received: ***");
      logMessage("WebRTC Session Id = " + sessionId);

      // Set up the WebRTC connection using the ephemeral key
      await initializeWebRTC(ephemeralKey);
    } catch (error) {
      console.error("Error fetching ephemeral key:", error);
      logMessage("Error fetching ephemeral key: " + error.message);
    }
  };

  // Initialize WebRTC connection
  const initializeWebRTC = async (ephemeralKey) => {
    let peerConnection = new RTCPeerConnection();
    peerConnectionRef.current = peerConnection;

    // Add connection state change handler
    peerConnection.onconnectionstatechange = () => {
      logMessage(`WebRTC connection state: ${peerConnection.connectionState}`);
      console.log("WebRTC connection state:", peerConnection.connectionState);
    };

    // Add ICE connection state change handler
    peerConnection.oniceconnectionstatechange = () => {
      logMessage(`ICE connection state: ${peerConnection.iceConnectionState}`);
      console.log("ICE connection state:", peerConnection.iceConnectionState);
    };

    // Add error handler
    peerConnection.onerror = (error) => {
      console.error("WebRTC error:", error);
      logMessage(`WebRTC error: ${error}`);
    };

    // Create audio element for remote audio
    const audioElement = document.createElement('audio');
    audioElement.autoplay = true;
    document.body.appendChild(audioElement);
    audioElementRef.current = audioElement;

    peerConnection.ontrack = (event) => {
      logMessage("Received remote audio track");
      audioElement.srcObject = event.streams[0];
    };

    // Set up media stream
    try {
      logMessage("Requesting microphone access...");
      const clientMedia = await navigator.mediaDevices.getUserMedia({ audio: true });
      const audioTrack = clientMedia.getAudioTracks()[0];
      peerConnection.addTrack(audioTrack);
      logMessage("Added local audio track to peer connection");

      // Start recording with the same microphone stream
      await startRecording(clientMedia);

      // Set up data channel
      const dataChannel = peerConnection.createDataChannel('realtime-channel');
      dataChannelRef.current = dataChannel;

      dataChannel.addEventListener('open', () => {
        logMessage('Data channel is open');
        updateSession();
      });

      dataChannel.addEventListener('message', async (event) => {
        const realtimeEvent = JSON.parse(event.data);
        console.log(realtimeEvent);
        logMessage("Received server event: " + JSON.stringify(realtimeEvent, null, 2));
        
        if (realtimeEvent.type === "session.update") {
          const instructions = realtimeEvent.session.instructions;
          logMessage("Instructions: " + instructions);
        } else if (realtimeEvent.type === "session.error") {
          logMessage("Error: " + realtimeEvent.error.message);
        } else if (realtimeEvent.type === "session.end") {
          logMessage("Session ended.");
          setSessionActive(false);
        } else if (realtimeEvent.type === "response.audio_transcript.delta") {
          // リアルタイムでテキストを追加
          setCurrentTranscript(prev => prev + realtimeEvent.delta);
        } else if (realtimeEvent.type === "response.audio_transcript.done") {
          // 完成したテキストを会話履歴に追加
          const completeTranscript = realtimeEvent.transcript;
          setConversationHistory(prev => [...prev, {
            role: 'assistant',
            content: completeTranscript,
            timestamp: new Date().toLocaleTimeString()
          }]);
          setCurrentTranscript(''); // リセット
        } else if (realtimeEvent.type === "output_audio_buffer.stopped") {
          // AIの音声出力停止時刻を記録（実際に話し終わったタイミング）
          aiSpeechEndTimeRef.current = Date.now();
          logMessage("🤖 AIの発話が停止しました");
          console.log("AI speech stopped at:", new Date(aiSpeechEndTimeRef.current).toISOString());
        } else if (realtimeEvent.type === "input_audio_buffer.speech_started") {
          logMessage("🎤 ユーザーが話し始めました");
          
          // AI発話完了からユーザー発話開始までの時間を計測（ターンアラウンドタイム）
          if (aiSpeechEndTimeRef.current) {
            const userSpeechStartTime = Date.now();
            const turnAroundTime = userSpeechStartTime - aiSpeechEndTimeRef.current;
            
            const timingData = {
              aiSpeechEndTime: aiSpeechEndTimeRef.current,
              userSpeechStartTime: userSpeechStartTime,
              turnAroundTimeMs: turnAroundTime,
              turnAroundTimeSec: (turnAroundTime / 1000).toFixed(2),
              timestamp: new Date().toLocaleTimeString()
            };
            
            // ターンアラウンドタイムを状態に保存
            setResponseTimings(prev => [...prev, timingData]);
            
            logMessage(`⏱️ ターンアラウンドタイム: ${timingData.turnAroundTimeSec}秒`);
            console.log("Turn-around timing data:", timingData);
            
            // AI発話完了時刻をリセット
            aiSpeechEndTimeRef.current = null;
          }
        } else if (realtimeEvent.type === "input_audio_buffer.speech_stopped") {
          logMessage("🎤 ユーザーが話し終わりました");
        } else if (realtimeEvent.type === "response.function_call_arguments.done") {
          const fn = fns[realtimeEvent.name];
          if (fn !== undefined) {
            console.log(`Calling function: ${realtimeEvent.name}`);
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
            logMessage(`Function ${realtimeEvent.name} executed with result: ${JSON.stringify(result)}`);
          } else {
            logMessage("Function not found: " + realtimeEvent.name);
          }
        }
      });

      dataChannel.addEventListener('close', () => {
        logMessage('Data channel is closed');
        setSessionActive(false);
      });

      // Start the session using the Session Description Protocol (SDP)
      const offer = await peerConnection.createOffer();
      await peerConnection.setLocalDescription(offer);

      logMessage("Created local offer, sending to Azure OpenAI...");
      console.log("Local SDP Offer:", offer.sdp);
      
      // Validate the local offer
      validateSDP(offer.sdp, "Local Offer");

      const sdpResponse = await fetch(`${process.env.REACT_APP_WEBRTC_URL}?model=${process.env.REACT_APP_DEPLOYMENT}`, {
        method: "POST",
        body: offer.sdp,
        headers: {
          Authorization: `Bearer ${ephemeralKey}`,
          "Content-Type": "application/sdp",
        },
      });

      // Check if the response is successful
      if (!sdpResponse.ok) {
        const errorText = await sdpResponse.text();
        throw new Error(`SDP request failed: ${sdpResponse.status} ${sdpResponse.statusText}. Response: ${errorText}`);
      }

      const answerSdp = await sdpResponse.text();
      logMessage("Received SDP answer from server");
      console.log("Remote SDP Answer:", answerSdp);

      // Validate the remote answer before using it
      validateSDP(answerSdp, "Remote Answer");

      const answer = { type: "answer", sdp: answerSdp };
      await peerConnection.setRemoteDescription(answer);
      logMessage("Successfully set remote description");
      
      setSessionActive(true);
    } catch (error) {
      console.error("Error setting up WebRTC:", error);
      logMessage("Error setting up WebRTC: " + error.message);
    }
  };

  // Function to validate and debug SDP
  const validateSDP = (sdp, type) => {
    if (!sdp) {
      throw new Error(`${type} SDP is empty or null`);
    }
    
    if (!sdp.trim().startsWith('v=')) {
      throw new Error(`${type} SDP does not start with 'v=' line. Content: ${sdp.substring(0, 200)}...`);
    }
    
    // Check for required SDP lines
    const requiredLines = ['v=', 'o=', 's=', 't=', 'm='];
    const missingLines = requiredLines.filter(line => !sdp.includes(line));
    
    if (missingLines.length > 0) {
      console.warn(`${type} SDP missing lines:`, missingLines);
    }
    
    console.log(`${type} SDP validation passed`);
    return true;
  };

  // Update the session with instructions and tools
  const updateSession = () => {
    if (!dataChannelRef.current) return;

    const event = {
      type: "session.update",
      session: {
        instructions: "あなたは高齢者向けの親しみやすい会話パートナーです。 以下の特徴を持って会話してください： - 話し方：丁寧で親しみやすく、ゆっくりとした口調 - 性格：優しく、聞き上手で、励ましが上手 - 知識：昭和の文化や歴史に詳しく、懐かしい話題を提供 - 目的：楽しい会話を通じて認知機能を刺激し、心の支えとなる",
        modalities: ['text', 'audio'],
        tools: [
          {
            type: 'function',
            name: 'changeBackgroundColor',
            description: 'Changes the background color of a web page',
            parameters: {
              type: 'object',
              properties: {
                color: { type: 'string', description: 'A hex value of the color' },
              },
            },
          },
          {
            type: 'function',
            name: 'changeTextColor',
            description: 'Changes the text color of a web page',
            parameters: {
              type: 'object',
              properties: {
                color: { type: 'string', description: 'A hex value of the color' },
              },
            },
          },
          {
            type: 'function',
            name: 'getPageHTML',
            description: 'Gets the HTML for the current page',
          },
        ],
      },
    };
    
    dataChannelRef.current.send(JSON.stringify(event));
    logMessage("Sent client event: " + JSON.stringify(event, null, 2));
  };

  // Stop the session
  const stopSession = useCallback(() => {
    // Stop recording first
    stopRecording();

    if (dataChannelRef.current) {
      dataChannelRef.current.close();
    }
    
    if (peerConnectionRef.current) {
      peerConnectionRef.current.close();
    }
    
    // Remove the audio element if it exists
    if (audioElementRef.current && audioElementRef.current.parentNode) {
      audioElementRef.current.parentNode.removeChild(audioElementRef.current);
    }
    
    // Clean up references
    peerConnectionRef.current = null;
    dataChannelRef.current = null;
    audioElementRef.current = null;
    mediaRecorderRef.current = null;
    recordedChunksRef.current = [];
    recordingStartTimeRef.current = null;
    sessionIdRef.current = null;
    aiSpeechEndTimeRef.current = null;
    
    setSessionActive(false);
    setIsRecording(false);
    setCurrentTranscript('');
    setConversationHistory([]);
    setResponseTimings([]);
    logMessage("Session closed.");
  }, []);

  // Cleanup on component unmount
  useEffect(() => {
    return () => {
      if (sessionActive) {
        stopSession();
      }
    };
  }, [sessionActive, stopSession]);

  return (
    <div className="App">
      <h1>Azure OpenAI Realtime Session</h1>
      <p className="warning">
        WARNING: Don't use this code sample in production with the API key hardcoded. 
        Use a protected backend service to call the sessions API and generate the ephemeral key. 
        Then return the ephemeral key to the client.
      </p>
      
      {!sessionActive ? (
        <div>
          <button onClick={startSession}>Start Session</button>
          <button onClick={testMediaRecorderSupport} style={{ marginLeft: '10px' }}>
            Test Audio Support
          </button>
        </div>
      ) : (
        <div>
          <button onClick={stopSession}>Close Session</button>
          {isRecording && <span className="recording-indicator"> 🎤 Recording...</span>}
        </div>
      )}
      
      {/* ターンアラウンドタイム統計 */}
      {sessionActive && responseTimings.length > 0 && (
        <div className="response-stats">
          <h3>ターンアラウンドタイム統計</h3>
          <p style={{ fontSize: '0.9em', color: '#666', marginBottom: '10px' }}>
            ※ AIが話し終わってからユーザーが話し始めるまでの時間
          </p>
          <div style={{ 
            backgroundColor: '#f5f5f5', 
            padding: '10px', 
            borderRadius: '8px',
            marginBottom: '20px'
          }}>
            <div>
              <strong>平均ターンアラウンドタイム:</strong> {
                (responseTimings.reduce((sum, timing) => sum + timing.turnAroundTimeMs, 0) / responseTimings.length / 1000).toFixed(2)
              }秒
            </div>
            <div>
              <strong>最短ターンアラウンドタイム:</strong> {
                (Math.min(...responseTimings.map(timing => timing.turnAroundTimeMs)) / 1000).toFixed(2)
              }秒
            </div>
            <div>
              <strong>最長ターンアラウンドタイム:</strong> {
                (Math.max(...responseTimings.map(timing => timing.turnAroundTimeMs)) / 1000).toFixed(2)
              }秒
            </div>
            <div>
              <strong>測定回数:</strong> {responseTimings.length}回
            </div>
          </div>
          
          <h4>詳細履歴</h4>
          <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
            {responseTimings.map((timing, index) => (
              <div 
                key={index}
                style={{
                  padding: '5px 10px',
                  margin: '2px 0',
                  backgroundColor: timing.turnAroundTimeMs < 2000 ? '#e8f5e8' : 
                                    timing.turnAroundTimeMs < 5000 ? '#fff3cd' : '#f8d7da',
                  borderRadius: '4px',
                  fontSize: '0.9em'
                }}
              >
                <span style={{ fontWeight: 'bold' }}>{timing.timestamp}</span>: 
                {timing.turnAroundTimeSec}秒
                {timing.turnAroundTimeMs < 2000 && ' 🚀'}
                {timing.turnAroundTimeMs >= 5000 && ' 🐌'}
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* 会話履歴とリアルタイムテキスト表示 */}
      {sessionActive && (
        <div className="conversation-container">
          <h3>会話履歴</h3>
          <div className="conversation-history">
            {conversationHistory.map((message, index) => (
              <div 
                key={index} 
                className={`message ${message.role}`}
                style={{
                  margin: '10px 0',
                  padding: '10px',
                  borderRadius: '8px',
                  backgroundColor: message.role === 'assistant' ? '#e3f2fd' : '#f3e5f5'
                }}
              >
                <div style={{ fontWeight: 'bold', fontSize: '0.9em', color: '#666' }}>
                  {message.role === 'assistant' ? 'AI' : 'ユーザー'} - {message.timestamp}
                </div>
                <div style={{ marginTop: '5px' }}>
                  {message.content}
                </div>
              </div>
            ))}
            
            {/* リアルタイムテキスト表示 */}
            {currentTranscript && (
              <div 
                className="message assistant current"
                style={{
                  margin: '10px 0',
                  padding: '10px',
                  borderRadius: '8px',
                  backgroundColor: '#e8f5e8',
                  border: '2px dashed #4caf50'
                }}
              >
                <div style={{ fontWeight: 'bold', fontSize: '0.9em', color: '#666' }}>
                  AI (入力中...)
                </div>
                <div style={{ marginTop: '5px' }}>
                  {currentTranscript}
                  <span className="typing-indicator">|</span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
      
      <div className="log-container">
        {logMessages.map((message, index) => (
          <p key={index}>{message}</p>
        ))}
      </div>
    </div>
  );
}

export default App;
