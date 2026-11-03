import React, { useEffect, useRef } from 'react';
import { Bot, User, ShieldAlert, Wrench, AlertTriangle, CheckCircle, Zap } from 'lucide-react';

export function ConversationFeed({ messages = [] }) {
  const feedEndRef = useRef(null);

  useEffect(() => {
    feedEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex flex-col h-[480px] bg-slate-900/40 border border-slate-800 rounded-3xl p-6 backdrop-blur-xl overflow-hidden shadow-2xl">
      <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
          <span>Live Conversation & Tool Telemetry</span>
        </h3>
        <span className="text-xs text-slate-500 font-mono">
          {messages.length} Events
        </span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-4 pr-2">
        {messages.map((msg) => {
          if (msg.sender === 'user') {
            return (
              <div key={msg.id} className="flex items-start justify-end gap-3">
                <div className="flex flex-col items-end max-w-[80%]">
                  <div className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-4 py-3 rounded-2xl rounded-tr-none text-sm shadow-md">
                    {msg.text}
                  </div>
                  <span className="text-[10px] text-slate-500 mt-1 font-mono">{msg.timestamp}</span>
                </div>
                <div className="w-8 h-8 rounded-full bg-purple-500/20 border border-purple-400/30 flex items-center justify-center shrink-0">
                  <User className="w-4 h-4 text-purple-300" />
                </div>
              </div>
            );
          }

          if (msg.sender === 'agent') {
            return (
              <div key={msg.id} className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-full bg-indigo-600/30 border border-indigo-400/40 flex items-center justify-center shrink-0">
                  <Bot className="w-4 h-4 text-indigo-300" />
                </div>
                <div className="flex flex-col max-w-[85%]">
                  <div className="bg-slate-800/90 border border-slate-700/80 text-slate-100 px-4 py-3 rounded-2xl rounded-tl-none text-sm leading-relaxed shadow-sm">
                    {msg.text}
                  </div>
                  <span className="text-[10px] text-slate-500 mt-1 font-mono">{msg.timestamp}</span>
                </div>
              </div>
            );
          }

          if (msg.type === 'tool_start') {
            return (
              <div key={msg.id} className="flex items-center gap-3 bg-cyan-950/30 border border-cyan-800/40 rounded-xl px-4 py-2 text-xs text-cyan-200">
                <Wrench className="w-4 h-4 text-cyan-400 shrink-0 animate-spin" />
                <div className="flex-1">
                  <span className="font-mono font-bold text-cyan-300">Tool Executing:</span>{' '}
                  <span className="font-mono">{msg.tool.name}</span>
                  {msg.tool.args && (
                    <span className="text-cyan-400/70 ml-2">
                      ({Object.entries(msg.tool.args).map(([k, v]) => `${k}: ${v}`).join(', ')})
                    </span>
                  )}
                </div>
              </div>
            );
          }

          if (msg.type === 'tool_result') {
            return (
              <div key={msg.id} className="flex items-center gap-3 bg-emerald-950/30 border border-emerald-800/40 rounded-xl px-4 py-2 text-xs text-emerald-200">
                <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
                <div className="flex-1 truncate">
                  <span className="font-mono font-bold text-emerald-300">Tool Result:</span>{' '}
                  <span className="font-mono">{msg.tool.name}</span> &rarr;{' '}
                  <span className="text-emerald-400/80">
                    {msg.tool.result?.message || 'Success'}
                  </span>
                </div>
              </div>
            );
          }

          if (msg.type === 'guardrail') {
            const isSevere = msg.guardrail?.risk === 'CRITICAL' || msg.guardrail?.risk === 'HIGH';
            return (
              <div key={msg.id} className={`flex items-start gap-3 rounded-xl px-4 py-3 text-xs border ${
                isSevere 
                  ? 'bg-rose-950/40 border-rose-700/60 text-rose-200' 
                  : 'bg-amber-950/40 border-amber-700/60 text-amber-200'
              }`}>
                <ShieldAlert className={`w-4 h-4 shrink-0 mt-0.5 ${isSevere ? 'text-rose-400' : 'text-amber-400'}`} />
                <div className="flex-1">
                  <div className="font-bold flex items-center gap-2">
                    <span>🛡️ Guardrail Intercept:</span>
                    <span className="uppercase text-[10px] px-2 py-0.5 rounded bg-black/40 font-mono">
                      {msg.guardrail?.type}
                    </span>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-rose-900/60 text-rose-300">
                      {msg.guardrail?.risk} RISK
                    </span>
                  </div>
                  <div className="mt-1 text-slate-300 leading-snug">
                    {msg.text}
                  </div>
                </div>
              </div>
            );
          }

          if (msg.type === 'interrupt') {
            return (
              <div key={msg.id} className="flex items-center justify-center gap-2 py-1.5 px-4 rounded-lg bg-red-950/50 border border-red-800/50 text-red-300 text-xs font-mono">
                <Zap className="w-3.5 h-3.5 text-amber-400" />
                <span>{msg.text}</span>
              </div>
            );
          }

          return null;
        })}
        <div ref={feedEndRef} />
      </div>
    </div>
  );
}

