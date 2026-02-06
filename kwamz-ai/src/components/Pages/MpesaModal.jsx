import React, { useState } from 'react';

const MpesaModal = ({ onSucess }) => {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [isFocused, setIsFocused] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');

    if (!phoneNumber) {
      setError('Phone number is required');
      return;
    }

    function sanitizePhoneNumber(phoneNumber) {
      if (phoneNumber.startsWith('0')) {
        return '254' + phoneNumber.substring(1);
      } else if (phoneNumber.startsWith('+')) {
        return phoneNumber.substring(1);
      } else if (!phoneNumber.startsWith('254')) {
        return '254' + phoneNumber;
      }
      return phoneNumber;
    }

    const sanitizedPhoneNumber = sanitizePhoneNumber(phoneNumber);

    function validatePhoneNumber(phone) {
      return /^\d{10,}$/.test(phone);
    }

    if (!validatePhoneNumber(sanitizedPhoneNumber)) {
      setError('Invalid phone number format');
      return;
    }

    setLoading(true);
    // Simulate API call
    // setTimeout(() => {
    //   setLoading(false);
    //   onSubmit({ success: true, message: 'STK Push sent successfully!', phoneNumber: sanitizedPhoneNumber });
    // }, 2000);
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl p-6 sm:p-10 w-full max-w-sm sm:max-w-md shadow-2xl relative">
        {/* Header */}
        <div className="text-center mb-6 sm:mb-8">
          <div className="w-16 h-16 sm:w-20 sm:h-20 mx-auto mb-4 bg-gradient-to-br from-green-400 to-green-600 rounded-full flex items-center justify-center text-3xl sm:text-4xl text-white font-bold shadow-lg shadow-green-500/30">
            M
          </div>
          <h3 className="text-xl sm:text-2xl font-bold text-gray-900 mb-1">M-Pesa Payment</h3>
          <p className="text-sm text-gray-500">Enter your phone number to complete payment</p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-5 flex items-center gap-2 text-sm text-red-700">
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {loading && (
          <div className="absolute inset-0 bg-white/95 flex flex-col items-center justify-center rounded-2xl z-10">
            <div className="w-12 h-12 border-4 border-gray-200 border-t-green-500 rounded-full animate-spin"></div>
            <p className="mt-4 text-green-600 font-semibold">Processing payment...</p>
          </div>
        )}

        <div>
          <div className="mb-6">
            <label className="block text-sm font-semibold text-gray-700 mb-2 pl-1">Phone Number</label>
            <input
              type="text"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleSubmit(e);
                }
              }}
              placeholder="e.g., 0712345678 or +254712345678"
              className={`w-full px-4 py-3 text-base border-2 rounded-xl outline-none transition-all ${
                isFocused
                  ? 'border-green-500 ring-4 ring-green-500/10'
                  : 'border-gray-200'
              }`}
            />
          </div>

          <button
            onClick={handleSubmit}
            disabled={loading}
            className="w-full py-3 px-6 text-base font-semibold text-white bg-gradient-to-r from-green-500 to-green-600 rounded-xl shadow-lg shadow-green-500/30 hover:from-green-400 hover:to-green-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Processing...' : 'Send STK Push'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default MpesaModal;