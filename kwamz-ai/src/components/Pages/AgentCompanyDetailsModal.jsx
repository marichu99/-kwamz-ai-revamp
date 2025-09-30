import { useState, useEffect } from 'react';
import { X, Building2, MapPin, Phone, CreditCard, Hash } from 'lucide-react';

function AgentCompanyDetailsModal({ isOpen, onClose, onSubmit, isLoading, agentCompany }) {
  const [formData, setFormData] = useState({
    company_name: '',
    location: '',
    contact_phone: '',
    till_number: '',
    agentcompany_code: '',
  });
  const [errors, setErrors] = useState({});

  useEffect(() => {
    if (agentCompany) {
      setFormData({
        company_name: agentCompany.company_name || '',
        location: agentCompany.location || '',
        contact_phone: agentCompany.contact_phone || '',
        till_number: agentCompany.till_number || '',
        agentcompany_code: agentCompany.agentcompany_code || '',
      });
    } else {
      setFormData({
        company_name: '',
        location: '',
        contact_phone: '',
        till_number: '',
        agentcompany_code: '',
      });
    }
    setErrors({});
  }, [agentCompany]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setErrors((prev) => ({ ...prev, [name]: '' }));
  };

  const validateForm = () => {
    const newErrors = {};
    if (!formData.company_name.trim()) {
      newErrors.company_name = 'Company name is required';
    }
    if (!formData.location.trim()) {
      newErrors.location = 'Location is required';
    }
    if (formData.contact_phone && !/^\+?\d{1,3}?\d{9,12}$/.test(formData.contact_phone)) {
      newErrors.contact_phone = 'Invalid phone number format (e.g., +254712345678)';
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

    onSubmit(formData, agentCompany?.id, () => {
      setFormData({
        company_name: '',
        location: '',
        contact_phone: '',
        till_number: '',
        agentcompany_code: '',
      });
      setErrors({});
    });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black/60 backdrop-blur-sm z-50 p-4">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-lg transform transition-all">
        <div className="relative bg-gradient-to-r from-blue-600 to-indigo-600 dark:from-blue-700 dark:to-indigo-700 rounded-t-2xl p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="bg-white/20 p-2 rounded-lg backdrop-blur-sm">
                <Building2 className="w-6 h-6 text-white" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-white">
                  {agentCompany ? 'Edit Agent Company' : 'New Agent'}
                </h2>
                <p className="text-blue-100 text-sm mt-1">
                  {agentCompany ? 'Update company information' : 'Register a new agent'}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-white/80 hover:text-white hover:bg-white/20 p-2 rounded-lg transition-all"
              disabled={isLoading}
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="p-6 space-y-5">
          {agentCompany && (
            <div className="bg-slate-50 dark:bg-slate-800 rounded-xl p-4 border-2 border-dashed border-slate-200 dark:border-slate-700">
              <label className="flex items-center space-x-2 text-sm font-semibold text-slate-600 dark:text-slate-400 mb-2">
                <Hash className="w-4 h-4" />
                <span>Agent Company Code</span>
              </label>
              <input
                type="text"
                value={formData.agentcompany_code}
                readOnly
                className="w-full px-4 py-2.5 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-lg text-slate-800 dark:text-slate-200 font-mono text-sm cursor-not-allowed"
              />
            </div>
          )}

          <div>
            <label className="flex items-center space-x-2 text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
              <Building2 className="w-4 h-4" />
              <span>Company Name</span>
              <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              name="company_name"
              value={formData.company_name}
              onChange={handleChange}
              className={`w-full px-4 py-3 border-2 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-800 dark:text-white transition-all ${
                errors.company_name
                  ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-500'
                  : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
              }`}
              placeholder="Enter company name"
              disabled={isLoading}
            />
            {errors.company_name && (
              <p className="text-red-500 text-xs mt-2 ml-1 flex items-center">
                <span className="mr-1">⚠</span>
                {errors.company_name}
              </p>
            )}
          </div>

          <div>
            <label className="flex items-center space-x-2 text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
              <MapPin className="w-4 h-4" />
              <span>Location</span>
              <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              name="location"
              value={formData.location}
              onChange={handleChange}
              className={`w-full px-4 py-3 border-2 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-800 dark:text-white transition-all ${
                errors.location
                  ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-500'
                  : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
              }`}
              placeholder="Enter location (e.g., Nairobi, CBD)"
              disabled={isLoading}
            />
            {errors.location && (
              <p className="text-red-500 text-xs mt-2 ml-1 flex items-center">
                <span className="mr-1">⚠</span>
                {errors.location}
              </p>
            )}
          </div>

          <div>
            <label className="flex items-center space-x-2 text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
              <Phone className="w-4 h-4" />
              <span>Contact Phone</span>
            </label>
            <input
              type="text"
              name="contact_phone"
              value={formData.contact_phone}
              onChange={handleChange}
              className={`w-full px-4 py-3 border-2 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-800 dark:text-white transition-all ${
                errors.contact_phone
                  ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-500'
                  : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
              }`}
              placeholder="+254712345678"
              disabled={isLoading}
            />
            {errors.contact_phone && (
              <p className="text-red-500 text-xs mt-2 ml-1 flex items-center">
                <span className="mr-1">⚠</span>
                {errors.contact_phone}
              </p>
            )}
          </div>

          <div>
            <label className="flex items-center space-x-2 text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
              <CreditCard className="w-4 h-4" />
              <span>Till Number</span>
            </label>
            <input
              type="text"
              name="till_number"
              value={formData.till_number}
              onChange={handleChange}
              className="w-full px-4 py-3 border-2 border-slate-200 dark:border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-slate-800 dark:text-white hover:border-slate-300 dark:hover:border-slate-600 transition-all"
              placeholder="Enter till number"
              disabled={isLoading}
            />
          </div>

          <div className="flex space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-3 px-4 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold rounded-xl hover:bg-slate-200 dark:hover:bg-slate-700 transition-all focus:outline-none focus:ring-2 focus:ring-slate-400"
              disabled={isLoading}
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={isLoading}
              className="flex-1 py-3 px-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold rounded-xl transition-all focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-blue-500/30"
            >
              {isLoading ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Saving...
                </span>
              ) : (
                <span>{agentCompany ? 'Update Company' : 'Create Company'}</span>
              )}
            </button>
          </div>

          <p className="text-xs text-slate-500 dark:text-slate-400 text-center pt-2">
            <span className="text-red-500">*</span> Required fields
          </p>
        </div>
      </div>
    </div>
  );
}

export default AgentCompanyDetailsModal;