import { useState,useEffect } from 'react';
import { X, Eye, EyeOff, AlertCircle } from 'lucide-react';

function MpesaAccountLogin({ isOpen, onClose, onSubmit, isLoading, company }) {
  const [formData, setFormData] = useState({
    shortCode: '',
    userName: '',
    password: '',
    swapsOnly: false,
  });
  const [errors, setErrors] = useState({});
  const [showPassword, setShowPassword] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    setErrors(prev => ({ ...prev, [name]: '' }));
  };

  const handleToggleSwapsOnly = () => {
    setFormData(prev => ({ ...prev, swapsOnly: !prev.swapsOnly }));
  };

    useEffect(() => {
     
      if (company) {
        setFormData({
          shortCode: company.shortcode || '',
          swapsOnly: false,
        });
      } else {
        setFormData({
          shortCode: '',
          swapsOnly: false,
        });
      }
      setErrors({});
    }, [company]);

  const validateForm = () => {
    const newErrors = {};

    if (!formData.shortCode.trim()) {
      newErrors.shortCode = 'Short Code is required';
    } else if (!/^\d{5,10}$/.test(formData.shortCode)) {
      newErrors.shortCode = 'Short Code must be 5-10 digits';
    }

    if (!formData.userName.trim()) {
      newErrors.userName = 'User Name is required';
    } else if (formData.userName.length < 3) {
      newErrors.userName = 'User Name must be at least 3 characters';
    }

    if (!formData.password.trim()) {
      newErrors.password = 'Password is required';
    } else if (formData.password.length < 6) {
      newErrors.password = 'Password must be at least 6 characters';
    }

    return newErrors;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const validationErrors = validateForm();
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    onSubmit(formData, () => {
      setFormData({
        shortCode: '',
        userName: '',
        password: '',
        swapsOnly: false,
      });
      setErrors({});
      setShowPassword(false);
    });
  };

  if (!isOpen) return null;

  // const hasErrors = Object.keys(errors).length > 0;

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black/60 backdrop-blur-sm z-50 p-4">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col">
        <div className="relative bg-gradient-to-r from-emerald-600 to-teal-600 dark:from-emerald-700 dark:to-teal-700 p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="bg-white/20 p-2 rounded-lg backdrop-blur-sm">
                <span className="text-xl font-bold text-white">m-pesa</span>
              </div>
              <div>
                <h2 className="text-2xl font-bold text-white">
                  M-Pesa Account Login
                </h2>
                <p className="text-emerald-100 text-sm mt-1">
                  Login to {company?.company_name || 'Company'} Portal
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-white/80 hover:text-white hover:bg-white/20 p-2 rounded-lg transition-all"
              // disabled={isLoading}
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <div className="space-y-4">
            {/* Short Code */}
            <div>
              <label className="flex items-center space-x-2 text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
                <span>Short Code</span>
                <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                name="shortCode"
                value={formData.shortCode}
                onChange={handleChange}
                placeholder="Enter Short Code"
                className={`w-full px-4 py-3 border-2 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 dark:bg-slate-800 dark:text-white transition-all ${
                  errors.shortCode
                    ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-500'
                    : 'border-slate-200 dark:border-slate-700 hover:border-slate-300'
                }`}
                disabled={isLoading}
              />
              {errors.shortCode && (
                <p className="text-red-500 text-xs mt-2 ml-1 flex items-center">
                  <AlertCircle className="w-4 h-4 mr-2" />
                  {errors.shortCode}
                </p>
              )}
            </div>

            {/* User Name */}
            <div>
              <label className="flex items-center space-x-2 text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
                <span>User Name</span>
                <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                name="userName"
                value={formData.userName}
                onChange={handleChange}
                placeholder="Enter User Name"
                className={`w-full px-4 py-3 border-2 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 dark:bg-slate-800 dark:text-white transition-all ${
                  errors.userName
                    ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-500'
                    : 'border-slate-200 dark:border-slate-700 hover:border-slate-300'
                }`}
                disabled={isLoading}
              />
              {errors.userName && (
                <p className="text-red-500 text-xs mt-2 ml-1 flex items-center">
                  <AlertCircle className="w-4 h-4 mr-2" />
                  {errors.userName}
                </p>
              )}
            </div>

            {/* Password */}
            <div>
              <label className="flex items-center space-x-2 text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
                <span>Password</span>
                <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="Enter Password"
                  className={`w-full px-4 py-3 border-2 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 dark:bg-slate-800 dark:text-white transition-all ${
                    errors.password
                      ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-500'
                      : 'border-slate-200 dark:border-slate-700 hover:border-slate-300'
                  }`}
                  disabled={isLoading}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
                  disabled={isLoading}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              {errors.password && (
                <p className="text-red-500 text-xs mt-2 ml-1 flex items-center">
                  <AlertCircle className="w-4 h-4 mr-2" />
                  {errors.password}
                </p>
              )}
            </div>

            {/* Swaps-only toggle */}
            <div className="flex items-start justify-between gap-4 p-4 rounded-xl border-2 border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
              <div>
                <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                  Start with swaps only
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  Skip the float &amp; KYC pass and go straight to operator swaps.
                  Only use this if till and sub-agent info is already up to date —
                  otherwise leave it off to run the normal float/KYC pass first.
                </p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={formData.swapsOnly}
                onClick={handleToggleSwapsOnly}
                disabled={isLoading}
                className={`relative inline-flex shrink-0 h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed ${
                  formData.swapsOnly ? 'bg-emerald-600' : 'bg-slate-300 dark:bg-slate-600'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
                    formData.swapsOnly ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

          </div>
        </div>

        <div className="border-t border-slate-200 dark:border-slate-700 p-6 bg-slate-50 dark:bg-slate-800">
          <div className="flex space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-3 px-4 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 font-semibold rounded-xl hover:bg-slate-300 dark:hover:bg-slate-600 transition-all"
              disabled={isLoading}
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={isLoading }
              className="flex-1 py-3 px-4 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white font-semibold rounded-xl transition-all focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-emerald-500/30"
            >
              {isLoading ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Logging in...
                </span>
              ) : (
                <span>Login</span>
              )}
            </button>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 text-center mt-3">
            <span className="text-red-500">*</span> Required fields
          </p>
        </div>
      </div>
    </div>
  );
}

export default MpesaAccountLogin;