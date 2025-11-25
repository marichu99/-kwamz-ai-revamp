import { useState, useEffect } from 'react';
import { X, Building, Code, Globe, Currency, Settings, Server, Folder, FileText, Clock, RotateCcw, Shield, ChevronRight } from 'lucide-react';

function BankDetailsModal({ isOpen, onClose, onSubmit, isLoading, bank }) {
    const [formData, setFormData] = useState({
        name: '',
        code: '',
        country: '',
        currency: 'USD',
        status: 'pending',
        config: {
            connection_type: 'sftp',
            host: '',
            port: 22,
            username: '',
            password_encrypted: '',
            api_key_encrypted: '',
            base_url: '',
            sftp_directory: '/',
            file_naming_convention: '',
            supported_formats: [],
            timezone: 'UTC',
            retry_attempts: 3,
            timeout_seconds: 30,
            additional_config: {}
        }
    });

    const [showAdvanced, setShowAdvanced] = useState(false);

    useEffect(() => {
        if (bank) {
            setFormData({
                name: bank.name || '',
                code: bank.code || '',
                country: bank.country || '',
                currency: bank.currency || 'USD',
                status: bank.status || 'pending',
                config: {
                    connection_type: bank.config?.connection_type || 'sftp',
                    host: bank.config?.host || '',
                    port: bank.config?.port || 22,
                    username: bank.config?.username || '',
                    password_encrypted: bank.config?.password_encrypted || '',
                    api_key_encrypted: bank.config?.api_key_encrypted || '',
                    base_url: bank.config?.base_url || '',
                    sftp_directory: bank.config?.sftp_directory || '/',
                    file_naming_convention: bank.config?.file_naming_convention || '',
                    supported_formats: bank.config?.supported_formats || [],
                    timezone: bank.config?.timezone || 'UTC',
                    retry_attempts: bank.config?.retry_attempts || 3,
                    timeout_seconds: bank.config?.timeout_seconds || 30,
                    additional_config: bank.config?.additional_config || {}
                }
            });
        } else {
            // Reset form for new bank
            setFormData({
                name: '',
                code: '',
                country: '',
                currency: 'USD',
                status: 'pending',
                config: {
                    connection_type: 'sftp',
                    host: '',
                    port: 22,
                    username: '',
                    password_encrypted: '',
                    api_key_encrypted: '',
                    base_url: '',
                    sftp_directory: '/',
                    file_naming_convention: '',
                    supported_formats: [],
                    timezone: 'UTC',
                    retry_attempts: 3,
                    timeout_seconds: 30,
                    additional_config: {}
                }
            });
        }
    }, [bank, isOpen]);

    const handleInputChange = (path, value) => {
        if (path.includes('.')) {
            const [parent, child] = path.split('.');
            setFormData(prev => ({
                ...prev,
                [parent]: {
                    ...prev[parent],
                    [child]: value
                }
            }));
        } else {
            setFormData(prev => ({
                ...prev,
                [path]: value
            }));
        }
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        onSubmit(formData, bank?.id, () => {
            setFormData({
                name: '',
                code: '',
                country: '',
                currency: 'USD',
                status: 'pending',
                config: {
                    connection_type: 'sftp',
                    host: '',
                    port: 22,
                    username: '',
                    password_encrypted: '',
                    api_key_encrypted: '',
                    base_url: '',
                    sftp_directory: '/',
                    file_naming_convention: '',
                    supported_formats: [],
                    timezone: 'UTC',
                    retry_attempts: 3,
                    timeout_seconds: 30,
                    additional_config: {}
                }
            });
        });
    };

    const handleClose = () => {
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-gradient-to-br from-black/60 via-black/50 to-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-white/95 dark:bg-slate-900/95 backdrop-blur-lg rounded-2xl shadow-2xl border border-white/20 dark:border-slate-700/50 w-full max-w-3xl transform transition-all duration-300 max-h-[90vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="bg-gradient-to-r from-emerald-500 to-emerald-600 px-6 py-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                            <Building className="w-6 h-6 text-white" />
                            <h2 className="text-xl font-semibold text-white">
                                {bank ? 'Edit Bank Configuration' : 'Create New Bank'}
                            </h2>
                        </div>
                        <button
                            onClick={handleClose}
                            className="p-1 hover:bg-emerald-400 rounded-lg transition-colors"
                        >
                            <X className="w-5 h-5 text-white" />
                        </button>
                    </div>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="overflow-y-auto max-h-[calc(90vh-80px)]">
                    <div className="p-6 space-y-6">
                        {/* Basic Information */}
                        <div className="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-6">
                            <h3 className="text-lg font-semibold text-slate-800 dark:text-white mb-4 flex items-center space-x-2">
                                <Building className="w-5 h-5 text-emerald-600" />
                                <span>Basic Information</span>
                            </h3>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                                        Bank Name *
                                    </label>
                                    <input
                                        type="text"
                                        required
                                        value={formData.name}
                                        onChange={(e) => handleInputChange('name', e.target.value)}
                                        className="w-full px-4 py-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
                                        placeholder="Enter bank name"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                                        Bank Code *
                                    </label>
                                    <div className="relative">
                                        <Code className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
                                        <input
                                            type="text"
                                            required
                                            value={formData.code}
                                            onChange={(e) => handleInputChange('code', e.target.value.toUpperCase())}
                                            className="w-full pl-10 pr-4 py-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
                                            placeholder="BANK001"
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                                        Country *
                                    </label>
                                    <div className="relative">
                                        <Globe className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
                                        <input
                                            type="text"
                                            required
                                            value={formData.country}
                                            onChange={(e) => handleInputChange('country', e.target.value)}
                                            className="w-full pl-10 pr-4 py-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
                                            placeholder="Enter country"
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                                        Currency *
                                    </label>
                                    <div className="relative">
                                        <Currency className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
                                        <select
                                            value={formData.currency}
                                            onChange={(e) => handleInputChange('currency', e.target.value)}
                                            className="w-full pl-10 pr-4 py-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all appearance-none"
                                        >
                                            <option value="USD">USD - US Dollar</option>
                                            <option value="EUR">EUR - Euro</option>
                                            <option value="GBP">GBP - British Pound</option>
                                            <option value="KES">KES - Kenyan Shilling</option>
                                            <option value="UGX">UGX - Ugandan Shilling</option>
                                            <option value="TZS">TZS - Tanzanian Shilling</option>
                                        </select>
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                                        Status
                                    </label>
                                    <select
                                        value={formData.status}
                                        onChange={(e) => handleInputChange('status', e.target.value)}
                                        className="w-full px-4 py-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
                                    >
                                        <option value="pending">Pending</option>
                                        <option value="active">Active</option>
                                        <option value="inactive">Inactive</option>
                                        <option value="testing">Testing</option>
                                    </select>
                                </div>
                            </div>
                        </div>

                        {/* Connection Configuration */}
                        <div className="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-6">
                            <h3 className="text-lg font-semibold text-slate-800 dark:text-white mb-4 flex items-center space-x-2">
                                <Server className="w-5 h-5 text-emerald-600" />
                                <span>Connection Configuration</span>
                            </h3>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="md:col-span-2">
                                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                                        Connection Type *
                                    </label>
                                    <select
                                        value={formData.config.connection_type}
                                        onChange={(e) => handleInputChange('config.connection_type', e.target.value)}
                                        className="w-full px-4 py-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
                                    >
                                        <option value="sftp">SFTP</option>
                                        <option value="api">API</option>
                                        <option value="swift">SWIFT</option>
                                        <option value="ftp">FTP</option>
                                        <option value="as2">AS2</option>
                                    </select>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                                        Host
                                    </label>
                                    <input
                                        type="text"
                                        value={formData.config.host}
                                        onChange={(e) => handleInputChange('config.host', e.target.value)}
                                        className="w-full px-4 py-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
                                        placeholder="sftp.bank.com"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                                        Port
                                    </label>
                                    <input
                                        type="number"
                                        value={formData.config.port}
                                        onChange={(e) => handleInputChange('config.port', parseInt(e.target.value) || 22)}
                                        className="w-full px-4 py-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
                                        placeholder="22"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                                        Username
                                    </label>
                                    <input
                                        type="text"
                                        value={formData.config.username}
                                        onChange={(e) => handleInputChange('config.username', e.target.value)}
                                        className="w-full px-4 py-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
                                        placeholder="username"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                                        Password
                                    </label>
                                    <div className="relative">
                                        <Shield className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
                                        <input
                                            type="password"
                                            value={formData.config.password_encrypted}
                                            onChange={(e) => handleInputChange('config.password_encrypted', e.target.value)}
                                            className="w-full pl-10 pr-4 py-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
                                            placeholder="••••••••"
                                        />
                                    </div>
                                </div>

                                {formData.config.connection_type === 'api' && (
                                    <div className="md:col-span-2">
                                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                                            Base URL
                                        </label>
                                        <input
                                            type="text"
                                            value={formData.config.base_url}
                                            onChange={(e) => handleInputChange('config.base_url', e.target.value)}
                                            className="w-full px-4 py-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
                                            placeholder="https://api.bank.com/v1"
                                        />
                                    </div>
                                )}

                                {formData.config.connection_type === 'sftp' && (
                                    <div className="md:col-span-2">
                                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                                            SFTP Directory
                                        </label>
                                        <div className="relative">
                                            <Folder className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
                                            <input
                                                type="text"
                                                value={formData.config.sftp_directory}
                                                onChange={(e) => handleInputChange('config.sftp_directory', e.target.value)}
                                                className="w-full pl-10 pr-4 py-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
                                                placeholder="/upload/"
                                            />
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* File Configuration */}
                        <div className="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-6">
                            <h3 className="text-lg font-semibold text-slate-800 dark:text-white mb-4 flex items-center space-x-2">
                                <FileText className="w-5 h-5 text-emerald-600" />
                                <span>File Configuration</span>
                            </h3>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="md:col-span-2">
                                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                                        File Naming Convention
                                    </label>
                                    <input
                                        type="text"
                                        value={formData.config.file_naming_convention}
                                        onChange={(e) => handleInputChange('config.file_naming_convention', e.target.value)}
                                        className="w-full px-4 py-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
                                        placeholder="payment_{timestamp}_{sequence}.txt"
                                    />
                                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
                                        Use placeholders like {'{timestamp}'}, {'{sequence}'}, {'{date}'}
                                    </p>
                                </div>

                                <div className="md:col-span-2">
                                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                                        Supported Formats
                                    </label>
                                    <div className="flex flex-wrap gap-2">
                                        {['CSV', 'XML', 'JSON', 'TXT', 'MT940', 'ISO20022'].map(format => (
                                            <label key={format} className="flex items-center space-x-2">
                                                <input
                                                    type="checkbox"
                                                    checked={formData.config.supported_formats.includes(format)}
                                                    onChange={(e) => {
                                                        const newFormats = e.target.checked
                                                            ? [...formData.config.supported_formats, format]
                                                            : formData.config.supported_formats.filter(f => f !== format);
                                                        handleInputChange('config.supported_formats', newFormats);
                                                    }}
                                                    className="w-4 h-4 text-emerald-600 border-slate-300 rounded focus:ring-emerald-500"
                                                />
                                                <span className="text-sm text-slate-700 dark:text-slate-300">{format}</span>
                                            </label>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Advanced Settings */}
                        <div className="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-6">
                            <button
                                type="button"
                                onClick={() => setShowAdvanced(!showAdvanced)}
                                className="flex items-center space-x-2 text-slate-800 dark:text-white hover:text-emerald-600 transition-colors mb-4"
                            >
                                <Settings className="w-5 h-5" />
                                <span className="text-lg font-semibold">Advanced Settings</span>
                                <ChevronRight className={`w-4 h-4 transition-transform ${showAdvanced ? 'rotate-90' : ''}`} />
                            </button>

                            {showAdvanced && (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-slate-200 dark:border-slate-600">
                                    <div>
                                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                                            Timezone
                                        </label>
                                        <div className="relative">
                                            <Clock className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
                                            <select
                                                value={formData.config.timezone}
                                                onChange={(e) => handleInputChange('config.timezone', e.target.value)}
                                                className="w-full pl-10 pr-4 py-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
                                            >
                                                <option value="UTC">UTC</option>
                                                <option value="America/New_York">Eastern Time</option>
                                                <option value="Europe/London">London</option>
                                                <option value="Africa/Nairobi">Nairobi</option>
                                            </select>
                                        </div>
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                                            Retry Attempts
                                        </label>
                                        <div className="relative">
                                            <RotateCcw className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
                                            <input
                                                type="number"
                                                min="1"
                                                max="10"
                                                value={formData.config.retry_attempts}
                                                onChange={(e) => handleInputChange('config.retry_attempts', parseInt(e.target.value) || 3)}
                                                className="w-full pl-10 pr-4 py-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
                                            />
                                        </div>
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                                            Timeout (seconds)
                                        </label>
                                        <input
                                            type="number"
                                            min="10"
                                            max="300"
                                            value={formData.config.timeout_seconds}
                                            onChange={(e) => handleInputChange('config.timeout_seconds', parseInt(e.target.value) || 30)}
                                            className="w-full px-4 py-2.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
                                        />
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Footer */}
                    <div className="bg-slate-100 dark:bg-slate-700 px-6 py-4 border-t border-slate-200 dark:border-slate-600">
                        <div className="flex justify-end space-x-3">
                            <button
                                type="button"
                                onClick={handleClose}
                                className="px-6 py-2.5 text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-600 border border-slate-300 dark:border-slate-500 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-500 transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                type="submit"
                                disabled={isLoading}
                                className="px-6 py-2.5 bg-emerald-500 text-white rounded-xl hover:bg-emerald-600 transition-colors disabled:bg-emerald-300 disabled:cursor-not-allowed flex items-center space-x-2"
                            >
                                {isLoading ? (
                                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                ) : (
                                    <Building className="w-4 h-4" />
                                )}
                                <span>{bank ? 'Update Bank' : 'Create Bank'}</span>
                            </button>
                        </div>
                    </div>
                </form>
            </div>
        </div>
    );
}

export default BankDetailsModal;