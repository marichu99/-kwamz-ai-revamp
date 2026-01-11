import { useState, useEffect } from 'react';
import { X, Info, Mail, Shield, Bell, Settings, Save, Eye, EyeOff } from 'lucide-react';

function ConfigDetailsModal({ isOpen, onClose, onSubmit, isLoading, config }) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    
    // SMTP Configuration
    smtp_server: 'smtp.gmail.com',
    smtp_port: 587,
    sender_email: '',
    sender_password: '',
    recipient_emails: 'fraud-team@company.com',
    
    // Detection Parameters
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
    is_active: false
  });
  
  const [errors, setErrors] = useState({});
  const [showPassword, setShowPassword] = useState(false);
  const [activeSection, setActiveSection] = useState('general');

  useEffect(() => {
    if (config) {
      setFormData({
        name: config.name || '',
        description: config.description || '',
        smtp_server: config.smtp_server || 'smtp.gmail.com',
        smtp_port: config.smtp_port || 587,
        sender_email: config.sender_email || '',
        sender_password: config.sender_password || '',
        recipient_emails: config.recipient_emails || 'fraud-team@company.com',
        time_window_minutes: config.time_window_minutes || 5,
        amount_variance: config.amount_variance || 0.1,
        min_transactions_rollover: config.min_transactions_rollover || 3,
        split_threshold: config.split_threshold || 2,
        rapid_back_forth_threshold: config.rapid_back_forth_threshold || 2,
        high_risk_score: config.high_risk_score || 50,
        medium_risk_score: config.medium_risk_score || 30,
        email_enabled: config.email_enabled || false,
        notify_high_risk: config.notify_high_risk !== undefined ? config.notify_high_risk : true,
        notify_medium_risk: config.notify_medium_risk || false,
        notify_split_transactions: config.notify_split_transactions !== undefined ? config.notify_split_transactions : true,
        notify_rollover_fraud: config.notify_rollover_fraud !== undefined ? config.notify_rollover_fraud : true,
        notify_rapid_patterns: config.notify_rapid_patterns !== undefined ? config.notify_rapid_patterns : true,
        email_subject_prefix: config.email_subject_prefix || '[Fraud Alert] ',
        is_active: config.is_active || false
      });
    } else {
      // Check for duplicate data from session storage
      const duplicateData = sessionStorage.getItem('duplicateConfig');
      if (duplicateData) {
        setFormData(JSON.parse(duplicateData));
      } else {
        resetForm();
      }
    }
  }, [config]);

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      smtp_server: 'smtp.gmail.com',
      smtp_port: 587,
      sender_email: '',
      sender_password: '',
      recipient_emails: 'fraud-team@company.com',
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
      is_active: false
    });
    setErrors({});
    setActiveSection('general');
  };

  const validateForm = () => {
    const newErrors = {};
    
    // General validation
    if (!formData.name.trim()) {
      newErrors.name = 'Configuration name is required';
    }
    
    // SMTP validation when email is enabled
    if (formData.email_enabled) {
      if (!formData.smtp_server.trim()) {
        newErrors.smtp_server = 'SMTP server is required';
      }
      if (!formData.sender_email.trim()) {
        newErrors.sender_email = 'Sender email is required';
      }
      if (!formData.recipient_emails.trim()) {
        newErrors.recipient_emails = 'At least one recipient email is required';
      }
    }
    
    // Detection parameters validation
    if (formData.time_window_minutes < 1 || formData.time_window_minutes > 60) {
      newErrors.time_window_minutes = 'Time window must be between 1 and 60 minutes';
    }
    if (formData.amount_variance < 0.01 || formData.amount_variance > 1) {
      newErrors.amount_variance = 'Amount variance must be between 0.01 and 1.0';
    }
    if (formData.min_transactions_rollover < 2) {
      newErrors.min_transactions_rollover = 'Minimum transactions must be at least 2';
    }
    
    // Risk thresholds validation
    if (formData.high_risk_score <= formData.medium_risk_score) {
      newErrors.high_risk_score = 'High risk score must be greater than medium risk score';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (validateForm()) {
      onSubmit(formData, config?.id, resetForm);
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
    
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: undefined }));
    }
  };

  const sections = [
    { id: 'general', label: 'General', icon: <Settings className="w-4 h-4" /> },
    { id: 'smtp', label: 'SMTP Configuration', icon: <Mail className="w-4 h-4" /> },
    { id: 'detection', label: 'Detection Parameters', icon: <Shield className="w-4 h-4" /> },
    { id: 'notifications', label: 'Notifications', icon: <Bell className="w-4 h-4" /> },
    { id: 'risk', label: 'Risk Thresholds', icon: <Info className="w-4 h-4" /> }
  ];

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black/60 backdrop-blur-sm z-50 p-4">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-200 dark:border-slate-700">
          <div>
            <h2 className="text-xl font-bold text-slate-800 dark:text-white">
              {config ? 'Edit Configuration' : 'Create New Configuration'}
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

        <div className="flex h-[calc(90vh-8rem)]">
          {/* Sidebar Navigation */}
          <div className="w-64 border-r border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-4">
            <div className="space-y-1">
              {sections.map((section) => (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${activeSection === section.id
                      ? 'bg-blue-500 text-white'
                      : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
                    }`}
                >
                  {section.icon}
                  <span className="font-medium">{section.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Main Form Content */}
          <div className="flex-1 overflow-y-auto p-6">
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

                  {!config && (
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

              {/* SMTP Configuration Section */}
              {activeSection === 'smtp' && (
                <div className="space-y-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-lg font-semibold text-slate-800 dark:text-white">SMTP Settings</h3>
                      <p className="text-sm text-slate-600 dark:text-slate-300">Configure email notifications</p>
                    </div>
                    <div className="flex items-center space-x-3">
                      <input
                        type="checkbox"
                        id="email_enabled"
                        name="email_enabled"
                        checked={formData.email_enabled}
                        onChange={handleChange}
                        className="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600"
                      />
                      <label htmlFor="email_enabled" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                        Enable email notifications
                      </label>
                    </div>
                  </div>

                  {formData.email_enabled && (
                    <>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                            SMTP Server *
                          </label>
                          <input
                            type="text"
                            name="smtp_server"
                            value={formData.smtp_server}
                            onChange={handleChange}
                            className={`w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border ${errors.smtp_server ? 'border-red-500' : 'border-slate-200 dark:border-slate-600'
                              } rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all`}
                            placeholder="smtp.gmail.com"
                          />
                          {errors.smtp_server && (
                            <p className="mt-2 text-sm text-red-600 dark:text-red-400">{errors.smtp_server}</p>
                          )}
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                            SMTP Port *
                          </label>
                          <input
                            type="number"
                            name="smtp_port"
                            value={formData.smtp_port}
                            onChange={handleChange}
                            min="1"
                            max="65535"
                            className="w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                          Sender Email *
                        </label>
                        <input
                          type="email"
                          name="sender_email"
                          value={formData.sender_email}
                          onChange={handleChange}
                          className={`w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border ${errors.sender_email ? 'border-red-500' : 'border-slate-200 dark:border-slate-600'
                            } rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all`}
                          placeholder="noreply@company.com"
                        />
                        {errors.sender_email && (
                          <p className="mt-2 text-sm text-red-600 dark:text-red-400">{errors.sender_email}</p>
                        )}
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                          Sender Password
                        </label>
                        <div className="relative">
                          <input
                            type={showPassword ? "text" : "password"}
                            name="sender_password"
                            value={formData.sender_password}
                            onChange={handleChange}
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
                          Recipient Emails *
                        </label>
                        <textarea
                          name="recipient_emails"
                          value={formData.recipient_emails}
                          onChange={handleChange}
                          rows="2"
                          className={`w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border ${errors.recipient_emails ? 'border-red-500' : 'border-slate-200 dark:border-slate-600'
                            } rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all`}
                          placeholder="fraud-team@company.com, manager@company.com"
                        />
                        {errors.recipient_emails && (
                          <p className="mt-2 text-sm text-red-600 dark:text-red-400">{errors.recipient_emails}</p>
                        )}
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
                          value={formData.email_subject_prefix}
                          onChange={handleChange}
                          className="w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                          placeholder="[Fraud Alert] "
                        />
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* Detection Parameters Section */}
              {activeSection === 'detection' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-semibold text-slate-800 dark:text-white mb-2">Detection Parameters</h3>
                    <p className="text-sm text-slate-600 dark:text-slate-300">Configure fraud detection sensitivity</p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        Time Window (minutes) *
                      </label>
                      <input
                        type="number"
                        name="time_window_minutes"
                        value={formData.time_window_minutes}
                        onChange={handleChange}
                        min="1"
                        max="60"
                        step="1"
                        className={`w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border ${errors.time_window_minutes ? 'border-red-500' : 'border-slate-200 dark:border-slate-600'
                          } rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all`}
                      />
                      {errors.time_window_minutes && (
                        <p className="mt-2 text-sm text-red-600 dark:text-red-400">{errors.time_window_minutes}</p>
                      )}
                      <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                        Time window to consider for fraud patterns (1-60 minutes)
                      </p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        Amount Variance *
                      </label>
                      <div className="relative">
                        <input
                          type="number"
                          name="amount_variance"
                          value={formData.amount_variance}
                          onChange={handleChange}
                          min="0.01"
                          max="1.0"
                          step="0.01"
                          className={`w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border ${errors.amount_variance ? 'border-red-500' : 'border-slate-200 dark:border-slate-600'
                            } rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all`}
                        />
                        <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
                          <span className="text-slate-500 dark:text-slate-400">%</span>
                        </div>
                      </div>
                      {errors.amount_variance && (
                        <p className="mt-2 text-sm text-red-600 dark:text-red-400">{errors.amount_variance}</p>
                      )}
                      <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                        Allowed variance between amounts (1-100%)
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        Min Split Transactions
                      </label>
                      <input
                        type="number"
                        name="split_threshold"
                        value={formData.split_threshold}
                        onChange={handleChange}
                        min="2"
                        max="10"
                        step="1"
                        className="w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        Min Roll-over Transactions
                      </label>
                      <input
                        type="number"
                        name="min_transactions_rollover"
                        value={formData.min_transactions_rollover}
                        onChange={handleChange}
                        min="2"
                        max="20"
                        step="1"
                        className={`w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border ${errors.min_transactions_rollover ? 'border-red-500' : 'border-slate-200 dark:border-slate-600'
                          } rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all`}
                      />
                      {errors.min_transactions_rollover && (
                        <p className="mt-2 text-sm text-red-600 dark:text-red-400">{errors.min_transactions_rollover}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        Rapid Pattern Threshold
                      </label>
                      <input
                        type="number"
                        name="rapid_back_forth_threshold"
                        value={formData.rapid_back_forth_threshold}
                        onChange={handleChange}
                        min="2"
                        max="10"
                        step="1"
                        className="w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                      />
                    </div>
                  </div>
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

                  <div className="grid grid-cols-2 gap-4">
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
                  <span>{isLoading ? 'Saving...' : config ? 'Update Configuration' : 'Create Configuration'}</span>
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