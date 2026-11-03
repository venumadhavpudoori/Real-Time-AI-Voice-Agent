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
  const ignoreSpeechUntilRef = useRef(0);

  // Sync state ref for event handlers
  useEffect(() => {
    isAgentSpeakingRef.current = agentState === AGENT_STATES.SPEAKING;
  }, [agentState]);

  // Audio player element setup for server TTS
  useEffect(() => {
    const audio = new Audio();
    audio.onended = () => {
      // Small cooldown to prevent room speaker reverberation from triggering mic
      ignoreSpeechUntilRef.current = Date.now() + 400;
      setAgentState(AGENT_STATES.LISTENING);
    };
    audio.onerror = () => {
      setAgentState(AGENT_STATES.LISTENING);
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
      setAgentState(AGENT_STATES.LISTENING);
    }, 300);
  }, [stopAllAudioPlayback]);

  // Speak agent message using Web Speech Synthesis or Server MP3 base64
  const speakWithBrowser = useCallback((text) => {
    if (!('speechSynthesis' in window)) {
      setAgentState(AGENT_STATES.LISTENING);
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.05;
    utterance.pitch = 1.0;

    // Pick clear English voice if available
    const voices = window.speechSynthesis.getVoices();
    const preferredVoice = voices.find(v => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Samantha') || v.name.includes('David')));
    if (preferredVoice) utterance.voice = preferredVoice;

    utterance.onend = () => {
      ignoreSpeechUntilRef.current = Date.now() + 400;
      setAgentState(AGENT_STATES.LISTENING);
    };
    utterance.onerror = () => {
      setAgentState(AGENT_STATES.LISTENING);
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
          console.warn('[Audio] Autoplay blocked, falling back to Web Speech API', err);
          speakWithBrowser(text);
        });
        return;
      } catch (err) {
        console.error('[Audio] Base64 playback error:', err);
      }
    }

    // Default: instantaneous local Web Speech API
    speakWithBrowser(text);
  }, [voiceEngine, speakWithBrowser]);

  // 2. Setup WebSocket Connection
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/voice-agent?session_id=${sessionId}`;
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => {
      console.log('[WebSocket] Connected');
      setWsConnected(true);
    };

    ws.onclose = () => {
      console.log('[WebSocket] Disconnected');
      setWsConnected(false);
    };

    ws.onerror = (err) => {
      console.error('[WebSocket] Error:', err);
      setWsConnected(false);
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

    // Keepalive ping
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 25000);

    return () => {
      clearInterval(pingInterval);
      ws.close();
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
      // 1. Check if we should ignore audio echo (e.g. while agent is speaking or in post-speak cooldown)
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
      if (err.error === 'not-allowed') {
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
      alert('Speech Recognition is not supported on this browser (Chrome or Edge recommended). You can still type in transcripts!');
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

  // Send typed text message (manual text input support)
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
