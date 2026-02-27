import { useState, useEffect, useCallback } from 'react';
import { X, Info, Mail, Shield, Bell, Settings, Save, Eye, EyeOff, ChevronRight, ToggleLeft, ToggleRight, SlidersHorizontal, CreditCard, CheckCircle, XCircle, RefreshCw } from 'lucide-react';
import config from '../../Config';
import { useToast } from './ToastProvider';

function ConfigDetailsModal({ isOpen, onClose, onSubmit, isLoading, config: configData }) {
  const userRole = localStorage.getItem('userRole');
  const isAdmin = userRole === 'admin';
  const { showToast } = useToast();

  const [smtpData, setSmtpData] = useState({
    smtp_server: 'smtp.gmail.com',
    smtp_port: 587,
    sender_email: '',
    sender_password: '',
    recipient_emails: '',
    email_subject_prefix: '[Fraud Alert] ',
    email_enabled: false,
    trial_days: 30,
    rate_per_till: 200,
  });
  const [smtpLoaded, setSmtpLoaded] = useState(false);
  const [smtpSaving, setSmtpSaving] = useState(false);

  const [pesapalData, setPesapalData] = useState({ callback_url: '', environment: 'SANDBOX' });
  const [ipnConfigs, setIpnConfigs] = useState([]);
  const [pesapalLoaded, setPesapalLoaded] = useState(false);
  const [pesapalSaving, setPesapalSaving] = useState(false);
  const [newIpnUrl, setNewIpnUrl] = useState('');
  const [newIpnType, setNewIpnType] = useState('GET');
  const [ipnRegistering, setIpnRegistering] = useState(false);
  const [ipnActivating, setIpnActivating] = useState(null);

  const [formData, setFormData] = useState({
    name: '',
    description: '',

    // Detection Parameters (flat — kept for backward compat)
    time_window_minutes: 5,
    amount_variance: 0.1,
    min_transactions_rollover: 3,
    split_threshold: 2,
    rapid_back_forth_threshold: 2,

    // Risk Thresholds
    high_risk_score: 50,
    medium_risk_score: 30,

    // Notification Settings
    email_enabled: false,
    notify_high_risk: true,
    notify_medium_risk: false,
    notify_split_transactions: true,
    notify_rollover_fraud: true,
    notify_rapid_patterns: true,

    // Email Settings
    email_subject_prefix: '[Fraud Alert] ',

    // System Settings
    is_active: false,

    // Per-fraud-type configs
    fraud_type_configs: null,
  });

  const [errors, setErrors] = useState({});
  const [showPassword, setShowPassword] = useState(false);
  const [activeSection, setActiveSection] = useState('general');
  const [fraudTypeInfo, setFraudTypeInfo] = useState(null);
  const [selectedFraudType, setSelectedFraudType] = useState(null);

  // Fetch fraud type metadata from the API
  useEffect(() => {
    if (isOpen) {
      const token = localStorage.getItem('token');
      fetch(`${config.API_URL}/fraud/config/fraud-types`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((res) => res.json())
        .then((data) => {
          if (data.success) {
            setFraudTypeInfo(data.data);
          }
        })
        .catch((err) => console.error('Failed to fetch fraud type info:', err));
    }
  }, [isOpen]);

  // Fetch global SMTP/platform config when admin opens SMTP or Platform Settings section
  useEffect(() => {
    if (isOpen && isAdmin && (activeSection === 'smtp' || activeSection === 'platform') && !smtpLoaded) {
      const token = localStorage.getItem('token');
      fetch(`${config.API_URL}/fraud/config/smtp`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((res) => res.json())
        .then((data) => {
          if (data.success) {
            setSmtpData({
              smtp_server: data.data.smtp_server || 'smtp.gmail.com',
              smtp_port: data.data.smtp_port || 587,
              sender_email: data.data.sender_email || '',
              sender_password: data.data.sender_password || '',
              recipient_emails: data.data.recipient_emails || '',
              email_subject_prefix: data.data.email_subject_prefix || '[Fraud Alert] ',
              email_enabled: data.data.email_enabled || false,
              trial_days: data.data.trial_days ?? 30,
              rate_per_till: data.data.rate_per_till ?? 200,
            });
          }
        })
        .catch((err) => console.error('Failed to fetch config:', err))
        .finally(() => setSmtpLoaded(true));
    }
  }, [isOpen, isAdmin, activeSection, smtpLoaded]);

  // Fetch Pesapal config when admin opens that section
  useEffect(() => {
    if (isOpen && isAdmin && activeSection === 'pesapal' && !pesapalLoaded) {
      const token = localStorage.getItem('token');
      Promise.all([
        fetch(`${config.API_URL}/payment/admin/pesapal-config`, {
          headers: { Authorization: `Bearer ${token}` },
        }).then(r => r.json()),
        fetch(`${config.API_URL}/payment/admin/ipn-configs`, {
          headers: { Authorization: `Bearer ${token}` },
        }).then(r => r.json()),
      ])
        .then(([cfgData, ipnData]) => {
          if (cfgData.success) {
            setPesapalData({
              callback_url: cfgData.data.callback_url || '',
              environment: cfgData.data.environment || 'SANDBOX',
            });
          }
          if (ipnData.success) setIpnConfigs(ipnData.configs || []);
        })
        .catch(err => console.error('Failed to load Pesapal config:', err))
        .finally(() => setPesapalLoaded(true));
    }
  }, [isOpen, isAdmin, activeSection, pesapalLoaded]);

  const handleSmtpChange = (e) => {
    const { name, value, type, checked } = e.target;
    setSmtpData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked :
              type === 'number' ? (value === '' ? '' : parseFloat(value)) :
              value
    }));
  };

  const handleSmtpSave = async () => {
    setSmtpSaving(true);
    const label = activeSection === 'platform' ? 'Platform settings' : 'SMTP settings';
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${config.API_URL}/fraud/config/smtp`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(smtpData),
      });
      const data = await res.json();
      if (data.success) {
        showToast(`${label} saved successfully`, 'success');
      } else {
        showToast(data.message || `Failed to save ${label.toLowerCase()}`, 'error');
      }
    } catch (err) {
      showToast(`Failed to save ${label.toLowerCase()}`, 'error');
    } finally {
      setSmtpSaving(false);
    }
  };

  const handlePesapalConfigSave = async () => {
    setPesapalSaving(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${config.API_URL}/payment/admin/pesapal-config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(pesapalData),
      });
      const data = await res.json();
      if (data.success) {
        showToast('Pesapal configuration saved successfully', 'success');
      } else {
        showToast(data.error || 'Failed to save Pesapal configuration', 'error');
      }
    } catch {
      showToast('Failed to save Pesapal configuration', 'error');
    } finally {
      setPesapalSaving(false);
    }
  };

  const handleRegisterIPN = async () => {
    if (!newIpnUrl.trim()) { showToast('IPN URL is required', 'warning'); return; }
    setIpnRegistering(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${config.API_URL}/payment/admin/ipn-configs/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ ipn_url: newIpnUrl.trim(), ipn_notification_type: newIpnType }),
      });
      const data = await res.json();
      if (data.success) {
        showToast('IPN registered successfully', 'success');
        setNewIpnUrl('');
        setPesapalLoaded(false); // re-fetch configs list
      } else {
        showToast(data.error || 'Failed to register IPN', 'error');
      }
    } catch {
      showToast('Failed to register IPN', 'error');
    } finally {
      setIpnRegistering(false);
    }
  };

  const handleActivateIPN = async (configId) => {
    setIpnActivating(configId);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${config.API_URL}/payment/admin/ipn-configs/${configId}/activate`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (data.success) {
        showToast('IPN config activated', 'success');
        setIpnConfigs(prev => prev.map(c => ({ ...c, is_active: c.id === configId })));
      } else {
        showToast(data.error || 'Failed to activate IPN config', 'error');
      }
    } catch {
      showToast('Failed to activate IPN config', 'error');
    } finally {
      setIpnActivating(null);
    }
  };

  const handleDeactivateIPN = async (configId) => {
    setIpnActivating(configId);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${config.API_URL}/payment/admin/ipn-configs/${configId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (data.success) {
        showToast('IPN config deactivated', 'success');
        setIpnConfigs(prev => prev.map(c => c.id === configId ? { ...c, is_active: false } : c));
      } else {
        showToast(data.error || 'Failed to deactivate IPN config', 'error');
      }
    } catch {
      showToast('Failed to deactivate IPN config', 'error');
    } finally {
      setIpnActivating(null);
    }
  };

  // Build initial fraud_type_configs from info defaults
  const buildDefaultFraudTypeConfigs = useCallback(() => {
    if (!fraudTypeInfo) return null;
    const configs = {};
    for (const [key, info] of Object.entries(fraudTypeInfo)) {
      configs[key] = { ...info.defaults };
    }
    return configs;
  }, [fraudTypeInfo]);

  useEffect(() => {
    if (configData) {
      const ftc = configData.fraud_type_configs || buildDefaultFraudTypeConfigs();
      setFormData({
        name: configData.name || '',
        description: configData.description || '',
        time_window_minutes: configData.time_window_minutes || 5,
        amount_variance: configData.amount_variance || 0.1,
        min_transactions_rollover: configData.min_transactions_rollover || 3,
        split_threshold: configData.split_threshold || 2,
        rapid_back_forth_threshold: configData.rapid_back_forth_threshold || 2,
        high_risk_score: configData.high_risk_score || 50,
        medium_risk_score: configData.medium_risk_score || 30,
        email_enabled: configData.email_enabled || false,
        notify_high_risk: configData.notify_high_risk !== undefined ? configData.notify_high_risk : true,
        notify_medium_risk: configData.notify_medium_risk || false,
        notify_split_transactions: configData.notify_split_transactions !== undefined ? configData.notify_split_transactions : true,
        notify_rollover_fraud: configData.notify_rollover_fraud !== undefined ? configData.notify_rollover_fraud : true,
        notify_rapid_patterns: configData.notify_rapid_patterns !== undefined ? configData.notify_rapid_patterns : true,
        email_subject_prefix: configData.email_subject_prefix || '[Fraud Alert] ',
        is_active: configData.is_active || false,
        fraud_type_configs: ftc,
      });
    } else {
      const duplicateData = sessionStorage.getItem('duplicateConfig');
      if (duplicateData) {
        setFormData(JSON.parse(duplicateData));
      } else {
        resetForm();
      }
    }
  }, [configData, fraudTypeInfo, buildDefaultFraudTypeConfigs]);

  const resetForm = () => {
    setSmtpLoaded(false);
    setPesapalLoaded(false);
    setFormData({
      name: '',
      description: '',
      time_window_minutes: 5,
      amount_variance: 0.1,
      min_transactions_rollover: 3,
      split_threshold: 2,
      rapid_back_forth_threshold: 2,
      high_risk_score: 50,
      medium_risk_score: 30,
      email_enabled: false,
      notify_high_risk: true,
      notify_medium_risk: false,
      notify_split_transactions: true,
      notify_rollover_fraud: true,
      notify_rapid_patterns: true,
      email_subject_prefix: '[Fraud Alert] ',
      is_active: false,
      fraud_type_configs: buildDefaultFraudTypeConfigs(),
    });
    setErrors({});
    setActiveSection('general');
    setSelectedFraudType(null);
  };

  const validateForm = () => {
    const newErrors = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Configuration name is required';
    }

    if (formData.high_risk_score <= formData.medium_risk_score) {
      newErrors.high_risk_score = 'High risk score must be greater than medium risk score';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (validateForm()) {
      onSubmit(formData, configData?.id, resetForm);
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked :
              type === 'number' ? (value === '' ? '' : parseFloat(value)) :
              value
    }));

    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: undefined }));
    }
  };

  const handleFraudTypeToggle = (fraudType) => {
    setFormData(prev => {
      const ftc = { ...(prev.fraud_type_configs || {}) };
      ftc[fraudType] = { ...ftc[fraudType], enabled: !ftc[fraudType]?.enabled };
      return { ...prev, fraud_type_configs: ftc };
    });
  };

  const handleFraudTypeParamChange = (fraudType, param, value) => {
    setFormData(prev => {
      const ftc = { ...(prev.fraud_type_configs || {}) };
      ftc[fraudType] = { ...ftc[fraudType], [param]: value };
      return { ...prev, fraud_type_configs: ftc };
    });
  };

  const sections = [
    { id: 'general', label: 'General', icon: <Settings className="w-4 h-4" /> },
    ...(isAdmin ? [{ id: 'platform', label: 'Platform Settings', icon: <SlidersHorizontal className="w-4 h-4" /> }] : []),
    ...(isAdmin ? [{ id: 'smtp', label: 'SMTP Configuration', icon: <Mail className="w-4 h-4" /> }] : []),
    ...(isAdmin ? [{ id: 'pesapal', label: 'Pesapal', icon: <CreditCard className="w-4 h-4" /> }] : []),
    { id: 'detection', label: 'Fraud Type Config', icon: <Shield className="w-4 h-4" /> },
    { id: 'notifications', label: 'Notifications', icon: <Bell className="w-4 h-4" /> },
    { id: 'risk', label: 'Risk Thresholds', icon: <Info className="w-4 h-4" /> }
  ];

  if (!isOpen) return null;

  const fraudTypes = fraudTypeInfo ? Object.keys(fraudTypeInfo) : [];
  const currentFtc = formData.fraud_type_configs || {};

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black/60 backdrop-blur-sm z-50 p-4">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-[95vw] sm:max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 sm:p-6 border-b border-slate-200 dark:border-slate-700">
          <div>
            <h2 className="text-xl font-bold text-slate-800 dark:text-white">
              {configData ? 'Edit Configuration' : 'Create New Configuration'}
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">
              Configure fraud detection parameters and settings
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-slate-500 dark:text-slate-400" />
          </button>
        </div>

        <div className="flex flex-col md:flex-row h-[calc(90vh-8rem)]">
          {/* Sidebar Navigation */}
          <div className="w-full md:w-64 border-b md:border-b-0 md:border-r border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-3 md:p-4 overflow-x-auto md:overflow-x-visible">
            <div className="flex md:flex-col gap-1 md:space-y-1 overflow-x-auto md:overflow-x-visible">
              {sections.map((section) => (
                <button
                  key={section.id}
                  onClick={() => { setActiveSection(section.id); if (section.id !== 'detection') setSelectedFraudType(null); }}
                  className={`flex items-center space-x-2 md:space-x-3 px-3 md:px-4 py-2 md:py-3 rounded-lg transition-colors whitespace-nowrap md:w-full ${activeSection === section.id
                      ? 'bg-blue-500 text-white'
                      : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
                    }`}
                >
                  {section.icon}
                  <span className="font-medium text-sm md:text-base">{section.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Main Form Content */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6">
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* General Section */}
              {activeSection === 'general' && (
                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                      Configuration Name *
                    </label>
                    <input
                      type="text"
                      name="name"
                      value={formData.name}
                      onChange={handleChange}
                      className={`w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border ${errors.name ? 'border-red-500' : 'border-slate-200 dark:border-slate-600'
                        } rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all`}
                      placeholder="e.g., Production Settings"
                    />
                    {errors.name && (
                      <p className="mt-2 text-sm text-red-600 dark:text-red-400">{errors.name}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                      Description
                    </label>
                    <textarea
                      name="description"
                      value={formData.description}
                      onChange={handleChange}
                      rows="3"
                      className="w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                      placeholder="Describe this configuration..."
                    />
                  </div>

                  {!configData && (
                    <div className="flex items-center space-x-3">
                      <input
                        type="checkbox"
                        id="is_active"
                        name="is_active"
                        checked={formData.is_active}
                        onChange={handleChange}
                        className="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600"
                      />
                      <label htmlFor="is_active" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                        Set as active configuration
                      </label>
                    </div>
                  )}
                </div>
              )}

              {/* Platform Settings Section — Admin Only */}
              {activeSection === 'platform' && isAdmin && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-semibold text-slate-800 dark:text-white">Platform Settings</h3>
                    <p className="text-sm text-slate-600 dark:text-slate-300">System-wide billing and trial configuration (admin only)</p>
                  </div>

                  {!smtpLoaded ? (
                    <div className="flex items-center justify-center py-12">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                      <span className="ml-3 text-slate-500 dark:text-slate-400">Loading settings...</span>
                    </div>
                  ) : (
                    <>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-lg">
                        <div>
                          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                            Trial Period (days)
                          </label>
                          <input
                            type="number"
                            name="trial_days"
                            value={smtpData.trial_days}
                            onChange={handleSmtpChange}
                            min="1"
                            max="365"
                            step="1"
                            className="w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                          />
                          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                            Days before payment is required
                          </p>
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                            Rate per Till (KES)
                          </label>
                          <input
                            type="number"
                            name="rate_per_till"
                            value={smtpData.rate_per_till}
                            onChange={handleSmtpChange}
                            min="1"
                            step="0.01"
                            className="w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                          />
                          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                            Monthly charge per active till
                          </p>
                        </div>
                      </div>

                      <div className="flex justify-end pt-4">
                        <button
                          type="button"
                          onClick={handleSmtpSave}
                          disabled={smtpSaving}
                          className="flex items-center space-x-2 px-6 py-2.5 bg-blue-500 text-white rounded-xl hover:bg-blue-600 transition-colors disabled:bg-blue-300 disabled:cursor-not-allowed"
                        >
                          <Save className="w-4 h-4" />
                          <span>{smtpSaving ? 'Saving...' : 'Save Platform Settings'}</span>
                        </button>
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* SMTP Configuration Section — Admin Only */}
              {activeSection === 'smtp' && isAdmin && (
                <div className="space-y-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-lg font-semibold text-slate-800 dark:text-white">Global SMTP Settings</h3>
                      <p className="text-sm text-slate-600 dark:text-slate-300">System-wide email configuration (admin only)</p>
                    </div>
                    <div className="flex items-center space-x-3">
                      <input
                        type="checkbox"
                        id="smtp_email_enabled"
                        name="email_enabled"
                        checked={smtpData.email_enabled}
                        onChange={handleSmtpChange}
                        className="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600"
                      />
                      <label htmlFor="smtp_email_enabled" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                        Enable SMTP email
                      </label>
                    </div>
                  </div>

                  {!smtpLoaded ? (
                    <div className="flex items-center justify-center py-12">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                      <span className="ml-3 text-slate-500 dark:text-slate-400">Loading SMTP settings...</span>
                    </div>
                  ) : (
                    <>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                            SMTP Server
                          </label>
                          <input
                            type="text"
                            name="smtp_server"
                            value={smtpData.smtp_server}
                            onChange={handleSmtpChange}
                            className="w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                            placeholder="smtp.gmail.com"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                            SMTP Port
                          </label>
                          <input
                            type="number"
                            name="smtp_port"
                            value={smtpData.smtp_port}
                            onChange={handleSmtpChange}
                            min="1"
                            max="65535"
                            className="w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                          Sender Email
                        </label>
                        <input
                          type="email"
                          name="sender_email"
                          value={smtpData.sender_email}
                          onChange={handleSmtpChange}
                          className="w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                          placeholder="noreply@company.com"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                          Sender Password
                        </label>
                        <div className="relative">
                          <input
                            type={showPassword ? "text" : "password"}
                            name="sender_password"
                            value={smtpData.sender_password}
                            onChange={handleSmtpChange}
                            className="w-full px-4 py-2.5 pr-10 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                            placeholder="Enter SMTP password"
                          />
                          <button
                            type="button"
                            onClick={() => setShowPassword(!showPassword)}
                            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-300"
                          >
                            {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                          </button>
                        </div>
                        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                          App password for the sender email account
                        </p>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                          Recipient Emails
                        </label>
                        <textarea
                          name="recipient_emails"
                          value={smtpData.recipient_emails}
                          onChange={handleSmtpChange}
                          rows="2"
                          className="w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                          placeholder="fraud-team@company.com, manager@company.com"
                        />
                        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                          Comma-separated list of email addresses
                        </p>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                          Email Subject Prefix
                        </label>
                        <input
                          type="text"
                          name="email_subject_prefix"
                          value={smtpData.email_subject_prefix}
                          onChange={handleSmtpChange}
                          className="w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                          placeholder="[Fraud Alert] "
                        />
                      </div>

                      <div className="flex justify-end pt-4">
                        <button
                          type="button"
                          onClick={handleSmtpSave}
                          disabled={smtpSaving}
                          className="flex items-center space-x-2 px-6 py-2.5 bg-blue-500 text-white rounded-xl hover:bg-blue-600 transition-colors disabled:bg-blue-300 disabled:cursor-not-allowed"
                        >
                          <Save className="w-4 h-4" />
                          <span>{smtpSaving ? 'Saving...' : 'Save SMTP Settings'}</span>
                        </button>
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* Pesapal Configuration Section — Admin Only */}
              {activeSection === 'pesapal' && isAdmin && (
                <div className="space-y-8">
                  <div>
                    <h3 className="text-lg font-semibold text-slate-800 dark:text-white">Pesapal Configuration</h3>
                    <p className="text-sm text-slate-600 dark:text-slate-300">Payment gateway URLs, environment, and IPN registrations (admin only)</p>
                  </div>

                  {!pesapalLoaded ? (
                    <div className="flex items-center justify-center py-12">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                      <span className="ml-3 text-slate-500 dark:text-slate-400">Loading Pesapal settings...</span>
                    </div>
                  ) : (
                    <>
                      {/* Gateway Settings */}
                      <div className="space-y-4">
                        <h4 className="font-medium text-slate-700 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700 pb-2">Gateway Settings</h4>
                        <div>
                          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                            Callback URL
                          </label>
                          <input
                            type="url"
                            value={pesapalData.callback_url}
                            onChange={e => setPesapalData(prev => ({ ...prev, callback_url: e.target.value }))}
                            className="w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all font-mono text-sm"
                            placeholder="https://kwamz-ai.org/api/payment/callback"
                          />
                          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">URL Pesapal redirects users to after payment</p>
                        </div>
                        <div className="max-w-xs">
                          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                            Environment
                          </label>
                          <select
                            value={pesapalData.environment}
                            onChange={e => setPesapalData(prev => ({ ...prev, environment: e.target.value }))}
                            className="w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                          >
                            <option value="SANDBOX">Sandbox</option>
                            <option value="PRODUCTION">Production</option>
                          </select>
                        </div>
                        <div className="flex justify-end">
                          <button
                            type="button"
                            onClick={handlePesapalConfigSave}
                            disabled={pesapalSaving}
                            className="flex items-center space-x-2 px-6 py-2.5 bg-blue-500 text-white rounded-xl hover:bg-blue-600 transition-colors disabled:bg-blue-300 disabled:cursor-not-allowed"
                          >
                            <Save className="w-4 h-4" />
                            <span>{pesapalSaving ? 'Saving...' : 'Save Gateway Settings'}</span>
                          </button>
                        </div>
                      </div>

                      {/* Registered IPN Configurations */}
                      <div className="space-y-3">
                        <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-700 pb-2">
                          <h4 className="font-medium text-slate-700 dark:text-slate-300">Registered IPN Configurations</h4>
                          <button
                            type="button"
                            onClick={() => setPesapalLoaded(false)}
                            className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                            title="Refresh"
                          >
                            <RefreshCw className="w-4 h-4" />
                          </button>
                        </div>
                        {ipnConfigs.length === 0 ? (
                          <p className="text-sm text-slate-500 dark:text-slate-400 italic py-4 text-center">No IPN configurations registered yet.</p>
                        ) : (
                          <div className="space-y-2">
                            {ipnConfigs.map(ipn => (
                              <div
                                key={ipn.id}
                                className={`flex items-start justify-between gap-3 p-3 rounded-xl border transition-colors ${
                                  ipn.is_active
                                    ? 'border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20'
                                    : 'border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/30'
                                }`}
                              >
                                <div className="min-w-0 flex-1 space-y-1">
                                  <p className="text-sm font-mono text-slate-800 dark:text-white truncate">{ipn.ipn_url}</p>
                                  <div className="flex flex-wrap gap-2 text-xs text-slate-500 dark:text-slate-400">
                                    <span>ID: <span className="font-mono">{ipn.notification_id}</span></span>
                                    <span>•</span>
                                    <span>{ipn.environment}</span>
                                    <span>•</span>
                                    <span>{ipn.ipn_notification_type}</span>
                                  </div>
                                </div>
                                <div className="flex items-center gap-2 flex-shrink-0">
                                  {ipn.is_active ? (
                                    <span className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400 font-medium">
                                      <CheckCircle className="w-3.5 h-3.5" /> Active
                                    </span>
                                  ) : (
                                    <button
                                      type="button"
                                      onClick={() => handleActivateIPN(ipn.id)}
                                      disabled={ipnActivating === ipn.id}
                                      className="text-xs px-3 py-1 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50"
                                    >
                                      {ipnActivating === ipn.id ? '...' : 'Activate'}
                                    </button>
                                  )}
                                  {ipn.is_active && (
                                    <button
                                      type="button"
                                      onClick={() => handleDeactivateIPN(ipn.id)}
                                      disabled={ipnActivating === ipn.id}
                                      className="text-xs px-3 py-1 border border-red-300 dark:border-red-700 text-red-600 dark:text-red-400 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-50"
                                    >
                                      {ipnActivating === ipn.id ? '...' : 'Deactivate'}
                                    </button>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Register New IPN */}
                      <div className="space-y-4">
                        <h4 className="font-medium text-slate-700 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700 pb-2">Register New IPN URL</h4>
                        <div>
                          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                            IPN URL
                          </label>
                          <input
                            type="url"
                            value={newIpnUrl}
                            onChange={e => setNewIpnUrl(e.target.value)}
                            className="w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all font-mono text-sm"
                            placeholder="https://kwamz-ai.org/api/payment/ipn"
                          />
                        </div>
                        <div className="max-w-xs">
                          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                            Notification Type
                          </label>
                          <select
                            value={newIpnType}
                            onChange={e => setNewIpnType(e.target.value)}
                            className="w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                          >
                            <option value="GET">GET</option>
                            <option value="POST">POST</option>
                          </select>
                        </div>
                        <div className="flex justify-end">
                          <button
                            type="button"
                            onClick={handleRegisterIPN}
                            disabled={ipnRegistering || !newIpnUrl.trim()}
                            className="flex items-center space-x-2 px-6 py-2.5 bg-green-500 text-white rounded-xl hover:bg-green-600 transition-colors disabled:bg-green-300 disabled:cursor-not-allowed"
                          >
                            <CreditCard className="w-4 h-4" />
                            <span>{ipnRegistering ? 'Registering...' : 'Register with Pesapal'}</span>
                          </button>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* Fraud Type Configuration Section */}
              {activeSection === 'detection' && (
                <div className="space-y-4">
                  <div>
                    <h3 className="text-lg font-semibold text-slate-800 dark:text-white mb-1">Fraud Type Configuration</h3>
                    <p className="text-sm text-slate-600 dark:text-slate-300">Enable/disable and configure each fraud detection type individually</p>
                  </div>

                  {!fraudTypeInfo ? (
                    <div className="flex items-center justify-center py-12">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                      <span className="ml-3 text-slate-500 dark:text-slate-400">Loading fraud types...</span>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {fraudTypes.map((ftKey) => {
                        const info = fraudTypeInfo[ftKey];
                        const ftConfig = currentFtc[ftKey] || info.defaults;
                        const isEnabled = ftConfig?.enabled !== false;
                        const isSelected = selectedFraudType === ftKey;

                        return (
                          <div
                            key={ftKey}
                            className={`border rounded-xl overflow-hidden transition-all ${
                              isSelected
                                ? 'border-blue-400 dark:border-blue-500 ring-1 ring-blue-200 dark:ring-blue-800'
                                : 'border-slate-200 dark:border-slate-700'
                            } ${!isEnabled ? 'opacity-60' : ''}`}
                          >
                            {/* Fraud type header / card */}
                            <div
                              className="flex items-center justify-between p-4 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
                              onClick={() => setSelectedFraudType(isSelected ? null : ftKey)}
                            >
                              <div className="flex items-center space-x-3 flex-1 min-w-0">
                                <ChevronRight className={`w-4 h-4 text-slate-400 transition-transform flex-shrink-0 ${isSelected ? 'rotate-90' : ''}`} />
                                <div className="min-w-0">
                                  <h4 className="font-semibold text-slate-800 dark:text-white text-sm">
                                    {info.display_name}
                                  </h4>
                                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-1">
                                    {info.description}
                                  </p>
                                </div>
                              </div>
                              <button
                                type="button"
                                onClick={(e) => { e.stopPropagation(); handleFraudTypeToggle(ftKey); }}
                                className="flex-shrink-0 ml-3"
                                title={isEnabled ? 'Disable this fraud type' : 'Enable this fraud type'}
                              >
                                {isEnabled ? (
                                  <ToggleRight className="w-8 h-8 text-blue-500" />
                                ) : (
                                  <ToggleLeft className="w-8 h-8 text-slate-400" />
                                )}
                              </button>
                            </div>

                            {/* Expanded detail panel */}
                            {isSelected && (
                              <div className="border-t border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/30 p-4 space-y-4">
                                {/* Description */}
                                <div className="flex items-start space-x-2 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                                  <Info className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
                                  <p className="text-xs text-blue-700 dark:text-blue-300 leading-relaxed">
                                    {info.description}
                                  </p>
                                </div>

                                {/* Parameters */}
                                {isEnabled && info.parameters && (
                                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                    {Object.entries(info.parameters).map(([paramKey, paramMeta]) => {
                                      const paramValue = ftConfig[paramKey] ?? info.defaults[paramKey] ?? '';
                                      return (
                                        <div key={paramKey}>
                                          <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">
                                            {paramMeta.label}
                                          </label>
                                          <input
                                            type="number"
                                            value={paramValue}
                                            onChange={(e) => {
                                              const val = e.target.value === '' ? '' : parseFloat(e.target.value);
                                              handleFraudTypeParamChange(ftKey, paramKey, val);
                                            }}
                                            min={paramMeta.min}
                                            max={paramMeta.max}
                                            step={paramMeta.type === 'float' ? '0.01' : '1'}
                                            className="w-full px-3 py-2 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg text-sm text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                                          />
                                        </div>
                                      );
                                    })}
                                  </div>
                                )}

                                {!isEnabled && (
                                  <p className="text-sm text-slate-500 dark:text-slate-400 italic">
                                    This fraud type is disabled. Enable it to configure parameters.
                                  </p>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* Notifications Section */}
              {activeSection === 'notifications' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-semibold text-slate-800 dark:text-white mb-2">Notification Settings</h3>
                    <p className="text-sm text-slate-600 dark:text-slate-300">Configure which fraud types trigger notifications</p>
                  </div>

                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-700/50 rounded-xl">
                      <div>
                        <h4 className="font-medium text-slate-800 dark:text-white">High Risk Transactions</h4>
                        <p className="text-sm text-slate-600 dark:text-slate-300">Notify for high-risk fraud cases</p>
                      </div>
                      <input
                        type="checkbox"
                        name="notify_high_risk"
                        checked={formData.notify_high_risk}
                        onChange={handleChange}
                        className="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600"
                      />
                    </div>

                    <div className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-700/50 rounded-xl">
                      <div>
                        <h4 className="font-medium text-slate-800 dark:text-white">Medium Risk Transactions</h4>
                        <p className="text-sm text-slate-600 dark:text-slate-300">Notify for medium-risk fraud cases</p>
                      </div>
                      <input
                        type="checkbox"
                        name="notify_medium_risk"
                        checked={formData.notify_medium_risk}
                        onChange={handleChange}
                        className="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600"
                      />
                    </div>

                    <div className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-700/50 rounded-xl">
                      <div>
                        <h4 className="font-medium text-slate-800 dark:text-white">Split Transactions</h4>
                        <p className="text-sm text-slate-600 dark:text-slate-300">Notify for split transaction fraud</p>
                      </div>
                      <input
                        type="checkbox"
                        name="notify_split_transactions"
                        checked={formData.notify_split_transactions}
                        onChange={handleChange}
                        className="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600"
                      />
                    </div>

                    <div className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-700/50 rounded-xl">
                      <div>
                        <h4 className="font-medium text-slate-800 dark:text-white">Roll-over Fraud</h4>
                        <p className="text-sm text-slate-600 dark:text-slate-300">Notify for roll-over fraud patterns</p>
                      </div>
                      <input
                        type="checkbox"
                        name="notify_rollover_fraud"
                        checked={formData.notify_rollover_fraud}
                        onChange={handleChange}
                        className="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600"
                      />
                    </div>

                    <div className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-700/50 rounded-xl">
                      <div>
                        <h4 className="font-medium text-slate-800 dark:text-white">Rapid Patterns</h4>
                        <p className="text-sm text-slate-600 dark:text-slate-300">Notify for rapid back-forth patterns</p>
                      </div>
                      <input
                        type="checkbox"
                        name="notify_rapid_patterns"
                        checked={formData.notify_rapid_patterns}
                        onChange={handleChange}
                        className="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Risk Thresholds Section */}
              {activeSection === 'risk' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-semibold text-slate-800 dark:text-white mb-2">Risk Thresholds</h3>
                    <p className="text-sm text-slate-600 dark:text-slate-300">Configure risk scoring thresholds</p>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        High Risk Score *
                      </label>
                      <input
                        type="number"
                        name="high_risk_score"
                        value={formData.high_risk_score}
                        onChange={handleChange}
                        min="0"
                        max="100"
                        step="1"
                        className={`w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border ${errors.high_risk_score ? 'border-red-500' : 'border-slate-200 dark:border-slate-600'
                          } rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all`}
                      />
                      {errors.high_risk_score && (
                        <p className="mt-2 text-sm text-red-600 dark:text-red-400">{errors.high_risk_score}</p>
                      )}
                      <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                        Minimum score for high-risk classification (0-100)
                      </p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        Medium Risk Score *
                      </label>
                      <input
                        type="number"
                        name="medium_risk_score"
                        value={formData.medium_risk_score}
                        onChange={handleChange}
                        min="0"
                        max="100"
                        step="1"
                        className="w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                      />
                      <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                        Minimum score for medium-risk classification (0-100)
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Footer */}
              <div className="flex justify-end space-x-3 pt-6 border-t border-slate-200 dark:border-slate-700">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-6 py-2.5 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                  disabled={isLoading}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="flex items-center space-x-2 px-6 py-2.5 bg-blue-500 text-white rounded-xl hover:bg-blue-600 transition-colors disabled:bg-blue-300 disabled:cursor-not-allowed"
                >
                  <Save className="w-4 h-4" />
                  <span>{isLoading ? 'Saving...' : configData ? 'Update Configuration' : 'Create Configuration'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ConfigDetailsModal;
