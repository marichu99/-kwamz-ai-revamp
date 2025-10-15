import { useState, useEffect } from 'react';
import { X, Building2, Calendar, MapPin, User, Mail, Users, Plus, Trash2, AlertCircle, Upload, FileText, Hash } from 'lucide-react';
import config from '../../Config';

function CompanyDetailsModal({ isOpen, onClose, onSubmit, isLoading, company }) {
  const [formData, setFormData] = useState({
    company_name: '',
    shortcode: '',
    company_number: '',
    registration_date: '',
    address: '',
    primary_owner_name: '',
    primary_owner_email: '',
    primary_owner_shares: 0,
    secondary_shareholders: [],
    directors: [],
    cr12_file: null,
    cr12_preview: '',
  });
  const [errors, setErrors] = useState({});
  const [isUploadingCR12, setIsUploadingCR12] = useState(false);
  const [isCR12Valid, setIsCR12Valid] = useState(false);

  useEffect(() => {
    if (company) {
      setFormData({
        company_name: company.company_name || '',
        shortcode: company.shortcode || '',
        company_number: company.company_number || '',
        registration_date: company.registration_date
          ? new Date(company.registration_date).toISOString().split('T')[0]
          : '',
        address: company.address || '',
        primary_owner_name: company.primary_owner_name || '',
        primary_owner_email: company.primary_owner_email || '',
        primary_owner_shares: company.primary_owner_shares || 0,
        secondary_shareholders: company.secondary_shareholders || [],
        directors: company.directors || [],
        cr12_file: null,
        cr12_preview: company.cr12_file_location || '',
      });
      setIsCR12Valid(true);
    } else {
      setFormData({
        company_name: '',
        shortcode: '',
        company_number: '',
        registration_date: '',
        address: '',
        primary_owner_name: '',
        primary_owner_email: '',
        primary_owner_shares: 0,
        secondary_shareholders: [],
        directors: [],
        cr12_file: null,
        cr12_preview: '',
      });
    }
    setErrors({});
  }, [company]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setErrors((prev) => ({ ...prev, [name]: '' }));
  };

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
      setErrors((prev) => ({ ...prev, cr12_file: 'File size must be less than 5MB' }));
      return;
    }
    if (file.type !== 'application/pdf') {
      setErrors((prev) => ({ ...prev, cr12_file: 'File must be a PDF' }));
      return;
    }

    setFormData((prev) => ({
      ...prev,
      cr12_file: file,
      cr12_preview: URL.createObjectURL(file),
    }));
    setErrors((prev) => ({ ...prev, cr12_file: '', company_number: '' }));

    // Upload and extract company number
    setIsUploadingCR12(true);
    try {
      const uploadFormData = new FormData();
      uploadFormData.append('file', file);

      // Replace with your actual API URL
      const API_URL = config.API_URL;
      const res = await fetch(`${API_URL}/document/extract_cr12`, {
        method: 'POST',
        body: uploadFormData
      });

      const result = await res.json();

      if (result.error) {
        setIsCR12Valid(false);
        setErrors((prev) => ({ ...prev, cr12_file: result.error }));
        setFormData((prev) => ({
          ...prev,
          cr12_file: null,
          cr12_preview: '',
          company_number: '',
        }));
        return;
      }

      if (result.cr12) {
        setFormData((prev) => ({
          ...prev,
          company_number: result.cr12,
        }));

      }
      setIsCR12Valid(true);
    } catch (err) {
      console.error('CR12 upload failed:', err);
      setIsCR12Valid(false);
      setErrors((prev) => ({ ...prev, cr12_file: 'Failed to process CR12 document' }));
      setFormData((prev) => ({
        ...prev,
        cr12_file: null,
        cr12_preview: '',
        company_number: '',
      }));
    } finally {
      setIsUploadingCR12(false);
    }
  };

  const addShareholder = () => {
    setFormData((prev) => ({
      ...prev,
      secondary_shareholders: [
        ...prev.secondary_shareholders,
        { name: '', email: '', shares: 0 }
      ],
    }));
  };

  const removeShareholder = (index) => {
    setFormData((prev) => ({
      ...prev,
      secondary_shareholders: prev.secondary_shareholders.filter((_, i) => i !== index),
    }));
  };

  const updateShareholder = (index, field, value) => {
    setFormData((prev) => ({
      ...prev,
      secondary_shareholders: prev.secondary_shareholders.map((sh, i) =>
        i === index ? { ...sh, [field]: value } : sh
      ),
    }));
    if (field === 'email') {
      setErrors((prev) => ({ ...prev, [`shareholder_email_${index}`]: '' }));
    }
  };

  const addDirector = () => {
    setFormData((prev) => ({
      ...prev,
      directors: [...prev.directors, { name: '', email: '' }],
    }));
  };

  const removeDirector = (index) => {
    setFormData((prev) => ({
      ...prev,
      directors: prev.directors.filter((_, i) => i !== index),
    }));
  };

  const updateDirector = (index, field, value) => {
    setFormData((prev) => ({
      ...prev,
      directors: prev.directors.map((dir, i) =>
        i === index ? { ...dir, [field]: value } : dir
      ),
    }));
    if (field === 'email') {
      setErrors((prev) => ({ ...prev, [`director_email_${index}`]: '' }));
    }
  };

  const calculateTotalShares = () => {
    const primaryShares = parseFloat(formData.primary_owner_shares) || 0;
    const secondaryShares = formData.secondary_shareholders.reduce(
      (sum, sh) => sum + (parseFloat(sh.shares) || 0),
      0
    );
    return primaryShares + secondaryShares;
  };

  const validateEmail = (email) => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  };

  const validateForm = () => {
    const newErrors = {};

    if (!formData.company_name.trim()) {
      newErrors.company_name = 'Company name is required';
    }
    if (!formData.shortcode.trim()) {
      newErrors.shortcode = 'Shortcode is required';
    } else if (!/^\d{5,6}$/.test(formData.shortcode)) {
      newErrors.shortcode = 'Shortcode must be 5-6 digits';
    }
    if (!formData.company_number.trim()) {
      newErrors.company_number = 'Company number is required (upload CR12 document)';
    }
    if (!formData.address.trim()) {
      newErrors.address = 'Address is required';
    }
    if (!formData.primary_owner_name.trim()) {
      newErrors.primary_owner_name = 'Primary owner name is required';
    }

    if (!formData.primary_owner_email.trim()) {
      newErrors.primary_owner_email = 'Primary owner email is required';
    } else if (!validateEmail(formData.primary_owner_email)) {
      newErrors.primary_owner_email = 'Invalid email format';
    }

    const primaryShares = parseFloat(formData.primary_owner_shares) || 0;
    if (primaryShares < 0 || primaryShares > 100) {
      newErrors.primary_owner_shares = 'Shares must be between 0 and 100';
    }

    const totalShares = calculateTotalShares();
    if (Math.abs(totalShares - 100) > 0.01) {
      newErrors.shares = `Total shareholding is ${totalShares.toFixed(2)}% - must equal exactly 100%`;
    }

    formData.secondary_shareholders.forEach((sh, i) => {
      if (sh.name.trim() && !sh.email.trim()) {
        newErrors[`shareholder_email_${i}`] = 'Email is required when name is provided';
      } else if (sh.email.trim() && !validateEmail(sh.email)) {
        newErrors[`shareholder_email_${i}`] = 'Invalid email format';
      }

      const shares = parseFloat(sh.shares) || 0;
      if (shares < 0 || shares > 100) {
        newErrors[`shareholder_shares_${i}`] = 'Shares must be between 0 and 100';
      }
    });

    formData.directors.forEach((dir, i) => {
      if (dir.name.trim() && !dir.email.trim()) {
        newErrors[`director_email_${i}`] = 'Email is required when name is provided';
      } else if (dir.email.trim() && !validateEmail(dir.email)) {
        newErrors[`director_email_${i}`] = 'Invalid email format';
      }
    });

    return newErrors;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const validationErrors = validateForm();
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    // Prepare the data for submission
    const submitData = {
      ...formData,
      primary_owner_shares: parseFloat(formData.primary_owner_shares) || 0,
      // Ensure proper serialization of arrays
      secondary_shareholders: formData.secondary_shareholders.map(sh => ({
        name: sh.name || '',
        email: sh.email || '',
        shares: parseFloat(sh.shares) || 0
      })),
      directors: formData.directors.map(dir => ({
        name: dir.name || '',
        email: dir.email || ''
      })),
      // Remove file preview from submission data
      cr12_preview: undefined
    };

    // Remove undefined values
    Object.keys(submitData).forEach(key => {
      if (submitData[key] === undefined) {
        delete submitData[key];
      }
    });

    onSubmit(submitData, company?.id, () => {
      setFormData({
        company_name: '',
        shortcode: '',
        company_number: '',
        registration_date: '',
        address: '',
        primary_owner_name: '',
        primary_owner_email: '',
        primary_owner_shares: 0,
        secondary_shareholders: [],
        directors: [],
        cr12_file: null,
        cr12_preview: '',
      });
      setErrors({});
    });
  };

  if (!isOpen) return null;

  const totalShares = calculateTotalShares();
  const sharesInvalid = Math.abs(totalShares - 100) > 0.01;

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black/60 backdrop-blur-sm z-50 p-4">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <div className="relative bg-gradient-to-r from-emerald-600 to-teal-600 dark:from-emerald-700 dark:to-teal-700 p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="bg-white/20 p-2 rounded-lg backdrop-blur-sm">
                <Building2 className="w-6 h-6 text-white" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-white">
                  {company ? 'Edit Company' : 'Register New Company'}
                </h2>
                <p className="text-emerald-100 text-sm mt-1">
                  Complete company registration details
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

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
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
                className={`w-full px-4 py-3 border-2 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 dark:bg-slate-800 dark:text-white transition-all ${errors.company_name
                    ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-500'
                    : 'border-slate-200 dark:border-slate-700 hover:border-slate-300'
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
                <Hash className="w-4 h-4" />
                <span>Shortcode</span>
                <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                name="shortcode"
                value={formData.shortcode}
                onChange={handleChange}
                className={`w-full px-4 py-3 border-2 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 dark:bg-slate-800 dark:text-white transition-all ${errors.shortcode
                    ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-500'
                    : 'border-slate-200 dark:border-slate-700 hover:border-slate-300'
                  }`}
                placeholder="Enter Shortcode"
                disabled={isLoading}
              />
              {errors.shortcode && (
                <p className="text-red-500 text-xs mt-2 ml-1 flex items-center">
                  <span className="mr-1">⚠</span>
                  {errors.shortcode}
                </p>
              )}
            </div>

            <div>
              <label className="flex items-center space-x-2 text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
                <Building2 className="w-4 h-4" />
                <span>Company Number (PIN)</span>
                <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                name="company_number"
                value={formData.company_number}
                readOnly
                className={`w-full px-4 py-3 border-2 rounded-xl focus:outline-none bg-slate-100 dark:bg-slate-800/50 dark:text-white cursor-not-allowed transition-all ${errors.company_number
                    ? 'border-red-300 dark:border-red-500'
                    : 'border-slate-200 dark:border-slate-700'
                  }`}
                placeholder="Auto-filled from CR12 document"
                disabled
              />
              {errors.company_number && (
                <p className="text-red-500 text-xs mt-2 ml-1 flex items-center">
                  <span className="mr-1">⚠</span>
                  {errors.company_number}
                </p>
              )}
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-2 ml-1">
                Upload CR12 document below to extract company number
              </p>
            </div>

            <div>
              <label className="flex items-center space-x-2 text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
                <Calendar className="w-4 h-4" />
                <span>Registration Date</span>
              </label>
              <input
                type="date"
                name="registration_date"
                value={formData.registration_date}
                onChange={handleChange}
                className="w-full px-4 py-3 border-2 border-slate-200 dark:border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 dark:bg-slate-800 dark:text-white hover:border-slate-300 transition-all"
                disabled={isLoading}
              />
            </div>

            <div>
              <label className="flex items-center space-x-2 text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
                <MapPin className="w-4 h-4" />
                <span>Address</span>
                <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                name="address"
                value={formData.address}
                onChange={handleChange}
                className={`w-full px-4 py-3 border-2 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 dark:bg-slate-800 dark:text-white transition-all ${errors.address
                    ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-500'
                    : 'border-slate-200 dark:border-slate-700 hover:border-slate-300'
                  }`}
                placeholder="Company address"
                disabled={isLoading}
              />
              {errors.address && (
                <p className="text-red-500 text-xs mt-2 ml-1 flex items-center">
                  <span className="mr-1">⚠</span>
                  {errors.address}
                </p>
              )}
            </div>

            <div>
              <label className="flex items-center space-x-2 text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
                <User className="w-4 h-4" />
                <span>Primary Owner Name</span>
                <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                name="primary_owner_name"
                value={formData.primary_owner_name}
                onChange={handleChange}
                className={`w-full px-4 py-3 border-2 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 dark:bg-slate-800 dark:text-white transition-all ${errors.primary_owner_name
                    ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-500'
                    : 'border-slate-200 dark:border-slate-700 hover:border-slate-300'
                  }`}
                placeholder="Full name"
                disabled={isLoading}
              />
              {errors.primary_owner_name && (
                <p className="text-red-500 text-xs mt-2 ml-1 flex items-center">
                  <span className="mr-1">⚠</span>
                  {errors.primary_owner_name}
                </p>
              )}
            </div>

            <div>
              <label className="flex items-center space-x-2 text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
                <Mail className="w-4 h-4" />
                <span>Primary Owner Email</span>
                <span className="text-red-500">*</span>
              </label>
              <input
                type="email"
                name="primary_owner_email"
                value={formData.primary_owner_email}
                onChange={handleChange}
                className={`w-full px-4 py-3 border-2 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 dark:bg-slate-800 dark:text-white transition-all ${errors.primary_owner_email
                    ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-500'
                    : 'border-slate-200 dark:border-slate-700 hover:border-slate-300'
                  }`}
                placeholder="owner@example.com"
                disabled={isLoading}
              />
              {errors.primary_owner_email && (
                <p className="text-red-500 text-xs mt-2 ml-1 flex items-center">
                  <span className="mr-1">⚠</span>
                  {errors.primary_owner_email}
                </p>
              )}
            </div>

            <div>
              <label className="flex items-center space-x-2 text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
                <Users className="w-4 h-4" />
                <span>Primary Owner Shares (%)</span>
                <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                name="primary_owner_shares"
                value={formData.primary_owner_shares}
                onChange={handleChange}
                min="0"
                max="100"
                step="0.01"
                className={`w-full px-4 py-3 border-2 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 dark:bg-slate-800 dark:text-white transition-all ${errors.primary_owner_shares
                    ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-500'
                    : 'border-slate-200 dark:border-slate-700 hover:border-slate-300'
                  }`}
                placeholder="0.00"
                disabled={isLoading}
              />
              {errors.primary_owner_shares && (
                <p className="text-red-500 text-xs mt-2 ml-1 flex items-center">
                  <span className="mr-1">⚠</span>
                  {errors.primary_owner_shares}
                </p>
              )}
            </div>
          </div>

          <div className="border-t-2 border-slate-200 dark:border-slate-700 pt-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="flex items-center space-x-2 text-lg font-bold text-slate-800 dark:text-white">
                  <Users className="w-5 h-5" />
                  <span>Secondary Shareholders</span>
                </h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                  Total shareholding: <span className={`font-semibold ${sharesInvalid ? 'text-red-500' : 'text-emerald-600'}`}>{totalShares.toFixed(2)}%</span> / 100%
                </p>
              </div>
              <button
                type="button"
                onClick={addShareholder}
                disabled={isLoading}
                className="flex items-center space-x-2 px-4 py-2 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 rounded-lg hover:bg-emerald-200 dark:hover:bg-emerald-900/50 transition-all font-medium"
              >
                <Plus className="w-4 h-4" />
                <span>Add Shareholder</span>
              </button>
            </div>

            {errors.shares && (
              <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 rounded">
                <p className="text-red-700 dark:text-red-400 text-sm flex items-center">
                  <AlertCircle className="w-4 h-4 mr-2" />
                  {errors.shares}
                </p>
              </div>
            )}

            <div className="space-y-3">
              {formData.secondary_shareholders.map((sh, index) => (
                <div key={index} className="bg-slate-50 dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700">
                  <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
                    <div className="md:col-span-5">
                      <input
                        type="text"
                        value={sh.name}
                        onChange={(e) => updateShareholder(index, 'name', e.target.value)}
                        placeholder="Shareholder name"
                        className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 dark:bg-slate-900 dark:text-white text-sm"
                        disabled={isLoading}
                      />
                    </div>
                    <div className="md:col-span-4">
                      <input
                        type="email"
                        value={sh.email}
                        onChange={(e) => updateShareholder(index, 'email', e.target.value)}
                        placeholder="Email"
                        className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 dark:bg-slate-900 dark:text-white text-sm ${errors[`shareholder_email_${index}`] ? 'border-red-500' : 'border-slate-300 dark:border-slate-600'
                          }`}
                        disabled={isLoading}
                      />
                      {errors[`shareholder_email_${index}`] && (
                        <p className="text-red-500 text-xs mt-1">{errors[`shareholder_email_${index}`]}</p>
                      )}
                    </div>
                    <div className="md:col-span-2">
                      <input
                        type="number"
                        value={sh.shares}
                        onChange={(e) => updateShareholder(index, 'shares', e.target.value)}
                        placeholder="Shares %"
                        min="0"
                        max="100"
                        step="0.01"
                        className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 dark:bg-slate-900 dark:text-white text-sm ${errors[`shareholder_shares_${index}`] ? 'border-red-500' : 'border-slate-300 dark:border-slate-600'
                          }`}
                        disabled={isLoading}
                      />
                    </div>
                    <div className="md:col-span-1 flex items-center">
                      <button
                        type="button"
                        onClick={() => removeShareholder(index)}
                        className="p-2 text-red-600 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-lg transition-all"
                        disabled={isLoading}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}

              {formData.secondary_shareholders.length === 0 && (
                <p className="text-center text-slate-500 dark:text-slate-400 py-8 text-sm">
                  No secondary shareholders added yet
                </p>
              )}
            </div>
          </div>

          <div className="border-t-2 border-slate-200 dark:border-slate-700 pt-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="flex items-center space-x-2 text-lg font-bold text-slate-800 dark:text-white">
                <Users className="w-5 h-5" />
                <span>Directors</span>
              </h3>
              <button
                type="button"
                onClick={addDirector}
                disabled={isLoading}
                className="flex items-center space-x-2 px-4 py-2 bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-400 rounded-lg hover:bg-teal-200 dark:hover:bg-teal-900/50 transition-all font-medium"
              >
                <Plus className="w-4 h-4" />
                <span>Add Director</span>
              </button>
            </div>

            <div className="space-y-3">
              {formData.directors.map((dir, index) => (
                <div key={index} className="bg-slate-50 dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700">
                  <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
                    <div className="md:col-span-5">
                      <input
                        type="text"
                        value={dir.name}
                        onChange={(e) => updateDirector(index, 'name', e.target.value)}
                        placeholder="Director name"
                        className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 dark:bg-slate-900 dark:text-white text-sm"
                        disabled={isLoading}
                      />
                    </div>
                    <div className="md:col-span-6">
                      <input
                        type="email"
                        value={dir.email}
                        onChange={(e) => updateDirector(index, 'email', e.target.value)}
                        placeholder="Email"
                        className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 dark:bg-slate-900 dark:text-white text-sm ${errors[`director_email_${index}`] ? 'border-red-500' : 'border-slate-300 dark:border-slate-600'
                          }`}
                        disabled={isLoading}
                      />
                      {errors[`director_email_${index}`] && (
                        <p className="text-red-500 text-xs mt-1">{errors[`director_email_${index}`]}</p>
                      )}
                    </div>
                    <div className="md:col-span-1 flex items-center">
                      <button
                        type="button"
                        onClick={() => removeDirector(index)}
                        className="p-2 text-red-600 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-lg transition-all"
                        disabled={isLoading}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}

              {formData.directors.length === 0 && (
                <p className="text-center text-slate-500 dark:text-slate-400 py-8 text-sm">
                  No directors added yet
                </p>
              )}
            </div>
          </div>

          <div className="border-t-2 border-slate-200 dark:border-slate-700 pt-6">
            <h3 className="flex items-center space-x-2 text-lg font-bold text-slate-800 dark:text-white mb-4">
              <FileText className="w-5 h-5" />
              <span>CR12 Document</span>
            </h3>

            <div className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-xl p-6 border-2 border-dashed border-blue-300 dark:border-blue-700">
              <div className="flex flex-col items-center justify-center space-y-4">
                <div className="bg-blue-100 dark:bg-blue-900/40 p-4 rounded-full">
                  <Upload className="w-8 h-8 text-blue-600 dark:text-blue-400" />
                </div>

                <div className="text-center">
                  <label htmlFor="cr12-upload" className="cursor-pointer">
                    <span className="text-blue-600 dark:text-blue-400 font-semibold hover:text-blue-700 dark:hover:text-blue-300 transition-colors">
                      Click to upload
                    </span>
                    <span className="text-slate-600 dark:text-slate-400"> or drag and drop</span>
                  </label>
                  <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                    PDF only (max 5MB)
                  </p>
                </div>

                <input
                  id="cr12-upload"
                  type="file"
                  accept=".pdf"
                  onChange={handleFileChange}
                  className="hidden"
                  disabled={isLoading || isUploadingCR12}
                />

                {isUploadingCR12 && (
                  <div className="flex items-center space-x-2 text-blue-600 dark:text-blue-400">
                    <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span className="text-sm font-medium">Extracting company number...</span>
                  </div>
                )}

                {formData.cr12_file && !isUploadingCR12 && (
                  <div className="flex items-center space-x-2 bg-white dark:bg-slate-800 px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700">
                    <FileText className="w-4 h-4 text-emerald-600" />
                    <span className="text-sm text-slate-700 dark:text-slate-300 font-medium">
                      {formData.cr12_file.name}
                    </span>
                  </div>
                )}

                {!formData.cr12_file && formData.cr12_preview && !isUploadingCR12 && (
                  <a
                    href={formData.cr12_preview}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center space-x-2 text-emerald-600 hover:text-emerald-700 dark:text-emerald-400 dark:hover:text-emerald-300 transition-colors"
                  >
                    <FileText className="w-4 h-4" />
                    <span className="text-sm font-medium">View Current CR12</span>
                  </a>
                )}
              </div>

              {errors.cr12_file && (
                <p className="text-red-500 text-sm mt-4 flex items-center justify-center">
                  <AlertCircle className="w-4 h-4 mr-2" />
                  {errors.cr12_file}
                </p>
              )}
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
              disabled={isLoading || sharesInvalid || isUploadingCR12 || !isCR12Valid}
              className="flex-1 py-3 px-4 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white font-semibold rounded-xl transition-all focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-emerald-500/30"
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
                <span>{company ? 'Update Company' : 'Register Company'}</span>
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

export default CompanyDetailsModal; 