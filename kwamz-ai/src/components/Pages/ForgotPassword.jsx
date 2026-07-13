import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff, Mail, Lock, CheckCircle, AlertCircle, KeyRound, ArrowLeft } from 'lucide-react';
import config from '../../Config';
import axios from 'axios';

const ForgotPassword = () => {
  const [step, setStep] = useState(1); // 1 = email, 2 = otp + new password, 3 = success
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [focusedField, setFocusedField] = useState('');
  const [resendCooldown, setResendCooldown] = useState(0);
  const navigate = useNavigate();

  // Resend cooldown timer
  useEffect(() => {
    if (resendCooldown > 0) {
      const timer = setTimeout(() => setResendCooldown(resendCooldown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [resendCooldown]);

  const validateEmail = (emailValue) => {
    const emailRegex = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;
    return emailRegex.test(emailValue);
  };

  const validatePassword = (password) => {
    const errors = [];
    if (password.length < 8) errors.push('At least 8 characters');
    if (!/\d/.test(password)) errors.push('At least one number');
    if (!/[^A-Za-z0-9]/.test(password)) errors.push('At least one special character');
    return errors;
  };

  const handleRequestOtp = async (e) => {
    e.preventDefault();
    setErrors({});

    if (!email.trim()) {
      setErrors({ email: 'Email is required' });
      return;
    }

    if (!validateEmail(email)) {
      setErrors({ email: 'Please enter a valid email address' });
      return;
    }

    setIsSubmitting(true);
    try {
      await axios.post(`${config.API_URL}/users/forgot-password/request-otp`, { email: email.trim() });
      setStep(2);
      setResendCooldown(60);
    } catch (error) {
      console.error('OTP Request error:', error);
      setErrors({ general: error.response?.data?.message || 'Failed to send OTP. Please try again.' });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResendOtp = async () => {
    if (resendCooldown > 0) return;

    setErrors({});
    setIsSubmitting(true);
    try {
      await axios.post(`${config.API_URL}/users/forgot-password/request-otp`, { email: email.trim() });
      setResendCooldown(60);
    } catch (error) {
      console.error('Resend OTP error:', error);
      setErrors({ general: error.response?.data?.message || 'Failed to resend OTP. Please try again.' });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    setErrors({});

    const newErrors = {};

    if (!otp.trim()) {
      newErrors.otp = 'OTP is required';
    } else if (otp.length !== 6 || !/^\d+$/.test(otp)) {
      newErrors.otp = 'OTP must be 6 digits';
    }

    const passwordErrors = validatePassword(newPassword);
    if (passwordErrors.length > 0) {
      newErrors.newPassword = passwordErrors.join(', ');
    }

    if (newPassword !== confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setIsSubmitting(true);
    try {
      await axios.post(`${config.API_URL}/users/forgot-password/reset`, {
        email: email.trim(),
        otp: otp.trim(),
        newPassword: newPassword
      });
      setStep(3);
    } catch (error) {
      console.error('Password reset error:', error);
      setErrors({ general: error.response?.data?.error || 'Failed to reset password. Please try again.' });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Success screen
  if (step === 3) {
    return (
      <div className="flex items-center justify-center min-h-screen p-4 bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
        <div className="bg-white/90 backdrop-blur-xl rounded-3xl shadow-2xl border border-white/20 p-8 text-center space-y-6 max-w-md w-full">
          <div className="w-16 h-16 bg-gradient-to-r from-green-500 to-emerald-600 rounded-2xl flex items-center justify-center mx-auto">
            <CheckCircle className="w-8 h-8 text-white" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900">Password Reset Successful!</h2>
          <p className="text-gray-600">Your password has been updated. You can now log in with your new password.</p>
          <button
            onClick={() => navigate('/login')}
            className="w-full bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white font-semibold py-3 px-6 rounded-xl transition-all duration-200 transform hover:scale-[1.02] active:scale-[0.98] shadow-lg hover:shadow-xl"
          >
            Go to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-screen p-4 bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      <div className="bg-white/90 backdrop-blur-xl rounded-3xl shadow-2xl border border-white/20 p-8 space-y-6 max-w-md w-full">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-2xl flex items-center justify-center mx-auto mb-4 transform hover:scale-105 transition-transform duration-200">
            <KeyRound className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">
            {step === 1 ? 'Forgot Password' : 'Reset Password'}
          </h1>
          <p className="text-gray-600">
            {step === 1
              ? 'Enter your email to receive a reset code'
              : 'Enter the code sent to your email and your new password'}
          </p>
        </div>

        {/* General Error */}
        {errors.general && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-start gap-2 animate-shake">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <span className="text-red-700 text-sm">{errors.general}</span>
          </div>
        )}

        {step === 1 ? (
          /* Step 1: Email Input */
          <form onSubmit={handleRequestOtp} className="space-y-5">
            <div className="space-y-1">
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className={`w-5 h-5 transition-all duration-200 ${errors.email ? 'text-red-400' :
                    email ? 'text-blue-500' :
                      focusedField === 'email' ? 'text-blue-500' : 'text-gray-400'
                    }`} />
                </div>
                <input
                  type="email"
                  name="email"
                  id="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (errors.email) setErrors({ ...errors, email: '' });
                  }}
                  onFocus={() => setFocusedField('email')}
                  onBlur={() => setFocusedField('')}
                  placeholder="Enter your email"
                  disabled={isSubmitting}
                  className={`w-full pl-10 pr-4 py-3 border rounded-xl bg-white/50 backdrop-blur-sm transition-all duration-200 ${errors.email ?
                    'border-red-300 focus:border-red-500 focus:ring-red-200 shadow-red-100' :
                    email ?
                      'border-blue-300 focus:border-blue-500 focus:ring-blue-200 shadow-blue-100' :
                      'border-gray-200 focus:border-blue-500 focus:ring-blue-200'
                    } focus:ring-4 focus:ring-opacity-20 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed placeholder:text-gray-400 shadow-sm hover:shadow-md`}
                />
                {email && !errors.email && validateEmail(email) && (
                  <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                    <CheckCircle className="w-5 h-5 text-green-500" />
                  </div>
                )}
              </div>
              {errors.email && (
                <div className="flex items-start gap-1 mt-1 animate-fadeIn">
                  <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                  <span className="text-red-600 text-xs">{errors.email}</span>
                </div>
              )}
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white font-semibold py-3 px-6 rounded-xl transition-all duration-200 transform hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none shadow-lg hover:shadow-xl flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                  Sending Code...
                </>
              ) : (
                'Send Reset Code'
              )}
            </button>
          </form>
        ) : (
          /* Step 2: OTP + New Password */
          <form onSubmit={handleResetPassword} className="space-y-5">
            {/* OTP Field */}
            <div className="space-y-1">
              <label htmlFor="otp" className="block text-sm font-medium text-gray-700 mb-2">
                Verification Code
              </label>
              <input
                type="text"
                name="otp"
                id="otp"
                value={otp}
                onChange={(e) => {
                  const value = e.target.value.replace(/\D/g, '').slice(0, 6);
                  setOtp(value);
                  if (errors.otp) setErrors({ ...errors, otp: '' });
                }}
                placeholder="Enter 6-digit code"
                disabled={isSubmitting}
                maxLength={6}
                className={`w-full px-4 py-3 border rounded-xl bg-white/50 backdrop-blur-sm transition-all duration-200 text-center text-2xl tracking-widest font-mono ${errors.otp ?
                  'border-red-300 focus:border-red-500 focus:ring-red-200' :
                  otp.length === 6 ?
                    'border-green-300 focus:border-green-500 focus:ring-green-200' :
                    'border-gray-200 focus:border-blue-500 focus:ring-blue-200'
                  } focus:ring-4 focus:ring-opacity-20 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed placeholder:text-gray-400 placeholder:text-base placeholder:tracking-normal shadow-sm hover:shadow-md`}
              />
              {errors.otp && (
                <div className="flex items-start gap-1 mt-1 animate-fadeIn">
                  <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                  <span className="text-red-600 text-xs">{errors.otp}</span>
                </div>
              )}
              <div className="text-center mt-2">
                <button
                  type="button"
                  onClick={handleResendOtp}
                  disabled={resendCooldown > 0 || isSubmitting}
                  className="text-sm text-blue-600 hover:text-blue-700 hover:underline transition-colors duration-200 disabled:text-gray-400 disabled:no-underline disabled:cursor-not-allowed"
                >
                  {resendCooldown > 0 ? `Resend code in ${resendCooldown}s` : 'Resend code'}
                </button>
              </div>
            </div>

            {/* New Password Field */}
            <div className="space-y-1">
              <label htmlFor="newPassword" className="block text-sm font-medium text-gray-700 mb-2">
                New Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className={`w-5 h-5 transition-all duration-200 ${errors.newPassword ? 'text-red-400' :
                    newPassword && validatePassword(newPassword).length === 0 ? 'text-green-500' :
                      focusedField === 'newPassword' ? 'text-blue-500' : 'text-gray-400'
                    }`} />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  name="newPassword"
                  id="newPassword"
                  value={newPassword}
                  onChange={(e) => {
                    setNewPassword(e.target.value);
                    if (errors.newPassword) setErrors({ ...errors, newPassword: '' });
                  }}
                  onFocus={() => setFocusedField('newPassword')}
                  onBlur={() => setFocusedField('')}
                  placeholder="Enter new password"
                  disabled={isSubmitting}
                  className={`w-full pl-10 pr-12 py-3 border rounded-xl bg-white/50 backdrop-blur-sm transition-all duration-200 ${errors.newPassword ?
                    'border-red-300 focus:border-red-500 focus:ring-red-200' :
                    newPassword && validatePassword(newPassword).length === 0 ?
                      'border-green-300 focus:border-green-500 focus:ring-green-200' :
                      'border-gray-200 focus:border-blue-500 focus:ring-blue-200'
                    } focus:ring-4 focus:ring-opacity-20 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed placeholder:text-gray-400 shadow-sm hover:shadow-md`}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center hover:bg-gray-50 rounded-r-xl transition-colors duration-200"
                  disabled={isSubmitting}
                >
                  {showPassword ?
                    <EyeOff className="w-5 h-5 text-gray-400 hover:text-gray-600" /> :
                    <Eye className="w-5 h-5 text-gray-400 hover:text-gray-600" />
                  }
                </button>
              </div>
              {errors.newPassword && (
                <div className="flex items-start gap-1 mt-1 animate-fadeIn">
                  <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                  <span className="text-red-600 text-xs">{errors.newPassword}</span>
                </div>
              )}
              <p className="text-xs text-gray-500 mt-1">
                Min 8 characters, 1 number, 1 special character
              </p>
            </div>

            {/* Confirm Password Field */}
            <div className="space-y-1">
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-2">
                Confirm Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className={`w-5 h-5 transition-all duration-200 ${errors.confirmPassword ? 'text-red-400' :
                    confirmPassword && confirmPassword === newPassword ? 'text-green-500' :
                      focusedField === 'confirmPassword' ? 'text-blue-500' : 'text-gray-400'
                    }`} />
                </div>
                <input
                  type={showConfirmPassword ? 'text' : 'password'}
                  name="confirmPassword"
                  id="confirmPassword"
                  value={confirmPassword}
                  onChange={(e) => {
                    setConfirmPassword(e.target.value);
                    if (errors.confirmPassword) setErrors({ ...errors, confirmPassword: '' });
                  }}
                  onFocus={() => setFocusedField('confirmPassword')}
                  onBlur={() => setFocusedField('')}
                  placeholder="Confirm new password"
                  disabled={isSubmitting}
                  className={`w-full pl-10 pr-12 py-3 border rounded-xl bg-white/50 backdrop-blur-sm transition-all duration-200 ${errors.confirmPassword ?
                    'border-red-300 focus:border-red-500 focus:ring-red-200' :
                    confirmPassword && confirmPassword === newPassword ?
                      'border-green-300 focus:border-green-500 focus:ring-green-200' :
                      'border-gray-200 focus:border-blue-500 focus:ring-blue-200'
                    } focus:ring-4 focus:ring-opacity-20 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed placeholder:text-gray-400 shadow-sm hover:shadow-md`}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center hover:bg-gray-50 rounded-r-xl transition-colors duration-200"
                  disabled={isSubmitting}
                >
                  {showConfirmPassword ?
                    <EyeOff className="w-5 h-5 text-gray-400 hover:text-gray-600" /> :
                    <Eye className="w-5 h-5 text-gray-400 hover:text-gray-600" />
                  }
                </button>
              </div>
              {errors.confirmPassword && (
                <div className="flex items-start gap-1 mt-1 animate-fadeIn">
                  <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                  <span className="text-red-600 text-xs">{errors.confirmPassword}</span>
                </div>
              )}
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white font-semibold py-3 px-6 rounded-xl transition-all duration-200 transform hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none shadow-lg hover:shadow-xl flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                  Resetting Password...
                </>
              ) : (
                'Reset Password'
              )}
            </button>

            {/* Back button */}
            <button
              type="button"
              onClick={() => setStep(1)}
              className="w-full text-gray-600 hover:text-gray-800 font-medium py-2 transition-colors duration-200 flex items-center justify-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to email
            </button>
          </form>
        )}

        {/* Footer */}
        <div className="text-center text-sm text-gray-600">
          Remember your password?{' '}
          <button
            onClick={() => navigate('/login')}
            className="text-blue-600 hover:text-blue-700 font-semibold hover:underline transition-colors duration-200"
          >
            Sign in
          </button>
        </div>
      </div>
    </div>
  );
};

export default ForgotPassword;
