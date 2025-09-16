import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff, User, Lock, CheckCircle, AlertCircle, LogIn } from 'lucide-react';

const LoginForm = ({ onSuccess }) => {
  const [formData, setFormData] = useState({
    username: '',
    password: ''
  });
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [focusedField, setFocusedField] = useState('');
  const [showSuccess, setShowSuccess] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));

    // Clear specific field error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrors({});

    // Client-side validation
    const newErrors = {};
    if (!formData.username.trim()) newErrors.username = 'Username is required';
    if (!formData.password.trim()) newErrors.password = 'Password is required';

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setIsSubmitting(true);

    // Simulate API call
    setTimeout(() => {
      setShowSuccess(true);
      setIsSubmitting(false);
      
      // Simulate success and redirect
      setTimeout(() => {
        if (onSuccess) {
          onSuccess();
        }
      }, 1500);
    }, 1500);
  };

  if (showSuccess) {
    return (
      <div className="flex items-center justify-center min-h-screen p-4">
        <div className="bg-white/90 backdrop-blur-xl rounded-3xl shadow-2xl border border-white/20 p-8 text-center space-y-6 max-w-md w-full">
          <div className="w-16 h-16 bg-gradient-to-r from-green-500 to-emerald-600 rounded-2xl flex items-center justify-center mx-auto">
            <CheckCircle className="w-8 h-8 text-white" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900">Welcome Back!</h2>
          <p className="text-gray-600">You have successfully logged in.</p>
          <div className="animate-pulse text-sm text-gray-500">Redirecting you to dashboard...</div>
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
            <LogIn className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Welcome Back</h1>
          <p className="text-gray-600">Sign in to your account</p>
        </div>

        {/* General Error */}
        {errors.general && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-start gap-2 animate-shake">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <span className="text-red-700 text-sm">{errors.general}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Username Field */}
          <div className="space-y-1">
            <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-2">
              Username
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <User className={`w-5 h-5 transition-all duration-200 ${errors.username ? 'text-red-400' :
                    formData.username ? 'text-blue-500' :
                      focusedField === 'username' ? 'text-blue-500' : 'text-gray-400'
                  }`} />
              </div>
              <input
                type="text"
                name="username"
                id="username"
                value={formData.username}
                onChange={handleChange}
                onFocus={() => setFocusedField('username')}
                onBlur={() => setFocusedField('')}
                placeholder="Enter your username"
                disabled={isSubmitting}
                className={`w-full pl-10 pr-4 py-3 border rounded-xl bg-white/50 backdrop-blur-sm transition-all duration-200 ${errors.username ?
                    'border-red-300 focus:border-red-500 focus:ring-red-200 shadow-red-100' :
                    formData.username ?
                      'border-blue-300 focus:border-blue-500 focus:ring-blue-200 shadow-blue-100' :
                      'border-gray-200 focus:border-blue-500 focus:ring-blue-200'
                  } focus:ring-4 focus:ring-opacity-20 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed placeholder:text-gray-400 shadow-sm hover:shadow-md`}
              />
              {formData.username && !errors.username && (
                <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                  <CheckCircle className="w-5 h-5 text-green-500" />
                </div>
              )}
            </div>
            {errors.username && (
              <div className="flex items-start gap-1 mt-1 animate-fadeIn">
                <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                <span className="text-red-600 text-xs">{errors.username}</span>
              </div>
            )}
          </div>

          {/* Password Field */}
          <div className="space-y-1">
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
              Password
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Lock className={`w-5 h-5 transition-all duration-200 ${errors.password ? 'text-red-400' :
                    formData.password ? 'text-blue-500' :
                      focusedField === 'password' ? 'text-blue-500' : 'text-gray-400'
                  }`} />
              </div>
              <input
                type={showPassword ? 'text' : 'password'}
                name="password"
                id="password"
                value={formData.password}
                onChange={handleChange}
                onFocus={() => setFocusedField('password')}
                onBlur={() => setFocusedField('')}
                placeholder="Enter your password"
                disabled={isSubmitting}
                className={`w-full pl-10 pr-12 py-3 border rounded-xl bg-white/50 backdrop-blur-sm transition-all duration-200 ${errors.password ?
                    'border-red-300 focus:border-red-500 focus:ring-red-200 shadow-red-100' :
                    formData.password ?
                      'border-blue-300 focus:border-blue-500 focus:ring-blue-200 shadow-blue-100' :
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
            {errors.password && (
              <div className="flex items-start gap-1 mt-1 animate-fadeIn">
                <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                <span className="text-red-600 text-xs">{errors.password}</span>
              </div>
            )}
          </div>

          {/* Forgot Password Link */}
          <div className="text-right">
            <button
              type="button"
              className="text-sm text-blue-600 hover:text-blue-700 hover:underline transition-colors duration-200"
            >
              Forgot your password?
            </button>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white font-semibold py-3 px-6 rounded-xl transition-all duration-200 transform hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none shadow-lg hover:shadow-xl flex items-center justify-center gap-2"
          >
            {isSubmitting ? (
              <>
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                Signing In...
              </>
            ) : (
              <>
                <LogIn className="w-5 h-5" />
                Sign In
              </>
            )}
          </button>
        </form>

        {/* Footer */}
        <div className="text-center text-sm text-gray-600">
          Don't have an account?{' '}
          <button
            onClick={() => navigate("/signup")}
            className="text-blue-600 hover:text-blue-700 font-semibold hover:underline transition-colors duration-200"
          >
            Create one
          </button>
        </div>
      </div>
    </div>
  );
};

export default LoginForm;