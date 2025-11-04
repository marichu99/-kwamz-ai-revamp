import config from "../Config";
const API_BASE_URL = config.API_URL || 'http://localhost:5000';

export const pesapalApi = {
  getAuthToken: () => localStorage.getItem('token'),
  
  setAuthToken: (token) => localStorage.setItem('token', token),
  
  clearAuthToken: () => localStorage.removeItem('token'),
  
  async request(endpoint, options = {}) {
    const token = this.getAuthToken();
    const headers = {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
      ...options.headers,
    };

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Request failed' }));
      throw new Error(error.error || error.message || 'Something went wrong');
    }

    return response.json();
  },

  // Payment endpoints
  createPayment: (data) => pesapalApi.request('/payment/create', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  getPayments: () => pesapalApi.request('/get-payments', {
    method: 'GET',
  }),

  getLatestPayment: () => pesapalApi.request('/get-latest-payment', {
    method: 'GET',
  }),

  getPaymentStatus: (merchantReference) => 
    pesapalApi.request(`/payment/status/${merchantReference}`),

  initiateRefund: (data) => pesapalApi.request('/payment/refund', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
};