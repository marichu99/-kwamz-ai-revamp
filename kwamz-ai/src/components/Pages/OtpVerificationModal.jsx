import React, { useState, useEffect } from 'react';

const OtpVerificationModal = ({ isOpen, onClose, onVerify, email, resendOtp }) => {
  const [otp, setOtp] = useState('');
  const [error, setError] = useState('');
  const [resendCooldown, setResendCooldown] = useState(60);
  const [isVerifying, setIsVerifying] = useState(false);

  // Effect to handle the resend OTP countdown
  useEffect(() => {
    if (!isOpen) {
      setResendCooldown(60); // Reset timer when modal opens
      setError('');
      setOtp('');
      setIsVerifying(false);
      return;
    }

    if (resendCooldown > 0) {
      const timerId = setTimeout(() => setResendCooldown(resendCooldown - 1), 1000);
      return () => clearTimeout(timerId); // Cleanup timer
    }
  }, [isOpen, resendCooldown]);

  const handleVerifyClick = async () => {
    if (!/^\d{6}$/.test(otp)) {
      setError('Please enter a valid 6-digit OTP.');
      return;
    }
    setError('');
    setIsVerifying(true);
    try {
      await onVerify(otp);
    } finally {
      setIsVerifying(false);
    }
  };

  const handleResendClick = () => {
    resendOtp();
    setResendCooldown(60); // Reset the timer
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl p-5 sm:p-8 w-full max-w-sm sm:max-w-md text-center">
        <h2 className="text-xl sm:text-2xl font-bold mb-2">Verify Your Account</h2>
        <p className="text-gray-600 text-sm sm:text-base mb-4">An OTP has been generated for {email}.</p>
        <p className="text-xs sm:text-sm text-red-500 mb-4 font-semibold">
          This OTP will be invalidated in 5 minutes.
        </p>

        <input
          type="text"
          value={otp}
          onChange={(e) => setOtp(e.target.value)}
          maxLength="6"
          className="w-full text-center text-xl sm:text-2xl tracking-[0.3em] sm:tracking-[0.5em] font-mono p-3 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
          placeholder="------"
        />

        {error && <p className="text-red-500 text-sm mt-3">{error}</p>}

        <button
          onClick={handleVerifyClick}
          disabled={isVerifying}
          className="w-full mt-5 sm:mt-6 bg-gradient-to-r from-indigo-500 to-purple-600 text-white font-semibold py-3 px-6 rounded-xl transition-all duration-200 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
        >
          {isVerifying ? 'Verifying...' : 'Validate'}
        </button>

        <div className="mt-4 text-sm text-gray-500">
          Didn't receive the code?{' '}
          {resendCooldown > 0 ? (
            <span>Resend in {resendCooldown}s</span>
          ) : (
            <button
              onClick={handleResendClick}
              className="font-semibold text-indigo-600 hover:underline"
            >
              Resend OTP
            </button>
          )}
        </div>
         <button onClick={onClose} className="mt-2 text-xs text-gray-400 hover:underline">Cancel</button>
      </div>
    </div>
  );
};

export default OtpVerificationModal;