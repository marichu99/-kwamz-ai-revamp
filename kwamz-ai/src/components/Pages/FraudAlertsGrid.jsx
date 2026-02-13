import React, { useState, useEffect } from 'react';
import { ChevronRight, ChevronDown, Shield, AlertTriangle, Search, RefreshCw, Building2, MapPin, Hash, Users } from 'lucide-react';
import config from '../../Config';
import { useToast } from './ToastProvider';

function FraudAlertsGrid() {
    const [alertData, setAlertData] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [expandedCompanies, setExpandedCompanies] = useState(new Set());
    const [expandedExplanations, setExpandedExplanations] = useState(new Set());
    const [limit, setLimit] = useState(5);
    const [searchTerm, setSearchTerm] = useState('');
    const { showToast } = useToast();

    useEffect(() => {
        fetchAlertData();
    }, [limit]);

    const fetchAlertData = async () => {
        setIsLoading(true);
        try {
            const token = localStorage.getItem('token');
            const response = await fetch(`${config.API_URL}/fraud/alerts/by-agent-company?limit=${limit}`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) throw new Error('Failed to fetch fraud alerts');

            const data = await response.json();
            setAlertData(data.data || []);
        } catch (error) {
            showToast('Error fetching fraud alerts', 'error');
            console.error('Error fetching fraud alerts:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const toggleCompany = (companyId) => {
        setExpandedCompanies(prev => {
            const newSet = new Set(prev);
            if (newSet.has(companyId)) {
                newSet.delete(companyId);
            } else {
                newSet.add(companyId);
            }
            return newSet;
        });
    };

    const toggleExplanation = (alertId) => {
        setExpandedExplanations(prev => {
            const newSet = new Set(prev);
            if (newSet.has(alertId)) {
                newSet.delete(alertId);
            } else {
                newSet.add(alertId);
            }
            return newSet;
        });
    };

    const riskBadge = (level) => {
        const styles = {
            HIGH: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
            MEDIUM: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
            LOW: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
        };
        return (
            <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${styles[level] || 'bg-gray-100 text-gray-600'}`}>
                {level}
            </span>
        );
    };

    const typeBadge = (fraudType) => {
        const label = (fraudType || 'unknown').replace(/_/g, ' ').toUpperCase();
        const styles = {
            'SPLIT TRANSACTION': 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
            'ROLLOVER FRAUD': 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400',
            'RAPID BACK FORTH': 'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400',
        };
        return (
            <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${styles[label] || 'bg-gray-100 text-gray-600'}`}>
                {label}
            </span>
        );
    };

    // Calculate summary stats
    const totalCompanies = alertData.filter(d => d.total_alerts > 0).length;
    const totalAlerts = alertData.reduce((sum, d) => sum + d.total_alerts, 0);
    const highRiskCount = alertData.reduce((sum, d) =>
        sum + d.fraud_alerts.filter(a => a.risk_level === 'HIGH').length, 0);
    const mediumRiskCount = alertData.reduce((sum, d) =>
        sum + d.fraud_alerts.filter(a => a.risk_level === 'MEDIUM').length, 0);

    // Filter by search term
    const filteredData = alertData.filter(d => {
        if (!searchTerm) return true;
        const term = searchTerm.toLowerCase();
        const company = d.agent_company;
        return (
            (company.company_name || '').toLowerCase().includes(term) ||
            (company.short_code || '').toLowerCase().includes(term) ||
            (company.location || '').toLowerCase().includes(term)
        );
    });

    if (isLoading) {
        return (
            <div className="flex flex-col items-center justify-center py-20">
                <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-4"></div>
                <p className="text-slate-600 dark:text-slate-400">Loading fraud alerts...</p>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
                        <Shield className="w-6 h-6 text-red-500" />
                        Fraud Alerts
                    </h1>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                        Monitor fraud detections across your agent companies
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    <button
                        onClick={fetchAlertData}
                        className="inline-flex items-center px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-sm hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                    >
                        <RefreshCw className="w-4 h-4 mr-2" />
                        Reload
                    </button>
                    <select
                        value={limit}
                        onChange={(e) => setLimit(Number(e.target.value))}
                        className="px-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-sm"
                    >
                        <option value={5}>5 per company</option>
                        <option value={10}>10 per company</option>
                        <option value={15}>15 per company</option>
                        <option value={20}>20 per company</option>
                    </select>
                    <div className="relative">
                        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                        <input
                            type="text"
                            placeholder="Search companies..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="pl-9 pr-3 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-sm w-48"
                        />
                    </div>
                </div>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700">
                    <div className="text-xs text-slate-500 dark:text-slate-400 uppercase font-semibold">Companies Flagged</div>
                    <div className="text-2xl font-bold text-slate-800 dark:text-white mt-1">{totalCompanies}</div>
                </div>
                <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700">
                    <div className="text-xs text-slate-500 dark:text-slate-400 uppercase font-semibold">Total Alerts</div>
                    <div className="text-2xl font-bold text-blue-600 mt-1">{totalAlerts}</div>
                </div>
                <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700">
                    <div className="text-xs text-slate-500 dark:text-slate-400 uppercase font-semibold">High Risk</div>
                    <div className="text-2xl font-bold text-red-600 mt-1">{highRiskCount}</div>
                </div>
                <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700">
                    <div className="text-xs text-slate-500 dark:text-slate-400 uppercase font-semibold">Medium Risk</div>
                    <div className="text-2xl font-bold text-orange-600 mt-1">{mediumRiskCount}</div>
                </div>
            </div>

            {/* Main Table */}
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="bg-slate-50 dark:bg-slate-900/50 border-b border-slate-200 dark:border-slate-700">
                                <th className="px-4 py-3 text-left w-10"></th>
                                <th className="px-4 py-3 text-left font-semibold text-slate-600 dark:text-slate-300">Agent Company</th>
                                <th className="px-4 py-3 text-left font-semibold text-slate-600 dark:text-slate-300">Location</th>
                                <th className="px-4 py-3 text-left font-semibold text-slate-600 dark:text-slate-300">Shortcode</th>
                                <th className="px-4 py-3 text-center font-semibold text-slate-600 dark:text-slate-300">Agents</th>
                                <th className="px-4 py-3 text-center font-semibold text-slate-600 dark:text-slate-300">Fraud Risk</th>
                                <th className="px-4 py-3 text-center font-semibold text-slate-600 dark:text-slate-300">Total Alerts</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredData.length === 0 ? (
                                <tr>
                                    <td colSpan="7" className="px-4 py-12 text-center text-slate-500 dark:text-slate-400">
                                        <AlertTriangle className="w-8 h-8 mx-auto mb-2 opacity-50" />
                                        No fraud alerts found
                                    </td>
                                </tr>
                            ) : (
                                filteredData.map((item) => {
                                    const company = item.agent_company;
                                    const companyId = company.id;
                                    const isExpanded = expandedCompanies.has(companyId);
                                    const agents = company.user_agents || [];

                                    return (
                                        <React.Fragment key={companyId}>
                                            {/* Company Row */}
                                            <tr
                                                className={`border-b border-slate-100 dark:border-slate-700 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors ${isExpanded ? 'bg-blue-50/50 dark:bg-blue-900/10' : ''}`}
                                                onClick={() => toggleCompany(companyId)}
                                            >
                                                <td className="px-4 py-3">
                                                    {isExpanded
                                                        ? <ChevronDown className="w-4 h-4 text-blue-500" />
                                                        : <ChevronRight className="w-4 h-4 text-slate-400" />
                                                    }
                                                </td>
                                                <td className="px-4 py-3">
                                                    <div className="flex items-center gap-2">
                                                        <Building2 className="w-4 h-4 text-slate-400" />
                                                        <span className="font-medium text-slate-800 dark:text-white">
                                                            {company.company_name || 'N/A'}
                                                        </span>
                                                    </div>
                                                </td>
                                                <td className="px-4 py-3 text-slate-600 dark:text-slate-300">
                                                    <div className="flex items-center gap-1">
                                                        <MapPin className="w-3 h-3 text-slate-400" />
                                                        {company.location || 'N/A'}
                                                    </div>
                                                </td>
                                                <td className="px-4 py-3">
                                                    <div className="flex items-center gap-1">
                                                        <Hash className="w-3 h-3 text-slate-400" />
                                                        <code className="text-xs bg-slate-100 dark:bg-slate-700 px-1.5 py-0.5 rounded">
                                                            {company.short_code || company.business_short_code || 'N/A'}
                                                        </code>
                                                    </div>
                                                </td>
                                                <td className="px-4 py-3 text-center">
                                                    <span
                                                        className="inline-flex items-center gap-1 bg-slate-100 dark:bg-slate-700 px-2 py-0.5 rounded-full text-xs font-medium"
                                                        title={agents.map(a => a.name || a.idnumber || 'Unknown').join(', ')}
                                                    >
                                                        <Users className="w-3 h-3" />
                                                        {agents.length}
                                                    </span>
                                                </td>
                                                <td className="px-4 py-3 text-center">
                                                    {item.fraud_risk ? riskBadge(item.fraud_risk) : <span className="text-slate-400 text-xs">None</span>}
                                                </td>
                                                <td className="px-4 py-3 text-center">
                                                    <span className={`inline-block min-w-[2rem] text-center font-bold rounded-full px-2 py-0.5 text-xs ${item.total_alerts > 0 ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' : 'bg-slate-100 text-slate-500'}`}>
                                                        {item.total_alerts}
                                                    </span>
                                                </td>
                                            </tr>

                                            {/* Expanded Sub-table */}
                                            {isExpanded && (
                                                <tr>
                                                    <td colSpan="7" className="px-0 py-0">
                                                        <div className="bg-slate-50 dark:bg-slate-900/30 border-y border-slate-200 dark:border-slate-700">
                                                            {item.fraud_alerts.length === 0 ? (
                                                                <div className="px-8 py-6 text-center text-slate-500 dark:text-slate-400 text-sm">
                                                                    No fraud alerts for this company
                                                                </div>
                                                            ) : (
                                                                <div className="overflow-x-auto">
                                                                    <table className="w-full text-xs">
                                                                        <thead>
                                                                            <tr className="bg-slate-100 dark:bg-slate-800">
                                                                                <th className="px-3 py-2 text-left font-semibold text-slate-500">#</th>
                                                                                <th className="px-3 py-2 text-left font-semibold text-slate-500">Type</th>
                                                                                <th className="px-3 py-2 text-left font-semibold text-slate-500">Risk</th>
                                                                                <th className="px-3 py-2 text-left font-semibold text-slate-500">Account</th>
                                                                                <th className="px-3 py-2 text-right font-semibold text-slate-500">Amount (KES)</th>
                                                                                <th className="px-3 py-2 text-left font-semibold text-slate-500">Receipts</th>
                                                                                <th className="px-3 py-2 text-left font-semibold text-slate-500">Detected</th>
                                                                                <th className="px-3 py-2 text-left font-semibold text-slate-500">Explanation</th>
                                                                            </tr>
                                                                        </thead>
                                                                        <tbody>
                                                                            {item.fraud_alerts.map((alert, idx) => {
                                                                                const explanation = alert.detection_details?.explanation || 'No explanation available';
                                                                                const isLong = explanation.length > 100;
                                                                                const showFull = expandedExplanations.has(alert.id);
                                                                                const receipts = (alert.receipt_nos || []).slice(0, 3).join(', ');
                                                                                const moreReceipts = (alert.receipt_nos || []).length > 3 ? ` +${alert.receipt_nos.length - 3}` : '';

                                                                                return (
                                                                                    <tr key={alert.id} className={`border-b border-slate-200 dark:border-slate-700 ${idx % 2 === 0 ? 'bg-white dark:bg-slate-800/50' : 'bg-slate-50 dark:bg-slate-900/20'}`}>
                                                                                        <td className="px-3 py-2 font-medium text-slate-500">{idx + 1}</td>
                                                                                        <td className="px-3 py-2">{typeBadge(alert.fraud_type)}</td>
                                                                                        <td className="px-3 py-2">{riskBadge(alert.risk_level)}</td>
                                                                                        <td className="px-3 py-2">
                                                                                            <div className="font-medium text-slate-700 dark:text-slate-200">{alert.account_phone || 'N/A'}</div>
                                                                                            <div className="text-slate-400">{alert.account_name || ''}</div>
                                                                                        </td>
                                                                                        <td className="px-3 py-2 text-right font-semibold text-slate-700 dark:text-slate-200">
                                                                                            {parseFloat(alert.total_amount || 0).toLocaleString('en-KE', { minimumFractionDigits: 2 })}
                                                                                        </td>
                                                                                        <td className="px-3 py-2">
                                                                                            <code className="text-[10px] bg-slate-100 dark:bg-slate-700 px-1 py-0.5 rounded">
                                                                                                {receipts}{moreReceipts}
                                                                                            </code>
                                                                                        </td>
                                                                                        <td className="px-3 py-2 text-slate-500 whitespace-nowrap">{alert.created_at || 'N/A'}</td>
                                                                                        <td className="px-3 py-2 max-w-[250px]">
                                                                                            <span className="text-slate-600 dark:text-slate-300">
                                                                                                {isLong && !showFull ? explanation.slice(0, 100) + '...' : explanation}
                                                                                            </span>
                                                                                            {isLong && (
                                                                                                <button
                                                                                                    onClick={(e) => { e.stopPropagation(); toggleExplanation(alert.id); }}
                                                                                                    className="ml-1 text-blue-500 hover:text-blue-600 text-[10px] font-medium"
                                                                                                >
                                                                                                    {showFull ? 'Show less' : 'Show more'}
                                                                                                </button>
                                                                                            )}
                                                                                        </td>
                                                                                    </tr>
                                                                                );
                                                                            })}
                                                                        </tbody>
                                                                    </table>
                                                                </div>
                                                            )}
                                                            {item.total_alerts > item.fraud_alerts.length && (
                                                                <div className="px-4 py-2 text-xs text-slate-500 dark:text-slate-400 border-t border-slate-200 dark:border-slate-700">
                                                                    Showing {item.fraud_alerts.length} of {item.total_alerts} alerts. Increase limit to see more.
                                                                </div>
                                                            )}
                                                        </div>
                                                    </td>
                                                </tr>
                                            )}
                                        </React.Fragment>
                                    );
                                })
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

export default FraudAlertsGrid;
