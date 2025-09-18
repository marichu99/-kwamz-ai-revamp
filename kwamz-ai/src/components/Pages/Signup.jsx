import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import config from '../../Config';
import { Eye, EyeOff, User, Mail, Phone, Calendar, Lock, CheckCircle, AlertCircle } from 'lucide-react';
import OtpVerificationModal from './OtpVerificationModal';

const SignUpForm = ({ onSuccess }) => {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    phoneNumber: '',
    dateOfBirth: '',
    password: '',
    confirmPassword: '',
  });
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showOtpModal, setShowOtpModal] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [focusedField, setFocusedField] = useState('');
  const [showSuccess, setShowSuccess] = useState(false);
  const navigate = useNavigate();

  const validate = (name, value) => {
    const newErrors = { ...errors };

    if (name === 'username') {
      newErrors.username = value.length < 3 ? 'Username must be at least 3 characters' : '';
    }

    if (name === 'email') {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      newErrors.email = !emailRegex.test(value) && value.length > 0 ? 'Invalid email address' : '';
    }

    if (name === 'phoneNumber') {
      const phoneRegex = /^\d{9,14}$/;
      newErrors.phoneNumber = !phoneRegex.test(value) && value.length > 0
        ? 'Phone number must be between 9 and 14 digits.'
        : '';
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

    if (name === 'dateOfBirth') {
      if (value) {
        const today = new Date();
        const dob = new Date(value);
        const age = today.getFullYear() - dob.getFullYear();
        const monthDiff = today.getMonth() - dob.getMonth();
        const dayDiff = today.getDate() - dob.getDate();

        const isOldEnough =
          age > 18 ||
          (age === 18 && (monthDiff > 0 || (monthDiff === 0 && dayDiff >= 0)));

        newErrors.dateOfBirth = !isOldEnough ? 'You must be at least 18 years old.' : '';
      } else {
        newErrors.dateOfBirth = '';
      }
    }

    setErrors(newErrors);
  };

  const validateAll = () => {
    const newErrors = {};

    if (formData.username.length < 3) {
      newErrors.username = 'Username must be at least 3 characters';
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(formData.email)) {
      newErrors.email = 'Invalid email address';
    }

    const phoneRegex = /^\d{9,14}$/;
    if (!phoneRegex.test(formData.phoneNumber)) {
      newErrors.phoneNumber = 'Phone number must be between 9 and 14 digits.';
    }

    const passwordRegex = /^(?=.*[0-9])(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{8,}$/;
    if (!passwordRegex.test(formData.password)) {
      newErrors.password = 'Password must be at least 8 characters, include a number and a special character.';
    }

    if (formData.confirmPassword !== formData.password) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    if (formData.dateOfBirth) {
      const today = new Date();
      const dob = new Date(formData.dateOfBirth);
      const age = today.getFullYear() - dob.getFullYear();
      const monthDiff = today.getMonth() - dob.getMonth();
      const dayDiff = today.getDate() - dob.getDate();

      const isOldEnough =
        age > 18 ||
        (age === 18 && (monthDiff > 0 || (monthDiff === 0 && dayDiff >= 0)));

      if (!isOldEnough) {
        newErrors.dateOfBirth = 'You must be at least 18 years old.';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    validate(name, value);
  };

  const handleResendOTP = async () =>{
    
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
      setShowOtpModal(true); // Open the modal on success
    } catch (error) {
      console.error('OTP Request error:', error);
      const errorMessage = error.response?.data?.message || 'Failed to send OTP..';
      setErrors(prev => ({ ...prev, general: errorMessage }));
    } finally {
      setIsSubmitting(false);
    }
  }

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
      await axios.post(`${config.API_URL}/users/request-otp`, { email: formData.email });
      setShowOtpModal(true); // Open the modal on success
    } catch (error) {
      console.error('OTP Request error:', error);
      const errorMessage = error.response?.data?.message || 'Failed to send OTP..';
      setErrors(prev => ({ ...prev, general: errorMessage }));
    } finally {
      setIsSubmitting(false);
    }
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
      const response = await axios.post(`${config.API_URL}/users/`, payload);
      
      const { access_token, username: user, id, email: userEmail, phone_number, date_of_birth } = response.data;
      // Store token and user data in localStorage
      localStorage.setItem('token', access_token);
      localStorage.setItem('user', JSON.stringify({
        id,
        username: user,
        email: userEmail,
        phone_number,
        date_of_birth
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
      setIsSubmitting(false);
    }
  };

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
      const response = await axios.post(`${config.API_URL}/users/`, formData);
      const { access_token, username: user, id, email: userEmail, phone_number, date_of_birth } = response.data;

      // Store token and user data in localStorage
      localStorage.setItem('token', access_token);
      localStorage.setItem('user', JSON.stringify({
        id,
        username: user,
        email: userEmail,
        phone_number,
        date_of_birth
      }));

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
      setIsSubmitting(false);
    }
  };

  const getFieldIcon = (fieldName) => {
    const iconMap = {
      username: User,
      email: Mail,
      phoneNumber: Phone,
      dateOfBirth: Calendar,
      password: Lock,
      confirmPassword: Lock,
    };
    return iconMap[fieldName];
  };

  const fields = [
    { name: 'username', type: 'text', label: 'Username', placeholder: 'Enter your username' },
    { name: 'email', type: 'email', label: 'Email', placeholder: 'your.email@example.com' },
    { name: 'phoneNumber', type: 'tel', label: 'Phone Number', placeholder: '+1234567890' },
    { name: 'dateOfBirth', type: 'date', label: 'Date of Birth', placeholder: '' },
    { name: 'password', type: 'password', label: 'Password', placeholder: 'Create a strong password' },
    { name: 'confirmPassword', type: 'password', label: 'Confirm Password', placeholder: 'Confirm your password' },
  ];

  if (showSuccess) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-cyan-50 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="bg-white/80 backdrop-blur-xl rounded-3xl shadow-2xl border border-white/20 p-8 text-center space-y-6">
            <div className="w-16 h-16 bg-gradient-to-r from-green-500 to-emerald-600 rounded-2xl flex items-center justify-center mx-auto">
              <CheckCircle className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900">Account Created!</h2>
            <p className="text-gray-600">Welcome aboard! Your account has been successfully created.</p>
            <div className="animate-pulse text-sm text-gray-500">Redirecting you shortly...</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-cyan-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-white/80 backdrop-blur-xl rounded-3xl shadow-2xl border border-white/20 p-8 space-y-6">
          {/* Header */}
          <div className="text-center space-y-2">
            <div className="w-16 h-16 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-4 transform hover:scale-105 transition-transform duration-200">
              <User className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900">Create Account</h1>
            <p className="text-gray-600">Join us and start your journey</p>
          </div>

          {/* General Error */}
          {errors.general && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-start gap-2 animate-shake">
              <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <span className="text-red-700 text-sm">{errors.general}</span>
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
                    className="block text-sm font-medium text-gray-700 mb-2"
                  >
                    {label}
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <Icon className={`w-5 h-5 transition-all duration-200 ${hasError ? 'text-red-400' :
                        hasValue && !hasError ? 'text-green-500' :
                          isFocused ? 'text-indigo-500' : 'text-gray-400'
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
                      className={`w-full pl-10 pr-${(name === 'password' || name === 'confirmPassword') ? '12' : '4'} py-3 border rounded-xl bg-white/50 backdrop-blur-sm transition-all duration-200 ${hasError ?
                        'border-red-300 focus:border-red-500 focus:ring-red-200 shadow-red-100' :
                        hasValue && !hasError ?
                          'border-green-300 focus:border-green-500 focus:ring-green-200 shadow-green-100' :
                          'border-gray-200 focus:border-indigo-500 focus:ring-indigo-200'
                        } focus:ring-4 focus:ring-opacity-20 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed placeholder:text-gray-400 shadow-sm hover:shadow-md`}
                    />

                    {/* Password toggle buttons */}
                    {name === 'password' && (
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute inset-y-0 right-0 pr-3 flex items-center hover:bg-gray-50 rounded-r-xl transition-colors duration-200"
                        disabled={isSubmitting}
                      >
                        {showPassword ?
                          <EyeOff className="w-5 h-5 text-gray-400 hover:text-gray-600" /> :
                          <Eye className="w-5 h-5 text-gray-400 hover:text-gray-600" />
                        }
                      </button>
                    )}

                    {name === 'confirmPassword' && (
                      <button
                        type="button"
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                        className="absolute inset-y-0 right-0 pr-3 flex items-center hover:bg-gray-50 rounded-r-xl transition-colors duration-200"
                        disabled={isSubmitting}
                      >
                        {showConfirmPassword ?
                          <EyeOff className="w-5 h-5 text-gray-400 hover:text-gray-600" /> :
                          <Eye className="w-5 h-5 text-gray-400 hover:text-gray-600" />
                        }
                      </button>
                    )}

                    {/* Success indicator */}
                    {hasValue && !hasError && (name !== 'password' && name !== 'confirmPassword') && (
                      <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                        <CheckCircle className="w-5 h-5 text-green-500 animate-pulse" />
                      </div>
                    )}
                  </div>

                  {/* Error message */}
                  {hasError && (
                    <div className="flex items-start gap-1 mt-1 animate-fadeIn">
                      <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                      <span className="text-red-600 text-xs">{hasError}</span>
                    </div>
                  )}
                </div>
              );
            })}

            <div className="flex gap-3 pt-4">
              <button
                onClick={handleRequestOtp}
                disabled={isSubmitting}
                className="flex-1 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white font-semibold py-3 px-6 rounded-xl transition-all duration-200 transform hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none shadow-lg hover:shadow-xl flex items-center justify-center gap-2"
              >
                {isSubmitting ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    Signing Up...
                  </>
                ) : (
                  'Create Account'
                )}
              </button>

              <button
                type="button"
                onClick={() => {
                  setFormData({
                    username: '',
                    email: '',
                    phoneNumber: '',
                    dateOfBirth: '',
                    password: '',
                    confirmPassword: '',
                  });
                  setErrors({});
                }}
                disabled={isSubmitting}
                className="px-6 py-3 border border-gray-200 text-gray-700 font-semibold rounded-xl hover:bg-gray-50 transition-all duration-200 transform hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
              >
                Cancel
              </button>
            </div>
          </div>

          {/* Footer */}
          <div className="text-center text-sm text-gray-600">
            Already have an account?
            <button className="text-indigo-600 hover:text-indigo-700 font-semibold ml-1 hover:underline transition-colors duration-200" onClick={() => navigate('/')}>
              Sign In
            </button>
          </div>
        </div>
      </div>
      <OtpVerificationModal
        isOpen={showOtpModal}
        onClose={() => setShowOtpModal(false)}
        onVerify={handleFinalSubmit}
        email={formData.email}
        resendOtp={handleResendOTP} 
      />
    </div>
  );
};

export default SignUpForm;