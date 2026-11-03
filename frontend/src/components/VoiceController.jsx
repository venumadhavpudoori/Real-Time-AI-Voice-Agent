import React, { useState } from 'react';
import { Mic, MicOff, Zap, RotateCcw, Send, Sparkles, Volume2, Settings2, Headphones } from 'lucide-react';
import { AGENT_STATES } from '../hooks/useVoiceAgent';

export function VoiceController({
  agentState,
  isMicActive,
  toggleMicrophone,
  interruptAgent,
  sendTextMessage,
  resetSession,
  interimTranscript,
  autoListenContinuous,
  setAutoListenContinuous,
  voiceEngine,
  setVoiceEngine
}) {
  const [textInput, setTextInput] = useState('');

  const isSpeaking = agentState === AGENT_STATES.SPEAKING;

  const handleSendText = (e) => {
    e.preventDefault();
    if (!textInput.trim()) return;
    sendTextMessage(textInput);
    setTextInput('');
  };

  const samplePrompts = [
    "Table for 4 tomorrow at 7:30 pm",
    "I have a severe peanut allergy, what can I eat?",
    "Wait, make that 6 people on the patio instead!",
    "Can you cancel my booking RES-DEMO01?"
  ];

  return (
    <div className="w-full bg-slate-900/60 border border-slate-800 rounded-3xl p-6 backdrop-blur-xl shadow-xl flex flex-col gap-5">
      {/* Real-time Interim transcript preview */}
      {interimTranscript && (
        <div className="bg-purple-950/40 border border-purple-800/50 rounded-xl px-4 py-2.5 flex items-center gap-3 text-purple-200 text-sm animate-pulse">
          <Volume2 className="w-4 h-4 text-purple-400 shrink-0" />
          <span className="italic">"{interimTranscript}..."</span>
        </div>
      )}

      {/* Primary Action Controls Row */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        {/* Left: Continuous Toggle & Engine Selector */}
        <div className="flex flex-wrap items-center gap-4">
          <label className="flex items-center gap-2 cursor-pointer select-none text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors">
            <input
              type="checkbox"
              checked={autoListenContinuous}
              onChange={(e) => setAutoListenContinuous(e.target.checked)}
              className="w-4 h-4 rounded border-slate-700 bg-slate-800 text-purple-600 focus:ring-purple-500 focus:ring-offset-slate-950"
            />
            <span>Continuous Voice Mode</span>
          </label>

          {/* Voice Engine Toggle */}
          <div className="flex items-center gap-1.5 p-1 bg-slate-950 border border-slate-800 rounded-xl text-[11px] font-mono">
            <button
              type="button"
              onClick={() => setVoiceEngine('browser')}
              className={`px-2.5 py-1 rounded-lg transition-all ${
                voiceEngine === 'browser'
                  ? 'bg-purple-600 text-white font-bold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Browser TTS (Instant)
            </button>
            <button
              type="button"
              onClick={() => setVoiceEngine('server')}
              className={`px-2.5 py-1 rounded-lg transition-all ${
                voiceEngine === 'server'
                  ? 'bg-purple-600 text-white font-bold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Server Audio (gTTS)
            </button>
          </div>
        </div>

        {/* Center: Main Voice Toggle & Barge-in Controls */}
        <div className="flex items-center gap-3 mx-auto sm:mx-0">
          {/* Main Mic Button */}
          <button
            onClick={toggleMicrophone}
            className={`relative flex items-center gap-3 px-6 py-3.5 rounded-full font-bold text-sm transition-all duration-300 shadow-lg ${
              isMicActive
                ? 'bg-gradient-to-r from-red-600 to-rose-600 text-white shadow-red-500/25 hover:from-red-500 hover:to-rose-500 ring-4 ring-red-500/20'
                : 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-purple-500/25 hover:from-purple-500 hover:to-indigo-500 ring-4 ring-purple-500/20'
            }`}
          >
            {isMicActive ? (
              <>
                <MicOff className="w-5 h-5 animate-pulse" />
                <span>Mute Mic</span>
              </>
            ) : (
              <>
                <Mic className="w-5 h-5" />
                <span>Start Microphone</span>
              </>
            )}
          </button>

          {/* Barge-In / Interrupt Agent Button */}
          <button
            onClick={interruptAgent}
            disabled={!isSpeaking}
            title="Interrupt the AI agent immediately (Press Space or Escape)"
            className={`flex items-center gap-2 px-5 py-3.5 rounded-full font-semibold text-xs tracking-wider uppercase transition-all duration-200 ${
              isSpeaking
                ? 'bg-amber-500 hover:bg-amber-400 text-slate-950 shadow-lg shadow-amber-500/30 ring-2 ring-amber-300 animate-bounce'
                : 'bg-slate-800/80 text-slate-500 border border-slate-700/60 cursor-not-allowed opacity-50'
            }`}
          >
            <Zap className={`w-4 h-4 ${isSpeaking ? 'fill-current text-slate-950' : ''}`} />
            <span>Barge In</span>
          </button>

          {/* Reset Session */}
          <button
            onClick={resetSession}
            title="Reset conversation state"
            className="p-3.5 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors border border-slate-700"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Suggested Quick Speech Chips */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
          <Sparkles className="w-3.5 h-3.5 text-purple-400" />
          <span>Quick Voice Prompts</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {samplePrompts.map((prompt, idx) => (
            <button
              key={idx}
              onClick={() => sendTextMessage(prompt)}
              className="text-xs bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-purple-300 px-3 py-1.5 rounded-lg border border-slate-700/80 transition-all text-left"
            >
              "{prompt}"
            </button>
          ))}
        </div>
      </div>

      {/* Text Fallback Bar */}
      <form onSubmit={handleSendText} className="relative flex items-center mt-1">
        <input
          type="text"
          value={textInput}
          onChange={(e) => setTextInput(e.target.value)}
          placeholder="Or type voice command manually (e.g. 'Book table for 2 tomorrow at 7pm')..."
          className="w-full bg-slate-950/80 border border-slate-700/80 rounded-2xl px-5 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-all pr-12"
        />
        <button
          type="submit"
          disabled={!textInput.trim()}
          className="absolute right-2 p-2 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:bg-slate-800 text-white disabled:text-slate-600 transition-colors"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}
