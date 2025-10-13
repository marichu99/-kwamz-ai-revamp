import React, { useState, useEffect } from 'react';

function Checkout() {
    const [selectedMethod, setSelectedMethod] = useState('mpesa');
    const [cardNumber, setCardNumber] = useState('');
    const [expiryDate, setExpiryDate] = useState('');

    // Handle payment method selection
    const handleMethodClick = (method) => {
        setSelectedMethod(method);
    };

    // Handle card number input with masking
    const handleCardNumberChange = (e) => {
        let value = e.target.value.replace(/\s/g, '');
        let cardValue = cardNumber.replace(/\s/g, '');

        if (value.length > cardValue.length) {
            cardValue = value;
        } else {
            cardValue = cardValue.slice(0, value.length);
        }

        let displayValue = '';
        for (let i = 0; i < cardValue.length; i++) {
            if (i > 3 && i < 12) {
                displayValue += '•';
            } else {
                displayValue += cardValue[i];
            }
            if ((i + 1) % 4 === 0 && i < 15) {
                displayValue += ' ';
            }
        }

        setCardNumber(displayValue);
    };

    // Handle expiry date formatting
    const handleExpiryChange = (e) => {
        let value = e.target.value.replace(/\D/g, '');
        if (value.length >= 2) {
            value = value.slice(0, 2) + '/' + value.slice(2, 4);
        }
        setExpiryDate(value);
    };

    // Handle form submissions
    const handleMpesaSubmit = (e) => {
        e.preventDefault();
        alert('M-Pesa payment initiated! You will receive a prompt on your phone to complete the payment.');
    };

    const handleBankSubmit = (e) => {
        e.preventDefault();
        alert('Card payment processing! You will be redirected to complete the secure payment.');
    };

    return (
        <div className="min-h-screen flex items-center justify-center p-5 bg-gradient-to-br from-indigo-500 to-purple-600">
            <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full overflow-hidden animate-slideUp">
                <div className="p-10">
                    <h2 className="text-2xl font-semibold text-gray-800 mb-2">Payment Method</h2>
                    <p className="text-gray-600 mb-8">Select your preferred payment method</p>

                    <div className="flex gap-4 mb-8 flex-col sm:flex-row">
                        <div
                            className={`flex-1 p-5 border-2 border-gray-200 rounded-xl cursor-pointer transition-all text-center hover:border-indigo-500 hover:shadow-md hover:-translate-y-0.5 ${selectedMethod === 'mpesa' ? 'border-indigo-500 bg-gradient-to-br from-indigo-100/30 to-purple-100/30' : ''
                                }`}
                            onClick={() => handleMethodClick('mpesa')}
                        >
                            <div className="text-3xl mb-2">📱</div>
                            <div className="font-semibold text-gray-800">M-Pesa</div>
                        </div>
                        <div
                            className={`flex-1 p-5 border-2 border-gray-200 rounded-xl cursor-pointer transition-all text-center hover:border-indigo-500 hover:shadow-md hover:-translate-y-0.5 ${selectedMethod === 'bank' ? 'border-indigo-500 bg-gradient-to-br from-indigo-100/30 to-purple-100/30' : ''
                                }`}
                            onClick={() => handleMethodClick('bank')}
                        >
                            <div className="text-3xl mb-2">💳</div>
                            <div className="font-semibold text-gray-800">Card Payment</div>
                        </div>
                    </div>

                    <div className={`transition-opacity duration-300 ${selectedMethod === 'mpesa' ? 'block' : 'hidden'}`}>
                        <form onSubmit={handleMpesaSubmit}>
                            <div className="mb-5">
                                <label htmlFor="mpesa-phone" className="block mb-2 text-sm font-medium text-gray-800">
                                    M-Pesa Phone Number
                                </label>
                                <input
                                    type="tel"
                                    id="mpesa-phone"
                                    placeholder="0700 000 000"
                                    required
                                    className="w-full p-3 border-2 border-gray-200 rounded-lg text-sm focus:outline-none focus:border-indigo-500 transition-colors"
                                />
                            </div>
                            <div className="mb-5">
                                <label htmlFor="mpesa-name" className="block mb-2 text-sm font-medium text-gray-800">
                                    Full Name
                                </label>
                                <input
                                    type="text"
                                    id="mpesa-name"
                                    placeholder="John Doe"
                                    required
                                    className="w-full p-3 border-2 border-gray-200 rounded-lg text-sm focus:outline-none focus:border-indigo-500 transition-colors"
                                />
                            </div>
                            <button
                                type="submit"
                                className="w-full p-4 bg-gradient-to-br from-indigo-500 to-purple-600 text-white rounded-lg font-semibold text-sm hover:shadow-lg hover:-translate-y-0.5 transition-all active:translate-y-0"
                            >
                                Pay with M-Pesa
                            </button>
                            <div className="flex items-center justify-center gap-2 text-gray-600 text-xs mt-4">
                                <span>🔒</span>
                                <span>Secure payment powered by M-Pesa</span>
                            </div>
                        </form>
                    </div>
                    <div className={`transition-opacity duration-300 ${selectedMethod === 'bank' ? 'block' : 'hidden'}`}>
                        <form onSubmit={handleBankSubmit}>
                            <div className="mb-5">
                                <label htmlFor="card-number" className="block mb-2 text-sm font-medium text-gray-800">
                                    Card Number
                                </label>
                                <input
                                    type="text"
                                    id="card-number"
                                    placeholder="1234 5678 9012 3456"
                                    maxLength="19"
                                    value={cardNumber}
                                    onChange={handleCardNumberChange}
                                    required
                                    className="w-full p-3 border-2 border-gray-200 rounded-lg text-sm focus:outline-none focus:border-indigo-500 transition-colors"
                                />
                            </div>
                            <div className="mb-5">
                                <label htmlFor="card-name" className="block mb-2 text-sm font-medium text-gray-800">
                                    Cardholder Name
                                </label>
                                <input
                                    type="text"
                                    id="card-name"
                                    placeholder="John Doe"
                                    required
                                    className="w-full p-3 border-2 border-gray-200 rounded-lg text-sm focus:outline-none focus:border-indigo-500 transition-colors"
                                />
                            </div>
                            <div className="flex gap-4">
                                <div className="flex-2">
                                    <label htmlFor="expiry-date" className="block mb-2 text-sm font-medium text-gray-800">
                                        Expiry Date
                                    </label>
                                    <input
                                        type="text"
                                        id="expiry-date"
                                        placeholder="MM/YY"
                                        maxLength="5"
                                        value={expiryDate}
                                        onChange={handleExpiryChange}
                                        required
                                        className="w-full p-3 border-2 border-gray-200 rounded-lg text-sm focus:outline-none focus:border-indigo-500 transition-colors"
                                    />
                                </div>
                                <div className="flex-1">
                                    <label htmlFor="cvv" className="block mb-2 text-sm font-medium text-gray-800">
                                        CVV
                                    </label>
                                    <input
                                        type="password"
                                        id="cvv"
                                        placeholder="•••"
                                        maxLength="3"
                                        required
                                        className="w-full p-3 border-2 border-gray-200 rounded-lg text-sm focus:outline-none focus:border-indigo-500 transition-colors"
                                    />
                                </div>
                            </div>
                            <button
                                type="submit"
                                className="w-full p-6 bg-gradient-to-br from-indigo-500 to-purple-600 text-white rounded-lg font-semibold text-sm hover:shadow-lg hover:-translate-y-0.5 transition-all active:translate-y-0 m-2"
                            >
                                Proceed to Pay
                            </button>
                            <div className="flex items-center justify-center gap-2 text-gray-600 text-xs mt-4">
                                <span>🔒</span>
                                <span>Your card details are encrypted & secure</span>
                            </div>
                        </form>
                    </div>  
                </div>
            </div>
        </div>
    );
}

export default Checkout;

<style jsx>{`
  @keyframes slideUp {
    from {
      opacity: 0;
      transform: translateY(30px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .animate-slideUp {
    animation: slideUp 0.5s ease;
  }
`}</style>