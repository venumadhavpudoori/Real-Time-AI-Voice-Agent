import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { LayoutGrid, Armchair, CheckCircle2, XCircle, Search, Sparkles, Plus, Clock } from 'lucide-react';

export function TableAvailability({ onQuickReserve = null }) {
  const [tables, setTables] = useState([]);
  const [loading, setLoading] = useState(false);
  const [checkDate, setCheckDate] = useState(() => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    return tomorrow.toISOString().split('T')[0];
  });
  const [checkTime, setCheckTime] = useState('19:00');
  const [partySize, setPartySize] = useState(4);
  const [seatingArea, setSeatingArea] = useState('all');
  const [activeAreaTab, setActiveAreaTab] = useState('all');
  const [checkResult, setCheckResult] = useState(null);
  const [checking, setChecking] = useState(false);

  const loadTables = async () => {
    setLoading(true);
    try {
      const data = await api.getTables(activeAreaTab === 'all' ? null : activeAreaTab);
      setTables(data);
    } catch (err) {
      console.error('Failed to load tables:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTables();

    const handleUpdate = () => {
      loadTables();
    };
    window.addEventListener('database-updated', handleUpdate);
    return () => window.removeEventListener('database-updated', handleUpdate);
  }, [activeAreaTab]);

  const handleCheck = async (e) => {
    e?.preventDefault();
    setChecking(true);
    try {
      const res = await api.checkAvailability(
        checkDate,
        checkTime,
        partySize,
        seatingArea === 'all' ? null : seatingArea
      );
      setCheckResult(res);
    } catch (err) {
      setCheckResult({
        available: false,
        message: err.response?.data?.detail || err.message
      });
    } finally {
      setChecking(false);
    }
  };

  // Group tables by seating area
  const tablesByArea = tables.reduce((acc, t) => {
    acc[t.seating_area] = acc[t.seating_area] || [];
    acc[t.seating_area].push(t);
    return acc;
  }, {});

  return (
    <div className="bg-slate-900/40 border border-slate-800 rounded-3xl p-6 backdrop-blur-xl shadow-2xl flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <LayoutGrid className="w-5 h-5 text-purple-400" />
            <span>Floor Plan & Real-Time Availability SQL Query</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            PostgreSQL relational table capacity, zoning, and live occupancy evaluation
          </p>
        </div>

        {/* Section Filter Pills */}
        <div className="flex items-center gap-1.5 p-1 bg-slate-950/70 border border-slate-800 rounded-xl">
          {['all', 'indoor', 'patio', 'private_room'].map((area) => (
            <button
              key={area}
              onClick={() => setActiveAreaTab(area)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider font-mono transition-all ${
                activeAreaTab === area
                  ? 'bg-purple-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {area.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Availability Tool Simulation Form */}
      <form onSubmit={handleCheck} className="p-4 bg-slate-950/70 border border-slate-800 rounded-2xl flex flex-wrap items-end gap-3 text-xs">
        <div className="flex flex-col gap-1">
          <label className="text-slate-400 font-semibold font-mono">Date</label>
          <input
            type="date"
            value={checkDate}
            onChange={(e) => setCheckDate(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-purple-500"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-slate-400 font-semibold font-mono">Time</label>
          <input
            type="time"
            value={checkTime}
            onChange={(e) => setCheckTime(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-purple-500"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-slate-400 font-semibold font-mono">Guests</label>
          <input
            type="number"
            min={1}
            max={12}
            value={partySize}
            onChange={(e) => setPartySize(parseInt(e.target.value) || 1)}
            className="w-20 bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-purple-500 font-mono"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-slate-400 font-semibold font-mono">Area</label>
          <select
            value={seatingArea}
            onChange={(e) => setSeatingArea(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-purple-500"
          >
            <option value="all">Any Area</option>
            <option value="indoor">Indoor Dining Room</option>
            <option value="patio">Patio</option>
            <option value="private_room">Private Room</option>
          </select>
        </div>
        <button
          type="submit"
          disabled={checking}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-semibold transition-all shadow-md shadow-purple-600/30"
        >
          <Search className="w-3.5 h-3.5" />
          <span>{checking ? 'Checking PostgreSQL...' : 'Query Availability'}</span>
        </button>
      </form>

      {/* Check Availability Result banner */}
      {checkResult && (
        <div className={`p-5 rounded-2xl border text-xs flex flex-wrap items-center justify-between gap-4 shadow-lg ${
          checkResult.available 
            ? 'bg-emerald-950/40 border-emerald-800 text-emerald-200' 
            : 'bg-rose-950/40 border-rose-800 text-rose-200'
        }`}>
          <div className="flex items-start gap-3">
            {checkResult.available ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
            ) : (
              <XCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            )}
            <div>
              <div className="font-bold text-sm">
                {checkResult.available ? 'Table Available!' : 'No Matching Table Available'}
              </div>
              <div className="mt-1 text-slate-300 leading-relaxed">
                {checkResult.message}
              </div>
              {checkResult.alternative_times?.length > 0 && (
                <div className="mt-2 text-slate-400 flex items-center gap-1.5 font-mono">
                  <Clock className="w-3.5 h-3.5 text-amber-400" />
                  <span>Alternative slots: {checkResult.alternative_times.join(', ')}</span>
                </div>
              )}
            </div>
          </div>

          {checkResult.available && checkResult.matched_table && (
            <div className="flex items-center gap-3">
              <div className="text-right">
                <span className="text-[10px] uppercase font-mono text-emerald-400 font-bold block">Assigned Table</span>
                <span className="font-mono font-bold text-lg text-white">Table {checkResult.matched_table.table_number}</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Seating Areas Grid */}
      <div className="space-y-6">
        {Object.entries(tablesByArea).map(([area, areaTables]) => (
          <div key={area} className="space-y-2">
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-purple-500" />
              <span>{area.replace('_', ' ')} Dining Section</span>
              <span className="text-[10px] text-slate-500">({areaTables.length} Tables)</span>
            </h3>

            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
              {areaTables.map((t) => {
                const isMatched = checkResult?.available && checkResult?.matched_table?.id === t.id;

                return (
                  <div
                    key={t.id}
                    className={`bg-slate-950/60 border rounded-2xl p-4 flex flex-col justify-between transition-all shadow-sm ${
                      isMatched 
                        ? 'border-emerald-500 ring-2 ring-emerald-500/30 bg-emerald-950/30' 
                        : 'border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className={`font-mono font-bold text-base ${isMatched ? 'text-emerald-300' : 'text-purple-300'}`}>
                        {t.table_number}
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-300">
                        {t.capacity} Seats
                      </span>
                    </div>

                    <div className="mt-3 text-slate-400 text-xs flex items-center justify-between">
                      <span className="text-[11px] font-mono">Min {t.min_capacity}p</span>
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                        isMatched ? 'bg-emerald-900/60 text-emerald-200 font-bold' : 'bg-slate-900 text-slate-500'
                      }`}>
                        {isMatched ? 'Matched' : 'Active'}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
