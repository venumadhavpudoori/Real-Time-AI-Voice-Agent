import React, { useEffect, useRef } from 'react';
import { AGENT_STATES } from '../hooks/useVoiceAgent';

export function VoiceVisualizer({ agentState, audioLevel = 0 }) {
  const canvasRef = useRef(null);

  // Status-dependent styles
  const getOrbConfig = () => {
    switch (agentState) {
      case AGENT_STATES.SPEAKING:
        return {
          bg: 'from-purple-600 via-indigo-600 to-pink-500',
          ring: 'border-purple-400',
          glow: 'glow-orb-speaking',
          label: 'AI Concierge Speaking...',
          colorHex: '#a855f7'
        };
      case AGENT_STATES.THINKING:
        return {
          bg: 'from-amber-500 via-yellow-600 to-orange-500',
          ring: 'border-amber-400',
          glow: 'glow-orb',
          label: 'Processing & Planning...',
          colorHex: '#f59e0b'
        };
      case AGENT_STATES.CALLING_TOOL:
        return {
          bg: 'from-cyan-500 via-blue-600 to-indigo-600',
          ring: 'border-cyan-400',
          glow: 'glow-orb',
          label: 'Executing SQL Tool...',
          colorHex: '#06b6d4'
        };
      case AGENT_STATES.LISTENING:
        return {
          bg: 'from-emerald-500 via-teal-600 to-cyan-500',
          ring: 'border-emerald-400',
          glow: 'glow-orb-listening',
          label: 'Listening to you...',
          colorHex: '#10b981'
        };
      case AGENT_STATES.INTERRUPTED:
        return {
          bg: 'from-rose-600 via-red-600 to-orange-600',
          ring: 'border-rose-400',
          glow: 'glow-orb-interrupted',
          label: 'Interrupted! Re-orienting...',
          colorHex: '#f43f5e'
        };
      default:
        return {
          bg: 'from-slate-700 via-slate-800 to-slate-900',
          ring: 'border-slate-600',
          glow: '',
          label: 'Voice Standby',
          colorHex: '#64748b'
        };
    }
  };

  const orb = getOrbConfig();
  const dynamicScale = 1 + Math.min(audioLevel * 1.5, 0.45);

  // Draw audio waves on canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationId;
    let phase = 0;

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const width = canvas.width;
      const height = canvas.height;
      const centerY = height / 2;

      ctx.lineWidth = 2.5;
      ctx.strokeStyle = orb.colorHex;
      ctx.beginPath();

      const waveCount = 3;
      for (let w = 0; w < waveCount; w++) {
        ctx.beginPath();
        ctx.strokeStyle = `${orb.colorHex}${Math.floor((1 - w * 0.25) * 255).toString(16).padStart(2, '0')}`;
        for (let x = 0; x < width; x++) {
          const normX = x / width;
          const amp = (agentState === AGENT_STATES.SPEAKING || agentState === AGENT_STATES.LISTENING)
            ? (20 + audioLevel * 70) * Math.sin(normX * Math.PI)
            : 6;
          const freq = 0.04 + w * 0.01;
          const y = centerY + Math.sin(x * freq + phase + w) * amp;
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      }

      phase += 0.08;
      animationId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationId);
    };
  }, [agentState, audioLevel, orb.colorHex]);

  return (
    <div className="relative flex flex-col items-center justify-center p-8 bg-slate-900/50 rounded-3xl border border-slate-800 backdrop-blur-xl overflow-hidden shadow-2xl">
      {/* Background radial gradient */}
      <div className="absolute inset-0 bg-radial-gradient from-purple-900/10 via-transparent to-transparent pointer-events-none" />

      {/* Pulsing Ripple Rings */}
      {(agentState === AGENT_STATES.SPEAKING || agentState === AGENT_STATES.LISTENING) && (
        <div className="absolute w-64 h-64 rounded-full border border-purple-500/20 animate-ripple pointer-events-none" />
      )}

      {/* Main Dynamic Glowing Orb */}
      <div 
        className={`relative w-44 h-44 rounded-full bg-gradient-to-tr ${orb.bg} ${orb.glow} flex items-center justify-center transition-all duration-300 shadow-xl`}
        style={{ transform: `scale(${dynamicScale})` }}
      >
        {/* Inner core shimmer */}
        <div className="w-36 h-36 rounded-full bg-slate-950/40 backdrop-blur-md flex flex-col items-center justify-center border border-white/20">
          <div className="w-12 h-12 rounded-full bg-white/20 blur-sm animate-pulse mb-1" />
          <span className="text-xs uppercase tracking-widest font-mono font-bold text-white/90">
            {agentState}
          </span>
        </div>
      </div>

      {/* Live Canvas Soundwave */}
      <div className="w-full max-w-md mt-6 h-16 flex items-center justify-center">
        <canvas 
          ref={canvasRef} 
          width={400} 
          height={64} 
          className="w-full h-full opacity-85"
        />
      </div>

      {/* Status Label */}
      <div className="mt-2 flex items-center gap-2">
        <span className={`w-2.5 h-2.5 rounded-full animate-ping ${
          agentState === AGENT_STATES.SPEAKING ? 'bg-purple-400' :
          agentState === AGENT_STATES.LISTENING ? 'bg-emerald-400' :
          agentState === AGENT_STATES.CALLING_TOOL ? 'bg-cyan-400' :
          agentState === AGENT_STATES.INTERRUPTED ? 'bg-rose-500' : 'bg-slate-400'
        }`} />
        <span className="text-sm font-semibold text-slate-300 font-sans tracking-wide">
          {orb.label}
        </span>
      </div>
    </div>
  );
}

