import { useState, useEffect, useRef } from 'react';
import { X, Building2, MapPin, Phone, CreditCard, Hash, ChevronDown, Check } from 'lucide-react';
import axios from 'axios';
import config from '../../Config';

function AgentCompanyDetailsModal({ isOpen, onClose, onSubmit, isLoading, agentCompany }) {
  const [formData, setFormData] = useState({
    company_name: '',
    location: '',
    location_details: '',
    contact_phone: '',
    store_number: '',
    agent_number: '',
    short_code: '',
    agentcompany_code: '',
    selected_company: null,
  });
  const [errors, setErrors] = useState({});
  const [searchQuery, setSearchQuery] = useState('');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [companySearchQuery, setCompanySearchQuery] = useState('');
  const [isCompanyDropdownOpen, setIsCompanyDropdownOpen] = useState(false);
  const [companies, setCompanies] = useState([]);
  const [loadingCompanies, setLoadingCompanies] = useState(false);
  const dropdownRef = useRef(null);
  const companyDropdownRef = useRef(null);

  // List of all 47 Kenyan counties
  const counties = [
    'Baringo', 'Bomet', 'Bungoma', 'Busia', 'Elgeyo-Marakwet', 'Embu', 'Garissa',
    'Homa Bay', 'Isiolo', 'Kajiado', 'Kakamega', 'Kericho', 'Kiambu', 'Kilifi',
    'Kirinyaga', 'Kisii', 'Kisumu', 'Kitui', 'Kwale', 'Laikipia', 'Lamu',
    'Machakos', 'Makueni', 'Mandera', 'Marsabit', 'Meru', 'Migori', 'Mombasa',
    'Murang\'a', 'Nairobi', 'Nakuru', 'Nandi', 'Narok', 'Nyamira', 'Nyandarua',
    'Nyeri', 'Samburu', 'Siaya', 'Taita-Taveta', 'Tana River', 'Tharaka-Nithi',
    'Trans Nzoia', 'Turkana', 'Uasin Gishu', 'Vihiga', 'Wajir', 'West Pokot'
  ];

  // Fetch companies from API when modal opens
  useEffect(() => {
    const fetchCompanies = async () => {
      if (!isOpen) return;

      setLoadingCompanies(true);
      try {
        const token = localStorage.getItem('token');
        const response = await axios.get(`${config.API_URL}/company/`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        setCompanies(response.data);
      } catch (error) {
        console.error('Error fetching companies:', error);
        // Fallback to demo data if API fails
        setCompanies([
          { id: 1, company_name: 'Safaricom Ltd' },
          { id: 2, company_name: 'Equity Bank' },
          { id: 3, company_name: 'KCB Bank' },
          { id: 4, company_name: 'M-Pesa Holdings' },
          { id: 5, company_name: 'Airtel Kenya' },
        ]);
      } finally {
        setLoadingCompanies(false);
      }
    };

    fetchCompanies();
  }, [isOpen]);

  // Filter counties based on search query
  const filteredCounties = counties.filter((county) =>
    county.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Filter companies based on search query
  const filteredCompanies = companies.filter((company) =>
    company.company_name.toLowerCase().includes(companySearchQuery.toLowerCase())
  );

  useEffect(() => {
    if (agentCompany) {
      setFormData({
        company_name: agentCompany.company_name || '',
        location: agentCompany.location || '',
        location_details: agentCompany.location_details || '',
        contact_phone: agentCompany.contact_phone || '',
        store_number: agentCompany.store_number || '',
        agent_number: agentCompany.agent_number || '',
        short_code: agentCompany.short_code || '',
        agentcompany_code: agentCompany.agentcompany_code || '',
        selected_company: agentCompany.company_id || null,
      });
    } else {
      setFormData({
        company_name: '',
        location: '',
        location_details: '',
        contact_phone: '',
        store_number: '',
        agent_number: '',
        short_code: '',
        agentcompany_code: '',
        selected_company: null,
      });
    }
    setErrors({});
    setSearchQuery('');
    setCompanySearchQuery('');
    setIsDropdownOpen(false);
    setIsCompanyDropdownOpen(false);
  }, [agentCompany, isOpen]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
      if (companyDropdownRef.current && !companyDropdownRef.current.contains(event.target)) {
        setIsCompanyDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setErrors((prev) => ({ ...prev, [name]: '' }));
  };

  const handleCountySelect = (county) => {
    setFormData((prev) => ({ ...prev, location: county }));
    setErrors((prev) => ({ ...prev, location: '' }));
    setSearchQuery('');
    setIsDropdownOpen(false);
  };

  const handleSearchChange = (e) => {
    setSearchQuery(e.target.value);
    setIsDropdownOpen(true);
  };

  const handleCompanySearchChange = (e) => {
    setCompanySearchQuery(e.target.value);
    setIsCompanyDropdownOpen(true);
  };

  const handleCompanySelect = (companyId) => {
    setFormData((prev) => ({ ...prev, selected_company: companyId }));
    setErrors((prev) => ({ ...prev, selected_company: '' }));
    setCompanySearchQuery('');
    setIsCompanyDropdownOpen(false);
  };

  const handleRemoveCompany = () => {
    setFormData((prev) => ({ ...prev, selected_company: null }));
  };

  const getSelectedCompanyName = () => {
    const selected = companies.find((company) => company.id === formData.selected_company);
    return selected ? selected.company_name : null;
  };

  const validateForm = () => {
    const newErrors = {};
    if (!formData.company_name.trim()) {
      newErrors.company_name = 'Company name is required';
    }
    if (!formData.location.trim()) {
      newErrors.location = 'Location is required';
    }
    if (!formData.location_details.trim()) {
      newErrors.location_details = 'Location details are required';
    }
    if (formData.contact_phone && !/^\+?\d{1,3}?\d{9,12}$/.test(formData.contact_phone)) {
      newErrors.contact_phone = 'Invalid phone number format (e.g., +254712345678)';
    }
    if (!formData.store_number.trim()) {
      newErrors.store_number = 'Store number is required';
    } else if (!/^\d+$/.test(formData.store_number)) {
      newErrors.store_number = 'Store number must contain only digits';
    }
    if (!formData.agent_number.trim()) {
      newErrors.agent_number = 'Agent number is required';
    } else if (!/^\d+$/.test(formData.agent_number)) {
      newErrors.agent_number = 'Agent number must contain only digits';
    }
    if (!formData.selected_company) {
      newErrors.selected_company = 'Please select a company';
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
        location_details: '',
        contact_phone: '',
        store_number: '',
        agent_number: '',
        short_code: '',
        agentcompany_code: '',
        selected_company: null,
      });
      setErrors({});
      setSearchQuery('');
      setCompanySearchQuery('');
      setIsDropdownOpen(false);
      setIsCompanyDropdownOpen(false);
    });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black/60 backdrop-blur-sm z-50 p-4">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-[95vw] sm:max-w-3xl transform transition-all max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 z-10 bg-gradient-to-r from-violet-600 via-purple-600 to-indigo-600 dark:from-violet-700 dark:via-purple-700 dark:to-indigo-700 rounded-t-2xl p-4 sm:p-6 md:p-8">
          <div className="absolute inset-0 bg-black/10 rounded-t-2xl"></div>
          <div className="relative flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="bg-white/20 p-3 rounded-xl backdrop-blur-sm shadow-lg">
                <Building2 className="w-7 h-7 text-white" />
              </div>
              <div>
                <h2 className="text-3xl font-bold text-white tracking-tight">
                  {agentCompany ? 'Edit Agent Till' : 'New Agent Till'}
                </h2>
                <p className="text-purple-100 text-sm mt-1.5 font-medium">
                  {agentCompany ? 'Update agent till information' : 'Register a new agent till'}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-white/80 hover:text-white hover:bg-white/20 p-2.5 rounded-xl transition-all hover:rotate-90 duration-300"
              disabled={isLoading}
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        <div className="p-8 space-y-6">
          {agentCompany && (
            <div className="bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-800 dark:to-slate-800/50 rounded-xl p-5 border-2 border-dashed border-slate-300 dark:border-slate-600 shadow-inner">
              <label className="flex items-center space-x-2 text-sm font-bold text-slate-600 dark:text-slate-400 mb-3">
                <Hash className="w-4 h-4" />
                <span>Agent Till Code</span>
              </label>
              <div className="bg-white dark:bg-slate-900 rounded-lg p-3 border border-slate-300 dark:border-slate-600">
                <input
                  type="text"
                  value={formData.agentcompany_code}
                  readOnly
                  className="w-full bg-transparent text-slate-800 dark:text-slate-200 font-mono text-base font-semibold cursor-not-allowed focus:outline-none"
                />
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="md:col-span-2">
              <label className="flex items-center space-x-2 text-sm font-bold text-slate-700 dark:text-slate-300 mb-3">
                <Building2 className="w-4 h-4 text-violet-600 dark:text-violet-400" />
                <span>Agent Till Name</span>
                <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                name="company_name"
                value={formData.company_name}
                onChange={handleChange}
                className={`w-full px-4 py-3.5 border-2 rounded-xl focus:outline-none focus:ring-2 focus:ring-violet-500 dark:bg-slate-800 dark:text-white transition-all font-medium ${errors.company_name
                    ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-500'
                    : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
                  }`}
                placeholder="Enter agent till name"
                disabled={isLoading}
              />
              {errors.company_name && (
                <p className="text-red-500 text-xs mt-2 ml-1 flex items-center font-medium">
                  <span className="mr-1">⚠</span>
                  {errors.company_name}
                </p>
              )}
            </div>

            <div className="md:col-span-2" ref={companyDropdownRef}>
              <label className="flex items-center space-x-2 text-sm font-bold text-slate-700 dark:text-slate-300 mb-3">
                <Building2 className="w-4 h-4 text-violet-600 dark:text-violet-400" />
                <span>Associated Company</span>
                <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <div
                  className={`w-full px-4 py-3.5 border-2 rounded-xl focus:outline-none focus:ring-2 focus:ring-violet-500 dark:bg-slate-800 dark:text-white transition-all font-medium flex items-center justify-between cursor-pointer ${errors.selected_company
                      ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-500'
                      : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
                    }`}
                  onClick={() => !isLoading && !loadingCompanies && setIsCompanyDropdownOpen(!isCompanyDropdownOpen)}
                >
                  {formData.selected_company ? (
                    <div className="flex items-center justify-between w-full">
                      <span>{getSelectedCompanyName()}</span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRemoveCompany();
                        }}
                        className="hover:bg-violet-200 dark:hover:bg-violet-800 rounded-full p-0.5 transition-colors"
                        disabled={isLoading}
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between w-full">
                      <span className="text-slate-500 dark:text-slate-400">
                        {loadingCompanies ? 'Loading companies...' : 'Select a company'}
                      </span>
                      <ChevronDown className="w-5 h-5 text-violet-600 dark:text-violet-400" />
                    </div>
                  )}
                </div>
                {isCompanyDropdownOpen && !loadingCompanies && (
                  <div className="absolute z-20 w-full mt-1 bg-white dark:bg-slate-800 border-2 border-slate-200 dark:border-slate-700 rounded-xl shadow-lg max-h-60 overflow-y-auto">
                    <input
                      type="text"
                      value={companySearchQuery}
                      onChange={handleCompanySearchChange}
                      placeholder="Search companies..."
                      className="w-full px-4 py-2.5 border-b border-slate-200 dark:border-slate-700 dark:text-white focus:outline-none sticky top-0 bg-white dark:bg-slate-800"
                      disabled={isLoading}
                      onClick={(e) => e.stopPropagation()}
                    />
                    {filteredCompanies.length > 0 ? (
                      filteredCompanies.map((company) => (
                        <div
                          key={company.id}
                          className="px-4 py-2.5 hover:bg-slate-100 dark:hover:bg-slate-700 cursor-pointer dark:text-white flex items-center justify-between"
                          onClick={() => handleCompanySelect(company.id)}
                        >
                          <span>{company.company_name}</span>
                          {formData.selected_company === company.id && (
                            <Check className="w-5 h-5 text-violet-600 dark:text-violet-400" />
                          )}
                        </div>
                      ))
                    ) : (
                      <div className="px-4 py-2.5 text-slate-500 dark:text-slate-400">
                        No companies found
                      </div>
                    )}
                  </div>
                )}
              </div>
              {errors.selected_company && (
                <p className="text-red-500 text-xs mt-2 ml-1 flex items-center font-medium">
                  <span className="mr-1">⚠</span>
                  {errors.selected_company}
                </p>
              )}
            </div>

            <div ref={dropdownRef}>
              <label className="flex items-center space-x-2 text-sm font-bold text-slate-700 dark:text-slate-300 mb-3">
                <MapPin className="w-4 h-4 text-violet-600 dark:text-violet-400" />
                <span>County</span>
                <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <div
                  className={`w-full px-4 py-3.5 border-2 rounded-xl focus:outline-none focus:ring-2 focus:ring-violet-500 dark:bg-slate-800 dark:text-white transition-all font-medium flex items-center justify-between cursor-pointer ${errors.location
                      ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-500'
                      : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
                    }`}
                  onClick={() => !isLoading && setIsDropdownOpen(!isDropdownOpen)}
                >
                  <span>{formData.location || 'Select a county'}</span>
                  <ChevronDown className="w-5 h-5 text-violet-600 dark:text-violet-400" />
                </div>
                {isDropdownOpen && (
                  <div className="absolute z-10 w-full mt-1 bg-white dark:bg-slate-800 border-2 border-slate-200 dark:border-slate-700 rounded-xl shadow-lg max-h-60 overflow-y-auto">
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={handleSearchChange}
                      placeholder="Search counties..."
                      className="w-full px-4 py-2.5 border-b border-slate-200 dark:border-slate-700 dark:text-white focus:outline-none sticky top-0 bg-white dark:bg-slate-800"
                      disabled={isLoading}
                    />
                    {filteredCounties.length > 0 ? (
                      filteredCounties.map((county) => (
                        <div
                          key={county}
                          className="px-4 py-2.5 hover:bg-slate-100 dark:hover:bg-slate-700 cursor-pointer dark:text-white"
                          onClick={() => handleCountySelect(county)}
                        >
                          {county}
                        </div>
                      ))
                    ) : (
                      <div className="px-4 py-2.5 text-slate-500 dark:text-slate-400">
                        No counties found
                      </div>
                    )}
                  </div>
                )}
              </div>
              {errors.location && (
                <p className="text-red-500 text-xs mt-2 ml-1 flex items-center font-medium">
                  <span className="mr-1">⚠</span>
                  {errors.location}
                </p>
              )}
            </div>

            <div>
              <label className="flex items-center space-x-2 text-sm font-bold text-slate-700 dark:text-slate-300 mb-3">
                <MapPin className="w-4 h-4 text-violet-600 dark:text-violet-400" />
                <span>Location Details</span>
                <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                name="location_details"
                value={formData.location_details}
                onChange={handleChange}
                className={`w-full px-4 py-3.5 border-2 rounded-xl focus:outline-none focus:ring-2 focus:ring-violet-500 dark:bg-slate-800 dark:text-white transition-all font-medium ${errors.location_details
                    ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-500'
                    : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
                  }`}
                placeholder="e.g., Westlands, CBD"
                disabled={isLoading}
              />
              {errors.location_details && (
                <p className="text-red-500 text-xs mt-2 ml-1 flex items-center font-medium">
                  <span className="mr-1">⚠</span>
                  {errors.location_details}
                </p>
              )}
            </div>

            <div>
              <label className="flex items-center space-x-2 text-sm font-bold text-slate-700 dark:text-slate-300 mb-3">
                <Phone className="w-4 h-4 text-violet-600 dark:text-violet-400" />
                <span>Contact Phone</span>
              </label>
              <input
                type="text"
                name="contact_phone"
                value={formData.contact_phone}
                onChange={handleChange}
                className={`w-full px-4 py-3.5 border-2 rounded-xl focus:outline-none focus:ring-2 focus:ring-violet-500 dark:bg-slate-800 dark:text-white transition-all font-medium ${errors.contact_phone
                    ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-500'
                    : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
                  }`}
                placeholder="+254712345678"
                disabled={isLoading}
              />
              {errors.contact_phone && (
                <p className="text-red-500 text-xs mt-2 ml-1 flex items-center font-medium">
                  <span className="mr-1">⚠</span>
                  {errors.contact_phone}
                </p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-6">
              <div>
                <label className="flex items-center space-x-2 text-sm font-bold text-slate-700 dark:text-slate-300 mb-3">
                  <CreditCard className="w-4 h-4 text-violet-600 dark:text-violet-400" />
                  <span>Agent Number</span>
                  <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  name="agent_number"
                  value={formData.agent_number}
                  onChange={handleChange}
                  className={`w-full px-4 py-3.5 border-2 rounded-xl focus:outline-none focus:ring-2 focus:ring-violet-500 dark:bg-slate-800 dark:text-white transition-all font-medium ${errors.agent_number
                      ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-500'
                      : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
                    }`}
                  placeholder="Enter agent number"
                  disabled={isLoading}
                />
                {errors.agent_number && (
                  <p className="text-red-500 text-xs mt-2 ml-1 flex items-center font-medium">
                    <span className="mr-1">⚠</span>
                    {errors.agent_number}
                  </p>
                )}
              </div>
              <div>
                <label className="flex items-center space-x-2 text-sm font-bold text-slate-700 dark:text-slate-300 mb-3">
                  <CreditCard className="w-4 h-4 text-violet-600 dark:text-violet-400" />
                  <span>Store Number</span>
                  <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  name="store_number"
                  value={formData.store_number}
                  onChange={handleChange}
                  className={`w-full px-4 py-3.5 border-2 rounded-xl focus:outline-none focus:ring-2 focus:ring-violet-500 dark:bg-slate-800 dark:text-white transition-all font-medium ${errors.store_number
                      ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-500'
                      : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
                    }`}
                  placeholder="Enter store number"
                  disabled={isLoading}
                />
                {errors.store_number && (
                  <p className="text-red-500 text-xs mt-2 ml-1 flex items-center font-medium">
                    <span className="mr-1">⚠</span>
                    {errors.store_number}
                  </p>
                )}
              </div>
            </div>

            <div>
              <label className="flex items-center space-x-2 text-sm font-bold text-slate-700 dark:text-slate-300 mb-3">
                <Hash className="w-4 h-4 text-violet-600 dark:text-violet-400" />
                <span>Till Short Code</span>
              </label>
              <input
                type="text"
                name="short_code"
                value={formData.short_code}
                onChange={handleChange}
                className="w-full px-4 py-3.5 border-2 rounded-xl focus:outline-none focus:ring-2 focus:ring-violet-500 dark:bg-slate-800 dark:text-white transition-all font-medium border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600"
                placeholder="e.g. 247247"
                disabled={isLoading}
              />
            </div>
          </div>

          <div className="flex space-x-4 pt-6 border-t-2 border-slate-200 dark:border-slate-700">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-3.5 px-5 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 font-bold rounded-xl hover:bg-slate-300 dark:hover:bg-slate-600 transition-all shadow-sm hover:shadow-md transform hover:scale-[1.02]"
              disabled={isLoading}
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={isLoading || loadingCompanies}
              className="flex-1 py-3.5 px-5 bg-gradient-to-r from-violet-600 via-purple-600 to-indigo-600 hover:from-violet-700 hover:via-purple-700 hover:to-indigo-700 text-white font-bold rounded-xl transition-all shadow-lg shadow-violet-500/40 hover:shadow-xl hover:shadow-violet-500/50 disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-[1.02]"
            >
              {isLoading ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-2 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
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
            <span className="text-red-500 font-bold">*</span> Required fields
          </p>
        </div>
      </div>
    </div>
  );
}

export default AgentCompanyDetailsModal;