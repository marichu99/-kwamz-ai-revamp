import { useState, useCallback } from 'react';
import {
    X,
    TrendingUp,
    AlertTriangle,
    ShieldAlert,
    ChevronDown,
    ChevronRight,
    Users,
    Calendar,
    Activity,
    Loader2,
    Download,
    Trophy,
    DollarSign,
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

const FRAUD_CAT_META = {
    split_transaction: {
        label: 'Split Transaction',
        color: 'red',
        description: 'Large transaction followed by multiple smaller opposite-type transactions to avoid detection.',
    },
    high_frequency_daily: {
        label: 'High Frequency Daily',
        color: 'amber',
        description: '5+ transactions by the same phone number at the same shortcode on a single day.',
    },
    rapid_back_forth: {
        label: 'Rapid Back & Forth',
        color: 'purple',
        description: '3+ alternating deposits and withdrawals by the same party within 1 minute — commission farming indicator.',
    },
};

const RISK_COLORS = {
    HIGH:   'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
    MEDIUM: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
    LOW:    'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
};

const fmt = (n) => Number(n || 0).toLocaleString('en-KE', { minimumFractionDigits: 2 });

// ── Fraud finding card ──────────────────────────────────
function FraudFindingCard({ finding, index }) {
    const [expanded, setExpanded] = useState(false);
    const riskColor = RISK_COLORS[finding.risk_level] || RISK_COLORS.LOW;

    return (
        <div className="border border-slate-200 dark:border-slate-600 rounded-xl overflow-hidden mb-2">
            <button
                onClick={() => setExpanded(e => !e)}
                className="w-full flex items-center justify-between px-4 py-2.5 bg-slate-50 dark:bg-slate-700 hover:bg-slate-100 dark:hover:bg-slate-600 transition-colors text-left"
            >
                <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-slate-400 w-5">#{index + 1}</span>
                    <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${riskColor}`}>
                        {finding.risk_level}
                    </span>
                    <span className="text-sm text-slate-700 dark:text-slate-200">
                        {finding.account_name || finding.account_phone}
                    </span>
                    {finding.account_phone && finding.account_name && (
                        <span className="text-xs text-slate-400 dark:text-slate-500">{finding.account_phone}</span>
                    )}
                    {finding.fraud_type === 'high_frequency_daily' && finding.day && (
                        <span className="text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1">
                            <Calendar className="w-3 h-3" /> {finding.transaction_count} txns on {finding.day}
                        </span>
                    )}
                </div>
                <div className="flex items-center gap-3">
                    <span className="text-sm font-semibold text-slate-600 dark:text-slate-300">
                        KES {fmt(finding.total_amount)}
                    </span>
                    {expanded
                        ? <ChevronDown className="w-4 h-4 text-slate-400" />
                        : <ChevronRight className="w-4 h-4 text-slate-400" />
                    }
                </div>
            </button>

            {expanded && (
                <div className="px-4 py-3 bg-white dark:bg-slate-800 space-y-3">
                    {finding.explanation && (
                        <p className="text-sm text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-700 p-3 rounded-lg leading-relaxed">
                            {finding.explanation}
                        </p>
                    )}
                    {finding.transaction_details?.length > 0 && (
                        <div>
                            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-2 uppercase tracking-wide">
                                Sample Transactions
                            </p>
                            <div className="overflow-x-auto">
                                <table className="w-full text-xs border-collapse">
                                    <thead>
                                        <tr className="bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
                                            <th className="px-3 py-2 text-left font-semibold">Receipt</th>
                                            <th className="px-3 py-2 text-left font-semibold">Type</th>
                                            <th className="px-3 py-2 text-right font-semibold">Amount (KES)</th>
                                            <th className="px-3 py-2 text-left font-semibold">Time</th>
                                            <th className="px-3 py-2 text-left font-semibold">Party</th>
                                            <th className="px-3 py-2 text-left font-semibold">Shortcode</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {finding.transaction_details.map((txn, i) => (
                                            <tr key={i} className="border-t border-slate-100 dark:border-slate-700">
                                                <td className="px-3 py-2 font-mono text-slate-600 dark:text-slate-300">{txn.receipt_no}</td>
                                                <td className="px-3 py-2">
                                                    <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                                                        txn.type === 'Deposit' || txn.type === 'DEPOSIT'
                                                            ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
                                                            : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
                                                    }`}>{txn.type}</span>
                                                </td>
                                                <td className="px-3 py-2 text-right font-medium text-slate-800 dark:text-white">
                                                    {fmt(txn.amount)}
                                                </td>
                                                <td className="px-3 py-2 text-slate-500 dark:text-slate-400 whitespace-nowrap">{txn.time}</td>
                                                <td className="px-3 py-2 text-slate-600 dark:text-slate-300">{txn.party_name || txn.party_phone || '—'}</td>
                                                <td className="px-3 py-2 text-slate-500 dark:text-slate-400">{txn.business_shortcode || '—'}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

// ── Fraud category panel ────────────────────────────────
function FraudCategoryPanel({ categoryKey, findings }) {
    const meta = FRAUD_CAT_META[categoryKey];
    const colorMap = {
        red:    'border-red-400 bg-red-50 dark:bg-red-900/20',
        amber:  'border-amber-400 bg-amber-50 dark:bg-amber-900/20',
        purple: 'border-purple-400 bg-purple-50 dark:bg-purple-900/20',
    };
    const textMap = {
        red:    'text-red-700 dark:text-red-300',
        amber:  'text-amber-700 dark:text-amber-300',
        purple: 'text-purple-700 dark:text-purple-300',
    };

    return (
        <div className="mb-5">
            <div className={`border-l-4 px-4 py-2 rounded-r-lg mb-3 ${colorMap[meta.color]}`}>
                <div className="flex items-center justify-between">
                    <div>
                        <span className={`text-sm font-bold ${textMap[meta.color]}`}>{meta.label}</span>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{meta.description}</p>
                    </div>
                    <span className={`text-2xl font-bold ${textMap[meta.color]}`}>{findings.length}</span>
                </div>
            </div>
            {findings.length > 0 ? (
                findings.map((f, i) => <FraudFindingCard key={i} finding={f} index={i} />)
            ) : (
                <p className="text-sm text-slate-400 dark:text-slate-500 text-center py-4">
                    No {meta.label.toLowerCase()} patterns found.
                </p>
            )}
        </div>
    );
}

// ── Main modal ──────────────────────────────────────────
export default function AgentPerformanceReportModal({ isOpen, onClose, companyId }) {
    const { showToast } = useToast();
    const [dateRange, setDateRange] = useState('this_month');
    const [customStartDate, setCustomStartDate] = useState('');
    const [customEndDate, setCustomEndDate] = useState('');
    const [showDatePicker, setShowDatePicker] = useState(false);
    const [commissionThreshold, setCommissionThreshold] = useState('5000');
    const [floatThreshold, setFloatThreshold] = useState('50000');
    const [isLoading, setIsLoading] = useState(false);
    const [isExporting, setIsExporting] = useState(false);
    const [report, setReport] = useState(null);
    const [activeSection, setActiveSection] = useState('earners');

    const getParams = useCallback(() => ({
        date_range: dateRange,
        ...(dateRange === 'custom' && { start_date: customStartDate, end_date: customEndDate }),
        ...(companyId && { company_id: companyId }),
        commission_threshold: commissionThreshold || '5000',
        float_threshold: floatThreshold || '50000',
    }), [dateRange, customStartDate, customEndDate, companyId, commissionThreshold, floatThreshold]);

    const fetchReport = useCallback(async () => {
        setIsLoading(true);
        setReport(null);
        try {
            const token = localStorage.getItem('token');
            const res = await axios.get(`${config.API_URL}/transactions/agent-performance-report`, {
                headers: { Authorization: `Bearer ${token}` },
                params: getParams(),
            });
            if (res.data.success) {
                setReport(res.data.report);
                setActiveSection('earners');
            } else {
                showToast(res.data.error || 'Failed to generate report', 'error');
            }
        } catch (err) {
            showToast(err.response?.data?.error || 'Failed to generate report', 'error');
        } finally {
            setIsLoading(false);
        }
    }, [getParams, showToast]);

    const exportPdf = useCallback(async () => {
        setIsExporting(true);
        try {
            const token = localStorage.getItem('token');
            const query = new URLSearchParams(getParams()).toString();
            const res = await fetch(
                `${config.API_URL}/transactions/agent-performance-report-pdf?${query}`,
                { headers: { Authorization: `Bearer ${token}` } }
            );
            if (!res.ok) throw new Error('PDF generation failed');
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `agent_performance_report_${new Date().toISOString().slice(0, 10)}.pdf`;
            a.click();
            URL.revokeObjectURL(url);
            showToast('Agent performance report exported as PDF', 'success');
        } catch {
            showToast('Failed to export PDF', 'error');
        } finally {
            setIsExporting(false);
        }
    }, [getParams, showToast]);

    if (!isOpen) return null;

    const summary = report?.summary || {};
    const fraudData = report?.fraud_flagged || {};
    const totalFraud = summary.fraud_flagged_count || 0;

    const SECTIONS = [
        { key: 'earners',   label: `Top Earners (${summary.top_earners_count ?? '—'})`,        icon: Trophy },
        { key: 'threshold', label: `Below Threshold (${summary.below_threshold_count ?? '—'})`, icon: AlertTriangle },
        { key: 'fraud',     label: `Fraud Flagged (${totalFraud})`,                             icon: ShieldAlert },
    ];

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-5xl max-h-[92vh] flex flex-col">

                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
                    <div className="flex items-center gap-3">
                        <TrendingUp className="w-6 h-6 text-emerald-500" />
                        <div>
                            <h2 className="text-xl font-bold text-slate-800 dark:text-white">Agent Performance Report</h2>
                            {report && (
                                <>
                                    <p className="text-sm text-slate-500 dark:text-slate-400">{report.period}</p>
                                    {report.commission_source && (
                                        <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-0.5">{report.commission_source}</p>
                                    )}
                                </>
                            )}
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                    >
                        <X className="w-5 h-5 text-slate-500" />
                    </button>
                </div>

                {/* Controls */}
                <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex flex-wrap items-end gap-3">

                    {/* Date range */}
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

                    {/* Thresholds */}
                    <div>
                        <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
                            <DollarSign className="w-3 h-3 inline" /> Float Threshold (KES)
                        </label>
                        <input
                            type="number" min="0" value={floatThreshold}
                            onChange={e => setFloatThreshold(e.target.value)}
                            className="w-32 px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700"
                        />
                    </div>

                    <div>
                        <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
                            <DollarSign className="w-3 h-3 inline" /> Commission Threshold (KES)
                        </label>
                        <input
                            type="number" min="0" value={commissionThreshold}
                            onChange={e => setCommissionThreshold(e.target.value)}
                            className="w-32 px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700"
                        />
                    </div>

                    <button
                        onClick={fetchReport}
                        disabled={isLoading || (dateRange === 'custom' && (!customStartDate || !customEndDate))}
                        className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-300 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors"
                    >
                        {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Activity className="w-4 h-4" />}
                        {isLoading ? 'Generating…' : 'Generate Report'}
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
                            <TrendingUp className="w-12 h-12 mb-3 opacity-40" />
                            <p className="text-sm">Set your parameters and generate the report.</p>
                        </div>
                    )}

                    {isLoading && (
                        <div className="flex flex-col items-center justify-center h-48 text-slate-400 dark:text-slate-500">
                            <Loader2 className="w-10 h-10 animate-spin mb-3 text-emerald-400" />
                            <p className="text-sm">Building agent performance report…</p>
                        </div>
                    )}

                    {report && !isLoading && (
                        <>
                            {/* Summary cards */}
                            <div className="grid grid-cols-3 gap-3 mb-6">
                                <div className="bg-emerald-50 dark:bg-emerald-900/30 rounded-xl p-3 text-center">
                                    <p className="text-xs text-emerald-600 dark:text-emerald-400 mb-1 flex items-center justify-center gap-1">
                                        <Trophy className="w-3 h-3" /> Top Earners
                                    </p>
                                    <p className="text-2xl font-bold text-emerald-700 dark:text-emerald-300">{summary.top_earners_count}</p>
                                </div>
                                <div className="bg-amber-50 dark:bg-amber-900/30 rounded-xl p-3 text-center">
                                    <p className="text-xs text-amber-600 dark:text-amber-400 mb-1 flex items-center justify-center gap-1">
                                        <AlertTriangle className="w-3 h-3" /> Below Threshold
                                    </p>
                                    <p className="text-2xl font-bold text-amber-700 dark:text-amber-300">{summary.below_threshold_count}</p>
                                    <p className="text-xs text-slate-400 mt-1">
                                        Float &lt; KES {Number(report.thresholds.float).toLocaleString()} or Commission &lt; KES {Number(report.thresholds.commission).toLocaleString()}
                                    </p>
                                </div>
                                <div className="bg-red-50 dark:bg-red-900/30 rounded-xl p-3 text-center">
                                    <p className="text-xs text-red-600 dark:text-red-400 mb-1 flex items-center justify-center gap-1">
                                        <ShieldAlert className="w-3 h-3" /> Fraud Flagged
                                    </p>
                                    <p className="text-2xl font-bold text-red-700 dark:text-red-300">{totalFraud}</p>
                                </div>
                            </div>

                            {/* Section tabs */}
                            <div className="flex gap-2 mb-5 flex-wrap">
                                {SECTIONS.map(({ key, label, icon: Icon }) => (
                                    <button
                                        key={key}
                                        onClick={() => setActiveSection(key)}
                                        className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                                            activeSection === key
                                                ? 'bg-slate-800 text-white dark:bg-slate-200 dark:text-slate-800'
                                                : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600'
                                        }`}
                                    >
                                        <Icon className="w-4 h-4" />
                                        {label}
                                    </button>
                                ))}
                            </div>

                            {/* ── Top Earners ── */}
                            {activeSection === 'earners' && (
                                <div>
                                    {report.top_earners?.length === 0 ? (
                                        <p className="text-center text-sm text-slate-400 dark:text-slate-500 py-8">No commission data in this period.</p>
                                    ) : (
                                        <div className="overflow-x-auto">
                                            <table className="w-full text-sm border-collapse">
                                                <thead>
                                                    <tr className="bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 text-xs">
                                                        <th className="px-3 py-2 text-left font-semibold">#</th>
                                                        <th className="px-3 py-2 text-left font-semibold">Agent Company</th>
                                                        <th className="px-3 py-2 text-left font-semibold">Short Code</th>
                                                        <th className="px-3 py-2 text-left font-semibold">Location</th>
                                                        <th className="px-3 py-2 text-right font-semibold">Commission (KES)</th>
                                                        <th className="px-3 py-2 text-right font-semibold">Deposits (KES)</th>
                                                        <th className="px-3 py-2 text-right font-semibold">Withdrawals (KES)</th>
                                                        <th className="px-3 py-2 text-right font-semibold">Float (KES)</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {report.top_earners.map((agent, i) => (
                                                        <tr key={agent.agent_company_id} className="border-t border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/50">
                                                            <td className="px-3 py-2.5">
                                                                <span className={`font-bold text-base ${i === 0 ? 'text-yellow-500' : i === 1 ? 'text-slate-400' : i === 2 ? 'text-amber-600' : 'text-slate-300'}`}>
                                                                    {i === 0 ? '①' : i === 1 ? '②' : i === 2 ? '③' : i + 1}
                                                                </span>
                                                            </td>
                                                            <td className="px-3 py-2.5">
                                                                <p className="font-semibold text-slate-800 dark:text-white">{agent.company_name}</p>
                                                                {agent.store_number && <p className="text-xs text-slate-400">Store: {agent.store_number}</p>}
                                                                {agent.user_agents?.length > 0 && (
                                                                    <div className="flex flex-wrap gap-1 mt-1">
                                                                        {agent.user_agents.map((ua, j) => (
                                                                            <span key={j} className={`text-xs px-2 py-0.5 rounded-full ${ua.is_authentic ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300' : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'}`}>
                                                                                {ua.name}
                                                                            </span>
                                                                        ))}
                                                                    </div>
                                                                )}
                                                            </td>
                                                            <td className="px-3 py-2.5 font-mono text-xs text-slate-500 dark:text-slate-400">{agent.short_code || '—'}</td>
                                                            <td className="px-3 py-2.5 text-xs text-slate-500 dark:text-slate-400">{agent.location || '—'}</td>
                                                            <td className="px-3 py-2.5 text-right font-bold text-emerald-600 dark:text-emerald-400">{fmt(agent.total_commission)}</td>
                                                            <td className="px-3 py-2.5 text-right text-slate-700 dark:text-slate-300">{fmt(agent.total_deposits)}</td>
                                                            <td className="px-3 py-2.5 text-right text-slate-700 dark:text-slate-300">{fmt(agent.total_withdrawals)}</td>
                                                            <td className="px-3 py-2.5 text-right text-slate-700 dark:text-slate-300">{fmt(agent.current_float_balance)}</td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* ── Below Threshold ── */}
                            {activeSection === 'threshold' && (
                                <div>
                                    {report.below_threshold?.length === 0 ? (
                                        <div className="flex flex-col items-center justify-center py-10 text-slate-400 dark:text-slate-500">
                                            <Users className="w-10 h-10 mb-2 text-emerald-400" />
                                            <p className="text-sm font-medium text-emerald-600 dark:text-emerald-400">All agents are above the defined thresholds.</p>
                                        </div>
                                    ) : (
                                        <div className="overflow-x-auto">
                                            <table className="w-full text-sm border-collapse">
                                                <thead>
                                                    <tr className="bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 text-xs">
                                                        <th className="px-3 py-2 text-left font-semibold">Agent Company</th>
                                                        <th className="px-3 py-2 text-left font-semibold">Short Code</th>
                                                        <th className="px-3 py-2 text-left font-semibold">Location</th>
                                                        <th className="px-3 py-2 text-right font-semibold">Float (KES)</th>
                                                        <th className="px-3 py-2 text-right font-semibold">Commission (KES)</th>
                                                        <th className="px-3 py-2 text-left font-semibold">Status</th>
                                                        <th className="px-3 py-2 text-left font-semibold">Flags</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {report.below_threshold.map((agent, i) => (
                                                        <tr key={agent.agent_company_id || i} className="border-t border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/50">
                                                            <td className="px-3 py-2.5">
                                                                <p className="font-semibold text-slate-800 dark:text-white">{agent.company_name}</p>
                                                                {agent.store_number && <p className="text-xs text-slate-400">Store: {agent.store_number}</p>}
                                                            </td>
                                                            <td className="px-3 py-2.5 font-mono text-xs text-slate-500 dark:text-slate-400">{agent.short_code || '—'}</td>
                                                            <td className="px-3 py-2.5 text-xs text-slate-500 dark:text-slate-400">{agent.location}</td>
                                                            <td className={`px-3 py-2.5 text-right font-semibold ${agent.below_float ? 'text-red-600 dark:text-red-400' : 'text-slate-700 dark:text-slate-300'}`}>
                                                                {fmt(agent.float_balance)}
                                                                {agent.below_float && (
                                                                    <span className="ml-1 text-xs bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300 px-1.5 py-0.5 rounded-full">LOW</span>
                                                                )}
                                                            </td>
                                                            <td className={`px-3 py-2.5 text-right font-semibold ${agent.below_commission ? 'text-amber-600 dark:text-amber-400' : 'text-slate-700 dark:text-slate-300'}`}>
                                                                {fmt(agent.period_commission)}
                                                                {agent.below_commission && (
                                                                    <span className="ml-1 text-xs bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300 px-1.5 py-0.5 rounded-full">LOW</span>
                                                                )}
                                                            </td>
                                                            <td className="px-3 py-2.5">
                                                                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${agent.status === 'active' ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300' : 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300'}`}>
                                                                    {agent.status}
                                                                </span>
                                                            </td>
                                                            <td className="px-3 py-2.5">
                                                                <div className="space-y-0.5">
                                                                    {agent.reasons.map((r, j) => (
                                                                        <p key={j} className="text-xs text-slate-500 dark:text-slate-400">• {r}</p>
                                                                    ))}
                                                                </div>
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* ── Fraud Flagged ── */}
                            {activeSection === 'fraud' && (
                                <div>
                                    {/* Fraud category mini summary */}
                                    <div className="grid grid-cols-3 gap-3 mb-5">
                                        {[
                                            { key: 'split_transaction', color: 'red', count: summary.split_transaction_count },
                                            { key: 'high_frequency_daily', color: 'amber', count: summary.high_frequency_daily_count },
                                            { key: 'rapid_back_forth', color: 'purple', count: summary.rapid_back_forth_count },
                                        ].map(({ key, color, count }) => {
                                            const meta = FRAUD_CAT_META[key];
                                            const bg = { red: 'bg-red-50 dark:bg-red-900/20', amber: 'bg-amber-50 dark:bg-amber-900/20', purple: 'bg-purple-50 dark:bg-purple-900/20' };
                                            const text = { red: 'text-red-600 dark:text-red-400', amber: 'text-amber-600 dark:text-amber-400', purple: 'text-purple-600 dark:text-purple-400' };
                                            return (
                                                <div key={key} className={`${bg[color]} rounded-xl p-3 text-center`}>
                                                    <p className={`text-xs font-semibold ${text[color]} mb-1`}>{meta.label}</p>
                                                    <p className={`text-2xl font-bold ${text[color]}`}>{count || 0}</p>
                                                </div>
                                            );
                                        })}
                                    </div>

                                    {totalFraud === 0 ? (
                                        <div className="flex flex-col items-center justify-center py-10 text-slate-400 dark:text-slate-500">
                                            <ShieldAlert className="w-10 h-10 mb-2 text-green-400" />
                                            <p className="text-sm font-medium text-green-600 dark:text-green-400">No fraud patterns detected in this period.</p>
                                        </div>
                                    ) : (
                                        Object.entries(FRAUD_CAT_META).map(([key]) => (
                                            <FraudCategoryPanel
                                                key={key}
                                                categoryKey={key}
                                                findings={fraudData.categories?.[key] || []}
                                            />
                                        ))
                                    )}
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
