import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { 
  Calendar, Users, Phone, AlertCircle, Ban, RefreshCw, 
  CheckCircle2, Utensils, Plus, Search, X, ShieldAlert, Sparkles 
} from 'lucide-react';

export function ReservationDashboard() {
  const [reservations, setReservations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filterDate, setFilterDate] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  // Modals state
  const [showBookModal, setShowBookModal] = useState(false);
  const [lookupCode, setLookupCode] = useState('');
  const [lookupResult, setLookupResult] = useState(null);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [bookingSuccessData, setBookingSuccessData] = useState(null);

  // Form State
  const [formData, setFormData] = useState({
    customer_name: '',
    customer_phone: '',
    party_size: 2,
    reservation_date: new Date(Date.now() + 86400000).toISOString().split('T')[0],
    reservation_time: '19:00',
    seating_area: 'indoor',
    dietary_requirements: '',
    special_requests: ''
  });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState('');

  const loadReservations = async () => {
    setLoading(true);
    try {
      const data = await api.getReservations({
        reservation_date: filterDate || undefined,
        status: filterStatus || undefined
      });
      setReservations(data);
    } catch (err) {
      console.error('Failed to load reservations:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReservations();

    // Listen for live database updates from Voice Agent tool execution
    const handleDbUpdate = (e) => {
      console.log('[ReservationDashboard] Live database update received:', e.detail);
      loadReservations();
    };

    window.addEventListener('database-updated', handleDbUpdate);
    return () => window.removeEventListener('database-updated', handleDbUpdate);
  }, [filterDate, filterStatus]);

  const handleCancel = async (code) => {
    if (!window.confirm(`Are you sure you want to cancel reservation ${code}?`)) return;
    try {
      await api.cancelReservation(code);
      await loadReservations();
      if (lookupResult && lookupResult.confirmation_code === code) {
        setLookupResult(prev => ({ ...prev, status: 'CANCELLED' }));
      }
    } catch (err) {
      alert(`Failed to cancel: ${err.response?.data?.detail || err.message}`);
    }
  };

  const handleLookup = async (e) => {
    e.preventDefault();
    if (!lookupCode.trim()) return;
    setLookupLoading(true);
    setLookupResult(null);
    try {
      const res = await api.getReservationByCode(lookupCode);
      setLookupResult(res);
    } catch (err) {
      alert(`Reservation not found: ${err.response?.data?.detail || err.message}`);
    } finally {
      setLookupLoading(false);
    }
  };

  const handleCreateBooking = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setFormError('');
    try {
      const payload = {
        ...formData,
        party_size: parseInt(formData.party_size, 10),
        reservation_time: formData.reservation_time.length === 5 ? `${formData.reservation_time}:00` : formData.reservation_time
      };
      const created = await api.createReservation(payload);
      setBookingSuccessData(created);
      setShowBookModal(false);
      await loadReservations();
      // Reset form
      setFormData({
        customer_name: '',
        customer_phone: '',
        party_size: 2,
        reservation_date: new Date(Date.now() + 86400000).toISOString().split('T')[0],
        reservation_time: '19:00',
        seating_area: 'indoor',
        dietary_requirements: '',
        special_requests: ''
      });
    } catch (err) {
      setFormError(err.response?.data?.detail || err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const filtered = reservations.filter(r => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      r.customer_name.toLowerCase().includes(query) ||
      r.confirmation_code.toLowerCase().includes(query) ||
      r.customer_phone.includes(query)
    );
  });

  return (
    <div className="bg-slate-900/40 border border-slate-800 rounded-3xl p-6 backdrop-blur-xl shadow-2xl flex flex-col gap-6">
      {/* Header and Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <Utensils className="w-5 h-5 text-purple-400" />
            <span>PostgreSQL Reservation Registry</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time bookings synchronized with SQL relational tables & allergen safety flags
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowBookModal(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-md shadow-purple-600/30 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>New Reservation</span>
          </button>

          <button
            onClick={loadReservations}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Filter & Code Lookup Row */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
        <div className="md:col-span-4">
          <input
            type="text"
            placeholder="Search by name, code, or phone..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950/70 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-purple-500"
          />
        </div>
        <div className="md:col-span-3">
          <input
            type="date"
            value={filterDate}
            onChange={(e) => setFilterDate(e.target.value)}
            className="w-full bg-slate-950/70 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-purple-500"
          />
        </div>
        <div className="md:col-span-2">
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="w-full bg-slate-950/70 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-purple-500"
          >
            <option value="">All Statuses</option>
            <option value="CONFIRMED">CONFIRMED</option>
            <option value="CANCELLED">CANCELLED</option>
          </select>
        </div>
        <form onSubmit={handleLookup} className="md:col-span-3 flex gap-2">
          <input
            type="text"
            placeholder="Lookup Code (e.g. RES-DEMO01)"
            value={lookupCode}
            onChange={(e) => setLookupCode(e.target.value)}
            className="w-full bg-slate-950/70 border border-slate-800 rounded-xl px-3 py-2.5 text-xs text-slate-200 placeholder-slate-500 uppercase font-mono focus:outline-none focus:border-purple-500"
          />
          <button
            type="submit"
            disabled={lookupLoading || !lookupCode.trim()}
            className="px-3 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl border border-slate-700 text-xs font-semibold"
          >
            <Search className="w-3.5 h-3.5" />
          </button>
        </form>
      </div>

      {/* Lookup Card Preview if searched */}
      {lookupResult && (
        <div className="p-4 rounded-2xl bg-slate-950/90 border border-purple-500/50 flex flex-wrap items-center justify-between gap-4 shadow-xl">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-600/20 border border-purple-500/40 flex items-center justify-center">
              <Utensils className="w-5 h-5 text-purple-300" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono font-bold text-sm text-purple-300">{lookupResult.confirmation_code}</span>
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full font-bold ${
                  lookupResult.status === 'CONFIRMED' ? 'bg-emerald-950 text-emerald-300 border border-emerald-700' : 'bg-red-950 text-red-300 border border-red-700'
                }`}>
                  {lookupResult.status}
                </span>
              </div>
              <div className="text-xs text-slate-300 mt-0.5">
                {lookupResult.customer_name} • Party of {lookupResult.party_size} on {lookupResult.reservation_date} at {lookupResult.reservation_time}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {lookupResult.status !== 'CANCELLED' && (
              <button
                onClick={() => handleCancel(lookupResult.confirmation_code)}
                className="px-3 py-1.5 rounded-lg bg-red-950/80 hover:bg-red-900 border border-red-800 text-red-200 text-xs font-semibold"
              >
                Cancel Booking
              </button>
            )}
            <button
              onClick={() => setLookupResult(null)}
              className="p-1.5 text-slate-400 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Booking Created Alert Modal */}
      {bookingSuccessData && (
        <div className="p-4 rounded-2xl bg-emerald-950/80 border border-emerald-700 text-emerald-100 flex items-start justify-between gap-3 shadow-xl">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <div className="font-bold text-sm">
                Reservation Confirmed! Reference: <span className="font-mono text-emerald-300">{bookingSuccessData.confirmation_code}</span>
              </div>
              <p className="text-xs text-emerald-200/90 mt-1">
                Booked for {bookingSuccessData.customer_name} (Party of {bookingSuccessData.party_size}) on {bookingSuccessData.reservation_date} at {bookingSuccessData.reservation_time} at Table {bookingSuccessData.table?.table_number || 'Reserved'}.
              </p>
              {bookingSuccessData.allergy_level && bookingSuccessData.allergy_level !== 'NONE' && (
                <div className="mt-2 text-xs text-rose-300 bg-black/40 px-3 py-1.5 rounded-lg border border-rose-800/80 font-mono">
                  🚨 Kitchen Safety Notice: Guest flagged with {bookingSuccessData.allergy_level}. Utensils sanitized.
                </div>
              )}
            </div>
          </div>
          <button
            onClick={() => setBookingSuccessData(null)}
            className="text-emerald-400 hover:text-white"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Table List */}
      <div className="overflow-x-auto rounded-2xl border border-slate-800/80">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-950/80 text-slate-400 font-mono uppercase text-[11px] border-b border-slate-800">
            <tr>
              <th className="py-3 px-4">Code</th>
              <th className="py-3 px-4">Customer</th>
              <th className="py-3 px-4">Date & Time</th>
              <th className="py-3 px-4">Party & Table</th>
              <th className="py-3 px-4">Dietary & Allergies</th>
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-sans">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-slate-500">
                  {loading ? 'Fetching reservations from PostgreSQL...' : 'No reservations found.'}
                </td>
              </tr>
            ) : (
              filtered.map((res) => {
                const isCancelled = res.status === 'CANCELLED';
                const isSevereAllergy = res.allergy_level === 'SEVERE_ANAPHYLAXIS';
                const hasAllergy = res.allergy_level && res.allergy_level !== 'NONE';

                return (
                  <tr key={res.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3.5 px-4 font-mono font-bold text-purple-300">
                      {res.confirmation_code}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-200">{res.customer_name}</div>
                      <div className="text-[11px] text-slate-500 flex items-center gap-1 font-mono">
                        <Phone className="w-3 h-3" />
                        <span>{res.customer_phone}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-1 text-slate-200 font-medium">
                        <Calendar className="w-3.5 h-3.5 text-slate-400" />
                        <span>{res.reservation_date}</span>
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono">
                        {res.reservation_time} (90 mins)
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-1.5 font-semibold text-slate-200">
                        <Users className="w-3.5 h-3.5 text-slate-400" />
                        <span>{res.party_size} Guests</span>
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono">
                        {res.table ? `${res.table.table_number} (${res.table.seating_area})` : 'Assigned'}
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      {hasAllergy ? (
                        <div className="flex flex-col gap-1 max-w-[200px]">
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider font-mono ${
                            isSevereAllergy 
                              ? 'bg-rose-950 border border-rose-700 text-rose-300 animate-pulse'
                              : 'bg-amber-950 border border-amber-700 text-amber-300'
                          }`}>
                            <AlertCircle className="w-3 h-3" />
                            {res.allergy_level.replace('_', ' ')}
                          </span>
                          <span className="text-[11px] text-slate-300 truncate">
                            {res.dietary_requirements}
                          </span>
                        </div>
                      ) : (
                        <span className="text-slate-500 text-[11px]">None specified</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold font-mono ${
                        isCancelled
                          ? 'bg-slate-800 text-slate-400 border border-slate-700'
                          : 'bg-emerald-950 border border-emerald-700 text-emerald-300'
                      }`}>
                        {isCancelled ? <Ban className="w-3 h-3" /> : <CheckCircle2 className="w-3 h-3" />}
                        {res.status}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      {!isCancelled && (
                        <button
                          onClick={() => handleCancel(res.confirmation_code)}
                          className="px-2.5 py-1 rounded-lg bg-red-950/60 hover:bg-red-900 border border-red-800/80 text-red-300 text-[11px] font-semibold transition-colors"
                        >
                          Cancel
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Manual Booking Modal Dialog */}
      {showBookModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 max-w-lg w-full shadow-2xl relative flex flex-col gap-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="font-bold text-base text-slate-100 flex items-center gap-2">
                <Utensils className="w-4 h-4 text-purple-400" />
                <span>Create Direct Reservation</span>
              </h3>
              <button
                onClick={() => setShowBookModal(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="p-3 rounded-xl bg-rose-950/80 border border-rose-700 text-rose-200 text-xs">
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateBooking} className="grid grid-cols-2 gap-3 text-xs">
              <div className="col-span-1 flex flex-col gap-1">
                <label className="text-slate-400 font-semibold">Customer Full Name *</label>
                <input
                  type="text"
                  required
                  value={formData.customer_name}
                  onChange={(e) => setFormData({ ...formData, customer_name: e.target.value })}
                  placeholder="e.g. Sarah Connor"
                  className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-purple-500"
                />
              </div>

              <div className="col-span-1 flex flex-col gap-1">
                <label className="text-slate-400 font-semibold">Phone Number *</label>
                <input
                  type="text"
                  required
                  value={formData.customer_phone}
                  onChange={(e) => setFormData({ ...formData, customer_phone: e.target.value })}
                  placeholder="e.g. (555) 123-4567"
                  className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-purple-500"
                />
              </div>

              <div className="col-span-1 flex flex-col gap-1">
                <label className="text-slate-400 font-semibold">Date *</label>
                <input
                  type="date"
                  required
                  value={formData.reservation_date}
                  onChange={(e) => setFormData({ ...formData, reservation_date: e.target.value })}
                  className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-purple-500"
                />
              </div>

              <div className="col-span-1 flex flex-col gap-1">
                <label className="text-slate-400 font-semibold">Time *</label>
                <input
                  type="time"
                  required
                  value={formData.reservation_time}
                  onChange={(e) => setFormData({ ...formData, reservation_time: e.target.value })}
                  className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-purple-500"
                />
              </div>

              <div className="col-span-1 flex flex-col gap-1">
                <label className="text-slate-400 font-semibold">Guests Count (1 - 12) *</label>
                <input
                  type="number"
                  min={1}
                  max={12}
                  required
                  value={formData.party_size}
                  onChange={(e) => setFormData({ ...formData, party_size: e.target.value })}
                  className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-purple-500"
                />
              </div>

              <div className="col-span-1 flex flex-col gap-1">
                <label className="text-slate-400 font-semibold">Seating Section</label>
                <select
                  value={formData.seating_area}
                  onChange={(e) => setFormData({ ...formData, seating_area: e.target.value })}
                  className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-purple-500"
                >
                  <option value="indoor">Indoor Dining Room</option>
                  <option value="patio">Outdoor Patio</option>
                  <option value="private_room">Private Room</option>
                </select>
              </div>

              <div className="col-span-2 flex flex-col gap-1">
                <label className="text-slate-400 font-semibold flex items-center justify-between">
                  <span>Dietary Requirements & Allergies</span>
                  <span className="text-[10px] text-purple-400">🛡️ Auto-evaluated by Safety Guardrail</span>
                </label>
                <input
                  type="text"
                  value={formData.dietary_requirements}
                  onChange={(e) => setFormData({ ...formData, dietary_requirements: e.target.value })}
                  placeholder="e.g. Severe peanut allergy, celiac disease, vegan..."
                  className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-purple-500"
                />
              </div>

              <div className="col-span-2 flex flex-col gap-1">
                <label className="text-slate-400 font-semibold">Special Requests</label>
                <input
                  type="text"
                  value={formData.special_requests}
                  onChange={(e) => setFormData({ ...formData, special_requests: e.target.value })}
                  placeholder="e.g. Birthday celebration, booth seating..."
                  className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-purple-500"
                />
              </div>

              <div className="col-span-2 flex items-center justify-end gap-3 pt-3 border-t border-slate-800 mt-2">
                <button
                  type="button"
                  onClick={() => setShowBookModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:text-white text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-md shadow-purple-600/30 transition-all"
                >
                  {submitting ? 'Confirming in SQL...' : 'Book Table'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
