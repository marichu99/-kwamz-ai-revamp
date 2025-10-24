import React, { useState } from 'react';

const MpesaModal = ({ onSucess }) => {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [isFocused, setIsFocused] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');

    if (!phoneNumber) {
      setError('Phone number is required');
      return;
    }

    function sanitizePhoneNumber(phoneNumber) {
      if (phoneNumber.startsWith('0')) {
        return '254' + phoneNumber.substring(1);
      } else if (phoneNumber.startsWith('+')) {
        return phoneNumber.substring(1);
      } else if (!phoneNumber.startsWith('254')) {
        return '254' + phoneNumber;
      }
      return phoneNumber;
    }

    const sanitizedPhoneNumber = sanitizePhoneNumber(phoneNumber);

    function validatePhoneNumber(phone) {
      return /^\d{10,}$/.test(phone);
    }

    if (!validatePhoneNumber(sanitizedPhoneNumber)) {
      setError('Invalid phone number format');
      return;
    }

    setLoading(true);
    // Simulate API call
    // setTimeout(() => {
    //   setLoading(false);
    //   onSubmit({ success: true, message: 'STK Push sent successfully!', phoneNumber: sanitizedPhoneNumber });
    // }, 2000);
  };

  const styles = {
    overlay: {
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.6)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      backdropFilter: 'blur(4px)',
      animation: 'fadeIn 0.3s ease-out'
    },
    modal: {
      backgroundColor: '#ffffff',
      borderRadius: '20px',
      padding: '40px',
      maxWidth: '450px',
      width: '90%',
      boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
      position: 'relative',
      animation: 'slideUp 0.3s ease-out'
    },
    header: {
      textAlign: 'center',
      marginBottom: '30px'
    },
    logo: {
      width: '80px',
      height: '80px',
      margin: '0 auto 20px',
      background: 'linear-gradient(135deg, #00d13f 0%, #00a832 100%)',
      borderRadius: '50%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: '40px',
      color: 'white',
      fontWeight: 'bold',
      boxShadow: '0 8px 20px rgba(0, 209, 63, 0.3)'
    },
    title: {
      fontSize: '24px',
      fontWeight: '700',
      color: '#1a1a1a',
      margin: '0 0 8px 0'
    },
    subtitle: {
      fontSize: '14px',
      color: '#666',
      margin: 0
    },
    formGroup: {
      marginBottom: '24px'
    },
    label: {
      display: 'block',
      fontSize: '14px',
      fontWeight: '600',
      color: '#333',
      marginBottom: '8px',
      paddingLeft: '4px'
    },
    input: {
      width: '100%',
      padding: '14px 16px',
      fontSize: '16px',
      border: '2px solid #e0e0e0',
      borderRadius: '12px',
      outline: 'none',
      transition: 'all 0.3s ease',
      fontFamily: 'inherit',
      boxSizing: 'border-box'
    },
    inputFocus: {
      border: '2px solid #00d13f',
      boxShadow: '0 0 0 4px rgba(0, 209, 63, 0.1)'
    },
    error: {
      backgroundColor: '#fee',
      color: '#c33',
      padding: '12px 16px',
      borderRadius: '10px',
      marginBottom: '20px',
      fontSize: '14px',
      border: '1px solid #fcc',
      display: 'flex',
      alignItems: 'center',
      gap: '8px'
    },
    buttonGroup: {
      display: 'flex',
      gap: '12px',
      marginTop: '30px'
    },
    submitButton: {
      width: '100%',
      padding: '14px 24px',
      fontSize: '16px',
      fontWeight: '600',
      color: 'white',
      background: 'linear-gradient(135deg, #00d13f 0%, #00a832 100%)',
      border: 'none',
      borderRadius: '12px',
      cursor: 'pointer',
      transition: 'all 0.3s ease',
      boxShadow: '0 4px 12px rgba(0, 209, 63, 0.3)'
    },
    spinnerOverlay: {
      position: 'absolute',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      borderRadius: '20px',
      zIndex: 10
    },
    spinner: {
      width: '50px',
      height: '50px',
      border: '4px solid #e0e0e0',
      borderTop: '4px solid #00d13f',
      borderRadius: '50%',
      animation: 'spin 1s linear infinite'
    },
    loadingText: {
      marginTop: '16px',
      color: '#00a832',
      fontSize: '16px',
      fontWeight: '600'
    }
  };

  return (
    <>
      <style>
        {`
          @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
          }
          @keyframes slideUp {
            from { 
              opacity: 0;
              transform: translateY(20px);
            }
            to { 
              opacity: 1;
              transform: translateY(0);
            }
          }
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
          button:hover {
            transform: translateY(-2px);
          }
          button:active {
            transform: translateY(0);
          }
        `}
      </style>
      <div style={styles.overlay}>
        <div style={styles.modal}>
          <div style={styles.header}>
            <div style={styles.logo}>M</div>
            <h3 style={styles.title}>M-Pesa Payment</h3>
            <p style={styles.subtitle}>Enter your phone number to complete payment</p>
          </div>

          {error && (
            <div style={styles.error}>
              <span>⚠️</span>
              <span>{error}</span>
            </div>
          )}

          {loading && (
            <div style={styles.spinnerOverlay}>
              <div style={styles.spinner}></div>
              <div style={styles.loadingText}>Processing payment...</div>
            </div>
          )}

          <div>
            <div style={styles.formGroup}>
              <label style={styles.label}>Phone Number</label>
              <input
                type="text"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                onFocus={() => setIsFocused(true)}
                onBlur={() => setIsFocused(false)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleSubmit(e);
                  }
                }}
                placeholder="e.g., 0712345678 or +254712345678"
                style={{
                  ...styles.input,
                  ...(isFocused ? styles.inputFocus : {})
                }}
              />
            </div>

            <div style={styles.buttonGroup}>
              <button 
                onClick={handleSubmit}
                style={styles.submitButton}
                disabled={loading}
              >
                {loading ? 'Processing...' : 'Send STK Push'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default MpesaModal;