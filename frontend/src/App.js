import React, { useState, useEffect, useRef } from 'react';
import './App.css';

function App() {
  const [logMessages, setLogMessages] = useState([]);
  const [sessionActive, setSessionActive] = useState(false);
  const dataChannelRef = useRef(null);
  const peerConnectionRef = useRef(null);
  const audioElementRef = useRef(null);
  
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
        instructions: "あなたはとても優秀なAIアシスタントです。会話内容に対して、非常にナチュラルな返事をします。",
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
  const stopSession = () => {
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
    
    peerConnectionRef.current = null;
    dataChannelRef.current = null;
    audioElementRef.current = null;
    
    setSessionActive(false);
    logMessage("Session closed.");
  };

  // Cleanup on component unmount
  useEffect(() => {
    return () => {
      if (sessionActive) {
        stopSession();
      }
    };
  }, [sessionActive]);

  return (
    <div className="App">
      <h1>Azure OpenAI Realtime Session</h1>
      <p className="warning">
        WARNING: Don't use this code sample in production with the API key hardcoded. 
        Use a protected backend service to call the sessions API and generate the ephemeral key. 
        Then return the ephemeral key to the client.
      </p>
      
      {!sessionActive ? (
        <button onClick={startSession}>Start Session</button>
      ) : (
        <button onClick={stopSession}>Close Session</button>
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
