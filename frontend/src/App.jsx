import React, { useState, useEffect } from 'react';
import { useVoiceAgent } from './hooks/useVoiceAgent';
import { useAudioVisualizer } from './hooks/useAudioVisualizer';
import { VoiceVisualizer } from './components/VoiceVisualizer';
import { VoiceController } from './components/VoiceController';
import { ConversationFeed } from './components/ConversationFeed';
import { ReservationDashboard } from './components/ReservationDashboard';
import { TableAvailability } from './components/TableAvailability';
import { MenuAllergenCatalog } from './components/MenuAllergenCatalog';
import { GuardrailMonitor } from './components/GuardrailMonitor';
import { api } from './services/api';
import { Mic, Utensils, LayoutGrid, Salad, Shield, Database, CheckCircle2, AlertTriangle } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('concierge');
  const [backendHealth, setBackendHealth] = useState(null);
  
  const {
    agentState,
    messages,
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
  } = useVoiceAgent();

  const { audioLevel } = useAudioVisualizer(isMicActive);

  // Poll backend health API
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const data = await api.getHealth();
        setBackendHealth(data);
      } catch (err) {
        console.warn('Backend health check pending:', err.message);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  // Global keyboard shortcut: Esc or Space to Barge-in when agent speaks
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        interruptAgent();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [interruptAgent]);

  const navTabs = [
    { id: 'concierge', label: 'Voice Concierge', icon: Mic },
    { id: 'reservations', label: 'Reservations', icon: Utensils },
    { id: 'tables', label: 'Tables & Floor Plan', icon: LayoutGrid },
    { id: 'menu', label: 'Menu & Allergens', icon: Salad },
    { id: 'guardrails', label: 'Safety Guardrails', icon: Shield },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Header */}
      <header className="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
          {/* Logo / Title */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-2xl bg-gradient-to-tr from-purple-600 to-indigo-500 flex items-center justify-center shadow-md shadow-purple-500/20">
              <Mic className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-extrabold text-base tracking-tight bg-gradient-to-r from-white via-slate-200 to-purple-300 bg-clip-text text-transparent">
                Grand Bistro AI Voice Concierge
              </h1>
              <p className="text-[11px] font-mono text-purple-400">
                PostgreSQL • FastAPI • Real-Time Voice • Safety Guardrails
              </p>
            </div>
          </div>

          {/* Connection & Telemetry Status Badges */}
          <div className="flex items-center gap-2.5">
            {/* Database indicator */}
            <div className="hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-950/80 border border-slate-800 text-xs font-mono text-slate-300">
              <Database className="w-3.5 h-3.5 text-purple-400" />
              <span>
                {backendHealth?.database ? `${backendHealth.database.toUpperCase()} Online` : 'Database Online'}
              </span>
            </div>

            {/* Guardrail active indicator */}
            <div className="hidden md:flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-950/80 border border-slate-800 text-xs font-mono text-emerald-400">
              <Shield className="w-3.5 h-3.5 text-emerald-400" />
              <span>Guardrails Active</span>
            </div>

            {/* WebSocket connection status badge */}
            <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-slate-950/80 border border-slate-800 text-xs font-mono">
              {wsConnected ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-emerald-400">WebSocket Live</span>
                </>
              ) : (
                <>
                  <span className="w-2 h-2 rounded-full bg-rose-500" />
                  <span className="text-rose-400">Reconnecting...</span>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 flex flex-col gap-6">
        {/* Navigation Tabs Bar */}
        <div className="flex overflow-x-auto gap-2 p-1.5 bg-slate-900/60 border border-slate-800 rounded-2xl backdrop-blur-md">
          {navTabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold whitespace-nowrap transition-all duration-200 ${
                  isActive
                    ? 'bg-purple-600 text-white shadow-md shadow-purple-600/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Tab 1: Voice Concierge */}
        {activeTab === 'concierge' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Left Column: Visualizer & Controller (5 cols) */}
            <div className="lg:col-span-5 flex flex-col gap-6">
              <VoiceVisualizer agentState={agentState} audioLevel={audioLevel} />
              <VoiceController
                agentState={agentState}
                isMicActive={isMicActive}
                toggleMicrophone={toggleMicrophone}
                interruptAgent={interruptAgent}
                sendTextMessage={sendTextMessage}
                resetSession={resetSession}
                interimTranscript={interimTranscript}
                autoListenContinuous={autoListenContinuous}
                setAutoListenContinuous={setAutoListenContinuous}
                voiceEngine={voiceEngine}
                setVoiceEngine={setVoiceEngine}
              />
            </div>

            {/* Right Column: Live Conversation Feed (7 cols) */}
            <div className="lg:col-span-7">
              <ConversationFeed messages={messages} />
            </div>
          </div>
        )}

        {/* Tab 2: PostgreSQL Reservations */}
        {activeTab === 'reservations' && <ReservationDashboard />}

        {/* Tab 3: Tables & Floor Plan */}
        {activeTab === 'tables' && <TableAvailability />}

        {/* Tab 4: Menu & Allergen Catalog */}
        {activeTab === 'menu' && <MenuAllergenCatalog />}

        {/* Tab 5: Safety Guardrails Telemetry */}
        {activeTab === 'guardrails' && <GuardrailMonitor />}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 py-4 text-center text-xs text-slate-500 font-mono">
        Real-Time AI Voice Agent Architecture • Tech Stack: PostgreSQL, FastAPI, ReactJS, Web Speech API & Web Audio
      </footer>
    </div>
  );
}
