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
        throw new Error(`API request failed: ${response.status}`);
      }

      const data = await response.json();

      const sessionId = data.id;
      const ephemeralKey = data.client_secret?.value;
      console.error("Ephemeral key:", ephemeralKey);

      // Mask the ephemeral key in the log message
      logMessage("Ephemeral Key Received: ***");
      logMessage("WebRTC Session Id = " + sessionId);

      // Set up the WebRTC connection using the ephemeral key
      initializeWebRTC(ephemeralKey);
    } catch (error) {
      console.error("Error fetching ephemeral key:", error);
      logMessage("Error fetching ephemeral key: " + error.message);
    }
  };

  // Initialize WebRTC connection
  const initializeWebRTC = async (ephemeralKey) => {
    let peerConnection = new RTCPeerConnection();
    peerConnectionRef.current = peerConnection;

    // Create audio element for remote audio
    const audioElement = document.createElement('audio');
    audioElement.autoplay = true;
    document.body.appendChild(audioElement);
    audioElementRef.current = audioElement;

    peerConnection.ontrack = (event) => {
      audioElement.srcObject = event.streams[0];
    };

    // Set up media stream
    try {
      const clientMedia = await navigator.mediaDevices.getUserMedia({ audio: true });
      const audioTrack = clientMedia.getAudioTracks()[0];
      peerConnection.addTrack(audioTrack);

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

      const sdpResponse = await fetch(`${process.env.REACT_APP_WEBRTC_URL}?model=${process.env.REACT_APP_DEPLOYMENT}`, {
        method: "POST",
        body: offer.sdp,
        headers: {
          Authorization: `Bearer ${ephemeralKey}`,
          "Content-Type": "application/sdp",
        },
      });

      const answer = { type: "answer", sdp: await sdpResponse.text() };
      await peerConnection.setRemoteDescription(answer);
      
      setSessionActive(true);
    } catch (error) {
      console.error("Error setting up WebRTC:", error);
      logMessage("Error setting up WebRTC: " + error.message);
    }
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
