import React, { useState } from 'react';
import { Eye, EyeOff, User, Lock, CheckCircle, AlertCircle, Shield } from 'lucide-react';
import OtpVerificationModal from './OtpVerificationModal';
import axios from 'axios';
import config from '../../Config';


const AdminSignUpForm = ({ onSuccess, onNavigateToLogin }) => {
    const [formData, setFormData] = useState({
        username: '',
        password: '',
        confirmPassword: '',
    });
    const [errors, setErrors] = useState({});
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [showPassword, setShowPassword] = useState(false);
    const [showOtpModal, setShowOtpModal] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [focusedField, setFocusedField] = useState('');
    const [showSuccess, setShowSuccess] = useState(false);

    const handleRequestOtp = async (e) => {
        e.preventDefault();

        // Clear previous errors
        setErrors(prev => ({ ...prev, general: undefined }));

        // Perform initial validation
        const isValid = validateAll();
        const allFieldsFilled = Object.values(formData).every(field => field.trim() !== '');

        if (!allFieldsFilled || !isValid) {
            setErrors(prev => ({ ...prev, general: 'Please fix the errors before proceeding.' }));
            return;
        }

        setIsSubmitting(true);
        try {
            // Ask the backend to send an OTP to the user's email
            await axios.post(`${config.API_URL}/users/request-otp`, { email: "marichufx@gmail.com" });
            setShowOtpModal(true); // Open the modal on success
        } catch (error) {
            console.error('OTP Request error:', error);
            const errorMessage = error.response?.data?.message || 'Failed to send OTP..';
            setErrors(prev => ({ ...prev, general: errorMessage }));
        } finally {
            setIsSubmitting(false);
        }
    };

    const validate = (name, value) => {
        const newErrors = { ...errors };

        if (name === 'username') {
            newErrors.username = value.length < 3 ? 'Username must be at least 3 characters' : '';
        }

        if (name === 'password') {
            const passwordRegex = /^(?=.*[0-9])(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{8,}$/;
            newErrors.password = !passwordRegex.test(value) && value.length > 0
                ? 'Password must be at least 8 characters, include a number and a special character.'
                : '';
        }

        if (name === 'confirmPassword') {
            newErrors.confirmPassword =
                value !== formData.password && value.length > 0 ? 'Passwords do not match' : '';
        }

        setErrors(newErrors);
    };

    const validateAll = () => {
        const newErrors = {};

        if (formData.username.length < 3) {
            newErrors.username = 'Username must be at least 3 characters';
        }

        const passwordRegex = /^(?=.*[0-9])(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{8,}$/;
        if (!passwordRegex.test(formData.password)) {
            newErrors.password = 'Password must be at least 8 characters, include a number and a special character.';
        }

        if (formData.confirmPassword !== formData.password) {
            newErrors.confirmPassword = 'Passwords do not match';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData((prev) => ({ ...prev, [name]: value }));
        validate(name, value);
    };


    const handleFinalSubmit = async (enteredOtp) => {

        const newErrors = { ...errors };
        delete newErrors.general;
        setErrors(newErrors);

        const isValid = validateAll();
        const allFieldsFilled = Object.values(formData).every(field => field.trim() !== '');

        if (!allFieldsFilled) {
            setErrors(prev => ({ ...prev, general: 'Please fill in all fields.' }));
            return;
        }

        if (!isValid) {
            setErrors(prev => ({ ...prev, general: 'Please fix the errors before submitting.' }));
            return;
        }

        setIsSubmitting(true);

        try {
            // Send all form data PLUS the OTP for final verification and user creation
            const payload = { ...formData, otp: enteredOtp };
            const response = await axios.post(`${config.API_URL}/users/admin`, payload);

            const { access_token, username: user, id, email: userEmail } = response.data;
            // Store token and user data in localStorage
            localStorage.setItem('token', access_token);
            localStorage.setItem('user', JSON.stringify({
                id,
                username: user,
                email: userEmail
            }));

            setShowOtpModal(false);
            if (onSuccess) {
                setShowSuccess(true);
                setTimeout(() => {
                    onSuccess();
                }, 2000);
            }

        } catch (error) {
            console.error('Signup error:', error);
            setShowOtpModal(false);
            let errorMessage = 'Signup failed. Please try again.';

            if (error.response?.data?.error) {
                errorMessage = error.response.data.error;
            } else if (error.response?.data?.message) {
                errorMessage = error.response.data.message;
            } else if (error.message) {
                errorMessage = error.message;
            }

            setErrors(prev => ({
                ...prev,
                general: errorMessage
            }));
        } finally {
            setShowOtpModal(false);
            setIsSubmitting(false);
        }
    };



    const handleResendOTP = async () => {

        // Clear previous errors
        setErrors(prev => ({ ...prev, general: undefined }));

        // Perform initial validation
        const isValid = validateAll();
        const allFieldsFilled = Object.values(formData).every(field => field.trim() !== '');

        if (!allFieldsFilled || !isValid) {
            setErrors(prev => ({ ...prev, general: 'Please fix the errors before proceeding.' }));
            return;
        }

        setIsSubmitting(true);
        try {
            // Ask the backend to send an OTP to the user's email
            await axios.post(`${config.API_URL}/users/resend-otp`, { email: formData.email });
            setShowOtpModal(true); 
        } catch (error) {
            console.error('OTP Request error:', error);
            const errorMessage = error.response?.data?.message || 'Failed to send OTP..';
            setErrors(prev => ({ ...prev, general: errorMessage }));
        } finally {
            setIsSubmitting(false);
        }
    }


    const handleSubmit = async (e) => {
        e.preventDefault();

        const newErrors = { ...errors };
        delete newErrors.general;
        setErrors(newErrors);

        const isValid = validateAll();
        const allFieldsFilled = Object.values(formData).every(field => field.trim() !== '');

        if (!allFieldsFilled) {
            setErrors(prev => ({ ...prev, general: 'Please fill in all fields.' }));
            return;
        }

        if (!isValid) {
            setErrors(prev => ({ ...prev, general: 'Please fix the errors before submitting.' }));
            return;
        }

        setIsSubmitting(true);

        try {
            const response = await fetch(`${config.API_URL}/admin/signup`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username: formData.username,
                    password: formData.password,
                }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || data.message || 'Admin signup failed');
            }

            const { access_token, username: adminUser, id } = data;

            // Store token and admin data in localStorage
            localStorage.setItem('token', access_token);
            localStorage.setItem('admin', JSON.stringify({
                id,
                username: adminUser,
                role: 'admin'
            }));

            setShowSuccess(true);
            setTimeout(() => {
                if (onSuccess) {
                    onSuccess();
                }
            }, 2000);
        } catch (error) {
            console.error('Admin signup error:', error);
            let errorMessage = 'Admin signup failed. Please try again.';

            if (error.message) {
                errorMessage = error.message;
            }

            setErrors(prev => ({
                ...prev,
                general: errorMessage
            }));
        } finally {
            setIsSubmitting(false);
        }
    };

    const getFieldIcon = (fieldName) => {
        const iconMap = {
            username: User,
            password: Lock,
            confirmPassword: Lock,
        };
        return iconMap[fieldName];
    };

    const fields = [
        { name: 'username', type: 'text', label: 'Admin Username', placeholder: 'Enter admin username' },
        { name: 'password', type: 'password', label: 'Password', placeholder: 'Create a strong password' },
        { name: 'confirmPassword', type: 'password', label: 'Confirm Password', placeholder: 'Confirm your password' },
    ];

    if (showSuccess) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center p-4">
                <div className="w-full max-w-md">
                    <div className="bg-white/10 backdrop-blur-xl rounded-3xl shadow-2xl border border-white/20 p-8 text-center space-y-6">
                        <div className="w-16 h-16 bg-gradient-to-r from-green-500 to-emerald-600 rounded-2xl flex items-center justify-center mx-auto">
                            <CheckCircle className="w-8 h-8 text-white" />
                        </div>
                        <h2 className="text-2xl font-bold text-white">Admin Account Created!</h2>
                        <p className="text-gray-300">Your admin account has been successfully created.</p>
                        <div className="animate-pulse text-sm text-gray-400">Redirecting you shortly...</div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center p-4">
            <div className="w-full max-w-md">
                <div className="bg-white/10 backdrop-blur-xl rounded-3xl shadow-2xl border border-white/20 p-8 space-y-6">
                    {/* Header */}
                    <div className="text-center space-y-2">
                        <div className="w-16 h-16 bg-gradient-to-r from-purple-500 to-pink-600 rounded-2xl flex items-center justify-center mx-auto mb-4 transform hover:scale-105 transition-transform duration-200">
                            <Shield className="w-8 h-8 text-white" />
                        </div>
                        <h1 className="text-2xl font-bold text-white">Create Admin Account</h1>
                        <p className="text-gray-300">Set up your administrator credentials</p>
                    </div>

                    {/* General Error */}
                    {errors.general && (
                        <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-3 flex items-start gap-2 animate-shake">
                            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                            <span className="text-red-200 text-sm">{errors.general}</span>
                        </div>
                    )}

                    <div className="space-y-5">
                        {fields.map(({ name, type, label, placeholder }) => {
                            const Icon = getFieldIcon(name);
                            const hasError = errors[name];
                            const hasValue = formData[name];
                            const isFocused = focusedField === name;

                            return (
                                <div key={name} className="space-y-1">
                                    <label
                                        htmlFor={name}
                                        className="block text-sm font-medium text-gray-200 mb-2"
                                    >
                                        {label}
                                    </label>
                                    <div className="relative">
                                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                            <Icon className={`w-5 h-5 transition-all duration-200 ${hasError ? 'text-red-400' :
                                                hasValue && !hasError ? 'text-green-400' :
                                                    isFocused ? 'text-purple-400' : 'text-gray-400'
                                                }`} />
                                        </div>
                                        <input
                                            type={
                                                name === 'password' ? (showPassword ? 'text' : 'password') :
                                                    name === 'confirmPassword' ? (showConfirmPassword ? 'text' : 'password') :
                                                        type
                                            }
                                            name={name}
                                            id={name}
                                            value={formData[name]}
                                            onChange={handleChange}
                                            onFocus={() => setFocusedField(name)}
                                            onBlur={() => setFocusedField('')}
                                            placeholder={placeholder}
                                            required
                                            disabled={isSubmitting}
                                            className={`w-full pl-10 pr-${(name === 'password' || name === 'confirmPassword') ? '12' : '4'} py-3 border rounded-xl bg-white/5 backdrop-blur-sm transition-all duration-200 text-white placeholder:text-gray-400 ${hasError ?
                                                'border-red-500/50 focus:border-red-500 focus:ring-red-500/20 shadow-red-500/10' :
                                                hasValue && !hasError ?
                                                    'border-green-500/50 focus:border-green-500 focus:ring-green-500/20 shadow-green-500/10' :
                                                    'border-white/20 focus:border-purple-500 focus:ring-purple-500/20'
                                                } focus:ring-4 focus:ring-opacity-20 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed shadow-sm hover:shadow-md`}
                                        />

                                        {/* Password toggle buttons */}
                                        {name === 'password' && (
                                            <button
                                                type="button"
                                                onClick={() => setShowPassword(!showPassword)}
                                                className="absolute inset-y-0 right-0 pr-3 flex items-center hover:bg-white/5 rounded-r-xl transition-colors duration-200"
                                                disabled={isSubmitting}
                                            >
                                                {showPassword ?
                                                    <EyeOff className="w-5 h-5 text-gray-400 hover:text-gray-300" /> :
                                                    <Eye className="w-5 h-5 text-gray-400 hover:text-gray-300" />
                                                }
                                            </button>
                                        )}

                                        {name === 'confirmPassword' && (
                                            <button
                                                type="button"
                                                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                                className="absolute inset-y-0 right-0 pr-3 flex items-center hover:bg-white/5 rounded-r-xl transition-colors duration-200"
                                                disabled={isSubmitting}
                                            >
                                                {showConfirmPassword ?
                                                    <EyeOff className="w-5 h-5 text-gray-400 hover:text-gray-300" /> :
                                                    <Eye className="w-5 h-5 text-gray-400 hover:text-gray-300" />
                                                }
                                            </button>
                                        )}

                                        {/* Success indicator */}
                                        {hasValue && !hasError && name === 'username' && (
                                            <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                                                <CheckCircle className="w-5 h-5 text-green-400 animate-pulse" />
                                            </div>
                                        )}
                                    </div>

                                    {/* Error message */}
                                    {hasError && (
                                        <div className="flex items-start gap-1 mt-1 animate-fadeIn">
                                            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                                            <span className="text-red-300 text-xs">{hasError}</span>
                                        </div>
                                    )}
                                </div>
                            );
                        })}

                        <div className="flex gap-3 pt-4">
                            <button
                                onClick={handleRequestOtp}
                                disabled={isSubmitting}
                                className="flex-1 bg-gradient-to-r from-purple-500 to-pink-600 hover:from-purple-600 hover:to-pink-700 text-white font-semibold py-3 px-6 rounded-xl transition-all duration-200 transform hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none shadow-lg hover:shadow-xl flex items-center justify-center gap-2"
                            >
                                {isSubmitting ? (
                                    <>
                                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                                        Creating...
                                    </>
                                ) : (
                                    'Create Admin Account'
                                )}
                            </button>

                            <button
                                type="button"
                                onClick={() => {
                                    setFormData({
                                        username: '',
                                        password: '',
                                        confirmPassword: '',
                                    });
                                    setErrors({});
                                }}
                                disabled={isSubmitting}
                                className="px-6 py-3 border border-white/20 text-gray-200 font-semibold rounded-xl hover:bg-white/5 transition-all duration-200 transform hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
                            >
                                Clear
                            </button>
                        </div>
                    </div>

                    {/* Footer */}
                    <div className="text-center text-sm text-gray-300">
                        Already have an admin account?
                        <button
                            className="text-purple-400 hover:text-purple-300 font-semibold ml-1 hover:underline transition-colors duration-200"
                            onClick={onNavigateToLogin}
                        >
                            Sign In
                        </button>
                    </div>
                </div>
            </div>
            <OtpVerificationModal
                isOpen={showOtpModal}
                onClose={() => setShowOtpModal(false)}
                onVerify={handleFinalSubmit}
                email={"marichufx@gmail.com"}
                resendOtp={handleResendOTP}
            />


            {/* CSS Animations */}
            <style>{`
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
          20%, 40%, 60%, 80% { transform: translateX(5px); }
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(-10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-shake {
          animation: shake 0.5s ease-in-out;
        }
        .animate-fadeIn {
          animation: fadeIn 0.3s ease-out;
        }
      `}</style>
        </div>
    );
};

export default AdminSignUpForm;