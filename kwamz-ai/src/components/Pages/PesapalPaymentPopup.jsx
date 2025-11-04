import React, { useState, useRef, useEffect, useCallback } from 'react';
import axios from 'axios';

export default function PesapalPaymentPopup({ userInfo }) {
  const [amount, setAmount] = useState('100');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('idle'); 

  const popupRef = useRef(null);
  const pollInterval = useRef(null);
  const checkClose = useRef(null);

  // Open centered popup + inject close button
  const openPopup = useCallback((url, orderId) => {
    const w = 520, h = 720;
    const left = window.screenX + (window.outerWidth - w) / 2;
    const top = window.screenY + (window.outerHeight - h) / 2;

    const popup = window.open(
      url,
      `pesapal_${orderId}`,
      `width=${w},height=${h},left=${left},top=${top},scrollbars=yes,resizable=yes`
    );

    if (!popup) {
      setError('Popup blocked. Allow popups and try again.');
      return;
    }

    popupRef.current = popup;

    // Inject close button when page loads
    const inject = setInterval(() => {
      if (popup.document.readyState === 'complete') {
        clearInterval(inject);

        // Prevent duplicate injection
        if (popup.document.getElementById('pesapal-close')) return;

        const overlay = popup.document.createElement('div');
        overlay.id = 'pesapal-close';
        overlay.innerHTML = `
          <div class="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50">
            <div class="bg-white p-6 rounded-lg shadow-xl text-center">
              <p class="text-lg font-semibold mb-4">Close Payment?</p>
              <button 
                class="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-6 rounded"
                onclick="window.close()"
              >
                Close
              </button>
            </div>
          </div>
        `;
        popup.document.body.appendChild(overlay);
      }
    }, 100);
  }, []);

  // Start polling when popup closes
  const startPolling = useCallback((orderId) => {
    setStatus('checking');

    const poll = async () => {
      try {
        const res = await axios.get(`/api/payment/status/${orderId}`);
        const paymentStatus = res.data.status;

        if (paymentStatus === 'COMPLETED') {
          setStatus('success');
          clearInterval(pollInterval.current);
        } else if (['FAILED', 'CANCELLED'].includes(paymentStatus)) {
          setStatus('failed');
          clearInterval(pollInterval.current);
        }
      } catch (err) {
        console.warn('Polling error:', err);
      }
    };

    poll(); // first check
    pollInterval.current = setInterval(poll, 3000);
  }, []);

  // Watch popup close
  useEffect(() => {
    if (!popupRef.current) return;

    checkClose.current = setInterval(() => {
      if (popupRef.current.closed) {
        const orderId = popupRef.current.name.replace('pesapal_', '');
        if (orderId) startPolling(orderId);
        clearInterval(checkClose.current);
        popupRef.current = null;
      }
    }, 500);

    return () => {
      if (checkClose.current) clearInterval(checkClose.current);
      if (pollInterval.current) clearInterval(pollInterval.current);
    };
  }, [startPolling]);

  // Submit payment
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setStatus('idle');
    if (pollInterval.current) clearInterval(pollInterval.current);

    try {
      const res = await axios.post('/api/payment/initiate', {
        user_id: userInfo.id,
        amount: parseFloat(amount),
        description: 'Monthly Subscription',
        currency: 'KES',
      });

      const { success, redirect_url, order_id } = res.data;

      if (success && redirect_url && order_id) {
        openPopup(redirect_url, order_id);
      } else {
        setError('Failed to start payment');
      }
    } catch (err) {
      setError(err.response?.data?.message || err.message || 'Network error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto p-6 bg-white rounded-xl shadow-lg">
      <h2 className="text-2xl font-bold text-center mb-6 text-gray-800">
        Subscribe with Pesapal
      </h2>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Amount (KES)
          </label>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            min="1"
            required
            disabled={loading}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
          />
        </div>

        <button
          type="submit"
          disabled={loading || status === 'checking'}
          className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-semibold rounded-lg transition duration-200"
        >
          {loading ? 'Processing...' : 'Pay with Pesapal'}
        </button>

        {error && (
          <p className="text-red-600 text-sm bg-red-50 p-3 rounded-lg">{error}</p>
        )}

        {status === 'checking' && (
          <p className="text-blue-600 text-sm bg-blue-50 p-3 rounded-lg flex items-center">
            <svg className="animate-spin h-4 w-4 mr-2" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
            </svg>
            Checking payment status...
          </p>
        )}

        {status === 'success' && (
          <p className="text-green-600 text-sm bg-green-50 p-3 rounded-lg font-semibold">
            Payment successful! Welcome aboard!
          </p>
        )}

        {status === 'failed' && (
          <p className="text-red-600 text-sm bg-red-50 p-3 rounded-lg">
            Payment failed or was cancelled.
          </p>
        )}
      </form>
    </div>
  );
}