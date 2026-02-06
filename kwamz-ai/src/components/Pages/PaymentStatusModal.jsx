import React, { useState, useEffect } from 'react';
import { X, CreditCard, Store, Clock, CheckCircle, AlertCircle, Loader2, User } from 'lucide-react';
import config from '../../Config';
import { useToast } from './ToastProvider';

const API_BASE_URL = config.API_URL || 'http://localhost:5000';

function PaymentStatusModal({ isOpen, onClose, user }) {
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [billingData, setBillingData] = useState(null);
  const [error, setError] = useState(null);
  const { showToast } = useToast();
  const token = localStorage.getItem('token');

  useEffect(() => {
    if (isOpen && user) {
      fetchBillingStatus();
    }
  }, [isOpen, user]);

  const fetchBillingStatus = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE_URL}/payment/admin/billing-status/${user.id}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!response.ok) throw new Error('Failed to fetch billing status');
      const data = await response.json();
      setBillingData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateStatus = async (newStatus) => {
    setUpdating(true);
    try {
      const response = await fetch(
        `${API_BASE_URL}/payment/admin/update-status/${user.id}`,
        {
          method: 'PATCH',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ status: newStatus }),
        }
      );

      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Failed to update status');

      showToast(`Payment status updated to ${newStatus}`, 'success');
      fetchBillingStatus();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setUpdating(false);
    }
  };

  if (!isOpen) return null;

  const billing = billingData?.billing;
  const summary = billingData?.summary;
  const targetUser = billingData?.user;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 p-5 text-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-white/20 rounded-lg">
                <CreditCard className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-semibold">Manage Payment Status</h2>
                <p className="text-sm text-blue-100">
                  {user?.username} ({user?.email})
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 hover:bg-white/20 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
            </div>
          ) : error ? (
            <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
            </div>
          ) : (
            <>
              {/* User Info */}
              <div className="flex items-center gap-3 p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                <div className="w-10 h-10 bg-slate-200 dark:bg-slate-600 rounded-full flex items-center justify-center">
                  <User className="w-5 h-5 text-slate-500" />
                </div>
                <div>
                  <p className="font-medium text-slate-800 dark:text-white">
                    {targetUser?.username}
                  </p>
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    {targetUser?.email} | Joined{' '}
                    {targetUser?.created_at
                      ? new Date(targetUser.created_at).toLocaleDateString()
                      : 'N/A'}
                  </p>
                </div>
              </div>

              {/* Current Status */}
              <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-600">
                <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">
                  Current Billing Status
                </h3>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {billing?.status === 'TRIAL' && (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                        <Clock className="w-4 h-4" />
                        Trial - {billing.trial_days_remaining} days left
                      </span>
                    )}
                    {billing?.status === 'PAID' && (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
                        <CheckCircle className="w-4 h-4" />
                        Paid
                      </span>
                    )}
                    {billing?.status === 'NOT_PAID' && (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
                        <AlertCircle className="w-4 h-4" />
                        Not Paid
                      </span>
                    )}
                  </div>
                  {billing?.trial_end_date && (
                    <span className="text-xs text-slate-500 dark:text-slate-400">
                      Trial ends: {billing.trial_end_date}
                    </span>
                  )}
                </div>
              </div>

              {/* Billing Details */}
              <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-600">
                <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">
                  Billing Details
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-slate-500 dark:text-slate-400">Active Tills</p>
                    <p className="text-lg font-semibold text-slate-800 dark:text-white">
                      {billing?.active_tills_count || 0}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 dark:text-slate-400">Rate per Till</p>
                    <p className="text-lg font-semibold text-slate-800 dark:text-white">
                      KES {(billing?.rate_per_till || 200).toFixed(2)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 dark:text-slate-400">Amount Due</p>
                    <p className="text-lg font-semibold text-blue-600">
                      KES {(billing?.amount_due || 0).toFixed(2)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 dark:text-slate-400">Current Period</p>
                    <p className="text-sm font-medium text-slate-800 dark:text-white">
                      {billing?.subscription?.billing_period_start || 'N/A'} to{' '}
                      {billing?.subscription?.billing_period_end || 'N/A'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Active Tills List */}
              {summary?.active_tills?.length > 0 && (
                <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-600">
                  <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">
                    Active Tills
                  </h3>
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {summary.active_tills.map((till) => (
                      <div
                        key={till.id}
                        className="flex items-center justify-between p-2 bg-slate-50 dark:bg-slate-700/50 rounded-lg"
                      >
                        <div className="flex items-center gap-2">
                          <Store className="w-4 h-4 text-slate-400" />
                          <span className="text-sm text-slate-700 dark:text-slate-300">
                            {till.company_name}
                          </span>
                        </div>
                        <span className="text-xs text-slate-500 dark:text-slate-400">
                          Agent: {till.agent_number || '-'} | Store: {till.store_number || '-'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Payment History */}
              {summary?.payment_history?.length > 0 && (
                <div className="p-4 rounded-lg border border-slate-200 dark:border-slate-600">
                  <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">
                    Payment History
                  </h3>
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {summary.payment_history.map((sub) => (
                      <div
                        key={sub.id}
                        className="flex items-center justify-between p-2 bg-slate-50 dark:bg-slate-700/50 rounded-lg"
                      >
                        <div>
                          <p className="text-sm text-slate-700 dark:text-slate-300">
                            {sub.billing_period_start} to {sub.billing_period_end}
                          </p>
                          <p className="text-xs text-slate-500">{sub.active_tills_count} tills</p>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                            KES {(sub.amount_due || 0).toFixed(2)}
                          </span>
                          <span
                            className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                              sub.status === 'PAID'
                                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                            }`}
                          >
                            {sub.status}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer - Admin Actions */}
        {!loading && !error && (
          <div className="p-5 border-t border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-700/50">
            <div className="flex items-center justify-between">
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Update subscription status for this billing period
              </p>
              <div className="flex items-center gap-3">
                {billing?.status !== 'PAID' && (
                  <button
                    onClick={() => handleUpdateStatus('PAID')}
                    disabled={updating}
                    className="inline-flex items-center gap-1.5 px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {updating ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <CheckCircle className="w-4 h-4" />
                    )}
                    Mark as Paid
                  </button>
                )}
                {billing?.status === 'PAID' && (
                  <button
                    onClick={() => handleUpdateStatus('PENDING')}
                    disabled={updating}
                    className="inline-flex items-center gap-1.5 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {updating ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Clock className="w-4 h-4" />
                    )}
                    Revert to Pending
                  </button>
                )}
                <button
                  onClick={onClose}
                  className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600 rounded-lg transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default PaymentStatusModal;
