import { useState, useCallback, useEffect } from 'react';
import {
    X,
    Droplets,
    ChevronDown,
    Calendar,
    Loader2,
    Activity,
    Search,
    ArrowUpDown,
    ArrowUp,
    ArrowDown,
    Users,
    TrendingUp,
    TrendingDown,
    AlertTriangle,
    ShieldAlert,
    CheckCircle2,
    HelpCircle,
} from 'lucide-react';
import axios from 'axios';
import config from '../../Config';
import { useToast } from './ToastProvider';

const PERIOD_TYPES = [
    { value: 'weekly', label: 'Weekly' },
    { value: 'monthly', label: 'Monthly' },
    { value: 'quarterly', label: 'Quarterly' },
    { value: 'semi_annual', label: 'Semi-Annually' },
    { value: 'yearly', label: 'Yearly' },
    { value: 'custom', label: 'Date Range' },
];

const MONTH_NAMES = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
];

const HEALTH_META = {
    healthy:  { label: 'Healthy',  icon: CheckCircle2,   badge: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' },
    low:      { label: 'Low',      icon: AlertTriangle,  badge: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300' },
    critical: { label: 'Critical', icon: ShieldAlert,    badge: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300' },
    no_data:  { label: 'No Data',  icon: HelpCircle,     badge: 'bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400' },
};

const fmt = (n) => Number(n || 0).toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function getIsoWeek(d) {
    const date = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
    const dayNum = date.getUTCDay() || 7;
    date.setUTCDate(date.getUTCDate() + 4 - dayNum);
    const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
    const week = Math.ceil((((date - yearStart) / 86400000) + 1) / 7);
    return { year: date.getUTCFullYear(), week };
}

function SortHeader({ label, field, sortField, sortDir, onSort, align = 'left' }) {
    const active = sortField === field;
    return (
        <th
            className={`px-3 py-2.5 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider cursor-pointer select-none hover:text-slate-700 dark:hover:text-slate-200 transition-colors ${align === 'right' ? 'text-right' : 'text-left'}`}
            onClick={() => onSort(field)}
        >
            <span className={`flex items-center gap-1 ${align === 'right' ? 'justify-end' : ''}`}>
                {label}
                {active
                    ? (sortDir === 'asc' ? <ArrowUp className="w-3 h-3 text-blue-500" /> : <ArrowDown className="w-3 h-3 text-blue-500" />)
                    : <ArrowUpDown className="w-3 h-3 opacity-30" />}
            </span>
        </th>
    );
}

export default function FloatHealthReportModal({ isOpen, onClose, companyId }) {
    const { showToast } = useToast();
    const now = new Date();
    const nowWeek = getIsoWeek(now);

    const [periodType, setPeriodType] = useState('monthly');
    const [year, setYear] = useState(now.getFullYear());
    const [month, setMonth] = useState(now.getMonth() + 1);
    const [quarter, setQuarter] = useState(Math.floor(now.getMonth() / 3) + 1);
    const [half, setHalf] = useState(now.getMonth() < 6 ? 1 : 2);
    const [week, setWeek] = useState(nowWeek.week);
    const [customStart, setCustomStart] = useState('');
    const [customEnd, setCustomEnd] = useState('');
    const [lowThreshold, setLowThreshold] = useState('20000');
    const [criticalThreshold, setCriticalThreshold] = useState('5000');

    const [report, setReport] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [sortField, setSortField] = useState('closing_balance');
    const [sortDir, setSortDir] = useState('asc');
    const [search, setSearch] = useState('');

    const yearOptions = [now.getFullYear(), now.getFullYear() - 1, now.getFullYear() - 2];

    const getParams = useCallback(() => {
        const params = {
            period_type: periodType,
            low_float_threshold: lowThreshold || '20000',
            critical_float_threshold: criticalThreshold || '5000',
            ...(companyId && { company_id: companyId }),
        };
        if (periodType === 'custom') {
            params.start_date = customStart;
            params.end_date = customEnd;
        } else if (periodType === 'weekly') {
            params.year = year;
            params.week = week;
        } else if (periodType === 'monthly') {
            params.year = year;
            params.month = month;
        } else if (periodType === 'quarterly') {
            params.year = year;
            params.quarter = quarter;
        } else if (periodType === 'semi_annual') {
            params.year = year;
            params.half = half;
        } else if (periodType === 'yearly') {
            params.year = year;
        }
        return params;
    }, [periodType, year, month, quarter, half, week, customStart, customEnd, lowThreshold, criticalThreshold, companyId]);

    const fetchReport = useCallback(async () => {
        setIsLoading(true);
        try {
            const token = localStorage.getItem('token');
            const res = await axios.get(`${config.API_URL}/transactions/float-health-report`, {
                headers: { Authorization: `Bearer ${token}` },
                params: getParams(),
            });
            if (res.data.success) {
                setReport(res.data.report);
            } else {
                showToast(res.data.error || 'Failed to generate float health report', 'error');
            }
        } catch (err) {
            showToast(err.response?.data?.error || 'Failed to generate float health report', 'error');
        } finally {
            setIsLoading(false);
        }
    }, [getParams, showToast]);

    useEffect(() => { if (isOpen) fetchReport(); }, [isOpen]); // eslint-disable-line react-hooks/exhaustive-deps

    const handleSort = (field) => {
        if (sortField === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
        else { setSortField(field); setSortDir('desc'); }
    };

    if (!isOpen) return null;

    const s = report?.summary || {};
    const tills = report?.tills || [];
    const filtered = tills.filter(t =>
        !search
        || t.company_name?.toLowerCase().includes(search.toLowerCase())
        || t.short_code?.includes(search)
        || t.user_agents?.some(ua => ua.name?.toLowerCase().includes(search.toLowerCase()))
    );
    const sorted = [...filtered].sort((a, b) => {
        const av = a[sortField] ?? 0;
        const bv = b[sortField] ?? 0;
        const cmp = typeof av === 'string' ? av.localeCompare(bv) : av - bv;
        return sortDir === 'asc' ? cmp : -cmp;
    });

    const canGenerate = periodType !== 'custom' || (customStart && customEnd);

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-6xl max-h-[92vh] flex flex-col">

                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700 shrink-0">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-xl bg-blue-100 dark:bg-blue-900/30">
                            <Droplets className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-slate-800 dark:text-white">Float Health Report</h2>
                            <p className="text-xs text-slate-500 dark:text-slate-400">
                                Per-till float balance health · {report?.label ?? '…'}
                            </p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors">
                        <X className="w-5 h-5 text-slate-500" />
                    </button>
                </div>

                {/* Controls */}
                <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex flex-wrap items-end gap-3 bg-slate-50 dark:bg-slate-800/50 shrink-0">
                    <div className="relative">
                        <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Period</label>
                        <div className="relative">
                            <select
                                value={periodType}
                                onChange={e => setPeriodType(e.target.value)}
                                className="appearance-none pl-3 pr-8 py-2 text-sm font-medium rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-400"
                            >
                                {PERIOD_TYPES.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
                            </select>
                            <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 pointer-events-none" />
                        </div>
                    </div>

                    {periodType === 'weekly' && (
                        <>
                            <div>
                                <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Week</label>
                                <input
                                    type="week"
                                    value={`${year}-W${String(week).padStart(2, '0')}`}
                                    onChange={e => {
                                        const [y, w] = e.target.value.split('-W');
                                        if (y && w) { setYear(Number(y)); setWeek(Number(w)); }
                                    }}
                                    className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700"
                                />
                            </div>
                        </>
                    )}

                    {periodType === 'monthly' && (
                        <>
                            <div>
                                <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Month</label>
                                <select value={month} onChange={e => setMonth(Number(e.target.value))}
                                    className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700">
                                    {MONTH_NAMES.map((m, i) => <option key={i + 1} value={i + 1}>{m}</option>)}
                                </select>
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Year</label>
                                <select value={year} onChange={e => setYear(Number(e.target.value))}
                                    className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700">
                                    {yearOptions.map(y => <option key={y} value={y}>{y}</option>)}
                                </select>
                            </div>
                        </>
                    )}

                    {periodType === 'quarterly' && (
                        <>
                            <div>
                                <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Quarter</label>
                                <select value={quarter} onChange={e => setQuarter(Number(e.target.value))}
                                    className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700">
                                    {[1, 2, 3, 4].map(q => <option key={q} value={q}>Q{q}</option>)}
                                </select>
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Year</label>
                                <select value={year} onChange={e => setYear(Number(e.target.value))}
                                    className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700">
                                    {yearOptions.map(y => <option key={y} value={y}>{y}</option>)}
                                </select>
                            </div>
                        </>
                    )}

                    {periodType === 'semi_annual' && (
                        <>
                            <div>
                                <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Half</label>
                                <select value={half} onChange={e => setHalf(Number(e.target.value))}
                                    className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700">
                                    <option value={1}>H1 (Jan–Jun)</option>
                                    <option value={2}>H2 (Jul–Dec)</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Year</label>
                                <select value={year} onChange={e => setYear(Number(e.target.value))}
                                    className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700">
                                    {yearOptions.map(y => <option key={y} value={y}>{y}</option>)}
                                </select>
                            </div>
                        </>
                    )}

                    {periodType === 'yearly' && (
                        <div>
                            <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Year</label>
                            <select value={year} onChange={e => setYear(Number(e.target.value))}
                                className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700">
                                {yearOptions.map(y => <option key={y} value={y}>{y}</option>)}
                            </select>
                        </div>
                    )}

                    {periodType === 'custom' && (
                        <>
                            <div>
                                <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">From</label>
                                <input type="date" value={customStart} onChange={e => setCustomStart(e.target.value)}
                                    className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700" />
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">To</label>
                                <input type="date" value={customEnd} onChange={e => setCustomEnd(e.target.value)}
                                    className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700" />
                            </div>
                        </>
                    )}

                    <div>
                        <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Low Float (KES)</label>
                        <input type="number" min="0" value={lowThreshold} onChange={e => setLowThreshold(e.target.value)}
                            className="w-28 px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700" />
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Critical Float (KES)</label>
                        <input type="number" min="0" value={criticalThreshold} onChange={e => setCriticalThreshold(e.target.value)}
                            className="w-28 px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700" />
                    </div>

                    <button
                        onClick={fetchReport}
                        disabled={isLoading || !canGenerate}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors"
                    >
                        {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Activity className="w-4 h-4" />}
                        {isLoading ? 'Generating…' : 'Generate Report'}
                    </button>
                </div>

                {/* Body */}
                <div className="flex-1 overflow-y-auto px-6 py-4">
                    {isLoading && (
                        <div className="flex flex-col items-center justify-center h-48 text-slate-400 dark:text-slate-500">
                            <Loader2 className="w-10 h-10 animate-spin mb-3 text-blue-400" />
                            <p className="text-sm">Building float health report…</p>
                        </div>
                    )}

                    {!isLoading && report && (
                        <>
                            {/* Summary cards */}
                            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
                                <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl p-3 border border-blue-100 dark:border-blue-800/40">
                                    <p className="text-xs text-blue-500 font-semibold uppercase tracking-wide mb-1">Tills</p>
                                    <p className="text-xl font-bold text-slate-800 dark:text-white">{s.till_count ?? 0}</p>
                                </div>
                                <div className="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-3 border border-slate-200 dark:border-slate-700">
                                    <p className="text-xs text-slate-500 font-semibold uppercase tracking-wide mb-1">Closing Float</p>
                                    <p className="text-lg font-bold text-slate-800 dark:text-white">{fmt(s.total_closing_float)}</p>
                                </div>
                                <div className="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-3 border border-slate-200 dark:border-slate-700">
                                    <p className="text-xs text-slate-500 font-semibold uppercase tracking-wide mb-1 flex items-center gap-1">
                                        {(s.net_change ?? 0) >= 0 ? <TrendingUp className="w-3 h-3 text-emerald-500" /> : <TrendingDown className="w-3 h-3 text-red-500" />}
                                        Net Change
                                    </p>
                                    <p className={`text-lg font-bold ${(s.net_change ?? 0) >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                                        {fmt(Math.abs(s.net_change ?? 0))}
                                    </p>
                                </div>
                                <div className="bg-emerald-50 dark:bg-emerald-900/20 rounded-xl p-3 text-center">
                                    <p className="text-xs text-emerald-600 dark:text-emerald-400 font-semibold mb-1">Healthy</p>
                                    <p className="text-xl font-bold text-emerald-700 dark:text-emerald-300">{s.healthy_count ?? 0}</p>
                                </div>
                                <div className="bg-amber-50 dark:bg-amber-900/20 rounded-xl p-3 text-center">
                                    <p className="text-xs text-amber-600 dark:text-amber-400 font-semibold mb-1">Low</p>
                                    <p className="text-xl font-bold text-amber-700 dark:text-amber-300">{s.low_count ?? 0}</p>
                                </div>
                                <div className="bg-red-50 dark:bg-red-900/20 rounded-xl p-3 text-center">
                                    <p className="text-xs text-red-600 dark:text-red-400 font-semibold mb-1">Critical</p>
                                    <p className="text-xl font-bold text-red-700 dark:text-red-300">{s.critical_count ?? 0}</p>
                                </div>
                            </div>

                            {/* Search */}
                            <div className="relative mb-4 w-full sm:w-72">
                                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                                <input
                                    type="text"
                                    placeholder="Search till, shortcode, or agent…"
                                    value={search}
                                    onChange={e => setSearch(e.target.value)}
                                    className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-400"
                                />
                            </div>

                            {/* Per-till table */}
                            {sorted.length === 0 ? (
                                <div className="text-center py-12 text-slate-400">
                                    <Droplets className="w-10 h-10 mx-auto mb-2 opacity-30" />
                                    <p>No float data for this period</p>
                                </div>
                            ) : (
                                <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-x-auto">
                                    <table className="w-full text-sm">
                                        <thead className="bg-slate-50 dark:bg-slate-800/70">
                                            <tr>
                                                <SortHeader label="Till / Company" field="company_name" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                                                <th className="px-3 py-2.5 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Agent(s)</th>
                                                <SortHeader label="Opening" field="opening_balance" sortField={sortField} sortDir={sortDir} onSort={handleSort} align="right" />
                                                <SortHeader label="Closing" field="closing_balance" sortField={sortField} sortDir={sortDir} onSort={handleSort} align="right" />
                                                <SortHeader label="Lowest" field="min_balance" sortField={sortField} sortDir={sortDir} onSort={handleSort} align="right" />
                                                <SortHeader label="Net Change" field="net_change" sortField={sortField} sortDir={sortDir} onSort={handleSort} align="right" />
                                                <SortHeader label="Deposits" field="deposits" sortField={sortField} sortDir={sortDir} onSort={handleSort} align="right" />
                                                <SortHeader label="Withdrawals" field="withdrawals" sortField={sortField} sortDir={sortDir} onSort={handleSort} align="right" />
                                                <th className="px-3 py-2.5 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Status</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                                            {sorted.map(t => {
                                                const meta = HEALTH_META[t.health_status] || HEALTH_META.no_data;
                                                const Icon = meta.icon;
                                                return (
                                                    <tr key={t.agent_company_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                                                        <td className="px-3 py-2.5">
                                                            <p className="font-semibold text-slate-800 dark:text-white">{t.company_name}</p>
                                                            <p className="text-xs text-slate-400 dark:text-slate-500">
                                                                {t.short_code || '—'} {t.location && t.location !== '—' ? `· ${t.location}` : ''}
                                                            </p>
                                                        </td>
                                                        <td className="px-3 py-2.5">
                                                            {t.user_agents?.length > 0 ? (
                                                                <div className="flex flex-wrap gap-1 max-w-[10rem]">
                                                                    {t.user_agents.map((ua, j) => (
                                                                        <span key={j} title={ua.phone_number || ''}
                                                                            className={`text-xs px-2 py-0.5 rounded-full ${ua.is_authentic ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300' : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'}`}>
                                                                            {ua.name}
                                                                        </span>
                                                                    ))}
                                                                </div>
                                                            ) : (
                                                                <span className="text-xs text-slate-400 flex items-center gap-1">
                                                                    <Users className="w-3 h-3" /> Unassigned
                                                                </span>
                                                            )}
                                                        </td>
                                                        <td className="px-3 py-2.5 text-right text-slate-600 dark:text-slate-300 tabular-nums">{fmt(t.opening_balance)}</td>
                                                        <td className="px-3 py-2.5 text-right font-semibold text-slate-800 dark:text-white tabular-nums">{fmt(t.closing_balance)}</td>
                                                        <td className="px-3 py-2.5 text-right text-slate-500 dark:text-slate-400 tabular-nums">{fmt(t.min_balance)}</td>
                                                        <td className={`px-3 py-2.5 text-right font-medium tabular-nums ${t.net_change >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                                                            {t.net_change >= 0 ? '+' : '-'}{fmt(Math.abs(t.net_change))}
                                                        </td>
                                                        <td className="px-3 py-2.5 text-right text-emerald-600 dark:text-emerald-400 tabular-nums">{fmt(t.deposits)}</td>
                                                        <td className="px-3 py-2.5 text-right text-red-600 dark:text-red-400 tabular-nums">{fmt(t.withdrawals)}</td>
                                                        <td className="px-3 py-2.5">
                                                            <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full ${meta.badge}`}>
                                                                <Icon className="w-3 h-3" /> {meta.label}
                                                            </span>
                                                        </td>
                                                    </tr>
                                                );
                                            })}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
