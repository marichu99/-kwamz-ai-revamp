import { useState, useCallback } from 'react';
import {
    X,
    ShieldAlert,
    Shield,
    ChevronDown,
    ChevronRight,
    Users,
    Building,
    Calendar,
    Activity,
    Loader2,
    Download,
} from 'lucide-react';
import axios from 'axios';
import config from '../../Config';
import { useToast } from './ToastProvider';

const DATE_RANGES = [
    { value: 'today', label: 'Today' },
    { value: 'yesterday', label: 'Yesterday' },
    { value: 'this_week', label: 'This Week' },
    { value: 'last_week', label: 'Last Week' },
    { value: 'this_month', label: 'This Month' },
    { value: 'last_month', label: 'Last Month' },
    { value: 'last_3_months', label: 'Last 3 Months' },
    { value: 'last_6_months', label: 'Last 6 Months' },
    { value: 'this_year', label: 'This Year' },
    { value: 'custom', label: 'Custom Range' },
];

const FRAUD_TYPE_META = {
    split_transaction: {
        label: 'Split Transaction',
        color: 'red',
        description: 'Multiple transactions of similar amounts within a short window to avoid detection thresholds.',
    },
    rollover_fraud: {
        label: 'Rollover Fraud',
        color: 'orange',
        description: 'Rapid cluster of deposits or withdrawals on the same account in a short time window.',
    },
    rapid_back_forth: {
        label: 'Rapid Back & Forth',
        color: 'yellow',
        description: '5+ alternating deposits and withdrawals by the same party within 3 minutes — commission farming or float manipulation.',
    },
    deposit_withdrawal_recovery: {
        label: 'Deposit-Withdrawal Recovery',
        color: 'purple',
        description: 'Large deposit followed by a similar-amount withdrawal within 24 hrs — possible wash transaction or pre-existing balance exploitation.',
    },
    high_frequency_daily: {
        label: 'High Frequency Daily',
        color: 'slate',
        description: null,
    },
};

const RISK_COLORS = {
    HIGH: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
    MEDIUM: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
    LOW: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
};

