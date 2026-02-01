import { useState, useEffect } from 'react';
import { X, Clock, Mail, FileText, Calendar, Save, AlertCircle, Shield, Bell, Info } from 'lucide-react';

function UserReportConfigModal({ isOpen, onClose, onSubmit, isLoading, config }) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    report_type: 'periodic_fraud',
    frequency_value: 1,
    frequency_unit: 'days',
    recipient_emails: '',
    is_active: true,

    // Fraud Detection Parameters
    time_window_minutes: 5,
    amount_variance: 0.1,
    min_transactions_rollover: 3,
    split_threshold: 5,
    split_min_amount: 100.0,
    split_max_amount: 50000.0,
    split_total_amount_threshold: 10000.0,
    rapid_back_forth_threshold: 2,

    // Risk Thresholds
    high_risk_score: 50,
    medium_risk_score: 30,

    // Analysis Settings
    analysis_period_days: 30,
    max_transactions_per_check: 100,

    // Notification Settings
    notify_high_risk: true,
    notify_medium_risk: false,
    notify_split_transactions: true,
    notify_rollover_fraud: true,
    notify_rapid_patterns: true
  });

  const [errors, setErrors] = useState({});
  const [activeSection, setActiveSection] = useState('general');

  // Report type options
  const reportTypes = [
    {
      value: 'periodic_fraud',
      label: 'Periodic Fraud Report',
      description: 'Regular fraud detection reports at specified intervals',
      icon: '🔄'
    },
    {
      value: 'historical_fraud',
      label: 'Historical Fraud Report',
      description: 'Analysis of historical fraud patterns over time',
      icon: '📊'
    },
    {
      value: 'daily_fraud',
      label: 'Daily Fraud Report',
      description: 'Daily summary of fraud detection results',
      icon: '📅'
    },
    {
      value: 'commissions',
      label: 'Commissions Report',
      description: 'Agent commission calculations and summaries',
      icon: '💰'
    }
  ];

  // Frequency unit options with constraints
  const frequencyUnits = [
    { value: 'minutes', label: 'Minutes', min: 5, max: 59 },
    { value: 'hours', label: 'Hours', min: 1, max: 23 },
    { value: 'days', label: 'Days', min: 1, max: 30 }
  ];

  useEffect(() => {
    if (config) {
      setFormData({
        name: config.name || '',
        description: config.description || '',
        report_type: config.report_type || 'periodic_fraud',
        frequency_value: config.frequency_value || 1,
        frequency_unit: config.frequency_unit || 'days',
        recipient_emails: config.recipient_emails || '',
        is_active: config.is_active !== undefined ? config.is_active : true,

        // Fraud Detection Parameters
        time_window_minutes: config.time_window_minutes || 5,
        amount_variance: config.amount_variance || 0.1,
        min_transactions_rollover: config.min_transactions_rollover || 3,
        split_threshold: config.split_threshold || 5,
        split_min_amount: config.split_min_amount || 100.0,
        split_max_amount: config.split_max_amount || 50000.0,
        split_total_amount_threshold: config.split_total_amount_threshold || 10000.0,
        rapid_back_forth_threshold: config.rapid_back_forth_threshold || 2,

        // Risk Thresholds
        high_risk_score: config.high_risk_score || 50,
        medium_risk_score: config.medium_risk_score || 30,

        // Analysis Settings
        analysis_period_days: config.analysis_period_days || 30,
        max_transactions_per_check: config.max_transactions_per_check || 100,

        // Notification Settings
        notify_high_risk: config.notify_high_risk !== undefined ? config.notify_high_risk : true,
        notify_medium_risk: config.notify_medium_risk !== undefined ? config.notify_medium_risk : false,
        notify_split_transactions: config.notify_split_transactions !== undefined ? config.notify_split_transactions : true,
        notify_rollover_fraud: config.notify_rollover_fraud !== undefined ? config.notify_rollover_fraud : true,
        notify_rapid_patterns: config.notify_rapid_patterns !== undefined ? config.notify_rapid_patterns : true
      });
    } else {
      resetForm();
    }
  }, [config]);

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      report_type: 'periodic_fraud',
      frequency_value: 1,
      frequency_unit: 'days',
      recipient_emails: '',
      is_active: true,

      // Fraud Detection Parameters
      time_window_minutes: 5,
      amount_variance: 0.1,
      min_transactions_rollover: 3,
      split_threshold: 5,
      split_min_amount: 100.0,
      split_max_amount: 50000.0,
      split_total_amount_threshold: 10000.0,
      rapid_back_forth_threshold: 2,

      // Risk Thresholds
      high_risk_score: 50,
      medium_risk_score: 30,

      // Analysis Settings
      analysis_period_days: 30,
      max_transactions_per_check: 100,

      // Notification Settings
      notify_high_risk: true,
      notify_medium_risk: false,
      notify_split_transactions: true,
      notify_rollover_fraud: true,
      notify_rapid_patterns: true
    });
    setErrors({});
    setActiveSection('general');
  };

  const validateForm = () => {
    const newErrors = {};

    // Name validation
    if (!formData.name.trim()) {
      newErrors.name = 'Schedule name is required';
    }

    // Report type validation
    if (!formData.report_type) {
      newErrors.report_type = 'Report type is required';
    }

    // Frequency validation
    const currentUnit = frequencyUnits.find(u => u.value === formData.frequency_unit);
    if (currentUnit) {
      if (formData.frequency_value < currentUnit.min) {
        newErrors.frequency_value = `Minimum value for ${currentUnit.label.toLowerCase()} is ${currentUnit.min}`;
      }
      if (formData.frequency_value > currentUnit.max) {
        newErrors.frequency_value = `Maximum value for ${currentUnit.label.toLowerCase()} is ${currentUnit.max}`;
      }
    }

    // Email validation
    if (!formData.recipient_emails.trim()) {
      newErrors.recipient_emails = 'At least one recipient email is required';
    } else {
      const emails = formData.recipient_emails.split(',').map(e => e.trim());
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      const invalidEmails = emails.filter(email => email && !emailRegex.test(email));
      if (invalidEmails.length > 0) {
        newErrors.recipient_emails = `Invalid email(s): ${invalidEmails.join(', ')}`;
      }
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
              type === 'number' ? (value === '' ? '' : parseInt(value, 10)) :
              value
    }));

    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: undefined }));
    }

    // Adjust frequency value when unit changes
    if (name === 'frequency_unit') {
      const unit = frequencyUnits.find(u => u.value === value);
      if (unit && formData.frequency_value < unit.min) {
        setFormData(prev => ({ ...prev, frequency_value: unit.min }));
      }
    }
  };

  const sections = [
    { id: 'general', label: 'General', icon: <FileText className="w-4 h-4" /> },
    { id: 'schedule', label: 'Schedule', icon: <Clock className="w-4 h-4" /> },
    { id: 'detection', label: 'Detection', icon: <Shield className="w-4 h-4" /> },
    { id: 'notifications', label: 'Notifications', icon: <Bell className="w-4 h-4" /> },
    { id: 'risk', label: 'Risk Thresholds', icon: <Info className="w-4 h-4" /> },
    { id: 'recipients', label: 'Recipients', icon: <Mail className="w-4 h-4" /> }
  ];

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black/60 backdrop-blur-sm z-50 p-4">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-200 dark:border-slate-700">
          <div>
            <h2 className="text-xl font-bold text-slate-800 dark:text-white">
              {config ? 'Edit Report Schedule' : 'Create New Report Schedule'}
            </h2>
            <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">
              Configure automated report generation and delivery
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
          <div className="w-56 border-r border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-4">
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
                      Schedule Name *
                    </label>
                    <input
                      type="text"
                      name="name"
                      value={formData.name}
                      onChange={handleChange}
                      className={`w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border ${errors.name ? 'border-red-500' : 'border-slate-200 dark:border-slate-600'
                        } rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all`}
                      placeholder="e.g., Daily Fraud Summary"
                    />
                    {errors.name && (
                      <p className="mt-2 text-sm text-red-600 dark:text-red-400 flex items-center">
                        <AlertCircle className="w-4 h-4 mr-1" />
                        {errors.name}
                      </p>
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
                      placeholder="Describe this schedule configuration..."
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">
                      Report Type *
                    </label>
                    <div className="grid grid-cols-2 gap-4">
                      {reportTypes.map((type) => (
                        <label
                          key={type.value}
                          className={`relative flex items-start p-4 border-2 rounded-xl cursor-pointer transition-all ${formData.report_type === type.value
                              ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                              : 'border-slate-200 dark:border-slate-600 hover:border-slate-300 dark:hover:border-slate-500'
                            }`}
                        >
                          <input
                            type="radio"
                            name="report_type"
                            value={type.value}
                            checked={formData.report_type === type.value}
                            onChange={handleChange}
                            className="sr-only"
                          />
                          <div className="flex items-start">
                            <span className="text-2xl mr-3">{type.icon}</span>
                            <div>
                              <div className="font-medium text-slate-800 dark:text-white">
                                {type.label}
                              </div>
                              <div className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                                {type.description}
                              </div>
                            </div>
                          </div>
                          {formData.report_type === type.value && (
                            <div className="absolute top-2 right-2 w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center">
                              <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                              </svg>
                            </div>
                          )}
                        </label>
                      ))}
                    </div>
                    {errors.report_type && (
                      <p className="mt-2 text-sm text-red-600 dark:text-red-400 flex items-center">
                        <AlertCircle className="w-4 h-4 mr-1" />
                        {errors.report_type}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center space-x-3 pt-4">
                    <input
                      type="checkbox"
                      id="is_active"
                      name="is_active"
                      checked={formData.is_active}
                      onChange={handleChange}
                      className="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600"
                    />
                    <label htmlFor="is_active" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                      Enable this schedule immediately
                    </label>
                  </div>
                </div>
              )}

              {/* Schedule Section */}
              {activeSection === 'schedule' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-semibold text-slate-800 dark:text-white mb-2">
                      Frequency Settings
                    </h3>
                    <p className="text-sm text-slate-600 dark:text-slate-300">
                      Configure how often this report should be generated and sent
                    </p>
                  </div>

                  <div className="bg-slate-50 dark:bg-slate-800 rounded-xl p-6">
                    <div className="flex items-center space-x-4">
                      <span className="text-slate-700 dark:text-slate-300 font-medium">
                        Run every
                      </span>
                      <div className="w-24">
                        <input
                          type="number"
                          name="frequency_value"
                          value={formData.frequency_value}
                          onChange={handleChange}
                          min={frequencyUnits.find(u => u.value === formData.frequency_unit)?.min || 1}
                          max={frequencyUnits.find(u => u.value === formData.frequency_unit)?.max || 30}
                          className={`w-full px-3 py-2.5 bg-white dark:bg-slate-700 border ${errors.frequency_value ? 'border-red-500' : 'border-slate-200 dark:border-slate-600'
                            } rounded-xl text-slate-800 dark:text-white text-center focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all`}
                        />
                      </div>
                      <select
                        name="frequency_unit"
                        value={formData.frequency_unit}
                        onChange={handleChange}
                        className="px-4 py-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                      >
                        {frequencyUnits.map((unit) => (
                          <option key={unit.value} value={unit.value}>
                            {unit.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    {errors.frequency_value && (
                      <p className="mt-3 text-sm text-red-600 dark:text-red-400 flex items-center">
                        <AlertCircle className="w-4 h-4 mr-1" />
                        {errors.frequency_value}
                      </p>
                    )}
                  </div>

                  {/* Frequency Guidelines */}
                  <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl p-4">
                    <h4 className="font-medium text-blue-800 dark:text-blue-200 mb-2 flex items-center">
                      <Calendar className="w-4 h-4 mr-2" />
                      Schedule Guidelines
                    </h4>
                    <ul className="text-sm text-blue-700 dark:text-blue-300 space-y-1">
                      <li>• Minutes: 5-59 (recommended for urgent fraud alerts)</li>
                      <li>• Hours: 1-23 (recommended for periodic monitoring)</li>
                      <li>• Days: 1-30 (recommended for summary reports)</li>
                    </ul>
                  </div>

                  {/* Preview */}
                  <div className="bg-slate-100 dark:bg-slate-700 rounded-xl p-4">
                    <h4 className="font-medium text-slate-800 dark:text-white mb-2">
                      Schedule Preview
                    </h4>
                    <p className="text-slate-600 dark:text-slate-300">
                      This report will be generated and sent every{' '}
                      <span className="font-semibold text-blue-600 dark:text-blue-400">
                        {formData.frequency_value}{' '}
                        {formData.frequency_value === 1
                          ? formData.frequency_unit.slice(0, -1)
                          : formData.frequency_unit}
                      </span>
                    </p>
                  </div>
                </div>
              )}

              {/* Detection Parameters Section */}
              {activeSection === 'detection' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-semibold text-slate-800 dark:text-white mb-2">
                      Fraud Detection Parameters
                    </h3>
                    <p className="text-sm text-slate-600 dark:text-slate-300">
                      Configure fraud detection sensitivity for this report
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        Time Window (minutes)
                      </label>
                      <input
                        type="number"
                        name="time_window_minutes"
                        value={formData.time_window_minutes}
                        onChange={handleChange}
                        min="1"
                        max="60"
                        className="w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                      />
                      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                        Time window for detecting patterns (1-60 min)
                      </p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        Amount Variance
                      </label>
                      <input
                        type="number"
                        name="amount_variance"
                        value={formData.amount_variance}
                        onChange={handleChange}
                        min="0.01"
                        max="1.0"
                        step="0.01"
                        className="w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                      />
                      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                        Allowed variance between amounts (0.1 = 10%)
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        Min Roll-over Txns
                      </label>
                      <input
                        type="number"
                        name="min_transactions_rollover"
                        value={formData.min_transactions_rollover}
                        onChange={handleChange}
                        min="2"
                        max="20"
                        className="w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        Split Threshold
                      </label>
                      <input
                        type="number"
                        name="split_threshold"
                        value={formData.split_threshold}
                        onChange={handleChange}
                        min="2"
                        max="20"
                        className="w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                      />
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
                        className="w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                      />
                    </div>
                  </div>

                  <div className="bg-slate-50 dark:bg-slate-800 rounded-xl p-4">
                    <h4 className="font-medium text-slate-800 dark:text-white mb-3">
                      Split Transaction Limits
                    </h4>
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                          Min Amount (KES)
                        </label>
                        <input
                          type="number"
                          name="split_min_amount"
                          value={formData.split_min_amount}
                          onChange={handleChange}
                          min="0"
                          step="100"
                          className="w-full px-3 py-2 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                          Max Amount (KES)
                        </label>
                        <input
                          type="number"
                          name="split_max_amount"
                          value={formData.split_max_amount}
                          onChange={handleChange}
                          min="0"
                          step="1000"
                          className="w-full px-3 py-2 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                          Total Threshold (KES)
                        </label>
                        <input
                          type="number"
                          name="split_total_amount_threshold"
                          value={formData.split_total_amount_threshold}
                          onChange={handleChange}
                          min="0"
                          step="1000"
                          className="w-full px-3 py-2 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        Analysis Period (days)
                      </label>
                      <input
                        type="number"
                        name="analysis_period_days"
                        value={formData.analysis_period_days}
                        onChange={handleChange}
                        min="1"
                        max="365"
                        className="w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                      />
                      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                        Days to analyze for historical reports
                      </p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        Max Transactions Per Check
                      </label>
                      <input
                        type="number"
                        name="max_transactions_per_check"
                        value={formData.max_transactions_per_check}
                        onChange={handleChange}
                        min="10"
                        max="1000"
                        className="w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                      />
                      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                        Max transactions per shortcode check
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Notifications Section */}
              {activeSection === 'notifications' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-semibold text-slate-800 dark:text-white mb-2">
                      Notification Settings
                    </h3>
                    <p className="text-sm text-slate-600 dark:text-slate-300">
                      Configure which fraud types trigger notifications
                    </p>
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
                    <h3 className="text-lg font-semibold text-slate-800 dark:text-white mb-2">
                      Risk Score Thresholds
                    </h3>
                    <p className="text-sm text-slate-600 dark:text-slate-300">
                      Configure risk scoring thresholds for fraud classification
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        High Risk Score
                      </label>
                      <input
                        type="number"
                        name="high_risk_score"
                        value={formData.high_risk_score}
                        onChange={handleChange}
                        min="0"
                        max="100"
                        className="w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                      />
                      <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                        Minimum score for high-risk classification (0-100)
                      </p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        Medium Risk Score
                      </label>
                      <input
                        type="number"
                        name="medium_risk_score"
                        value={formData.medium_risk_score}
                        onChange={handleChange}
                        min="0"
                        max="100"
                        className="w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                      />
                      <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                        Minimum score for medium-risk classification (0-100)
                      </p>
                    </div>
                  </div>

                  {/* Risk Level Guide */}
                  <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl p-4">
                    <h4 className="font-medium text-blue-800 dark:text-blue-200 mb-3 flex items-center">
                      <Info className="w-4 h-4 mr-2" />
                      Risk Level Guide
                    </h4>
                    <div className="space-y-2 text-sm text-blue-700 dark:text-blue-300">
                      <div className="flex items-center">
                        <span className="w-3 h-3 rounded-full bg-red-500 mr-2"></span>
                        <span>High Risk: Score &ge; {formData.high_risk_score}</span>
                      </div>
                      <div className="flex items-center">
                        <span className="w-3 h-3 rounded-full bg-yellow-500 mr-2"></span>
                        <span>Medium Risk: Score between {formData.medium_risk_score} and {formData.high_risk_score - 1}</span>
                      </div>
                      <div className="flex items-center">
                        <span className="w-3 h-3 rounded-full bg-green-500 mr-2"></span>
                        <span>Low Risk: Score &lt; {formData.medium_risk_score}</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Recipients Section */}
              {activeSection === 'recipients' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-semibold text-slate-800 dark:text-white mb-2">
                      Email Recipients
                    </h3>
                    <p className="text-sm text-slate-600 dark:text-slate-300">
                      Configure which email addresses will receive this report
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                      Recipient Email Addresses *
                    </label>
                    <textarea
                      name="recipient_emails"
                      value={formData.recipient_emails}
                      onChange={handleChange}
                      rows="4"
                      className={`w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-700 border ${errors.recipient_emails ? 'border-red-500' : 'border-slate-200 dark:border-slate-600'
                        } rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all`}
                      placeholder="fraud-team@company.com, manager@company.com, alerts@company.com"
                    />
                    {errors.recipient_emails && (
                      <p className="mt-2 text-sm text-red-600 dark:text-red-400 flex items-center">
                        <AlertCircle className="w-4 h-4 mr-1" />
                        {errors.recipient_emails}
                      </p>
                    )}
                    <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                      Enter email addresses separated by commas
                    </p>
                  </div>

                  {/* Email Preview */}
                  {formData.recipient_emails && (
                    <div className="bg-slate-50 dark:bg-slate-800 rounded-xl p-4">
                      <h4 className="font-medium text-slate-800 dark:text-white mb-3 flex items-center">
                        <Mail className="w-4 h-4 mr-2" />
                        Recipients Preview
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {formData.recipient_emails.split(',').map((email, index) => {
                          const trimmedEmail = email.trim();
                          if (!trimmedEmail) return null;
                          const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                          const isValid = emailRegex.test(trimmedEmail);
                          return (
                            <span
                              key={index}
                              className={`px-3 py-1 rounded-full text-sm ${isValid
                                  ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                                  : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                                }`}
                            >
                              {trimmedEmail}
                              {!isValid && ' (invalid)'}
                            </span>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Tips */}
                  <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-xl p-4">
                    <h4 className="font-medium text-yellow-800 dark:text-yellow-200 mb-2">
                      Tips
                    </h4>
                    <ul className="text-sm text-yellow-700 dark:text-yellow-300 space-y-1">
                      <li>• Add multiple recipients to ensure reports reach the right people</li>
                      <li>• Use team distribution lists for broader coverage</li>
                      <li>• Verify email addresses before saving</li>
                    </ul>
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
                  <span>{isLoading ? 'Saving...' : config ? 'Update Schedule' : 'Create Schedule'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

export default UserReportConfigModal;
