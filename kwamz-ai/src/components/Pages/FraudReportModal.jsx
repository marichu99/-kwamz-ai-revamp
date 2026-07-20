import { useState, useCallback, useEffect } from 'react';
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
    AlertTriangle,
    Clock,
    TrendingUp,
    Hash,
    Percent,
} from 'lucide-react';
import axios from 'axios';
import config from '../../Config';
import { useToast } from './ToastProvider';
import { CompanyDropdown } from '../Dashboard/DashboardHeader';

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

const RISK_BADGE = {
    HIGH: 'bg-red-500 text-white',
    MEDIUM: 'bg-amber-500 text-white',
    LOW: 'bg-blue-500 text-white',
};

const RISK_PILL = {
    HIGH: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
    MEDIUM: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
    LOW: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
};

function fmt(n) {
    return Number(n || 0).toLocaleString('en-KE', { minimumFractionDigits: 2 });
}

function SplitFindingCard({ finding, index }) {
    const [expanded, setExpanded] = useState(false);

    const agentCompanies = finding.agent_info?.agent_companies || [];
    const userAgents = finding.agent_info?.user_agents || [];
    const shortcodes = finding.agent_info?.shortcodes || [];
    const riskBadge = RISK_BADGE[finding.risk_level] || RISK_BADGE.LOW;

    return (
        <div className="border border-slate-200 dark:border-slate-600 rounded-xl overflow-hidden mb-3 shadow-sm">
            {/* Header row — always visible */}
            <button
                onClick={() => setExpanded(e => !e)}
                className="w-full flex items-center justify-between px-4 py-3 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-750 transition-colors text-left"
            >
                <div className="flex items-center gap-3 min-w-0">
                    <span className="text-xs font-semibold text-slate-400 dark:text-slate-500 w-6 shrink-0">
                        #{index + 1}
                    </span>
                    <span className={`text-xs font-bold px-2 py-0.5 rounded-full shrink-0 ${riskBadge}`}>
                        {finding.risk_level}
                    </span>
                    <span className="text-sm font-semibold text-slate-800 dark:text-white shrink-0">
                        Split Transaction
                    </span>
                    <span className="text-sm text-slate-600 dark:text-slate-300 truncate">
                        {finding.account_name || '—'}
                    </span>
                    {finding.account_phone && (
                        <span className="text-xs text-slate-400 dark:text-slate-500 font-mono shrink-0 hidden sm:block">
                            {finding.account_phone}
                        </span>
                    )}
                </div>
                <div className="flex items-center gap-3 shrink-0 ml-3">
                    <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                        KES {fmt(finding.anchor_amount)}
                    </span>
                    {expanded
                        ? <ChevronDown className="w-4 h-4 text-slate-400" />
                        : <ChevronRight className="w-4 h-4 text-slate-400" />}
                </div>
            </button>

            {expanded && (
                <div className="px-4 py-4 bg-white dark:bg-slate-800 border-t border-slate-100 dark:border-slate-700 space-y-4">

                    {/* Narrative explanation */}
                    {finding.explanation && (
                        <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed px-4 py-3 bg-slate-50 dark:bg-slate-700/60 rounded-lg">
                            {finding.explanation}
                        </p>
                    )}

                    {/* Key stat cards */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                        <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-3 text-center">
                            <p className="text-xs text-red-500 dark:text-red-400 mb-1">Anchor deposit</p>
                            <p className="text-sm font-bold text-slate-800 dark:text-white">
                                KES {fmt(finding.anchor_amount)}
                            </p>
                        </div>
                        <div className="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-3 text-center">
                            <p className="text-xs text-amber-600 dark:text-amber-400 mb-1">Depositor reclaimed</p>
                            <p className="text-sm font-bold text-slate-800 dark:text-white">
                                KES {fmt(finding.depositor_own_withdrawal)}
                            </p>
                            <p className="text-xs text-amber-500 dark:text-amber-400 mt-0.5 font-semibold">
                                {finding.depositor_withdrawal_pct}% of deposit
                            </p>
                        </div>
                        <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3 text-center">
                            <p className="text-xs text-green-600 dark:text-green-400 mb-1">
                                {finding.subsequent_count} split withdrawals
                            </p>
                            <p className="text-sm font-bold text-slate-800 dark:text-white">
                                KES {fmt(finding.subsequent_total)}
                            </p>
                        </div>
                        <div className="bg-slate-50 dark:bg-slate-700 rounded-lg p-3 text-center">
                            <p className="text-xs text-slate-500 dark:text-slate-400 mb-1">Within</p>
                            <p className="text-sm font-bold text-slate-800 dark:text-white">
                                {finding.time_window_minutes} min
                            </p>
                        </div>
                    </div>

                    {/* Secondary metadata row */}
                    <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-500 dark:text-slate-400 px-1">
                        {finding.unique_withdrawers != null && (
                            <span className="flex items-center gap-1">
                                <Users className="w-3 h-3" />
                                <span className="font-semibold text-slate-700 dark:text-slate-200">
                                    {finding.unique_withdrawers}
                                </span>
                                &nbsp;unique withdrawers
                            </span>
                        )}
                        {finding.coverage_ratio != null && (
                            <span className="flex items-center gap-1">
                                <Percent className="w-3 h-3" />
                                Coverage:&nbsp;
                                <span className={`font-semibold ${
                                    finding.coverage_ratio >= 90 ? 'text-red-600 dark:text-red-400' : 'text-slate-700 dark:text-slate-200'
                                }`}>
                                    {finding.coverage_ratio}%
                                </span>
                            </span>
                        )}
                        <span className="flex items-center gap-1">
                            <Hash className="w-3 h-3" />
                            Till:&nbsp;
                            <span className="font-mono font-semibold text-slate-700 dark:text-slate-200">
                                {finding.business_shortcode || '—'}
                            </span>
                        </span>
                        {(finding.recurring_associates?.length > 0) && (
                            <span className="flex items-center gap-1 text-orange-600 dark:text-orange-400">
                                <AlertTriangle className="w-3 h-3" />
                                <span className="font-semibold">{finding.recurring_associates.length}</span>
                                &nbsp;known repeat suspect{finding.recurring_associates.length !== 1 ? 's' : ''}
                            </span>
                        )}
                    </div>

                    {/* Transaction table */}
                    {finding.transaction_details?.length > 0 && (
                        <div>
                            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-2 uppercase tracking-wide">
                                Transactions
                            </p>
                            <div className="overflow-x-auto rounded-lg border border-slate-100 dark:border-slate-700">
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
                                            <tr
                                                key={i}
                                                className={`border-t border-slate-100 dark:border-slate-700 ${
                                                    txn.is_anchor
                                                        ? 'bg-red-50/60 dark:bg-red-900/10'
                                                        : txn.is_depositor_withdrawal
                                                            ? 'bg-amber-50/70 dark:bg-amber-900/15'
                                                            : 'hover:bg-slate-50 dark:hover:bg-slate-700/40'
                                                }`}
                                            >
                                                <td className="px-3 py-2 font-mono text-slate-600 dark:text-slate-300 whitespace-nowrap">
                                                    {txn.receipt_no}
                                                </td>
                                                <td className="px-3 py-2">
                                                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                                                        txn.type === 'Deposit'
                                                            ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
                                                            : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
                                                    }`}>
                                                        {txn.type}
                                                    </span>
                                                </td>
                                                <td className="px-3 py-2 text-right font-medium text-slate-800 dark:text-white whitespace-nowrap">
                                                    {fmt(txn.amount)}
                                                </td>
                                                <td className="px-3 py-2 text-slate-500 dark:text-slate-400 whitespace-nowrap">
                                                    {txn.time}
                                                </td>
                                                <td className="px-3 py-2 text-slate-600 dark:text-slate-300">
                                                    <div className="flex items-center gap-1.5 flex-wrap">
                                                        <span>{txn.party_name || txn.party_phone || txn.other_party_info || '—'}</span>
                                                        {txn.is_depositor_withdrawal && (
                                                            <span className="text-xs bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300 px-1.5 py-0.5 rounded font-semibold whitespace-nowrap">
                                                                ← depositor
                                                            </span>
                                                        )}
                                                        {txn.is_recurring_suspect && (
                                                            <span className="text-xs bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300 px-1.5 py-0.5 rounded font-semibold whitespace-nowrap">
                                                                ⚑ {txn.recurring_incident_count}× suspect
                                                            </span>
                                                        )}
                                                    </div>
                                                </td>
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
                                <div className="space-y-2">
                                    {agentCompanies.map((ac, i) => (
                                        <div key={i} className="bg-slate-50 dark:bg-slate-700 rounded-lg overflow-hidden">
                                            <div className="flex items-center gap-3 text-sm text-slate-700 dark:text-slate-300 px-3 py-2 flex-wrap">
                                                <span className="font-semibold">{ac.company_name}</span>
                                                {ac.short_code && (
                                                    <span className="text-xs text-slate-400">SC: {ac.short_code}</span>
                                                )}
                                                {ac.location && (
                                                    <span className="text-xs text-slate-400">{ac.location}</span>
                                                )}
                                                {ac.fraud_risk_level && (
                                                    <span className={`ml-auto text-xs font-semibold px-2 py-0.5 rounded-full ${RISK_PILL[ac.fraud_risk_level?.toUpperCase()] || RISK_PILL.LOW}`}>
                                                        {ac.fraud_risk_level.toLowerCase()}
                                                    </span>
                                                )}
                                            </div>
                                            {userAgents.length > 0 && (
                                                <div className="border-t border-slate-200 dark:border-slate-600 px-3 py-2">
                                                    <p className="text-xs font-medium text-slate-400 dark:text-slate-500 mb-1.5 flex items-center gap-1">
                                                        <Users className="w-3 h-3" /> User Agents
                                                    </p>
                                                    <div className="flex flex-wrap gap-2">
                                                        {userAgents.map((ua, j) => (
                                                            <div key={j} className="text-xs bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 px-2.5 py-1.5 rounded-lg flex items-center gap-1.5">
                                                                <span className="font-medium">{ua.name}</span>
                                                                {ua.phone_number && (
                                                                    <span className="opacity-70 font-mono">{ua.phone_number}</span>
                                                                )}
                                                                {ua.is_authentic === false && (
                                                                    <span className="text-red-500 font-semibold">· Unverified</span>
                                                                )}
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
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
                </div>
            )}
        </div>
    );
}

const TYPE_LABELS = {
    split_transaction: 'Split Transaction',
    split_deposit: 'Split Deposit',
    continuous_rapid_activity: 'Continuous Rapid Activity',
};

function GenericFindingCard({ finding, index }) {
    const [expanded, setExpanded] = useState(false);
    const riskBadge = RISK_BADGE[finding.risk_level] || RISK_BADGE.LOW;
    const label = TYPE_LABELS[finding.fraud_type] || finding.fraud_type;
    const agentCompanies = finding.agent_info?.agent_companies || [];
    const userAgents = finding.agent_info?.user_agents || [];
    const shortcodes = finding.agent_info?.shortcodes || [];

    return (
        <div className="border border-slate-200 dark:border-slate-600 rounded-xl overflow-hidden mb-3 shadow-sm">
            <button
                onClick={() => setExpanded(e => !e)}
                className="w-full flex items-center justify-between px-4 py-3 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-750 transition-colors text-left"
            >
                <div className="flex items-center gap-3 min-w-0">
                    <span className="text-xs font-semibold text-slate-400 dark:text-slate-500 w-6 shrink-0">
                        #{index + 1}
                    </span>
                    <span className={`text-xs font-bold px-2 py-0.5 rounded-full shrink-0 ${riskBadge}`}>
                        {finding.risk_level}
                    </span>
                    <span className="text-sm font-semibold text-slate-800 dark:text-white shrink-0">
                        {label}
                    </span>
                    <span className="text-sm text-slate-600 dark:text-slate-300 truncate">
                        {finding.account_name || (finding.business_shortcode ? `Till ${finding.business_shortcode}` : '—')}
                    </span>
                    {finding.account_phone && (
                        <span className="text-xs text-slate-400 dark:text-slate-500 font-mono shrink-0 hidden sm:block">
                            {finding.account_phone}
                        </span>
                    )}
                </div>
                <div className="flex items-center gap-3 shrink-0 ml-3">
                    <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                        KES {fmt(finding.total_amount)}
                    </span>
                    {expanded
                        ? <ChevronDown className="w-4 h-4 text-slate-400" />
                        : <ChevronRight className="w-4 h-4 text-slate-400" />}
                </div>
            </button>

            {expanded && (
                <div className="px-4 py-4 bg-white dark:bg-slate-800 border-t border-slate-100 dark:border-slate-700 space-y-4">
                    {finding.explanation && (
                        <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed px-4 py-3 bg-slate-50 dark:bg-slate-700/60 rounded-lg">
                            {finding.explanation}
                        </p>
                    )}

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                        <div className="bg-slate-50 dark:bg-slate-700 rounded-lg p-3 text-center">
                            <p className="text-xs text-slate-500 dark:text-slate-400 mb-1">Transactions</p>
                            <p className="text-sm font-bold text-slate-800 dark:text-white">
                                {finding.transaction_count}
                            </p>
                        </div>
                        <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-3 text-center">
                            <p className="text-xs text-red-500 dark:text-red-400 mb-1">Total amount</p>
                            <p className="text-sm font-bold text-slate-800 dark:text-white">
                                KES {fmt(finding.total_amount)}
                            </p>
                        </div>
                        <div className="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-3 text-center">
                            <p className="text-xs text-amber-600 dark:text-amber-400 mb-1">
                                {finding.fraud_type === 'continuous_rapid_activity' ? 'Non-stop for' : 'Within'}
                            </p>
                            <p className="text-sm font-bold text-slate-800 dark:text-white">
                                {finding.span_minutes} min
                            </p>
                        </div>
                        <div className="bg-slate-50 dark:bg-slate-700 rounded-lg p-3 text-center">
                            <p className="text-xs text-slate-500 dark:text-slate-400 mb-1">Till</p>
                            <p className="text-sm font-bold text-slate-800 dark:text-white font-mono">
                                {finding.business_shortcode || '—'}
                            </p>
                        </div>
                    </div>

                    {/* Extra badges */}
                    <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-500 dark:text-slate-400 px-1">
                        {finding.cap_structuring && (
                            <span className="flex items-center gap-1 text-red-600 dark:text-red-400 font-semibold">
                                <AlertTriangle className="w-3 h-3" />
                                Combined amount exceeds the single-deposit cap
                            </span>
                        )}
                        {finding.unique_parties != null && (
                            <span className="flex items-center gap-1">
                                <Users className="w-3 h-3" />
                                <span className="font-semibold text-slate-700 dark:text-slate-200">
                                    {finding.unique_parties}
                                </span>
                                &nbsp;distinct parties
                            </span>
                        )}
                        {finding.deposit_count != null && (
                            <span>
                                {finding.deposit_count} deposits · {finding.withdrawal_count} withdrawals
                            </span>
                        )}
                    </div>

                    {finding.transaction_details?.length > 0 && (
                        <div>
                            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-2 uppercase tracking-wide">
                                Transactions
                            </p>
                            <div className="overflow-x-auto max-h-80 overflow-y-auto rounded-lg border border-slate-100 dark:border-slate-700">
                                <table className="w-full text-xs border-collapse">
                                    <thead className="sticky top-0">
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
                                            <tr key={i} className="border-t border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/40">
                                                <td className="px-3 py-2 font-mono text-slate-600 dark:text-slate-300 whitespace-nowrap">
                                                    {txn.receipt_no}
                                                </td>
                                                <td className="px-3 py-2">
                                                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                                                        txn.type === 'Deposit'
                                                            ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
                                                            : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
                                                    }`}>
                                                        {txn.type}
                                                    </span>
                                                </td>
                                                <td className="px-3 py-2 text-right font-medium text-slate-800 dark:text-white whitespace-nowrap">
                                                    {fmt(txn.amount)}
                                                </td>
                                                <td className="px-3 py-2 text-slate-500 dark:text-slate-400 whitespace-nowrap">
                                                    {txn.time}
                                                </td>
                                                <td className="px-3 py-2 text-slate-600 dark:text-slate-300">
                                                    {txn.party_name || txn.party_phone || txn.other_party_info || '—'}
                                                </td>
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
                                <div className="space-y-2">
                                    {agentCompanies.map((ac, i) => (
                                        <div key={i} className="bg-slate-50 dark:bg-slate-700 rounded-lg overflow-hidden">
                                            <div className="flex items-center gap-3 text-sm text-slate-700 dark:text-slate-300 px-3 py-2 flex-wrap">
                                                <span className="font-semibold">{ac.company_name}</span>
                                                {ac.short_code && (
                                                    <span className="text-xs text-slate-400">SC: {ac.short_code}</span>
                                                )}
                                                {ac.location && (
                                                    <span className="text-xs text-slate-400">{ac.location}</span>
                                                )}
                                                {ac.fraud_risk_level && (
                                                    <span className={`ml-auto text-xs font-semibold px-2 py-0.5 rounded-full ${RISK_PILL[ac.fraud_risk_level?.toUpperCase()] || RISK_PILL.LOW}`}>
                                                        {ac.fraud_risk_level.toLowerCase()}
                                                    </span>
                                                )}
                                            </div>
                                            {userAgents.length > 0 && (
                                                <div className="border-t border-slate-200 dark:border-slate-600 px-3 py-2">
                                                    <p className="text-xs font-medium text-slate-400 dark:text-slate-500 mb-1.5 flex items-center gap-1">
                                                        <Users className="w-3 h-3" /> User Agents
                                                    </p>
                                                    <div className="flex flex-wrap gap-2">
                                                        {userAgents.map((ua, j) => (
                                                            <div key={j} className="text-xs bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 px-2.5 py-1.5 rounded-lg flex items-center gap-1.5">
                                                                <span className="font-medium">{ua.name}</span>
                                                                {ua.phone_number && (
                                                                    <span className="opacity-70 font-mono">{ua.phone_number}</span>
                                                                )}
                                                                {ua.is_authentic === false && (
                                                                    <span className="text-red-500 font-semibold">· Unverified</span>
                                                                )}
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
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
    // Companies linked to the logged-in user; null = all companies
    const [companies, setCompanies] = useState([]);
    const [selectedCompany, setSelectedCompany] = useState(null);

    const effectiveCompanyId = selectedCompany?.id ?? companyId;

    // Load the user's companies once, when the modal first opens
    useEffect(() => {
        if (!isOpen || companies.length > 0) return;
        const token = localStorage.getItem('token');
        axios.get(`${config.API_URL}/transactions/user-companies`, {
            headers: { Authorization: `Bearer ${token}` },
        })
            .then(({ data }) => { if (data.success) setCompanies(data.data); })
            .catch(() => { /* dropdown simply stays hidden */ });
    }, [isOpen, companies.length]);

    const fetchReport = useCallback(async () => {
        setIsLoading(true);
        setReport(null);
        try {
            const token = localStorage.getItem('token');
            const params = {
                date_range: dateRange,
                ...(dateRange === 'custom' && { start_date: customStartDate, end_date: customEndDate }),
                ...(effectiveCompanyId && { company_id: effectiveCompanyId }),
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
    }, [dateRange, customStartDate, customEndDate, effectiveCompanyId, showToast]);

    const exportPdf = useCallback(async () => {
        setIsExporting(true);
        try {
            const token = localStorage.getItem('token');
            const params = {
                date_range: dateRange,
                ...(dateRange === 'custom' && { start_date: customStartDate, end_date: customEndDate }),
                ...(effectiveCompanyId && { company_id: effectiveCompanyId }),
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
            a.download = `split_fraud_report_${new Date().toISOString().slice(0, 10)}.pdf`;
            a.click();
            URL.revokeObjectURL(url);
            showToast('Fraud report exported as PDF', 'success');
        } catch {
            showToast('Failed to export PDF', 'error');
        } finally {
            setIsExporting(false);
        }
    }, [dateRange, customStartDate, customEndDate, effectiveCompanyId, showToast]);

    if (!isOpen) return null;

    // Show all split-style findings: classic split, split deposits, continuous rapid activity
    const SHOWN_TYPES = ['split_transaction', 'split_deposit', 'continuous_rapid_activity'];
    const allFindings = report?.findings || [];
    const findings = allFindings.filter(f => SHOWN_TYPES.includes(f.fraud_type));
    const summary = report?.summary;

    // Compute stats from filtered findings
    const highRisk = findings.filter(f => f.risk_level === 'HIGH').length;
    const mediumRisk = findings.filter(f => f.risk_level === 'MEDIUM').length;
    const lowRisk = findings.filter(f => f.risk_level === 'LOW').length;
    const totalKesAtRisk = findings.reduce(
        (s, f) => s + Number(f.anchor_amount ?? f.total_amount ?? 0), 0);
    const splitOnly = findings.filter(f => f.fraud_type === 'split_transaction');
    const avgSplits = splitOnly.length
        ? (splitOnly.reduce((s, f) => s + Number(f.subsequent_count || 0), 0) / splitOnly.length).toFixed(1)
        : '—';
    const tillsAffected = new Set(findings.map(f => f.business_shortcode).filter(Boolean)).size;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col">

                {/* ── Header ── */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
                    <div className="flex items-center gap-3">
                        <ShieldAlert className="w-6 h-6 text-red-500" />
                        <div>
                            <h2 className="text-xl font-bold text-slate-800 dark:text-white">
                                Split Transaction Fraud Report
                            </h2>
                            {report && (
                                <p className="text-sm text-slate-500 dark:text-slate-400">{report.period}</p>
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

                {/* ── Controls ── */}
                <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex flex-wrap items-end gap-3">
                    <div className="relative">
                        <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">
                            Date Range
                        </label>
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
                                        className={`w-full text-left px-4 py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-600 transition-colors first:rounded-t-xl last:rounded-b-xl ${
                                            dateRange === r.value
                                                ? 'font-semibold text-blue-600 dark:text-blue-400'
                                                : 'text-slate-700 dark:text-slate-300'
                                        }`}
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
                                <input
                                    type="date"
                                    value={customStartDate}
                                    onChange={e => setCustomStartDate(e.target.value)}
                                    className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">To</label>
                                <input
                                    type="date"
                                    value={customEndDate}
                                    onChange={e => setCustomEndDate(e.target.value)}
                                    className="px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700"
                                />
                            </div>
                        </>
                    )}

                    {/* Company (scoped to the logged-in user) */}
                    {companies.length > 0 && (
                        <CompanyDropdown
                            companies={companies}
                            selectedCompany={selectedCompany}
                            onCompanyChange={setSelectedCompany}
                        />
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

                {/* ── Body ── */}
                <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">

                    {/* Empty state */}
                    {!report && !isLoading && (
                        <div className="flex flex-col items-center justify-center h-48 text-slate-400 dark:text-slate-500">
                            <ShieldAlert className="w-12 h-12 mb-3 opacity-40" />
                            <p className="text-sm">Select a date range and run the analysis to detect split fraud.</p>
                        </div>
                    )}

                    {/* Loading */}
                    {isLoading && (
                        <div className="flex flex-col items-center justify-center h-48 text-slate-400 dark:text-slate-500">
                            <Loader2 className="w-10 h-10 animate-spin mb-3 text-red-400" />
                            <p className="text-sm">Scanning transactions for split fraud patterns…</p>
                        </div>
                    )}

                    {report && !isLoading && (
                        <>
                            {/* ── Overview: risk-level stat cards ── */}
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                                <div className="bg-slate-50 dark:bg-slate-700 rounded-xl p-4 text-center">
                                    <p className="text-xs text-slate-500 dark:text-slate-400 mb-1">Transactions Scanned</p>
                                    <p className="text-2xl font-bold text-slate-800 dark:text-white">
                                        {(summary?.total_transactions_analyzed || 0).toLocaleString()}
                                    </p>
                                </div>
                                <div className="bg-red-50 dark:bg-red-900/30 rounded-xl p-4 text-center">
                                    <p className="text-xs text-red-600 dark:text-red-400 mb-1">High Risk</p>
                                    <p className="text-2xl font-bold text-red-700 dark:text-red-300">{highRisk}</p>
                                </div>
                                <div className="bg-amber-50 dark:bg-amber-900/30 rounded-xl p-4 text-center">
                                    <p className="text-xs text-amber-600 dark:text-amber-400 mb-1">Medium Risk</p>
                                    <p className="text-2xl font-bold text-amber-700 dark:text-amber-300">{mediumRisk}</p>
                                </div>
                                <div className="bg-blue-50 dark:bg-blue-900/30 rounded-xl p-4 text-center">
                                    <p className="text-xs text-blue-600 dark:text-blue-400 mb-1">Low Risk</p>
                                    <p className="text-2xl font-bold text-blue-700 dark:text-blue-300">{lowRisk}</p>
                                </div>
                            </div>

                            {/* ── Split fraud explainer card ── */}
                            <div className="bg-gradient-to-r from-red-50 to-orange-50 dark:from-red-900/20 dark:to-orange-900/20 border border-red-100 dark:border-red-800/40 rounded-xl p-4">
                                <div className="flex items-start gap-4">
                                    <div className="p-2.5 bg-red-100 dark:bg-red-900/40 rounded-lg shrink-0">
                                        <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <h3 className="text-base font-semibold text-slate-800 dark:text-white mb-1">
                                            What is Split Transaction Fraud?
                                        </h3>
                                        <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
                                            A fraudster makes one large deposit at an agent till, then sends multiple
                                            accomplices to withdraw smaller amounts — each below the threshold that would
                                            trigger a manual review. Related variants flagged here: a single deposit
                                            broken into several smaller deposits by the same person in quick succession
                                            (e.g. 50,000 arriving as 20,000 + 20,000 + 10,000), and tills processing
                                            back-to-back transactions — gaps of 2 minutes or less — continuously for an
                                            hour or more. All are ways of splitting activity to evade transaction
                                            monitoring thresholds.
                                        </p>
                                    </div>
                                    <div className="text-right shrink-0">
                                        <p className="text-3xl font-bold text-red-600 dark:text-red-400">
                                            {findings.length}
                                        </p>
                                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">incidents</p>
                                    </div>
                                </div>
                            </div>

                            {/* ── Key metrics ── */}
                            {findings.length > 0 && (
                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                                    <div className="bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl p-3 flex items-center gap-3">
                                        <div className="p-2 bg-red-100 dark:bg-red-900/30 rounded-lg shrink-0">
                                            <ShieldAlert className="w-4 h-4 text-red-500" />
                                        </div>
                                        <div>
                                            <p className="text-xs text-slate-500 dark:text-slate-400">Total Incidents</p>
                                            <p className="text-lg font-bold text-slate-800 dark:text-white">{findings.length}</p>
                                        </div>
                                    </div>
                                    <div className="bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl p-3 flex items-center gap-3">
                                        <div className="p-2 bg-amber-100 dark:bg-amber-900/30 rounded-lg shrink-0">
                                            <TrendingUp className="w-4 h-4 text-amber-500" />
                                        </div>
                                        <div>
                                            <p className="text-xs text-slate-500 dark:text-slate-400">KES at Risk</p>
                                            <p className="text-lg font-bold text-slate-800 dark:text-white">
                                                {totalKesAtRisk >= 1_000_000
                                                    ? `${(totalKesAtRisk / 1_000_000).toFixed(1)}M`
                                                    : totalKesAtRisk >= 1_000
                                                        ? `${(totalKesAtRisk / 1_000).toFixed(0)}K`
                                                        : fmt(totalKesAtRisk)}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl p-3 flex items-center gap-3">
                                        <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg shrink-0">
                                            <Clock className="w-4 h-4 text-blue-500" />
                                        </div>
                                        <div>
                                            <p className="text-xs text-slate-500 dark:text-slate-400">Avg Splits</p>
                                            <p className="text-lg font-bold text-slate-800 dark:text-white">{avgSplits}</p>
                                        </div>
                                    </div>
                                    <div className="bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl p-3 flex items-center gap-3">
                                        <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg shrink-0">
                                            <Building className="w-4 h-4 text-purple-500" />
                                        </div>
                                        <div>
                                            <p className="text-xs text-slate-500 dark:text-slate-400">Tills Affected</p>
                                            <p className="text-lg font-bold text-slate-800 dark:text-white">{tillsAffected}</p>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* ── Findings list ── */}
                            {findings.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-32 text-slate-400 dark:text-slate-500">
                                    <Shield className="w-10 h-10 mb-2 text-green-400" />
                                    <p className="text-sm font-medium text-green-600 dark:text-green-400">
                                        No split fraud patterns detected in this period.
                                    </p>
                                </div>
                            ) : (
                                <div>
                                    <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-3">
                                        Flagged Incidents — sorted by severity
                                    </p>
                                    {findings.map((finding, i) => (
                                        finding.fraud_type === 'split_transaction'
                                            ? <SplitFindingCard key={i} finding={finding} index={i} />
                                            : <GenericFindingCard key={i} finding={finding} index={i} />
                                    ))}
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
