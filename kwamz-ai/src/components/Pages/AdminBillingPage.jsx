import React, { useState, useEffect, useCallback } from 'react';
import {
  CreditCard, Search, RefreshCw, CheckCircle, Clock, AlertCircle,
  ChevronDown, ChevronUp, User, Loader2
} from 'lucide-react';
import config from '../../Config';
import { useToast } from './ToastProvider';

const API_BASE_URL = config.API_URL || 'http://localhost:5000';

function StatusBadge({ status }) {
  const map = {
    PAID:    { cls: 'bg-green-100 text-green-700', icon: <CheckCircle className="w-3 h-3" />, label: 'Paid' },
    TRIAL:   { cls: 'bg-blue-100 text-blue-700',  icon: <Clock className="w-3 h-3" />,       label: 'Trial' },
    PENDING: { cls: 'bg-yellow-100 text-yellow-700', icon: <Clock className="w-3 h-3" />,    label: 'Pending' },
    NOT_PAID:{ cls: 'bg-red-100 text-red-700',    icon: <AlertCircle className="w-3 h-3" />, label: 'Not Paid' },
  };
  const s = map[status] || map['PENDING'];
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${s.cls}`}>
      {s.icon}{s.label}
    </span>
  );
}

function UserBillingRow({ user, onConfirmPayment, onMarkPending }) {
  const [billing, setBilling] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const token = localStorage.getItem('token');

  const fetchBilling = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/payment/admin/billing-status/${user.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed');
      const data = await res.json();
      setBilling(data.billing);
    } catch {
      setBilling(null);
    } finally {
      setLoading(false);
    }
  }, [user.id, token]);

  useEffect(() => { fetchBilling(); }, [fetchBilling]);

  const handleConfirm = async () => {
    setConfirming(true);
    await onConfirmPayment(user.id, fetchBilling);
    setConfirming(false);
  };

  const handlePending = async () => {
    setConfirming(true);
    await onMarkPending(user.id, fetchBilling);
    setConfirming(false);
  };

  const status = billing?.status || 'PENDING';
  const isPaid = status === 'PAID';
  const isTrial = status === 'TRIAL';

  return (
    <div className="border border-slate-200 rounded-lg overflow-hidden">
      <div
        className="flex items-center justify-between p-4 bg-white hover:bg-slate-50 cursor-pointer"
        onClick={() => setExpanded(e => !e)}
      >
        <div className="flex items-center gap-3 min-w-0">
          <div className="p-2 bg-slate-100 rounded-full flex-shrink-0">
            <User className="w-4 h-4 text-slate-500" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium text-slate-800 truncate">{user.username}</p>
            <p className="text-xs text-slate-500 truncate">{user.email}</p>
          </div>
        </div>

        <div className="flex items-center gap-3 flex-shrink-0 ml-3">
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin text-slate-400" />
          ) : (
            <>
              <StatusBadge status={status} />
              {billing && (
                <span className="text-xs text-slate-500 hidden sm:block">
                  {billing.active_tills_count ?? 0} till{billing.active_tills_count !== 1 ? 's' : ''} · KES {(billing.amount_due ?? 0).toLocaleString()}
                </span>
              )}
            </>
          )}
          {expanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </div>
      </div>

      {expanded && (
        <div className="border-t border-slate-100 bg-slate-50 p-4 space-y-4">
          {loading ? (
            <div className="flex justify-center py-4">
              <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
            </div>
          ) : billing ? (
            <>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                <div>
                  <p className="text-xs text-slate-500 mb-0.5">Status</p>
                  <StatusBadge status={status} />
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-0.5">Active Tills</p>
                  <p className="font-medium text-slate-800">{billing.active_tills_count ?? 0}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 mb-0.5">Amount Due</p>
                  <p className="font-medium text-slate-800">KES {(billing.amount_due ?? 0).toLocaleString()}</p>
                </div>
                {billing.trial_end_date && (
                  <div>
                    <p className="text-xs text-slate-500 mb-0.5">Trial Ends</p>
                    <p className="font-medium text-slate-800">{billing.trial_end_date}</p>
                  </div>
                )}
              </div>

              <div className="flex gap-2 flex-wrap">
                {!isPaid && !isTrial && (
                  <button
                    onClick={handleConfirm}
                    disabled={confirming}
                    className="inline-flex items-center gap-1.5 px-3 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-medium rounded-lg transition disabled:opacity-50"
                  >
                    {confirming ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
                    Confirm Payment
                  </button>
                )}
                {isPaid && (
                  <button
                    onClick={handlePending}
                    disabled={confirming}
                    className="inline-flex items-center gap-1.5 px-3 py-2 bg-yellow-500 hover:bg-yellow-600 text-white text-sm font-medium rounded-lg transition disabled:opacity-50"
                  >
                    {confirming ? <Loader2 className="w-4 h-4 animate-spin" /> : <Clock className="w-4 h-4" />}
                    Mark as Pending
                  </button>
                )}
                <button
                  onClick={fetchBilling}
                  className="inline-flex items-center gap-1.5 px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium rounded-lg transition"
                >
                  <RefreshCw className="w-4 h-4" />
                  Refresh
                </button>
              </div>
            </>
          ) : (
            <p className="text-sm text-slate-500">Failed to load billing info.</p>
          )}
        </div>
      )}
    </div>
  );
}

function AdminBillingPage() {
  const [users, setUsers] = useState([]);
  const [filtered, setFiltered] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const { showToast } = useToast();
  const token = localStorage.getItem('token');

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/users`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to fetch users');
      const data = await res.json();
      // Only show regular users (not admins/agents)
      const clientUsers = (Array.isArray(data) ? data : (data.users || [])).filter(
        u => !['admin', 'administrator', 'agent'].includes(u.role?.toLowerCase())
      );
      setUsers(clientUsers);
      setFiltered(clientUsers);
    } catch (err) {
      showToast('Failed to load users: ' + err.message, 'error');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  useEffect(() => {
    const q = search.toLowerCase();
    setFiltered(
      q ? users.filter(u => u.username?.toLowerCase().includes(q) || u.email?.toLowerCase().includes(q)) : users
    );
  }, [search, users]);

  const confirmPayment = async (userId, refresh) => {
    try {
      const res = await fetch(`${API_BASE_URL}/payment/admin/update-status/${userId}`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'PAID' }),
      });
      const data = await res.json();
      if (data.success) {
        showToast('Payment confirmed successfully', 'success');
        refresh();
      } else {
        showToast(data.error || 'Failed to confirm payment', 'error');
      }
    } catch (err) {
      showToast('Error: ' + err.message, 'error');
    }
  };

  const markPending = async (userId, refresh) => {
    try {
      const res = await fetch(`${API_BASE_URL}/payment/admin/update-status/${userId}`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'PENDING' }),
      });
      const data = await res.json();
      if (data.success) {
        showToast('Status set to pending', 'success');
        refresh();
      } else {
        showToast(data.error || 'Failed to update status', 'error');
      }
    } catch (err) {
      showToast('Error: ' + err.message, 'error');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-100 rounded-lg">
            <CreditCard className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-800">Client Billing</h1>
            <p className="text-sm text-slate-500">Confirm or manage client subscription payments</p>
          </div>
        </div>
        <button
          onClick={fetchUsers}
          className="inline-flex items-center gap-1.5 px-3 py-2 text-sm text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <input
          type="text"
          placeholder="Search by name or email..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full pl-9 pr-4 py-2.5 border border-slate-200 rounded-lg text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
        />
      </div>

      {/* Users list */}
      {loading ? (
        <div className="flex justify-center py-16">
          <div className="text-center">
            <Loader2 className="w-10 h-10 animate-spin text-blue-500 mx-auto mb-3" />
            <p className="text-sm text-slate-500">Loading clients...</p>
          </div>
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-slate-500">
          <CreditCard className="w-10 h-10 mx-auto mb-3 text-slate-300" />
          <p className="font-medium">No clients found</p>
          {search && <p className="text-sm mt-1">Try clearing your search</p>}
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map(user => (
            <UserBillingRow
              key={user.id}
              user={user}
              onConfirmPayment={confirmPayment}
              onMarkPending={markPending}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default AdminBillingPage;
