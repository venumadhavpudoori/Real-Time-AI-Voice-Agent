import { useState, useEffect, useRef, useCallback } from 'react';

export const AGENT_STATES = {
  IDLE: 'IDLE',
  LISTENING: 'LISTENING',
  THINKING: 'THINKING',
  CALLING_TOOL: 'CALLING_TOOL',
  SPEAKING: 'SPEAKING',
  INTERRUPTED: 'INTERRUPTED',
  ERROR: 'ERROR'
};

export function useVoiceAgent(sessionId = 'default-session') {
  const [agentState, setAgentState] = useState(AGENT_STATES.IDLE);
  const [messages, setMessages] = useState([
    {
      id: 'init-1',
      sender: 'agent',
      text: "Hello! Welcome to The Grand Bistro. I can check table availability, book reservations, or check menu allergen safety. How can I help you today?",
      timestamp: new Date().toLocaleTimeString(),
      type: 'agent_response'
    }
  ]);
  const [activeTool, setActiveTool] = useState(null);
  const [latestGuardrail, setLatestGuardrail] = useState(null);
  const [interimTranscript, setInterimTranscript] = useState('');
  const [isMicActive, setIsMicActive] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [autoListenContinuous, setAutoListenContinuous] = useState(true);
  const [voiceEngine, setVoiceEngine] = useState('browser'); // 'browser' (instant 0ms) or 'server' (gTTS MP3)

  const socketRef = useRef(null);
  const recognitionRef = useRef(null);
  const audioPlayerRef = useRef(null);
  const isAgentSpeakingRef = useRef(false);
  const isMicActiveRef = useRef(false);
  const ignoreSpeechUntilRef = useRef(0);

  // Sync state refs for event listeners and callbacks
  useEffect(() => {
    isAgentSpeakingRef.current = agentState === AGENT_STATES.SPEAKING;
  }, [agentState]);

  useEffect(() => {
    isMicActiveRef.current = isMicActive;
  }, [isMicActive]);

  // Audio player setup for server TTS
  useEffect(() => {
    const audio = new Audio();
    audio.onended = () => {
      ignoreSpeechUntilRef.current = Date.now() + 500;
      setAgentState(isMicActiveRef.current ? AGENT_STATES.LISTENING : AGENT_STATES.IDLE);
    };
    audio.onerror = () => {
      setAgentState(isMicActiveRef.current ? AGENT_STATES.LISTENING : AGENT_STATES.IDLE);
    };
    audioPlayerRef.current = audio;
    return () => {
      audio.pause();
    };
  }, []);

  // Halt all audio playback immediately
  const stopAllAudioPlayback = useCallback(() => {
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
      audioPlayerRef.current.currentTime = 0;
    }
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
  }, []);

  // 1. Interruption Handler (Barge-in)
  const interruptAgent = useCallback(() => {
    console.log('[VoiceAgent] User barge-in triggered.');
    stopAllAudioPlayback();

    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'interrupt' }));
    }

    setAgentState(AGENT_STATES.INTERRUPTED);
    setMessages(prev => [
      ...prev,
      {
        id: `int-${Date.now()}`,
        sender: 'system',
        text: '⚡ Agent speech halted (Barge-in acknowledged).',
        timestamp: new Date().toLocaleTimeString(),
        type: 'interrupt'
      }
    ]);

    setTimeout(() => {
      setAgentState(isMicActiveRef.current ? AGENT_STATES.LISTENING : AGENT_STATES.IDLE);
    }, 300);
  }, [stopAllAudioPlayback]);

  // Keyboard shortcut for Barge-in (Escape or Spacebar outside inputs)
  useEffect(() => {
    const handleKeyDown = (e) => {
      const tag = e.target?.tagName?.toLowerCase();
      const isInput = tag === 'input' || tag === 'textarea';
      if (e.key === 'Escape' || (!isInput && e.key === ' ')) {
        if (isAgentSpeakingRef.current) {
          if (e.key === ' ') e.preventDefault();
          interruptAgent();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [interruptAgent]);

  // Speak agent message using Web Speech Synthesis
  const speakWithBrowser = useCallback((text) => {
    if (!('speechSynthesis' in window)) {
      setAgentState(isMicActiveRef.current ? AGENT_STATES.LISTENING : AGENT_STATES.IDLE);
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.05;
    utterance.pitch = 1.0;

    // Pick clear English voice if available
    const voices = window.speechSynthesis.getVoices();
    const preferredVoice = voices.find(v => 
      v.lang.startsWith('en') && 
      (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Samantha') || v.name.includes('David') || v.name.includes('Jenny'))
    );
    if (preferredVoice) utterance.voice = preferredVoice;

    utterance.onend = () => {
      ignoreSpeechUntilRef.current = Date.now() + 500;
      setAgentState(isMicActiveRef.current ? AGENT_STATES.LISTENING : AGENT_STATES.IDLE);
    };
    utterance.onerror = () => {
      setAgentState(isMicActiveRef.current ? AGENT_STATES.LISTENING : AGENT_STATES.IDLE);
    };

    window.speechSynthesis.speak(utterance);
  }, []);

  const playAgentResponse = useCallback((text, audioBase64) => {
    setAgentState(AGENT_STATES.SPEAKING);

    if (voiceEngine === 'server' && audioBase64) {
      try {
        const audio = audioPlayerRef.current;
        audio.src = `data:audio/mp3;base64,${audioBase64}`;
        audio.play().catch(err => {
          console.warn('[Audio] Server audio play failed, falling back to Web Speech API', err);
          speakWithBrowser(text);
        });
        return;
      } catch (err) {
        console.error('[Audio] Base64 playback error:', err);
      }
    }

    // Default instantaneous local Web Speech API
    speakWithBrowser(text);
  }, [voiceEngine, speakWithBrowser]);

  // 2. Setup WebSocket Connection with Auto-Reconnect
  useEffect(() => {
    let reconnectTimeout = null;
    let isUnmounted = false;

    // Direct connect to backend port 8000 on localhost to prevent proxy disconnects
    const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    const wsHost = isLocalhost ? '127.0.0.1:8000' : window.location.host;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${wsHost}/ws/voice-agent?session_id=${sessionId}`;

    function connect() {
      if (isUnmounted) return;
      console.log('[WebSocket] Connecting to', wsUrl);
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        console.log('[WebSocket] Connected successfully');
        setWsConnected(true);
      };

      ws.onclose = () => {
        console.log('[WebSocket] Disconnected. Reconnecting in 2s...');
        setWsConnected(false);
        if (!isUnmounted) {
          reconnectTimeout = setTimeout(connect, 2000);
        }
      };

      ws.onerror = (err) => {
        console.warn('[WebSocket] Socket encountered error:', err);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const { type, state, text, audio_base64, tool_name, tool_args, tool_result, guardrail_info } = data;

          if (state) {
            setAgentState(state);
          }

          if (type === 'agent_response' && text) {
            setMessages(prev => [
              ...prev,
              {
                id: `msg-${Date.now()}-${Math.random()}`,
                sender: 'agent',
                text,
                timestamp: new Date().toLocaleTimeString(),
                type: 'agent_response'
              }
            ]);
            playAgentResponse(text, audio_base64);
          } else if (type === 'tool_start') {
            setActiveTool({ name: tool_name, args: tool_args, status: 'running' });
            setMessages(prev => [
              ...prev,
              {
                id: `tool-${Date.now()}`,
                sender: 'system',
                text: `Executing tool: ${tool_name}`,
                tool: { name: tool_name, args: tool_args, status: 'running' },
                timestamp: new Date().toLocaleTimeString(),
                type: 'tool_start'
              }
            ]);
          } else if (type === 'tool_result') {
            setActiveTool(prev => prev ? { ...prev, result: tool_result, status: 'completed' } : null);
            setMessages(prev => [
              ...prev,
              {
                id: `tool-res-${Date.now()}`,
                sender: 'system',
                text: `Tool completed: ${tool_name}`,
                tool: { name: tool_name, result: tool_result, status: 'completed' },
                timestamp: new Date().toLocaleTimeString(),
                type: 'tool_result'
              }
            ]);
            // Broadcast database mutation so other UI components refresh in real-time
            window.dispatchEvent(new CustomEvent('database-updated', { detail: { tool_name, tool_result } }));
          } else if (type === 'guardrail_triggered') {
            setLatestGuardrail(guardrail_info);
            window.dispatchEvent(new CustomEvent('guardrail-updated', { detail: guardrail_info }));
            setMessages(prev => [
              ...prev,
              {
                id: `guard-${Date.now()}`,
                sender: 'guardrail',
                text: text || `Guardrail: ${guardrail_info?.type}`,
                guardrail: guardrail_info,
                timestamp: new Date().toLocaleTimeString(),
                type: 'guardrail'
              }
            ]);
          }
        } catch (err) {
          console.error('[WebSocket] Parse error:', err);
        }
      };
    }

    connect();

    // Keepalive ping
    const pingInterval = setInterval(() => {
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        socketRef.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, 20000);

    return () => {
      isUnmounted = true;
      clearInterval(pingInterval);
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (socketRef.current) socketRef.current.close();
    };
  }, [sessionId, playAgentResponse]);

  // 3. Web Speech Recognition (STT) setup
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.warn('SpeechRecognition API is not supported in this browser.');
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onresult = (event) => {
      // Ignore audio echo while agent is speaking or in post-speak cooldown
      if (isAgentSpeakingRef.current || Date.now() < ignoreSpeechUntilRef.current) {
        return;
      }

      let finalTranscript = '';
      let interim = '';

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript;
        } else {
          interim += transcript;
        }
      }

      if (interim) {
        setInterimTranscript(interim);
      }

      if (finalTranscript.trim()) {
        const trimmed = finalTranscript.trim();
        setInterimTranscript('');

        // Add to user messages
        setMessages(prev => [
          ...prev,
          {
            id: `usr-${Date.now()}`,
            sender: 'user',
            text: trimmed,
            timestamp: new Date().toLocaleTimeString(),
            type: 'user_speech'
          }
        ]);

        // Send to backend via WebSocket
        if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
          socketRef.current.send(JSON.stringify({
            type: 'user_transcript',
            text: trimmed
          }));
        }
      }
    };

    recognition.onerror = (err) => {
      console.warn('[SpeechRecognition] Error:', err.error);
      if (err.error === 'not-allowed' || err.error === 'service-not-allowed') {
        setIsMicActive(false);
      }
    };

    recognition.onend = () => {
      if (isMicActive && autoListenContinuous) {
        try {
          recognition.start();
        } catch {
          // ignore
        }
      } else {
        setIsMicActive(false);
      }
    };

    recognitionRef.current = recognition;

    return () => {
      try {
        recognition.stop();
      } catch {
        // cleanup
      }
    };
  }, [isMicActive, autoListenContinuous]);

  // Toggle microphone
  const toggleMicrophone = useCallback(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('Speech Recognition is not supported on this browser (Chrome or Edge recommended). You can still type in voice queries!');
      return;
    }

    if (isMicActive) {
      try {
        recognitionRef.current?.stop();
      } catch (err) {
        console.error(err);
      }
      setIsMicActive(false);
      setAgentState(AGENT_STATES.IDLE);
    } else {
      try {
        recognitionRef.current?.start();
        setIsMicActive(true);
        setAgentState(AGENT_STATES.LISTENING);
      } catch (err) {
        console.error(err);
      }
    }
  }, [isMicActive]);

  // Send typed text message (manual text input or quick voice prompts)
  const sendTextMessage = useCallback((text) => {
    if (!text || !text.trim()) return;
    const clean = text.trim();

    if (isAgentSpeakingRef.current) {
      interruptAgent();
    }

    setMessages(prev => [
      ...prev,
      {
        id: `usr-${Date.now()}`,
        sender: 'user',
        text: clean,
        timestamp: new Date().toLocaleTimeString(),
        type: 'user_speech'
      }
    ]);

    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({
        type: 'user_transcript',
        text: clean
      }));
    } else {
      console.warn('[WebSocket] Cannot send message, socket not open. ReadyState:', socketRef.current?.readyState);
    }
  }, [interruptAgent]);

  // Reset dialogue session
  const resetSession = useCallback(() => {
    stopAllAudioPlayback();
    setMessages([
      {
        id: `init-${Date.now()}`,
        sender: 'agent',
        text: "Session reset. Hello! How can I assist you with reservations or menu safety today?",
        timestamp: new Date().toLocaleTimeString(),
        type: 'agent_response'
      }
    ]);
    setActiveTool(null);
    setLatestGuardrail(null);
    setAgentState(isMicActive ? AGENT_STATES.LISTENING : AGENT_STATES.IDLE);
  }, [stopAllAudioPlayback, isMicActive]);

  return {
    agentState,
    messages,
    activeTool,
    latestGuardrail,
    interimTranscript,
    isMicActive,
    wsConnected,
    autoListenContinuous,
    setAutoListenContinuous,
    voiceEngine,
    setVoiceEngine,
    toggleMicrophone,
    interruptAgent,
    sendTextMessage,
    resetSession
  };
}
