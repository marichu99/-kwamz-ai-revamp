import { useState, useEffect } from 'react';
import axios from 'axios';
import { X, User as UserIcon, Phone, IdCard, Calendar, Shield, FileText, Camera, Briefcase, AlertCircle, Search, Check, Database, Clock } from 'lucide-react';
import { useToast } from './ToastProvider';
import config from '../../Config';

function UserDetailsModal({ isOpen, onClose, onSubmit, isLoading, user }) {
  const { showToast } = useToast();
  const [formData, setFormData] = useState({
    firstname: '',
    lastname: '',
    idnumber: '',
    phone_number: '',
    is_authentic: 'false',
    authenticity_desc: '',
    date_of_birth: '',
    image: null,
    imagePreview: null,
    agent_company_ids: [],
    agent_company_id: '',
  });
  const [agentCompanies, setAgentCompanies] = useState([]);
  const [loadingAgentCompanies, setLoadingAgentCompanies] = useState(false);
  const [fetchError, setFetchError] = useState('');
  const [errors, setErrors] = useState({});
  const [searchTerm, setSearchTerm] = useState('');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  const isEditMode = !!user;

  // Fetch agent companies when modal opens
  useEffect(() => {
    const abortController = new AbortController();

    const fetchAgentCompanies = async () => {
      if (!isOpen) return;

      setLoadingAgentCompanies(true);
      setFetchError('');
      
      try {
        const token = localStorage.getItem('token');
        if (!token) {
          throw new Error('Authentication token not found');
        }
        const response = await axios.get(`${config.API_URL}/agentcompany`, {
          headers: { Authorization: `Bearer ${token}` },
          signal: abortController.signal,
        });
        setAgentCompanies(Array.isArray(response.data) ? response.data : []);
      } catch (error) {
        if (error.name !== 'AbortError') {
          console.error('Error fetching agent companies:', error.response?.data || error.message);
          setFetchError('Failed to load agent companies. Please try again.');
          showToast('Failed to load agent companies', 'error');
        }
      } finally {
        setLoadingAgentCompanies(false);
      }
    };

    fetchAgentCompanies();

    return () => {
      abortController.abort();
    };
  }, [isOpen, showToast]);

  // Populate form with user data when in edit mode or apply provided data
  useEffect(() => {
    if (isEditMode && user) {
      setFormData({
        firstname: user.firstname || '',
        lastname: user.lastname || '',
        idnumber: user.idnumber || '',
        phone_number: user.phone_number || '',
        is_authentic: user.is_authentic ? 'true' : 'false',
        authenticity_desc: user.authenticity_desc || '',
        date_of_birth: user.date_of_birth ? new Date(user.date_of_birth).toISOString().split('T')[0] : '',
        image: null,
        imagePreview: user.image_loc ? `/useragents/profiles/${user.image_loc.split('/').pop()}` : null,
        agent_company_ids: user.agent_company_ids || [],
        agent_company_id: user.agent_company_id || '',
      });
    } else {
      setFormData({
        firstname: '',
        lastname: '',
        idnumber: '',
        phone_number: '',
        is_authentic: '',
        authenticity_desc: '',
        date_of_birth: '',
        image: null,
        imagePreview: null,
        agent_company_ids: [],
        agent_company_id: '',
      });
    }
    setErrors({});
    setSearchTerm('');
    setIsDropdownOpen(false);
  }, [user, isOpen, isEditMode]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setErrors((prev) => ({ ...prev, [name]: '' }));
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) {
        setErrors((prev) => ({ ...prev, image: 'Image size must be less than 5MB' }));
        showToast('Image size must be less than 5MB', 'error');
        return;
      }
      const reader = new FileReader();
      reader.onload = (e) => {
        setFormData((prev) => ({
          ...prev,
          image: file,
          imagePreview: e.target.result,
        }));
        setErrors((prev) => ({ ...prev, image: '' }));
      };
      reader.readAsDataURL(file);
    }
  };

  const toggleAgentCompany = (companyId) => {
    setFormData(prev => {
      const currentIds = prev.agent_company_ids || [];
      const newIds = currentIds.includes(companyId)
        ? currentIds.filter(id => id !== companyId)
        : [...currentIds, companyId];
      
      // Clear error when at least one company is selected
      if (newIds.length > 0) {
        setErrors(prevErrors => ({ ...prevErrors, agent_company_ids: '' }));
      }
      
      return { ...prev, agent_company_ids: newIds };
    });
  };

  const removeAgentCompany = (companyId, e) => {
    e.stopPropagation();
    toggleAgentCompany(companyId);
  };

  const filteredAgentCompanies = agentCompanies.filter(company =>
    company.company_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    company.registration_number?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    company.short_code?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getSelectedCompanyNames = () => {
    return formData.agent_company_ids.map(id => {
      const company = agentCompanies.find(c => c.id === id);
      return company ? company.company_name : 'Unknown Company';
    });
  };

  const validateForm = () => {
    const newErrors = {};
    if (!formData.firstname) newErrors.firstname = 'First name is required';
    if (!formData.lastname) newErrors.lastname = 'Last name is required';
    if (!formData.idnumber) newErrors.idnumber = 'ID number is required';
    if (!formData.agent_company_id) {
      newErrors.agent_company_id = 'Primary agent company is required';
    }
    if (formData.phone_number && !/^\+?\d{1,3}?\d{9,12}$/.test(formData.phone_number)) {
      newErrors.phone_number = 'Invalid phone number format';
    }
    if (formData.date_of_birth && new Date(formData.date_of_birth) > new Date()) {
      newErrors.date_of_birth = 'Date of birth cannot be in the future';
    }
    return newErrors;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const validationErrors = validateForm();
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      showToast('Please fix the form errors', 'error');
      return;
    }

    const formDataToSend = new FormData();
    Object.entries(formData).forEach(([key, value]) => {
      if (key !== 'imagePreview' && value !== null && value !== undefined) {
        if (key === 'agent_company_ids' && Array.isArray(value)) {
          // Join agent_company_ids into a comma-separated string
          formDataToSend.append('agent_company_ids', value.join(','));
        } else if (key === 'agent_company_id') {
          formDataToSend.append('agent_company_id', value);
        } else {
          formDataToSend.append(key, value);
        }
      }
    });

    onSubmit(formDataToSend, isEditMode ? user.id : null);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gradient-to-br from-black/60 via-black/50 to-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white/95 dark:bg-slate-900/95 backdrop-blur-lg rounded-2xl shadow-2xl border border-white/20 dark:border-slate-700/50 w-full max-w-[95vw] sm:max-w-3xl transform transition-all duration-300 max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="relative bg-gradient-to-r from-blue-600 via-cyan-600 to-blue-700 dark:from-blue-700 dark:via-cyan-700 dark:to-blue-800 p-4 sm:p-6 md:p-8">
          <div className="absolute inset-0 bg-black/10"></div>
          <div className="relative flex items-center justify-between">
            <div className="flex items-center space-x-3 sm:space-x-4">
              <div className="bg-white/20 p-2 sm:p-3 rounded-xl backdrop-blur-sm shadow-lg">
                <UserIcon className="w-5 h-5 sm:w-7 sm:h-7 text-white" />
              </div>
              <div>
                <h2 className="text-xl sm:text-2xl md:text-3xl font-bold text-white tracking-tight">
                  {isEditMode ? 'Edit User Details' : 'Create New Agent User'}
                </h2>
                <p className="text-blue-100 text-sm mt-1.5 font-medium">
                  {isEditMode ? 'Update the details of the selected user' : 'Fill in the details to add a new user'}
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

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-8 space-y-6">
          {/* Profile Image Section */}
          <div className="text-center pb-6 border-b-2 border-slate-200 dark:border-slate-700">
            <div className="relative inline-block">
              <div className="w-28 h-28 rounded-full bg-gradient-to-br from-blue-200 to-cyan-200 dark:from-blue-800 dark:to-cyan-800 ring-4 ring-blue-500 dark:ring-blue-400 overflow-hidden shadow-xl">
                {formData.imagePreview ? (
                  <img src={formData.imagePreview} alt="Profile" className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <Camera className="w-12 h-12 text-slate-500 dark:text-slate-400" />
                  </div>
                )}
              </div>

              {formData.imagePreview && (
                <button
                  type="button"
                  onClick={() => {
                    setFormData((prev) => ({ ...prev, image: null, imagePreview: null }));
                    const fileInput = document.querySelector('input[type="file"]');
                    if (fileInput) fileInput.value = '';
                  }}
                  className="absolute -top-1 -right-1 w-8 h-8 bg-red-500 hover:bg-red-600 text-white rounded-full flex items-center justify-center transition-all shadow-lg transform hover:scale-110"
                >
                  <X className="w-4 h-4" />
                </button>
              )}

              <label
                htmlFor="profile-image"
                className="absolute -bottom-2 -right-2 bg-blue-600 hover:bg-blue-700 text-white p-2.5 rounded-full cursor-pointer transition-all shadow-lg transform hover:scale-110"
              >
                <Camera className="w-5 h-5" />
              </label>
              <input
                id="profile-image"
                type="file"
                accept="image/*"
                onChange={handleFileChange}
                className="hidden"
                disabled={isLoading}
              />
              {errors.image && (
                <p className="text-red-500 text-xs mt-2 flex items-center font-medium">
                  <span className="mr-1">⚠</span>
                  {errors.image}
                </p>
              )}
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400 mt-3 font-medium">
              Click the camera icon to change profile picture (max 5MB)
            </p>
          </div>

          {/* Primary Agent Company Selection */}
          <div className="bg-gradient-to-br from-green-50/50 to-emerald-50/50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-xl p-6 border-2 border-green-100 dark:border-green-800/30">
            <label className="flex items-center space-x-2 text-sm font-bold text-slate-700 dark:text-slate-300 mb-3">
              <Briefcase className="w-5 h-5 text-green-600 dark:text-green-400" />
              <span>Primary Agent Company</span>
              <span className="text-red-500">*</span>
            </label>
            <select
              name="agent_company_id"
              value={formData.agent_company_id}
              onChange={handleInputChange}
              className={`w-full px-4 py-3.5 border-2 rounded-xl font-medium transition-all bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-green-200 dark:focus:ring-green-900 hover:border-slate-300 ${
                errors.agent_company_id
                  ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-500'
                  : 'border-slate-200 dark:border-slate-700'
              }`}
              disabled={isLoading || loadingAgentCompanies}
            >
              <option value="">
                {loadingAgentCompanies ? 'Loading...' : 'Select primary company...'}
              </option>
              {agentCompanies.map((company) => (
                <option key={company.id} value={company.id}>
                  {company.company_name} {company.short_code ? `[${company.short_code}]` : ''} {company.registration_number ? `(${company.registration_number})` : ''}
                </option>
              ))}
            </select>
            {errors.agent_company_id && (
              <p className="text-red-500 text-xs mt-2 ml-1 flex items-center font-medium">
                <span className="mr-1">⚠</span>
                {errors.agent_company_id}
              </p>
            )}
            {/* Show primary company scrape status in edit mode */}
            {isEditMode && user?.primary_company && (
              <div className={`mt-2 ml-1 flex items-center gap-2 text-xs font-medium ${user.primary_company.is_scraped ? 'text-green-600 dark:text-green-400' : 'text-amber-600 dark:text-amber-400'}`}>
                <Database className="w-3.5 h-3.5" />
                {user.primary_company.is_scraped ? (
                  <span>Scraped on {new Date(user.primary_company.last_scraped_at).toLocaleDateString()}</span>
                ) : (
                  <span>Not yet scraped from portal</span>
                )}
                {user.primary_company.identity_status && (
                  <span className={`px-1.5 py-0.5 rounded text-xs ${user.primary_company.identity_status === 'Active' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'}`}>
                    {user.primary_company.identity_status}
                  </span>
                )}
              </div>
            )}
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-2 ml-1">
              The main company this agent is associated with
            </p>
          </div>

          {/* Additional Agent Companies Selection */}
          <div className="bg-gradient-to-br from-blue-50/50 to-cyan-50/50 dark:from-blue-900/20 dark:to-cyan-900/20 rounded-xl p-6 border-2 border-blue-100 dark:border-blue-800/30">
            <label className="flex items-center space-x-2 text-sm font-bold text-slate-700 dark:text-slate-300 mb-3">
              <Briefcase className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              <span>Additional Agent Companies</span>
            </label>
            
            {fetchError && (
              <div className="mb-3 p-3 bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 rounded">
                <p className="text-red-700 dark:text-red-400 text-sm flex items-center">
                  <AlertCircle className="w-4 h-4 mr-2" />
                  {fetchError}
                </p>
              </div>
            )}
            
            {/* Multi-select Dropdown */}
            <div className="relative">
              {/* Selected Companies Display */}
              <div 
                className={`min-h-12 p-3 border-2 rounded-xl cursor-pointer transition-all font-medium flex flex-wrap items-center gap-2 ${
                  errors.agent_company_ids
                    ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-500'
                    : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
                } ${isDropdownOpen ? 'ring-2 ring-blue-500 border-blue-500' : ''}`}
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              >
                {formData.agent_company_ids.length === 0 ? (
                  <span className="text-slate-400 dark:text-slate-500">
                    {loadingAgentCompanies ? 'Loading agent companies...' : 'Select agent companies...'}
                  </span>
                ) : (
                  getSelectedCompanyNames().map((companyName, index) => {
                    const companyId = formData.agent_company_ids[index];
                    const isPrimary = companyId === Number(formData.agent_company_id);
                    return (
                    <span
                      key={companyId}
                      className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg text-sm font-medium ${
                        isPrimary
                          ? 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300 ring-1 ring-green-300 dark:ring-green-700'
                          : 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300'
                      }`}
                    >
                      {isPrimary && <Shield className="w-3 h-3" />}
                      {companyName}
                      <button
                        type="button"
                        onClick={(e) => removeAgentCompany(companyId, e)}
                        className="hover:text-red-500 transition-colors"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                    );
                  })
                )}
              </div>

              {/* Dropdown Panel */}
              {isDropdownOpen && (
                <div className="absolute z-50 w-full mt-1 bg-white dark:bg-slate-800 border-2 border-slate-200 dark:border-slate-700 rounded-xl shadow-2xl max-h-60 overflow-hidden">
                  {/* Search Input */}
                  <div className="p-2 border-b border-slate-200 dark:border-slate-700">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
                      <input
                        type="text"
                        placeholder="Search agent companies..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full pl-10 pr-4 py-2.5 border border-slate-200 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        onClick={(e) => e.stopPropagation()}
                      />
                    </div>
                  </div>

                  {/* Options List */}
                  <div className="overflow-y-auto max-h-44">
                    {loadingAgentCompanies ? (
                      <div className="p-4 text-center text-slate-500 dark:text-slate-400">
                        <svg className="animate-spin h-5 w-5 mx-auto text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        <p className="mt-2 text-sm">Loading agent companies...</p>
                      </div>
                    ) : filteredAgentCompanies.length === 0 ? (
                      <div className="p-4 text-center text-slate-500 dark:text-slate-400">
                        No agent companies found
                      </div>
                    ) : (
                      filteredAgentCompanies.map((company) => {
                        const linkedCompany = isEditMode && user?.agent_companies?.find(c => c.id === company.id);
                        return (
                        <div
                          key={company.id}
                          className={`flex items-center px-4 py-3 cursor-pointer transition-colors ${
                            formData.agent_company_ids.includes(company.id)
                              ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                              : 'hover:bg-slate-50 dark:hover:bg-slate-700'
                          }`}
                          onClick={() => toggleAgentCompany(company.id)}
                        >
                          <div className={`w-5 h-5 border-2 rounded flex items-center justify-center mr-3 ${
                            formData.agent_company_ids.includes(company.id)
                              ? 'bg-blue-600 border-blue-600'
                              : 'border-slate-300 dark:border-slate-600'
                          }`}>
                            {formData.agent_company_ids.includes(company.id) && (
                              <Check className="w-3 h-3 text-white" />
                            )}
                          </div>
                          <div className="flex-1">
                            <div className="font-medium text-slate-900 dark:text-white flex items-center gap-2">
                              {company.company_name}
                              {linkedCompany?.is_primary && (
                                <span className="text-[10px] px-1.5 py-0.5 bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300 rounded font-semibold">PRIMARY</span>
                              )}
                            </div>
                            <div className="flex items-center gap-2 mt-0.5">
                              {company.short_code && (
                                <span className="text-xs text-slate-500 dark:text-slate-400">
                                  Code: {company.short_code}
                                </span>
                              )}
                              {company.registration_number && (
                                <span className="text-xs text-slate-500 dark:text-slate-400">
                                  Reg: {company.registration_number}
                                </span>
                              )}
                            </div>
                            {linkedCompany && (
                              <div className={`flex items-center gap-1 mt-0.5 text-[10px] ${linkedCompany.is_scraped ? 'text-green-600 dark:text-green-400' : 'text-amber-500 dark:text-amber-400'}`}>
                                <Database className="w-3 h-3" />
                                {linkedCompany.is_scraped ? 'Scraped' : 'Not scraped'}
                                {linkedCompany.identity_status && (
                                  <span className="ml-1">| {linkedCompany.identity_status}</span>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                        );
                      })
                    )}
                  </div>
                </div>
              )}
            </div>

            {!loadingAgentCompanies && agentCompanies.length === 0 && !fetchError && (
              <p className="text-sm text-amber-600 dark:text-amber-400 mt-2 ml-1">
                No agent companies available. Please create an agent company first.
              </p>
            )}
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-2 ml-1">
              Optionally link this user to additional agent companies
            </p>
          </div>

          {/* Form Fields */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* First Name */}
            <div>
              <label className="flex items-center space-x-2 text-sm font-bold text-slate-700 dark:text-slate-300 mb-3">
                <UserIcon className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                <span>First Name</span>
                <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                name="firstname"
                value={formData.firstname}
                onChange={handleInputChange}
                required
                className={`w-full px-4 py-3.5 border-2 rounded-xl font-medium transition-all bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-200 dark:focus:ring-blue-900 hover:border-slate-300 ${
                  errors.firstname
                    ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-500'
                    : 'border-slate-200 dark:border-slate-700'
                }`}
                placeholder="Enter first name"
                disabled={isLoading}
              />
              {errors.firstname && (
                <p className="text-red-500 text-xs mt-2 ml-1 flex items-center font-medium">
                  <span className="mr-1">⚠</span>
                  {errors.firstname}
                </p>
              )}
            </div>

            {/* Last Name */}
            <div>
              <label className="flex items-center space-x-2 text-sm font-bold text-slate-700 dark:text-slate-300 mb-3">
                <UserIcon className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                <span>Last Name</span>
                <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                name="lastname"
                value={formData.lastname}
                onChange={handleInputChange}
                required
                className={`w-full px-4 py-3.5 border-2 rounded-xl font-medium transition-all bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-200 dark:focus:ring-blue-900 hover:border-slate-300 ${
                  errors.lastname
                    ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-500'
                    : 'border-slate-200 dark:border-slate-700'
                }`}
                placeholder="Enter last name"
                disabled={isLoading}
              />
              {errors.lastname && (
                <p className="text-red-500 text-xs mt-2 ml-1 flex items-center font-medium">
                  <span className="mr-1">⚠</span>
                  {errors.lastname}
                </p>
              )}
            </div>

            {/* ID Number */}
            <div>
              <label className="flex items-center space-x-2 text-sm font-bold text-slate-700 dark:text-slate-300 mb-3">
                <IdCard className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                <span>ID Number</span>
                <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                name="idnumber"
                value={formData.idnumber}
                onChange={handleInputChange}
                required
                className={`w-full px-4 py-3.5 border-2 rounded-xl font-medium transition-all bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-200 dark:focus:ring-blue-900 hover:border-slate-300 ${
                  errors.idnumber
                    ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-500'
                    : 'border-slate-200 dark:border-slate-700'
                }`}
                placeholder="Enter ID number"
                disabled={isLoading}
              />
              {errors.idnumber && (
                <p className="text-red-500 text-xs mt-2 ml-1 flex items-center font-medium">
                  <span className="mr-1">⚠</span>
                  {errors.idnumber}
                </p>
              )}
            </div>

            {/* Phone Number */}
            <div>
              <label className="flex items-center space-x-2 text-sm font-bold text-slate-700 dark:text-slate-300 mb-3">
                <Phone className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                <span>Phone Number</span>
              </label>
              <input
                type="text"
                name="phone_number"
                value={formData.phone_number}
                onChange={handleInputChange}
                className={`w-full px-4 py-3.5 border-2 rounded-xl font-medium transition-all bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-200 dark:focus:ring-blue-900 hover:border-slate-300 ${
                  errors.phone_number
                    ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-500'
                    : 'border-slate-200 dark:border-slate-700'
                }`}
                placeholder="e.g., +254712345678"
                disabled={isLoading}
              />
              {errors.phone_number && (
                <p className="text-red-500 text-xs mt-2 ml-1 flex items-center font-medium">
                  <span className="mr-1">⚠</span>
                  {errors.phone_number}
                </p>
              )}
            </div>

            {/* Date of Birth */}
            <div className="md:col-span-2">
              <label className="flex items-center space-x-2 text-sm font-bold text-slate-700 dark:text-slate-300 mb-3">
                <Calendar className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                <span>Date of Birth</span>
              </label>
              <input
                type="date"
                name="date_of_birth"
                value={formData.date_of_birth}
                onChange={handleInputChange}
                className={`w-full px-4 py-3.5 border-2 rounded-xl font-medium transition-all bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-200 dark:focus:ring-blue-900 hover:border-slate-300 ${
                  errors.date_of_birth
                    ? 'border-red-300 bg-red-50 dark:bg-red-900/20 dark:border-red-500'
                    : 'border-slate-200 dark:border-slate-700'
                }`}
                disabled={isLoading}
              />
              {errors.date_of_birth && (
                <p className="text-red-500 text-xs mt-2 ml-1 flex items-center font-medium">
                  <span className="mr-1">⚠</span>
                  {errors.date_of_birth}
                </p>
              )}
            </div>
          </div>

          {/* Authentication Section */}
          <div className="bg-gradient-to-br from-purple-50/50 to-blue-50/50 dark:from-purple-900/20 dark:to-blue-900/20 rounded-xl p-6 border-2 border-purple-100 dark:border-purple-800/30">
            <div className="flex items-center space-x-2 mb-4">
              <Shield className="w-5 h-5 text-purple-600 dark:text-purple-400" />
              <h3 className="text-lg font-bold text-slate-800 dark:text-slate-200">Authentication Details</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Authentication Status */}
              <div>
                <label className="flex items-center space-x-2 text-sm font-bold text-slate-700 dark:text-slate-300 mb-3">
                  <Shield className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                  <span>Authentication Status</span>
                </label>
                <select
                  name="is_authentic"
                  value={formData.is_authentic}
                  onChange={handleInputChange}
                  className="w-full px-4 py-3.5 border-2 rounded-xl font-medium transition-all bg-white dark:bg-slate-800 text-slate-900 dark:text-white border-slate-200 dark:border-slate-700 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 dark:focus:ring-purple-900 hover:border-slate-300 focus:outline-none"
                  disabled={isLoading}
                >
                  <option value="true">✓ Verified</option>
                  <option value="false">✗ Unverified</option>
                </select>
              </div>

              {/* Authenticity Description */}
              <div>
                <label className="flex items-center space-x-2 text-sm font-bold text-slate-700 dark:text-slate-300 mb-3">
                  <FileText className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                  <span>Authenticity Notes</span>
                </label>
                <input
                  type="text"
                  name="authenticity_desc"
                  value={formData.authenticity_desc}
                  onChange={handleInputChange}
                  className="w-full px-4 py-3.5 border-2 rounded-xl font-medium transition-all bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 border-slate-200 dark:border-slate-700 focus:border-purple-500 focus:ring-2 focus:ring-purple-200 dark:focus:ring-purple-900 hover:border-slate-300 focus:outline-none"
                  placeholder="Optional verification notes"
                  disabled={isLoading}
                />
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex space-x-4 pt-6 border-t-2 border-slate-200 dark:border-slate-700">
            <button
              type="button"
              onClick={onClose}
              disabled={isLoading}
              className="flex-1 py-3.5 px-5 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 font-bold rounded-xl hover:bg-slate-300 dark:hover:bg-slate-600 transition-all shadow-sm hover:shadow-md transform hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span className="flex items-center justify-center space-x-2">
                <X className="w-5 h-5" />
                <span>Cancel</span>
              </span>
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={isLoading}
              className="flex-1 py-3.5 px-5 bg-gradient-to-r from-blue-600 via-cyan-600 to-blue-700 hover:from-blue-700 hover:via-cyan-700 hover:to-blue-800 text-white font-bold rounded-xl transition-all shadow-lg shadow-blue-500/40 hover:shadow-xl hover:shadow-blue-500/50 disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-[1.02]"
            >
              {isLoading ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-2 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  {isEditMode ? 'Updating...' : 'Creating...'}
                </span>
              ) : (
                <span>{isEditMode ? 'Update User' : 'Create User'}</span>
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

export default UserDetailsModal;