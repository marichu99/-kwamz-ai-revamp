import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Settings, User, LogOut, Camera, Lock, Eye, EyeOff, Save, AlertCircle, Upload, Mail, X } from 'lucide-react';
import config from '../../Config';
import { useToast } from './ToastProvider';

/* -------------------------------------------
   ProfileTab Component
-------------------------------------------- */
const ProfileTab = React.memo(({ formData, handleInputChange, handleImageChange, handleSave, isLoading, previewImage }) => {
    const [touched, setTouched] = useState({});
    const [dragActive, setDragActive] = useState(false);

    // Mark field as touched when user interacts with it
    const handleFieldTouch = (fieldName) => {
        setTouched(prev => ({
            ...prev,
            [fieldName]: true
        }));
    };

    // Enhanced input change handler that marks field as touched
    const handleEnhancedInputChange = (fieldName, value) => {
        handleInputChange(fieldName, value);
        handleFieldTouch(fieldName);
    };

    // Validation logic
    const errors = useMemo(() => {
        const newErrors = {};

        // Username validation
        if (touched.username) {
            if (!formData.username || formData.username.trim() === '') {
                newErrors.username = 'Username is required';
            } else if (formData.username.trim().length < 2) {
                newErrors.username = 'Username must be at least 2 characters';
            } else if (formData.username.trim().length > 30) {
                newErrors.username = 'Username must be less than 30 characters';
            } else if (!/^[a-zA-Z0-9_\s]+$/.test(formData.username)) {
                newErrors.username = 'Username can only contain letters, numbers, underscores, and spaces';
            }
        }

        // Email validation
        if (touched.email) {
            if (!formData.email || formData.email.trim() === '') {
                newErrors.email = 'Email is required';
            } else {
                const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                if (!emailRegex.test(formData.email)) {
                    newErrors.email = 'Please enter a valid email address';
                }
            }
        }

        return newErrors;
    }, [formData, touched]);

    // Check if form is valid
    const isFormValid = useMemo(() => {
        return Object.keys(errors).length === 0 &&
            formData.username?.trim() &&
            formData.email?.trim() &&
            /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email || '');
    }, [errors, formData]);

    // Handle drag and drop for image upload
    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true);
        } else if (e.type === 'dragleave') {
            setDragActive(false);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);

        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            const file = e.dataTransfer.files[0];
            if (file.type.startsWith('image/')) {
                handleImageChange({ target: { files: [file] } });
            }
        }
    };

    // Remove image handler
    const handleRemoveImage = (e) => {
        e.stopPropagation();
        handleInputChange('profileImage', null);
    };

    return (
        <div className="space-y-6 max-h-[70vh] overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-slate-300 dark:scrollbar-thumb-slate-600 scrollbar-track-transparent">
            {/* Profile Image Section */}
            <div className="text-center">
                <div className="relative inline-block">
                    <div className="w-24 h-24 rounded-full bg-gray-300 ring-4 ring-blue-500 overflow-hidden">
                        {previewImage ? (
                            <img src={previewImage} alt="Profile" className="w-full h-full object-cover" />
                        ) : (
                            <div className="w-full h-full flex items-center justify-center">
                                <User className="w-12 h-12 text-gray-500" />
                            </div>
                        )}
                    </div>
                    <label
                        htmlFor="profile-image"
                        className="absolute -bottom-2 -right-2 bg-blue-600 hover:bg-blue-700 text-white p-2 rounded-full cursor-pointer transition-colors"
                    >
                        <Camera className="w-4 h-4" />
                    </label>
                    <input
                        id="profile-image"
                        type="file"
                        accept="image/"
                        onChange={handleImageChange}
                        className="hidden"
                    />
                </div>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-2">
                    Click the camera icon to change your profile picture
                </p>
            </div>
            {/* Username Field */}
            <div className="space-y-2">
                <label className="block text-sm font-semibold text-slate-700 dark:text-slate-200">
                    Username
                </label>
                <div className="relative group">
                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                        <User className="w-5 h-5 text-slate-400 group-focus-within:text-blue-500 transition-colors" />
                    </div>
                    <input
                        type="text"
                        value={formData.username || ''}
                        onChange={(e) => handleEnhancedInputChange('username', e.target.value)}
                        onBlur={() => handleFieldTouch('username')}
                        className={`w-full pl-12 pr-4 py-4 border-2 rounded-xl font-medium transition-all duration-300 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 ${errors.username
                            ? 'border-red-300 dark:border-red-600 focus:border-red-500 focus:ring-red-200 dark:focus:ring-red-900'
                            : 'border-slate-200 dark:border-slate-600 focus:border-blue-500 focus:ring-blue-200 dark:focus:ring-blue-900 hover:border-slate-300 dark:hover:border-slate-500'
                            } focus:ring-4 focus:outline-none`}
                        placeholder="Enter your username"
                    />
                    {formData.username && !errors.username && (
                        <div className="absolute inset-y-0 right-0 pr-4 flex items-center">
                            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                        </div>
                    )}
                </div>

                {errors.username && (
                    <div className="flex items-start space-x-2 animate-shake">
                        <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                        <p className="text-sm text-red-600 dark:text-red-400">{errors.username}</p>
                    </div>
                )}

                <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500 dark:text-slate-400">
                        {formData.username?.length || 0}/30 characters
                    </span>
                    {formData.username && !errors.username && (
                        <span className="text-green-600 dark:text-green-400 flex items-center space-x-1">
                            <div className="w-3 h-3 rounded-full bg-green-500 flex items-center justify-center">
                                <svg className="w-2 h-2 text-white" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                </svg>
                            </div>
                            <span>Valid</span>
                        </span>
                    )}
                </div>
            </div>

            {/* Email Field */}
            <div className="space-y-2">
                <label className="block text-sm font-semibold text-slate-700 dark:text-slate-200">
                    Email Address
                </label>
                <div className="relative group">
                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                        <Mail className="w-5 h-5 text-slate-400 group-focus-within:text-blue-500 transition-colors" />
                    </div>
                    <input
                        type="email"
                        value={formData.email || ''}
                        onChange={(e) => handleEnhancedInputChange('email', e.target.value)}
                        onBlur={() => handleFieldTouch('email')}
                        className={`w-full pl-12 pr-4 py-4 border-2 rounded-xl font-medium transition-all duration-300 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 ${errors.email
                            ? 'border-red-300 dark:border-red-600 focus:border-red-500 focus:ring-red-200 dark:focus:ring-red-900'
                            : 'border-slate-200 dark:border-slate-600 focus:border-blue-500 focus:ring-blue-200 dark:focus:ring-blue-900 hover:border-slate-300 dark:hover:border-slate-500'
                            } focus:ring-4 focus:outline-none`}
                        placeholder="Enter your email address"
                    />
                    {formData.email && !errors.email && (
                        <div className="absolute inset-y-0 right-0 pr-4 flex items-center">
                            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                        </div>
                    )}
                </div>

                {errors.email && (
                    <div className="flex items-start space-x-2 animate-shake">
                        <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                        <p className="text-sm text-red-600 dark:text-red-400">{errors.email}</p>
                    </div>
                )}

                {formData.email && !errors.email && (
                    <div className="flex items-center space-x-1 text-xs text-green-600 dark:text-green-400">
                        <div className="w-3 h-3 rounded-full bg-green-500 flex items-center justify-center">
                            <svg className="w-2 h-2 text-white" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                            </svg>
                        </div>
                        <span>Valid email format</span>
                    </div>
                )}
            </div>

            {/* Save Button */}
            <div className="pt-4">
                <button
                    onClick={handleSave}
                    disabled={isLoading || !isFormValid}
                    className="w-full group relative bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 disabled:from-blue-300 disabled:to-blue-400 disabled:cursor-not-allowed text-white py-4 px-6 rounded-xl font-semibold transition-all duration-300 shadow-lg hover:shadow-xl transform hover:scale-[1.02] disabled:transform-none disabled:shadow-md"
                >
                    <div className="flex items-center justify-center space-x-3">
                        {isLoading ? (
                            <>
                                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                <span>Saving Changes...</span>
                            </>
                        ) : (
                            <>
                                <Save className="w-5 h-5 group-hover:scale-110 transition-transform" />
                                <span>Save Changes</span>
                            </>
                        )}
                    </div>

                    {/* Button shine effect */}
                    {!isLoading && isFormValid && (
                        <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-transparent via-white to-transparent opacity-0 group-hover:opacity-20 transform -skew-x-12 group-hover:animate-pulse"></div>
                    )}
                </button>

                {!isFormValid && Object.keys(touched).length > 0 && (
                    <p className="text-sm text-slate-500 dark:text-slate-400 text-center mt-3">
                        Please fix the errors above to save your changes
                    </p>
                )}
            </div>

            {/* Form validation summary */}
            {Object.keys(errors).length > 0 && Object.keys(touched).length > 0 && (
                <div className="bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 rounded-r-xl p-4 animate-slideIn">
                    <div className="flex items-center space-x-2 mb-2">
                        <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
                        <h4 className="text-sm font-semibold text-red-800 dark:text-red-200">
                            Please fix the following issues:
                        </h4>
                    </div>
                    <ul className="text-sm text-red-700 dark:text-red-300 space-y-1 pl-7">
                        {Object.entries(errors).map(([field, error]) => (
                            <li key={field} className="flex items-center space-x-2">
                                <div className="w-1 h-1 bg-red-500 rounded-full"></div>
                                <span>{error}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
});

/* -------------------------------------------
   SecurityTab Component
-------------------------------------------- */
const SecurityTab = React.memo(({ formData, handleInputChange, handleSave, isLoading }) => {
    const [showCurrentPassword, setShowCurrentPassword] = useState(false);
    const [showNewPassword, setShowNewPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [touched, setTouched] = useState({});

    // Mark field as touched when user interacts with it
    const handleFieldTouch = (fieldName) => {
        setTouched(prev => ({
            ...prev,
            [fieldName]: true
        }));
    };

    // Validation logic
    const errors = useMemo(() => {
        const newErrors = {};

        // Current password validation
        if (touched.currentPassword && (!formData.currentPassword || formData.currentPassword.trim() === '')) {
            newErrors.currentPassword = 'Current password is required';
        }

        // New password validation
        if (touched.newPassword) {
            if (!formData.newPassword || formData.newPassword.trim() === '') {
                newErrors.newPassword = 'New password is required';
            } else {
                const password = formData.newPassword;
                const passwordErrors = [];

                if (password.length < 8) {
                    passwordErrors.push('at least 8 characters');
                }
                if (!/[a-z]/.test(password)) {
                    passwordErrors.push('one lowercase letter');
                }
                if (!/[A-Z]/.test(password)) {
                    passwordErrors.push('one uppercase letter');
                }
                if (!/\d/.test(password)) {
                    passwordErrors.push('one number');
                }
                if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
                    passwordErrors.push('one special character');
                }

                if (passwordErrors.length > 0) {
                    newErrors.newPassword = `Password must contain ${passwordErrors.join(', ')}`;
                }
            }
        }

        // Confirm password validation
        if (touched.confirmPassword) {
            if (!formData.confirmPassword || formData.confirmPassword.trim() === '') {
                newErrors.confirmPassword = 'Please confirm your new password';
            } else if (formData.newPassword !== formData.confirmPassword) {
                newErrors.confirmPassword = 'Passwords do not match';
            }
        }

        // Cross-field validation: new password same as current password
        if (touched.newPassword && touched.currentPassword &&
            formData.currentPassword && formData.newPassword &&
            formData.currentPassword === formData.newPassword) {
            newErrors.newPassword = 'New password must be different from current password';
        }

        return newErrors;
    }, [formData, touched]);

    // Check if form is valid
    const isFormValid = useMemo(() => {
        return Object.keys(errors).length === 0 &&
            formData.currentPassword &&
            formData.newPassword &&
            formData.confirmPassword &&
            formData.newPassword === formData.confirmPassword;
    }, [errors, formData]);

    // Enhanced input change handler that marks field as touched
    const handleEnhancedInputChange = (fieldName, value) => {
        handleInputChange(fieldName, value);
        handleFieldTouch(fieldName);
    };

    // Password strength indicator
    const getPasswordStrength = (password) => {
        if (!password) return { score: 0, label: '', color: '' };

        let score = 0;
        if (password.length >= 8) score++;
        if (/[a-z]/.test(password)) score++;
        if (/[A-Z]/.test(password)) score++;
        if (/\d/.test(password)) score++;
        if (/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) score++;

        if (score <= 2) return { score, label: 'Weak', color: 'text-red-600 dark:text-red-400' };
        if (score <= 3) return { score, label: 'Fair', color: 'text-yellow-600 dark:text-yellow-400' };
        if (score <= 4) return { score, label: 'Good', color: 'text-blue-600 dark:text-blue-400' };
        return { score, label: 'Strong', color: 'text-green-600 dark:text-green-400' };
    };

    const passwordStrength = getPasswordStrength(formData.newPassword);

    return (
        <div className="space-y-6 max-h-[70vh] overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-slate-300 dark:scrollbar-thumb-slate-600 scrollbar-track-transparent">
            {/* Current Password */}
            <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                    Current Password
                </label>
                <div className="relative">
                    <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-slate-400" />
                    <input
                        type={showCurrentPassword ? 'text' : 'password'}
                        value={formData.currentPassword || ''}
                        onChange={(e) => handleEnhancedInputChange('currentPassword', e.target.value)}
                        onBlur={() => handleFieldTouch('currentPassword')}
                        className={`w-full pl-10 pr-12 py-3 border rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-slate-800 text-slate-900 dark:text-white transition-colors ${errors.currentPassword
                            ? 'border-red-300 dark:border-red-600'
                            : 'border-slate-200 dark:border-slate-600'
                            }`}
                        placeholder="Enter current password"
                    />
                    <button
                        type="button"
                        onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                        className="absolute right-3 top-1/2 transform -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                    >
                        {showCurrentPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                </div>
                {errors.currentPassword && (
                    <div className="flex items-center space-x-2 mt-2">
                        <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
                        <p className="text-sm text-red-600 dark:text-red-400">{errors.currentPassword}</p>
                    </div>
                )}
            </div>

            {/* New Password */}
            <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                    New Password
                </label>
                <div className="relative">
                    <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-slate-400" />
                    <input
                        type={showNewPassword ? 'text' : 'password'}
                        value={formData.newPassword || ''}
                        onChange={(e) => handleEnhancedInputChange('newPassword', e.target.value)}
                        onBlur={() => handleFieldTouch('newPassword')}
                        className={`w-full pl-10 pr-12 py-3 border rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-slate-800 text-slate-900 dark:text-white transition-colors ${errors.newPassword
                            ? 'border-red-300 dark:border-red-600'
                            : 'border-slate-200 dark:border-slate-600'
                            }`}
                        placeholder="Enter new password"
                    />
                    <button
                        type="button"
                        onClick={() => setShowNewPassword(!showNewPassword)}
                        className="absolute right-3 top-1/2 transform -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                    >
                        {showNewPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                </div>

                {/* Password Strength Indicator */}
                {formData.newPassword && (
                    <div className="mt-2">
                        <div className="flex items-center justify-between mb-1">
                            <span className="text-xs text-slate-500 dark:text-slate-400">Password strength:</span>
                            <span className={`text-xs font-medium ${passwordStrength.color}`}>
                                {passwordStrength.label}
                            </span>
                        </div>
                        <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
                            <div
                                className={`h-2 rounded-full transition-all duration-300 ${passwordStrength.score <= 2 ? 'bg-red-500' :
                                    passwordStrength.score <= 3 ? 'bg-yellow-500' :
                                        passwordStrength.score <= 4 ? 'bg-blue-500' : 'bg-green-500'
                                    }`}
                                style={{ width: `${(passwordStrength.score / 5) * 100}%` }}
                            />
                        </div>
                    </div>
                )}

                {errors.newPassword && (
                    <div className="flex items-center space-x-2 mt-2">
                        <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
                        <p className="text-sm text-red-600 dark:text-red-400">{errors.newPassword}</p>
                    </div>
                )}
            </div>

            {/* Confirm Password */}
            <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                    Confirm New Password
                </label>
                <div className="relative">
                    <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-slate-400" />
                    <input
                        type={showConfirmPassword ? 'text' : 'password'}
                        value={formData.confirmPassword || ''}
                        onChange={(e) => handleEnhancedInputChange('confirmPassword', e.target.value)}
                        onBlur={() => handleFieldTouch('confirmPassword')}
                        className={`w-full pl-10 pr-12 py-3 border rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-slate-800 text-slate-900 dark:text-white transition-colors ${errors.confirmPassword
                            ? 'border-red-300 dark:border-red-600'
                            : formData.confirmPassword && formData.newPassword === formData.confirmPassword
                                ? 'border-green-300 dark:border-green-600'
                                : 'border-slate-200 dark:border-slate-600'
                            }`}
                        placeholder="Confirm new password"
                    />
                    <button
                        type="button"
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                        className="absolute right-3 top-1/2 transform -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                    >
                        {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                </div>

                {/* Match indicator */}
                {formData.confirmPassword && formData.newPassword && !errors.confirmPassword && (
                    <div className="flex items-center space-x-2 mt-2">
                        <div className="w-4 h-4 rounded-full bg-green-500 flex items-center justify-center">
                            <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                            </svg>
                        </div>
                        <p className="text-sm text-green-600 dark:text-green-400">Passwords match</p>
                    </div>
                )}

                {errors.confirmPassword && (
                    <div className="flex items-center space-x-2 mt-2">
                        <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
                        <p className="text-sm text-red-600 dark:text-red-400">{errors.confirmPassword}</p>
                    </div>
                )}
            </div>

            {/* Password Requirements */}
            <div className="bg-slate-50 dark:bg-slate-800/50 p-4 rounded-xl">
                <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                    Password Requirements:
                </h4>
                <ul className="text-xs text-slate-600 dark:text-slate-400 space-y-1">
                    <li className={`flex items-center space-x-2 ${formData.newPassword?.length >= 8 ? 'text-green-600 dark:text-green-400' : ''
                        }`}>
                        <span className={`w-3 h-3 rounded-full ${formData.newPassword?.length >= 8 ? 'bg-green-500' : 'bg-slate-300 dark:bg-slate-600'
                            }`}></span>
                        <span>At least 8 characters long</span>
                    </li>
                    <li className={`flex items-center space-x-2 ${/[a-z]/.test(formData.newPassword || '') && /[A-Z]/.test(formData.newPassword || '')
                        ? 'text-green-600 dark:text-green-400' : ''
                        }`}>
                        <span className={`w-3 h-3 rounded-full ${/[a-z]/.test(formData.newPassword || '') && /[A-Z]/.test(formData.newPassword || '')
                            ? 'bg-green-500' : 'bg-slate-300 dark:bg-slate-600'
                            }`}></span>
                        <span>Contains uppercase and lowercase letters</span>
                    </li>
                    <li className={`flex items-center space-x-2 ${/\d/.test(formData.newPassword || '') ? 'text-green-600 dark:text-green-400' : ''
                        }`}>
                        <span className={`w-3 h-3 rounded-full ${/\d/.test(formData.newPassword || '') ? 'bg-green-500' : 'bg-slate-300 dark:bg-slate-600'
                            }`}></span>
                        <span>Contains at least one number</span>
                    </li>
                    <li className={`flex items-center space-x-2 ${/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(formData.newPassword || '')
                        ? 'text-green-600 dark:text-green-400' : ''
                        }`}>
                        <span className={`w-3 h-3 rounded-full ${/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(formData.newPassword || '')
                            ? 'bg-green-500' : 'bg-slate-300 dark:bg-slate-600'
                            }`}></span>
                        <span>Contains at least one special character</span>
                    </li>
                </ul>
            </div>

            {/* Update Password Button */}
            <button
                onClick={handleSave}
                disabled={isLoading || !isFormValid}
                className="w-full flex items-center justify-center space-x-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed text-white py-3 px-4 rounded-xl transition-colors font-medium"
            >
                {isLoading ? (
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                    <Save className="w-5 h-5" />
                )}
                <span>{isLoading ? 'Updating...' : 'Update Password'}</span>
            </button>

            {/* Form validation summary */}
            {Object.keys(errors).length > 0 && Object.keys(touched).length > 0 && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4">
                    <div className="flex items-center space-x-2 mb-2">
                        <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
                        <h4 className="text-sm font-medium text-red-800 dark:text-red-200">
                            Please fix the following issues:
                        </h4>
                    </div>
                    <ul className="text-sm text-red-700 dark:text-red-300 space-y-1 pl-7">
                        {Object.entries(errors).map(([field, error]) => (
                            <li key={field}>• {error}</li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
});
/* -------------------------------------------
   Main Modal Component
-------------------------------------------- */
const UserSettingsModal = ({ isOpen, onClose, userData, onUpdateUser }) => {
    const [activeTab, setActiveTab] = useState('profile');
    const [formData, setFormData] = useState({
        username: userData?.username || '',
        email: userData?.email || '',
        profileImage: null
    });

    const [previewImage, setPreviewImage] = useState(userData?.profileImage || null);
    const [isLoading, setIsLoading] = useState(false);
    const { showToast } = useToast();

    // Reset form when modal opens
    useEffect(() => {
        if (isOpen) {
            setFormData({
                username: userData?.username || '',
                email: userData?.email || '',
                profileImage: null
            });
            setPreviewImage(userData?.profileImage || null);
        }
    }, [isOpen, userData]);

    // Handle text field changes
    const handleInputChange = useCallback((field, value) => {
        setFormData(prev => ({
            ...prev,
            [field]: value
        }));
    }, []);

    // Handle image selection
    const handleImageChange = useCallback((e) => {
        const file = e.target.files[0];
        if (file) {
            setFormData(prev => ({ ...prev, profileImage: file }));
            const reader = new FileReader();
            reader.onload = (event) => setPreviewImage(event.target.result);
            reader.readAsDataURL(file);
        }
    }, []);

    // Handle save action
    const handleSave = useCallback(async () => {
        setIsLoading(true);
        try {
            const loggedInUser = localStorage.getItem('user');
            if (!loggedInUser) {
                throw new Error('User not found in localStorage');
            }
            const loggedInUserId = JSON.parse(loggedInUser).id;

            const token = localStorage.getItem("token");

            const formDataToSend = new FormData();
            formDataToSend.append('username', formData.username);
            formDataToSend.append('email', formData.email);

            // Only append if there's a new image
            if (formData.profileImage && typeof formData.profileImage !== 'string') {
                formDataToSend.append('profileImage', formData.profileImage);
            }

            // Add password fields if they exist
            if (formData.currentPassword) {
                formDataToSend.append('currentPassword', formData.currentPassword);
                formDataToSend.append('newPassword', formData.newPassword);
            }

            const res = await fetch(`${config.API_URL}/users/${loggedInUserId}`, {
                method: 'PUT',
                headers: {
                    Authorization: `Bearer ${token}`,
                },
                body: formDataToSend,
                
            });

            if (!res.ok) {
                const errorData = await res.json().catch(() => ({ error: 'Unknown error' }));
                throw new Error(errorData.error || `HTTP error! status: ${res.status}`);
            }

            const result = await res.json();
            showToast('Profile updated successfully!', 'success');
            onUpdateUser(result);
            onClose();

        } catch (err) {
            showToast('Update failed: ' + err.message, 'error');
        } finally {
            setIsLoading(false);
        }
    }, [formData, onClose, onUpdateUser, showToast]);

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-md">
                {/* Modal Header */}
                <div className="flex justify-between p-6 border-b">
                    <h2 className="text-xl font-semibold">Settings</h2>
                    <button onClick={onClose}>✖️</button>
                </div>

                {/* Tabs */}
                <div className="flex border-b">
                    <button
                        onClick={() => setActiveTab('profile')}
                        className={`flex-1 py-3 px-4 ${activeTab === 'profile' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-500'}`}
                    >
                        Profile
                    </button>
                    <button
                        onClick={() => setActiveTab('security')}
                        className={`flex-1 py-3 px-4 ${activeTab === 'security' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-500'}`}
                    >
                        Security
                    </button>
                </div>

                {/* Modal Content */}
                <div className="p-6">
                    {activeTab === 'profile' ? (
                        <ProfileTab
                            formData={formData}
                            handleInputChange={handleInputChange}
                            handleImageChange={handleImageChange}
                            handleSave={handleSave}
                            isLoading={isLoading}
                            previewImage={previewImage}
                        />
                    ) : (
                        <SecurityTab
                            formData={formData}
                            handleInputChange={handleInputChange}
                            handleSave={handleSave}
                            isLoading={isLoading}
                        />
                    )}
                </div>
            </div>
        </div>
    );
};

export default React.memo(UserSettingsModal);