function FindingCard({ finding, index }) {
    const [expanded, setExpanded] = useState(false);
    const meta = FRAUD_TYPE_META[finding.fraud_type] || { label: finding.fraud_type, color: 'slate', description: '' };
    const riskColor = RISK_COLORS[finding.risk_level] || RISK_COLORS.LOW;

    const agentCompanies = finding.agent_info?.agent_companies || [];
    const userAgents = finding.agent_info?.user_agents || [];
    const shortcodes = finding.agent_info?.shortcodes || [];

    return (
        <div className="border border-slate-200 dark:border-slate-600 rounded-xl overflow-hidden mb-3">
            {/* Header row */}
            <button
                onClick={() => setExpanded(e => !e)}
                className="w-full flex items-center justify-between px-4 py-3 bg-slate-50 dark:bg-slate-700 hover:bg-slate-100 dark:hover:bg-slate-600 transition-colors text-left"
            >
                <div className="flex items-center gap-3">
                    <span className="text-xs font-semibold text-slate-400 dark:text-slate-500 w-6">#{index + 1}</span>
                    <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${riskColor}`}>
                        {finding.risk_level}
                    </span>
                    <span className="text-sm font-semibold text-slate-800 dark:text-white">
                        {meta.label}
                    </span>
                    <span className="text-sm text-slate-500 dark:text-slate-400">
                        {finding.account_name || finding.account_phone}
                    </span>
                    {finding.account_phone && finding.account_name && (
                        <span className="text-xs text-slate-400 dark:text-slate-500">{finding.account_phone}</span>
                    )}
                </div>
                <div className="flex items-center gap-4">
                    <span className="text-sm font-medium text-slate-600 dark:text-slate-300">
                        KES {Number(finding.total_amount || 0).toLocaleString('en-KE', { minimumFractionDigits: 2 })}
                    </span>
                    {expanded ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
                </div>
            </button>

            {expanded && (
                <div className="px-4 py-4 bg-white dark:bg-slate-800 space-y-4">
                    {/* Explanation — omitted for high_frequency_daily */}
                    {finding.explanation && (
                        <div className="p-3 bg-slate-50 dark:bg-slate-700 rounded-lg text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                            {finding.explanation}
                        </div>
                    )}

                    {/* Date badge for high-frequency findings */}
                    {finding.fraud_type === 'high_frequency_daily' && finding.day && (
                        <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                            <Calendar className="w-4 h-4 text-slate-400" />
                            <span>{finding.transaction_count} transactions on <span className="font-semibold">{finding.day}</span></span>
                        </div>
                    )}

                    {/* Split transaction anchor stats */}
                    {finding.fraud_type === 'split_transaction' && (
                        <div className="grid grid-cols-3 gap-2">
                            <div className={`rounded-lg p-2 text-center ${finding.anchor_type === 'deposit' ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20'}`}>
                                <p className={`text-xs ${finding.anchor_type === 'deposit' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                                    Anchor {finding.anchor_type}
                                </p>
                                <p className="text-sm font-bold text-slate-800 dark:text-white">
                                    KES {Number(finding.anchor_amount || 0).toLocaleString('en-KE', { minimumFractionDigits: 2 })}
                                </p>
                            </div>
                            <div className={`rounded-lg p-2 text-center ${finding.anchor_type === 'deposit' ? 'bg-red-50 dark:bg-red-900/20' : 'bg-green-50 dark:bg-green-900/20'}`}>
                                <p className={`text-xs ${finding.anchor_type === 'deposit' ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
                                    {finding.subsequent_count} follow-up {finding.anchor_type === 'deposit' ? 'withdrawals' : 'deposits'}
                                </p>
                                <p className="text-sm font-bold text-slate-800 dark:text-white">
                                    KES {Number(finding.subsequent_total || 0).toLocaleString('en-KE', { minimumFractionDigits: 2 })}
                                </p>
                            </div>
                            <div className="bg-slate-50 dark:bg-slate-700 rounded-lg p-2 text-center">
                                <p className="text-xs text-slate-500 dark:text-slate-400">Within</p>
                                <p className="text-sm font-bold text-slate-800 dark:text-white">{finding.time_window_minutes} min</p>
                            </div>
                        </div>
                    )}

                    {/* Recovery stats for deposit-withdrawal pattern */}
                    {finding.fraud_type === 'deposit_withdrawal_recovery' && (
                        <div className="grid grid-cols-3 gap-2">
                            <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-2 text-center">
                                <p className="text-xs text-green-600 dark:text-green-400">Deposited</p>
                                <p className="text-sm font-bold text-slate-800 dark:text-white">
                                    KES {Number(finding.deposit_amount || 0).toLocaleString('en-KE', { minimumFractionDigits: 2 })}
                                </p>
                            </div>
                            <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-2 text-center">
                                <p className="text-xs text-red-600 dark:text-red-400">Withdrawn</p>
                                <p className="text-sm font-bold text-slate-800 dark:text-white">
                                    KES {Number(finding.total_withdrawn || 0).toLocaleString('en-KE', { minimumFractionDigits: 2 })}
                                </p>
                            </div>
                            <div className={`rounded-lg p-2 text-center ${finding.overdraw ? 'bg-red-100 dark:bg-red-900/30' : 'bg-amber-50 dark:bg-amber-900/20'}`}>
                                <p className={`text-xs ${finding.overdraw ? 'text-red-600 dark:text-red-400' : 'text-amber-600 dark:text-amber-400'}`}>
                                    Recovery {finding.overdraw ? '⚠ Overdraw' : ''}
                                </p>
                                <p className="text-sm font-bold text-slate-800 dark:text-white">{finding.recovery_pct}%</p>
                            </div>
                        </div>
                    )}

                    {/* Transaction details */}
                    {finding.transaction_details?.length > 0 && (
                        <div>
                            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-2 uppercase tracking-wide">Transactions</p>
                            <div className="overflow-x-auto">
                                <table className="w-full text-xs border-collapse">
                                    <thead>
                                        <tr className="bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
                                            <th className="px-3 py-2 text-left font-semibold">Receipt</th>
                                            <th className="px-3 py-2 text-left font-semibold">Type</th>
                                            <th className="px-3 py-2 text-right font-semibold">Amount (KES)</th>
                                            <th className="px-3 py-2 text-left font-semibold">Time</th>
                                            <th className="px-3 py-2 text-left font-semibold">Party</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {finding.transaction_details.map((txn, i) => (
                                            <tr key={i} className="border-t border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/50">
                                                <td className="px-3 py-2 font-mono text-slate-600 dark:text-slate-300">{txn.receipt_no}</td>
                                                <td className="px-3 py-2">
                                                    <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${txn.type === 'Deposit' || txn.type === 'DEPOSIT'
                                                        ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
                                                        : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'}`}>
                                                        {txn.type}
                                                    </span>
                                                </td>
                                                <td className="px-3 py-2 text-right font-medium text-slate-800 dark:text-white">
                                                    {Number(txn.amount || 0).toLocaleString('en-KE', { minimumFractionDigits: 2 })}
                                                </td>
                                                <td className="px-3 py-2 text-slate-500 dark:text-slate-400 whitespace-nowrap">{txn.time}</td>
                                                <td className="px-3 py-2 text-slate-600 dark:text-slate-300">{txn.party_name || txn.party_phone || '—'}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {/* Agent companies */}
                    {(agentCompanies.length > 0 || shortcodes.length > 0) && (
                        <div>
                            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-2 uppercase tracking-wide flex items-center gap-1">
                                <Building className="w-3 h-3" /> Agent Companies
                            </p>
                            {agentCompanies.length > 0 ? (
                                <div className="space-y-1">
                                    {agentCompanies.map((ac, i) => (
                                        <div key={i} className="flex items-center gap-3 text-sm text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-700 px-3 py-2 rounded-lg">
                                            <span className="font-medium">{ac.company_name}</span>
                                            {ac.short_code && <span className="text-xs text-slate-400">SC: {ac.short_code}</span>}
                                            {ac.location && <span className="text-xs text-slate-400">{ac.location}</span>}
                                            {ac.fraud_risk_level && (
                                                <span className={`ml-auto text-xs font-semibold px-2 py-0.5 rounded-full ${RISK_COLORS[ac.fraud_risk_level?.toUpperCase()] || RISK_COLORS.LOW}`}>
                                                    {ac.fraud_risk_level}
                                                </span>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-xs text-slate-400 dark:text-slate-500">
                                    Shortcodes: {shortcodes.join(', ')}
                                </p>
                            )}
                        </div>
                    )}

                    {/* User agents */}
                    {userAgents.length > 0 && (
                        <div>
                            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-2 uppercase tracking-wide flex items-center gap-1">
                                <Users className="w-3 h-3" /> User Agents
                            </p>
                            <div className="flex flex-wrap gap-2">
                                {userAgents.map((ua, i) => (
                                    <div key={i} className="text-xs bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 px-3 py-1.5 rounded-lg">
                                        <span className="font-medium">{ua.name}</span>
                                        {ua.phone_number && <span className="ml-1 opacity-70">{ua.phone_number}</span>}
                                        {ua.is_authentic === false && (
                                            <span className="ml-1 text-red-500 font-semibold">· Unverified</span>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export default function FraudReportModal({ isOpen, onClose, companyId }) {
    const { showToast } = useToast();
    const [dateRange, setDateRange] = useState('this_month');
    const [customStartDate, setCustomStartDate] = useState('');
    const [customEndDate, setCustomEndDate] = useState('');
    const [showDatePicker, setShowDatePicker] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [isExporting, setIsExporting] = useState(false);
    const [report, setReport] = useState(null);
    const [activeType, setActiveType] = useState('all');

    const fetchReport = useCallback(async () => {
        setIsLoading(true);
        setReport(null);
        try {
            const token = localStorage.getItem('token');
            const params = {
                date_range: dateRange,
                ...(dateRange === 'custom' && { start_date: customStartDate, end_date: customEndDate }),
                ...(companyId && { company_id: companyId }),
            };
            const res = await axios.get(`${config.API_URL}/transactions/fraud-report`, {
                headers: { Authorization: `Bearer ${token}` },
                params,
            });
            if (res.data.success) {
                setReport(res.data.report);
            } else {
                showToast(res.data.error || 'Failed to generate report', 'error');
            }
        } catch (err) {
            showToast(err.response?.data?.error || 'Failed to generate report', 'error');
        } finally {
            setIsLoading(false);
        }
    }, [dateRange, customStartDate, customEndDate, companyId, showToast]);

    const exportPdf = useCallback(async () => {
        setIsExporting(true);
        try {
            const token = localStorage.getItem('token');
            const params = {
                date_range: dateRange,
                ...(dateRange === 'custom' && { start_date: customStartDate, end_date: customEndDate }),
                ...(companyId && { company_id: companyId }),
            };
            const query = new URLSearchParams(params).toString();
            const res = await fetch(`${config.API_URL}/transactions/fraud-report-pdf?${query}`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!res.ok) throw new Error('PDF generation failed');
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `fraud_report_${new Date().toISOString().slice(0, 10)}.pdf`;
            a.click();
            URL.revokeObjectURL(url);
            showToast('Fraud report exported as PDF', 'success');
        } catch (err) {
            showToast('Failed to export PDF', 'error');
        } finally {
            setIsExporting(false);
        }
    }, [dateRange, customStartDate, customEndDate, companyId, showToast]);

    if (!isOpen) return null;

    const findings = report?.findings || [];
    const filtered = activeType === 'all' ? findings : findings.filter(f => f.fraud_type === activeType);

    const summary = report?.summary;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
                    <div className="flex items-center gap-3">
                        <ShieldAlert className="w-6 h-6 text-red-500" />
                        <div>
                            <h2 className="text-xl font-bold text-slate-800 dark:text-white">Historical Fraud Report</h2>
                            {report && (
                                <p className="text-sm text-slate-500 dark:text-slate-400">{report.period}</p>
                            )}
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors">
                        <X className="w-5 h-5 text-slate-500" />
                    </button>
                </div>

                {/* Controls */}
                <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex flex-wrap items-end gap-3">
                    {/* Date range selector */}
                    <div className="relative">
                        <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Date Range</label>
                        <button
                            onClick={() => setShowDatePicker(p => !p)}
                            className="flex items-center gap-2 px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700 hover:bg-slate-50 dark:hover:bg-slate-600 transition-colors"
                        >
                            <Calendar className="w-4 h-4" />
                            {DATE_RANGES.find(r => r.value === dateRange)?.label || 'Select Range'}
                            <ChevronDown className="w-4 h-4" />
                        </button>
                        {showDatePicker && (
                            <div className="absolute z-20 mt-1 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl shadow-xl w-48">
                                {DATE_RANGES.map(r => (
                                    <button
                                        key={r.value}
                                        onClick={() => { setDateRange(r.value); setShowDatePicker(false); }}
                                        className={`w-full text-left px-4 py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-600 transition-colors first:rounded-t-xl last:rounded-b-xl ${dateRange === r.value ? 'font-semibold text-blue-600 dark:text-blue-400' : 'text-slate-700 dark:text-slate-300'}`}
                                    >
                                        {r.label}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                    {dateRange === 'custom' && (
                        <>
                            <div>
                                <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">From</label>
                                <input type="date" value={customStartDate} onChange={e => setCustomStartDate(e.target.value)}
                                    className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700" />
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">To</label>
                                <input type="date" value={customEndDate} onChange={e => setCustomEndDate(e.target.value)}
                                    className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700" />
                            </div>
                        </>
                    )}

                    <button
                        onClick={fetchReport}
                        disabled={isLoading || (dateRange === 'custom' && (!customStartDate || !customEndDate))}
                        className="flex items-center gap-2 px-4 py-2 bg-red-500 hover:bg-red-600 disabled:bg-red-300 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors"
                    >
                        {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Activity className="w-4 h-4" />}
                        {isLoading ? 'Analysing…' : 'Run Analysis'}
                    </button>

                    {report && (
                        <button
                            onClick={exportPdf}
                            disabled={isExporting}
                            className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-800 disabled:bg-slate-400 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors"
                        >
                            {isExporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                            {isExporting ? 'Generating…' : 'Export PDF'}
                        </button>
                    )}
                </div>

                {/* Body */}
                <div className="flex-1 overflow-y-auto px-6 py-4">
                    {!report && !isLoading && (
                        <div className="flex flex-col items-center justify-center h-48 text-slate-400 dark:text-slate-500">
                            <ShieldAlert className="w-12 h-12 mb-3 opacity-40" />
                            <p className="text-sm">Select a date range and run the analysis to view findings.</p>
                        </div>
                    )}

                    {isLoading && (
                        <div className="flex flex-col items-center justify-center h-48 text-slate-400 dark:text-slate-500">
                            <Loader2 className="w-10 h-10 animate-spin mb-3 text-red-400" />
                            <p className="text-sm">Scanning transactions for fraud patterns…</p>
                        </div>
                    )}

                    {report && !isLoading && (
                        <>
                            {/* Summary cards */}
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
                                <div className="bg-slate-50 dark:bg-slate-700 rounded-xl p-3 text-center">
                                    <p className="text-xs text-slate-500 dark:text-slate-400 mb-1">Transactions Scanned</p>
                                    <p className="text-xl font-bold text-slate-800 dark:text-white">{summary.total_transactions_analyzed.toLocaleString()}</p>
                                </div>
                                <div className="bg-red-50 dark:bg-red-900/30 rounded-xl p-3 text-center">
                                    <p className="text-xs text-red-600 dark:text-red-400 mb-1">High Risk</p>
                                    <p className="text-xl font-bold text-red-700 dark:text-red-300">{summary.high_risk}</p>
                                </div>
                                <div className="bg-amber-50 dark:bg-amber-900/30 rounded-xl p-3 text-center">
                                    <p className="text-xs text-amber-600 dark:text-amber-400 mb-1">Medium Risk</p>
                                    <p className="text-xl font-bold text-amber-700 dark:text-amber-300">{summary.medium_risk}</p>
                                </div>
                                <div className="bg-blue-50 dark:bg-blue-900/30 rounded-xl p-3 text-center">
                                    <p className="text-xs text-blue-600 dark:text-blue-400 mb-1">Low Risk</p>
                                    <p className="text-xl font-bold text-blue-700 dark:text-blue-300">{summary.low_risk}</p>
                                </div>
                            </div>

                            {/* Fraud type breakdown */}
                            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-6">
                                {Object.entries(FRAUD_TYPE_META).map(([type, meta]) => {
                                    const count = type === 'split_transaction' ? summary.split_transactions
                                        : type === 'rollover_fraud' ? summary.rollover_fraud
                                        : type === 'rapid_back_forth' ? summary.rapid_back_forth
                                        : type === 'deposit_withdrawal_recovery' ? summary.deposit_withdrawal_recovery
                                        : summary.high_frequency_daily;
                                    return (
                                        <div key={type} className="bg-slate-50 dark:bg-slate-700 rounded-xl p-3">
                                            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1">{meta.label}</p>
                                            <p className="text-2xl font-bold text-slate-800 dark:text-white">{count}</p>
                                            {meta.description && (
                                                <p className="text-xs text-slate-400 dark:text-slate-500 mt-1 leading-tight">{meta.description}</p>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>

                            {findings.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-32 text-slate-400 dark:text-slate-500">
                                    <Shield className="w-10 h-10 mb-2 text-green-400" />
                                    <p className="text-sm font-medium text-green-600 dark:text-green-400">No suspicious patterns detected in this period.</p>
                                </div>
                            ) : (
                                <>
                                    {/* Filter tabs */}
                                    <div className="flex gap-2 mb-4 flex-wrap">
                                        {[{ value: 'all', label: `All (${findings.length})` },
                                        { value: 'split_transaction', label: `Split (${summary.split_transactions})` },
                                        { value: 'rollover_fraud', label: `Rollover (${summary.rollover_fraud})` },
                                        { value: 'rapid_back_forth', label: `Rapid B&F (${summary.rapid_back_forth})` },
                                        { value: 'deposit_withdrawal_recovery', label: `Dep-Withdrawal (${summary.deposit_withdrawal_recovery})` },
                                        { value: 'high_frequency_daily', label: `High Freq (${summary.high_frequency_daily})` },
                                        ].map(tab => (
                                            <button key={tab.value} onClick={() => setActiveType(tab.value)}
                                                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${activeType === tab.value
                                                    ? 'bg-red-500 text-white'
                                                    : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600'}`}>
                                                {tab.label}
                                            </button>
                                        ))}
                                    </div>

                                    {/* Findings list */}
                                    <div>
                                        {filtered.map((finding, i) => (
                                            <FindingCard key={i} finding={finding} index={i} />
                                        ))}
                                    </div>
                                </>
                            )}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
