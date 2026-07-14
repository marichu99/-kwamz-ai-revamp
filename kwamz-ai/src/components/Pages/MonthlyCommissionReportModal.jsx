import { useState, useEffect, useCallback } from 'react';
import {
    X, ChevronDown, TrendingUp, TrendingDown, Minus,
    Loader2, BarChart3, Building2, ArrowUpDown, ArrowUp, ArrowDown,
    FileSpreadsheet, FileText,
} from 'lucide-react';
import axios from 'axios';
import config from '../../Config';
import { CompanyDropdown } from '../Dashboard/DashboardHeader';

const API = config.API_URL || 'http://localhost:5000';
const token = () => localStorage.getItem('token');

const fmt = (n) =>
    Number(n || 0).toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const pct = (n) => (n == null ? '—' : `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`);

function MoMBadge({ change, pctVal }) {
    if (change == null) return null;
    if (Math.abs(change) < 0.01) return (
        <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-500">
            <Minus className="w-3 h-3" /> 0%
        </span>
    );
    const up = change > 0;
    return (
        <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium
            ${up ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                 : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'}`}>
            {up ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
            {pct(pctVal)}
        </span>
    );
}

function SortHeader({ label, field, sortField, sortDir, onSort }) {
    const active = sortField === field;
    return (
        <th
            className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider cursor-pointer select-none hover:text-slate-700 dark:hover:text-slate-200 transition-colors"
            onClick={() => onSort(field)}
        >
            <span className="flex items-center gap-1">
                {label}
                {active
                    ? sortDir === 'asc'
                        ? <ArrowUp className="w-3 h-3 text-purple-500" />
                        : <ArrowDown className="w-3 h-3 text-purple-500" />
                    : <ArrowUpDown className="w-3 h-3 opacity-30" />}
            </span>
        </th>
    );
}

export default function MonthlyCommissionReportModal({ isOpen, onClose }) {
    const now = new Date();
    const [year, setYear]   = useState(now.getFullYear());
    const [month, setMonth] = useState(now.getMonth() + 1);
    const [report, setReport]   = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError]     = useState(null);
    const [sortField, setSortField] = useState('amount');
    const [sortDir, setSortDir]     = useState('desc');
    const [search, setSearch]       = useState('');
    const [exporting, setExporting] = useState(null); // 'pdf' | 'excel' | null
    // Companies linked to the logged-in user; null = all companies
    const [companies, setCompanies] = useState([]);
    const [selectedCompany, setSelectedCompany] = useState(null);

    const MONTH_NAMES = [
        'January','February','March','April','May','June',
        'July','August','September','October','November','December',
    ];
    const yearOptions = [now.getFullYear(), now.getFullYear() - 1, now.getFullYear() - 2];

    const fetchReport = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const { data } = await axios.get(
                `${API}/transactions/monthly-commission-report`,
                {
                    params: { year, month, ...(selectedCompany ? { company_id: selectedCompany.id } : {}) },
                    headers: { Authorization: `Bearer ${token()}` },
                }
            );
            if (data.success) setReport(data.data);
            else setError(data.error || 'Failed to load report');
        } catch (e) {
            setError(e.response?.data?.error || 'Failed to load report');
        } finally {
            setLoading(false);
        }
    }, [year, month, selectedCompany]);

    useEffect(() => { if (isOpen) fetchReport(); }, [isOpen, fetchReport]);

    // Load the user's companies once, when the modal first opens
    useEffect(() => {
        if (!isOpen || companies.length > 0) return;
        axios.get(`${API}/transactions/user-companies`, {
            headers: { Authorization: `Bearer ${token()}` },
        })
            .then(({ data }) => { if (data.success) setCompanies(data.data); })
            .catch(() => { /* dropdown simply stays hidden */ });
    }, [isOpen, companies.length]);

    const handleExport = async (format) => {
        setExporting(format);
        try {
            const endpoint = format === 'pdf'
                ? '/transactions/monthly-commission-report-pdf'
                : '/transactions/monthly-commission-report-excel';
            const resp = await axios.get(`${API}${endpoint}`, {
                params: { year, month, ...(selectedCompany ? { company_id: selectedCompany.id } : {}) },
                headers: { Authorization: `Bearer ${token()}` },
                responseType: 'blob',
            });
            const ext = format === 'pdf' ? 'pdf' : 'xlsx';
            const mime = format === 'pdf'
                ? 'application/pdf'
                : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
            const url = URL.createObjectURL(new Blob([resp.data], { type: mime }));
            const a = document.createElement('a');
            a.href = url;
            a.download = `monthly_commission_${report?.label?.replace(' ', '_') ?? ''}.${ext}`;
            a.click();
            URL.revokeObjectURL(url);
        } catch {
            alert(`Failed to export ${format.toUpperCase()}`);
        } finally {
            setExporting(null);
        }
    };

    const handleSort = (field) => {
        if (sortField === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
        else { setSortField(field); setSortDir('desc'); }
    };

    const tills = report?.tills ?? [];
    const filtered = tills.filter(t =>
        !search || t.company_name?.toLowerCase().includes(search.toLowerCase())
            || t.shortcode?.includes(search)
    );
    const sorted = [...filtered].sort((a, b) => {
        const av = a[sortField] ?? 0;
        const bv = b[sortField] ?? 0;
        const cmp = typeof av === 'string' ? av.localeCompare(bv) : av - bv;
        return sortDir === 'asc' ? cmp : -cmp;
    });

    if (!isOpen) return null;

    const s = report?.summary;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
            <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden">

                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700 shrink-0">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-xl bg-purple-100 dark:bg-purple-900/30">
                            <BarChart3 className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-slate-800 dark:text-white">Monthly Commission Rollup</h2>
                            <p className="text-xs text-slate-500 dark:text-slate-400">
                                Aggregator roll-up per till · {report?.label ?? '…'}
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => handleExport('excel')}
                            disabled={!report || exporting !== null}
                            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800 hover:bg-emerald-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            {exporting === 'excel' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileSpreadsheet className="w-3.5 h-3.5" />}
                            Excel
                        </button>
                        <button
                            onClick={() => handleExport('pdf')}
                            disabled={!report || exporting !== null}
                            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 border border-red-200 dark:border-red-800 hover:bg-red-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            {exporting === 'pdf' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileText className="w-3.5 h-3.5" />}
                            PDF
                        </button>
                        <button onClick={onClose} className="p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
                            <X className="w-5 h-5 text-slate-500" />
                        </button>
                    </div>
                </div>

                {/* Controls */}
                <div className="flex flex-wrap items-center gap-3 px-6 py-4 border-b border-slate-100 dark:border-slate-800 shrink-0 bg-slate-50 dark:bg-slate-800/50">
                    {/* Month */}
                    <div className="flex items-center gap-2">
                        <label className="text-xs font-medium text-slate-500 dark:text-slate-400">Month</label>
                        <div className="relative">
                            <select
                                value={month}
                                onChange={e => setMonth(Number(e.target.value))}
                                className="appearance-none pl-3 pr-7 py-1.5 text-sm font-medium rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-400"
                            >
                                {MONTH_NAMES.map((m, i) => <option key={i+1} value={i+1}>{m}</option>)}
                            </select>
                            <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 pointer-events-none" />
                        </div>
                    </div>
                    {/* Year */}
                    <div className="flex items-center gap-2">
                        <label className="text-xs font-medium text-slate-500 dark:text-slate-400">Year</label>
                        <div className="relative">
                            <select
                                value={year}
                                onChange={e => setYear(Number(e.target.value))}
                                className="appearance-none pl-3 pr-7 py-1.5 text-sm font-medium rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-400"
                            >
                                {yearOptions.map(y => <option key={y} value={y}>{y}</option>)}
                            </select>
                            <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 pointer-events-none" />
                        </div>
                    </div>
                    {/* Company (scoped to the logged-in user) */}
                    {companies.length > 0 && (
                        <CompanyDropdown
                            companies={companies}
                            selectedCompany={selectedCompany}
                            onCompanyChange={setSelectedCompany}
                        />
                    )}
                    {/* Search */}
                    <input
                        type="text"
                        placeholder="Search company or shortcode…"
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        className="ml-auto px-3 py-1.5 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-400 w-56"
                    />
                    {/* Available months pills */}
                    {report?.available_months?.length > 0 && (
                        <div className="flex flex-wrap gap-1 w-full mt-1">
                            <span className="text-xs text-slate-400 mr-1 self-center">Available:</span>
                            {report.available_months.slice(0, 8).map(m => (
                                <button
                                    key={`${m.year}-${m.month}`}
                                    onClick={() => { setYear(m.year); setMonth(m.month); }}
                                    className={`text-xs px-2 py-0.5 rounded-full border transition-colors
                                        ${m.year === year && m.month === month
                                            ? 'bg-purple-500 text-white border-purple-500'
                                            : 'border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:border-purple-400 hover:text-purple-600'
                                        }`}
                                >
                                    {m.label}
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                {/* Body */}
                <div className="flex-1 overflow-y-auto px-6 py-4">
                    {loading && (
                        <div className="flex items-center justify-center py-16 gap-3 text-slate-400">
                            <Loader2 className="w-6 h-6 animate-spin" />
                            <span>Loading report…</span>
                        </div>
                    )}
                    {error && !loading && (
                        <div className="text-center py-12 text-red-500">{error}</div>
                    )}

                    {!loading && !error && report && (
                        <>
                            {/* Summary cards */}
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
                                <div className="bg-purple-50 dark:bg-purple-900/20 rounded-xl p-4 border border-purple-100 dark:border-purple-800/40">
                                    <p className="text-xs text-purple-500 font-semibold uppercase tracking-wide mb-1">Total Rolled Up</p>
                                    <p className="text-xl font-bold text-slate-800 dark:text-white">KES {fmt(s?.total_amount)}</p>
                                    <div className="mt-1"><MoMBadge change={s?.mom_change} pctVal={s?.mom_pct} /></div>
                                </div>
                                <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-4 border border-slate-200 dark:border-slate-700">
                                    <p className="text-xs text-slate-500 font-semibold uppercase tracking-wide mb-1">Prev Month</p>
                                    <p className="text-xl font-bold text-slate-700 dark:text-slate-200">KES {fmt(s?.prev_total_amount)}</p>
                                    <p className="text-xs text-slate-400 mt-1">{report.prev_label}</p>
                                </div>
                                <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-4 border border-slate-200 dark:border-slate-700">
                                    <p className="text-xs text-slate-500 font-semibold uppercase tracking-wide mb-1">MoM Change</p>
                                    <p className={`text-xl font-bold ${(s?.mom_change ?? 0) >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                                        KES {fmt(Math.abs(s?.mom_change ?? 0))}
                                    </p>
                                    <p className="text-xs text-slate-400 mt-1">{pct(s?.mom_pct)}</p>
                                </div>
                                <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-4 border border-slate-200 dark:border-slate-700">
                                    <p className="text-xs text-slate-500 font-semibold uppercase tracking-wide mb-1">Tills</p>
                                    <p className="text-xl font-bold text-slate-800 dark:text-white">{s?.till_count ?? 0}</p>
                                    <p className="text-xs text-slate-400 mt-1">with rollup data</p>
                                </div>
                            </div>

                            {/* Table */}
                            {sorted.length === 0 ? (
                                <div className="text-center py-12 text-slate-400">
                                    <Building2 className="w-10 h-10 mx-auto mb-2 opacity-30" />
                                    <p>No rollup data for this period</p>
                                </div>
                            ) : (
                                <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
                                    <table className="w-full text-sm">
                                        <thead className="bg-slate-50 dark:bg-slate-800/70">
                                            <tr>
                                                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider w-8">#</th>
                                                <SortHeader label="Company / Till" field="company_name" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                                                <SortHeader label="Shortcode" field="shortcode" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                                                <SortHeader label="Rolled Up (KES)" field="amount" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                                                <SortHeader label="Prev Month (KES)" field="prev_amount" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                                                <SortHeader label="MoM Change" field="mom_change" sortField={sortField} sortDir={sortDir} onSort={handleSort} />
                                                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Receipt</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                                            {sorted.map((t, i) => (
                                                <tr key={t.receipt_no} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                                                    <td className="px-4 py-3 text-xs text-slate-400">{i + 1}</td>
                                                    <td className="px-4 py-3">
                                                        <p className="font-medium text-slate-800 dark:text-slate-200 text-xs leading-snug">{t.company_name || '—'}</p>
                                                        {t.location && t.location !== '—' && (
                                                            <p className="text-xs text-slate-400">{t.location}</p>
                                                        )}
                                                    </td>
                                                    <td className="px-4 py-3">
                                                        <span className="text-xs font-mono bg-slate-100 dark:bg-slate-700 px-2 py-0.5 rounded">
                                                            {t.shortcode}
                                                        </span>
                                                    </td>
                                                    <td className="px-4 py-3 font-semibold text-slate-800 dark:text-white tabular-nums">
                                                        {fmt(t.amount)}
                                                    </td>
                                                    <td className="px-4 py-3 text-slate-500 dark:text-slate-400 tabular-nums text-xs">
                                                        {fmt(t.prev_amount)}
                                                    </td>
                                                    <td className="px-4 py-3">
                                                        <MoMBadge change={t.mom_change} pctVal={t.mom_pct} />
                                                    </td>
                                                    <td className="px-4 py-3 text-xs font-mono text-slate-400">
                                                        {t.receipt_no}
                                                    </td>
                                                </tr>
                                            ))}
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
