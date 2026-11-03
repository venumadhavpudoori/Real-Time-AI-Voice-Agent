import axios from 'axios';

const isLocalhost = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
const baseURL = isLocalhost ? 'http://127.0.0.1:8000' : '';

const apiClient = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json'
  }
});

const API_BASE = '/api';

export const api = {
  // System Health & Info
  getHealth: async () => {
    const res = await apiClient.get('/health');
    return res.data;
  },

  getRoot: async () => {
    const res = await apiClient.get('/');
    return res.data;
  },

  // Reservations
  getReservations: async (params = {}) => {
    const res = await apiClient.get(`${API_BASE}/reservations`, { params });
    return res.data;
  },

  getReservationByCode: async (confirmation_code) => {
    const res = await apiClient.get(`${API_BASE}/reservations/${confirmation_code.trim().toUpperCase()}`);
    return res.data;
  },

  createReservation: async (data) => {
    const res = await apiClient.post(`${API_BASE}/reservations`, data);
    return res.data;
  },

  cancelReservation: async (confirmation_code, customer_phone = null) => {
    const res = await apiClient.post(`${API_BASE}/reservations/cancel`, {
      confirmation_code: confirmation_code.trim().toUpperCase(),
      customer_phone
    });
    return res.data;
  },

  // Tables & Availability
  getTables: async (seating_area = null) => {
    const res = await apiClient.get(`${API_BASE}/tables`, {
      params: seating_area ? { seating_area } : {}
    });
    return res.data;
  },

  checkAvailability: async (date, time, party_size, seating_area = null) => {
    const res = await apiClient.get(`${API_BASE}/tables/check-availability`, {
      params: {
        target_date: date,
        target_time: time,
        party_size,
        seating_area: seating_area || undefined
      }
    });
    return res.data;
  },

  // Menu & Dietary Safety
  getMenu: async (params = {}) => {
    const res = await apiClient.get(`${API_BASE}/menu`, { params });
    return res.data;
  },

  checkDietarySafety: async (dietary_requirements, dish_names = null) => {
    const res = await apiClient.post(`${API_BASE}/menu/check-dietary-safety`, {
      dietary_requirements,
      dish_names
    });
    return res.data;
  },

  // Guardrail Telemetry & Logs
  getGuardrailLogs: async (limit = 50, event_type = null, risk_level = null) => {
    const res = await apiClient.get(`${API_BASE}/guardrails/logs`, { 
      params: { 
        limit, 
        event_type: event_type || undefined, 
        risk_level: risk_level || undefined 
      } 
    });
    return res.data;
  },

  getGuardrailStats: async () => {
    const res = await apiClient.get(`${API_BASE}/guardrails/stats`);
    return res.data;
  },

  testGuardrail: async (text) => {
    const res = await apiClient.post(`${API_BASE}/guardrails/test`, { text });
    return res.data;
  }
};
