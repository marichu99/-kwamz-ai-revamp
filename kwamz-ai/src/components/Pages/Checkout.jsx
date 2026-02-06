import React, { useState, useEffect } from 'react';
import { CreditCard, AlertCircle, Loader2, X, Store, Clock, CheckCircle } from 'lucide-react';
import config from '../../Config';
import { useToast } from './ToastProvider';
import { useNavigate } from 'react-router-dom';

const API_BASE_URL = config.API_URL || 'http://localhost:5000';

function Checkout() {
  const [loading, setLoading] = useState(true);
  const [paying, setPaying] = useState(false);
  const [error, setError] = useState(null);
  const [billingSummary, setBillingSummary] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [iframeUrl, setIframeUrl] = useState('');
  const { showToast } = useToast();
  const navigate = useNavigate();

  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const token = localStorage.getItem('token');

  useEffect(() => {
    fetchBillingSummary();
  }, []);

  const fetchBillingSummary = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/payment/billing-summary`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      if (!response.ok) throw new Error('Failed to fetch billing summary');
      const data = await response.json();
      setBillingSummary(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handlePayment = async () => {
    setPaying(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/payment/create`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          currency: 'KES',
          description: `Monthly subscription - ${billingSummary?.active_tills_count || 0} active tills`,
          customer_email: user?.email || '',
          customer_phone: user?.phone_number || '',
          customer_first_name: user?.username || '',
          customer_last_name: user?.username || '',
        }),
      });

      const data = await response.json();

      if (data.success && data.redirect_url) {
        setIframeUrl(data.redirect_url);
        setModalOpen(true);
        startPolling(data.order_id);
      } else {
        setError(data.error || 'Failed to initiate payment');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setPaying(false);
    }
  };

  let pollCount = 0;
  const startPolling = (orderId) => {
    const interval = setInterval(async () => {
      pollCount++;
      try {
        const res = await fetch(`${API_BASE_URL}/payment/callback`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ order_id: orderId }),
        });
        const data = await res.json();
        const status = data?.payment?.payment_status;

        if (status === 'COMPLETED') {
          clearInterval(interval);
          showToast('Payment completed successfully!', 'success');
          setModalOpen(false);
          setIframeUrl('');
          navigate('/dashboard');
        } else if (status === 'FAILED') {
          clearInterval(interval);
          showToast('Payment failed. Please try again.', 'error');
          setModalOpen(false);
          setIframeUrl('');
        }

        if (pollCount >= 100) {
          clearInterval(interval);
          showToast('Payment confirmation timed out. Please check later.', 'error');
        }
      } catch (err) {
        console.warn('Polling error:', err);
      }
    }, 6000);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-10 h-10 animate-spin text-blue-600 mx-auto mb-3" />
          <p className="text-slate-600">Loading billing information...</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 p-4 sm:p-6 flex items-center justify-center">
        <div className="w-full max-w-2xl space-y-6">
          {/* Header */}
          <div className="text-center">
            <h1 className="text-3xl font-bold text-slate-800">Subscription Payment</h1>
            <p className="text-slate-600 mt-2">
              {billingSummary?.is_trial
                ? `Your free trial ends on ${billingSummary.trial_end_date}. You can pay early or wait until it expires.`
                : 'Your free trial has ended. Pay to continue using the platform.'}
            </p>
          </div>

          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {/* Billing Summary Card */}
          <div className="bg-white rounded-xl shadow-lg overflow-hidden">
            <div className="p-6 border-b border-slate-100">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <CreditCard className="w-5 h-5 text-blue-600" />
                </div>
                <h2 className="text-xl font-semibold text-slate-800">Billing Summary</h2>
              </div>

              {billingSummary?.is_trial && (
                <div className="p-3 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2">
                  <Clock className="w-5 h-5 text-green-600" />
                  <span className="text-sm text-green-700">
                    Free trial active - {billingSummary.trial_days_remaining} days remaining
                  </span>
                </div>
              )}
            </div>

            {/* Active Tills */}
            <div className="p-6 border-b border-slate-100">
              <h3 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-3">
                Active Tills ({billingSummary?.active_tills_count || 0})
              </h3>
              {billingSummary?.active_tills?.length > 0 ? (
                <div className="space-y-2">
                  {billingSummary.active_tills.map((till) => (
                    <div
                      key={till.id}
                      className="flex items-center justify-between p-3 bg-slate-50 rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <Store className="w-4 h-4 text-slate-400" />
                        <div>
                          <p className="text-sm font-medium text-slate-700">{till.company_name}</p>
                          <p className="text-xs text-slate-500">
                            Agent: {till.agent_number || '-'} | Store: {till.store_number || '-'}
                            {till.till_number ? ` | Till: ${till.till_number}` : ''}
                          </p>
                        </div>
                      </div>
                      <span className="text-sm font-medium text-slate-700">
                        KES {(billingSummary?.rate_per_till || 200).toFixed(2)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-500 italic">
                  No active tills found. Add tills from the dashboard to start your subscription.
                </p>
              )}
            </div>

            {/* Total */}
            <div className="p-6 bg-slate-50">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-slate-600">
                  {billingSummary?.active_tills_count || 0} tills x KES{' '}
                  {(billingSummary?.rate_per_till || 200).toFixed(2)}/month
                </span>
                <span className="text-sm text-slate-600">
                  KES {(billingSummary?.total_amount_due || 0).toFixed(2)}
                </span>
              </div>
              <div className="flex items-center justify-between pt-3 border-t border-slate-200">
                <span className="text-lg font-bold text-slate-800">Total Due</span>
                <span className="text-2xl font-bold text-blue-600">
                  KES {(billingSummary?.total_amount_due || 0).toFixed(2)}
                </span>
              </div>
            </div>

            {/* Pay Button */}
            <div className="p-6">
              <button
                onClick={handlePayment}
                disabled={paying || (billingSummary?.total_amount_due || 0) <= 0}
                className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold py-3.5 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-lg hover:shadow-xl"
              >
                {paying ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <CreditCard className="w-5 h-5" />
                    Pay KES {(billingSummary?.total_amount_due || 0).toFixed(2)}
                  </>
                )}
              </button>
              <p className="text-xs text-center text-gray-500 mt-3">
                Your payment is secured by Pesapal
              </p>
            </div>
          </div>

          {/* Payment History */}
          {billingSummary?.payment_history?.length > 0 && (
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h3 className="text-lg font-semibold text-slate-800 mb-4">Recent Payments</h3>
              <div className="space-y-3">
                {billingSummary.payment_history.map((sub) => (
                  <div
                    key={sub.id}
                    className="flex items-center justify-between p-3 border border-slate-100 rounded-lg"
                  >
                    <div>
                      <p className="text-sm font-medium text-slate-700">
                        {sub.billing_period_start} to {sub.billing_period_end}
                      </p>
                      <p className="text-xs text-slate-500">{sub.active_tills_count} tills</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium text-slate-700">
                        KES {(sub.amount_due || 0).toFixed(2)}
                      </span>
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                          sub.status === 'PAID'
                            ? 'bg-green-100 text-green-700'
                            : 'bg-yellow-100 text-yellow-700'
                        }`}
                      >
                        {sub.status === 'PAID' ? (
                          <CheckCircle className="w-3 h-3" />
                        ) : (
                          <Clock className="w-3 h-3" />
                        )}
                        {sub.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Back to dashboard link (only if in trial) */}
          {billingSummary?.is_trial && (
            <div className="text-center">
              <button
                onClick={() => navigate('/dashboard')}
                className="text-sm text-blue-600 hover:text-blue-700 underline"
              >
                Continue with free trial
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Pesapal Payment Modal */}
      {modalOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
            <div className="flex justify-between items-center p-4 border-b bg-gray-50">
              <h3 className="text-lg font-semibold text-gray-800">Complete Payment</h3>
              <button
                onClick={() => {
                  setModalOpen(false);
                  setIframeUrl('');
                }}
                className="text-gray-500 hover:text-gray-700"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
            <div className="h-96 md:h-[600px]">
              <iframe
                src={iframeUrl}
                title="Pesapal Payment"
                className="w-full h-full border-0"
                allow="payment"
                sandbox="allow-scripts allow-same-origin allow-forms allow-modals allow-popups"
              />
            </div>
            <div className="p-4 border-t bg-gray-50 text-center">
              <button
                onClick={() => {
                  setModalOpen(false);
                  setIframeUrl('');
                }}
                className="px-6 py-2 bg-red-600 hover:bg-red-700 text-white font-medium rounded-lg transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default Checkout;
