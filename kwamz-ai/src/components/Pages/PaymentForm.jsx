import React, { useState } from 'react';
import { CreditCard, AlertCircle, Loader2, X } from 'lucide-react';
import config from "../../Config";

const API_BASE_URL = config.API_URL || 'http://localhost:5000';

const pesapalApi = {
  getAuthToken: () => localStorage.getItem('token'),
  
  async createPayment(data) {
    const token = this.getAuthToken();
    const headers = {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
    };

    const response = await fetch(`${API_BASE_URL}/payment/create`, {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Request failed' }));
      throw new Error(error.error || error.message || 'Something went wrong');
    }

    return response.json();
  },
};

const PaymentForm = ({ onSuccess, userInfo }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [iframeUrl, setIframeUrl] = useState('');

  const [formData, setFormData] = useState({
    amount: '100',
    currency: 'KES',
    description: 'Monthly Subscription Payment',
    customer_email: userInfo?.email || '',
    customer_phone: userInfo?.phone || '',
    customer_first_name: userInfo?.first_name || '',
    customer_last_name: userInfo?.last_name || '',
  });

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    setError(null);
  };

  // MODIFIED: Open modal with iframe instead of redirect
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await pesapalApi.createPayment({
        user_id: userInfo?.id,
        ...formData,
        amount: parseFloat(formData.amount),
      });

      if (response.success && response.redirect_url) {
        setIframeUrl(response.redirect_url);
        setModalOpen(true); // Open modal
      } else {
        setError('Failed to initiate payment');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const closeModal = () => {
    setModalOpen(false);
    setIframeUrl('');
  };

  return (
    <>
      {/* ==================== ORIGINAL FORM ==================== */}
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 p-6 flex items-center justify-center">
        <div className="w-full max-w-2xl bg-white rounded-xl shadow-lg p-8">
          <div className="flex items-center gap-3 mb-8">
            <div className="p-3 bg-blue-100 rounded-lg">
              <CreditCard className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gray-800">Make Payment</h2>
              <p className="text-sm text-gray-600">Complete your subscription payment</p>
            </div>
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          <div className="space-y-5">
            {/* ... all your input fields ... */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Amount</label>
                <input type="number" name="amount" value={formData.amount} onChange={handleChange} required min="1" step="0.01"
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Currency</label>
                <select name="currency" value={formData.currency} onChange={handleChange}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all">
                  <option value="KES">KES - Kenyan Shilling</option>
                  <option value="USD">USD - US Dollar</option>
                  <option value="EUR">EUR - Euro</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Description</label>
              <input type="text" name="description" value={formData.description} onChange={handleChange} required
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all" />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">First Name</label>
                <input type="text" name="customer_first_name" value={formData.customer_first_name} onChange={handleChange} required
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Last Name</label>
                <input type="text" name="customer_last_name" value={formData.customer_last_name} onChange={handleChange} required
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all" />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Email Address</label>
              <input type="email" name="customer_email" value={formData.customer_email} onChange={handleChange} required
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all" />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Phone Number</label>
              <input type="tel" name="customer_phone" value={formData.customer_phone} onChange={handleChange} required placeholder="+254712345678"
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all" />
            </div>

            <button
              onClick={handleSubmit}
              disabled={loading}
              className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold py-3.5 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-lg hover:shadow-xl"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Processing Payment...
                </>
              ) : (
                <>
                  <CreditCard className="w-5 h-5" />
                  Proceed to Payment
                </>
              )}
            </button>

            <p className="text-xs text-center text-gray-500 mt-4">
              Your payment is secured by Pesapal
            </p>
          </div>
        </div>
      </div>

      {/* ==================== MODAL WITH IFRAME ==================== */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-60">
          <div className="relative w-full max-w-3xl bg-white rounded-xl shadow-2xl overflow-hidden">
            {/* Header */}
            <div className="flex justify-between items-center p-4 border-b bg-gray-50">
              <h3 className="text-lg font-semibold text-gray-800">Complete Payment</h3>
              <button
                onClick={closeModal}
                className="text-gray-500 hover:text-gray-700 text-2xl font-bold"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            {/* iframe */}
            <div className="h-96 md:h-[600px]">
              <iframe
                src={iframeUrl}
                title="Pesapal Payment"
                className="w-full h-full border-0"
                allow="payment"
                sandbox="allow-scripts allow-same-origin allow-forms allow-modals allow-popups"
              />
            </div>

            {/* Footer */}
            <div className="p-4 border-t bg-gray-50 text-center">
              <button
                onClick={closeModal}
                className="px-6 py-2 bg-red-600 hover:bg-red-700 text-white font-medium rounded-lg transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default PaymentForm;