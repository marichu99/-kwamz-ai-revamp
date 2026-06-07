import { useState, useEffect, useMemo } from 'react';
import { Search, Calendar, AlertTriangle, Loader2, X, RefreshCw, ChevronDown, ChevronRight, Building, Store, Download } from 'lucide-react';
import axios from 'axios';
import config from '../../Config';
import { useToast } from './ToastProvider';

function ClawbacksGrid() {
  const [rows, setRows] = useState([]);
  const [filtered, setFiltered] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState(new Set());
  const [expandedSubGroups, setExpandedSubGroups] = useState(new Set());
  const { showToast } = useToast();

  const fetchClawbacks = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams();
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      const res = await axios.get(`${config.API_URL}/transactions/clawbacks?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = res.data?.data || [];
      setRows(data);
      setFiltered(data);
      // Auto-expand all groups and sub-groups on load
      const groupKeys = new Set(data.map(r => r.company_shortcode || r.business_shortcode || 'unknown'));
      const subGroupKeys = new Set(data.map(r => `${r.company_shortcode || 'unknown'}__${r.business_shortcode || 'unknown'}`));
      setExpandedGroups(groupKeys);
      setExpandedSubGroups(subGroupKeys);
      showToast(`${data.length} clawback(s) loaded`, 'success');
    } catch (err) {
      console.error(err);
      showToast('Failed to load clawbacks', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchClawbacks(); }, []);

  useEffect(() => {
    if (!searchTerm) { setFiltered(rows); return; }
    const q = searchTerm.toLowerCase();
    setFiltered(rows.filter(r =>
      r.receipt_no?.toLowerCase().includes(q) ||
      r.details?.toLowerCase().includes(q) ||
      r.reason_type?.toLowerCase().includes(q) ||
      r.company_name?.toLowerCase().includes(q) ||
      r.business_shortcode?.toLowerCase().includes(q)
    ));
  }, [searchTerm, rows]);

  // Two-level grouping: company → business_shortcode → rows
  const groups = useMemo(() => {
    const map = {};
    filtered.forEach(r => {
      const companyKey = r.company_shortcode || r.business_shortcode || 'unknown';
      const subKey = `${companyKey}__${r.business_shortcode || 'unknown'}`;

      if (!map[companyKey]) {
        map[companyKey] = {
          key: companyKey,
          company_name: r.company_name || 'Unknown Company',
          company_shortcode: r.company_shortcode || '—',
          subGroups: {},
          total_withdrawn: 0,
          count: 0,
        };
      }
      if (!map[companyKey].subGroups[subKey]) {
        map[companyKey].subGroups[subKey] = {
          key: subKey,
          business_shortcode: r.business_shortcode || '—',
          agent_company_name: r.agent_company_name || null,
          rows: [],
          total_withdrawn: 0,
        };
      }
      map[companyKey].subGroups[subKey].rows.push(r);
      map[companyKey].subGroups[subKey].total_withdrawn += Math.abs(r.withdrawn || 0);
      map[companyKey].total_withdrawn += Math.abs(r.withdrawn || 0);
      map[companyKey].count++;
    });
    return Object.values(map)
      .sort((a, b) => a.company_name.localeCompare(b.company_name))
      .map(g => ({ ...g, subGroups: Object.values(g.subGroups).sort((a, b) => a.business_shortcode.localeCompare(b.business_shortcode)) }));
  }, [filtered]);

  const toggleGroup = (key) => {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  };

  const toggleSubGroup = (key) => {
    setExpandedSubGroups(prev => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  };

  const handleApplyFilter = () => { fetchClawbacks(); };

  const handleClearDates = () => {
    setStartDate('');
    setEndDate('');
    setTimeout(fetchClawbacks, 0);
  };

  const formatDate = (iso) => {
    if (!iso) return 'N/A';
    return new Date(iso).toLocaleDateString('en-GB', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  };

  const fmtAmt = (v) =>
    `KES ${Math.abs(v || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}`;

  const handleExport = () => {
    const headers = [
      'Company Name', 'Company Shortcode', 'Agent Company Name', 'Business Shortcode',
      'Receipt No.', 'Completion Time', 'Details', 'Reason Type',
      'Withdrawn (KES)', 'Currency', 'Status',
    ];
    const escape = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`;
    const csvRows = [
      headers.join(','),
      ...filtered.map(r => [
        escape(r.company_name),
        escape(r.company_shortcode),
        escape(r.agent_company_name),
        escape(r.business_shortcode),
        escape(r.receipt_no),
        escape(formatDate(r.completion_time)),
        escape(r.details),
        escape(r.reason_type),
        Math.abs(r.withdrawn || 0).toFixed(2),
        escape(r.currency),
        escape(r.transaction_status),
      ].join(',')),
    ];
    const blob = new Blob([csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `commission_clawbacks_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-lg p-6">

      <div className="sticky top-0 z-20 bg-white dark:bg-slate-800">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
            <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-800 dark:text-white">Commission Clawbacks</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">Commission amounts recovered by M-Pesa</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleExport}
            disabled={filtered.length === 0}
            className="flex items-center gap-2 py-2 px-4 bg-blue-500 text-white rounded-xl hover:bg-blue-600 transition-colors disabled:bg-blue-300 disabled:cursor-not-allowed"
          >
            <Download className="w-4 h-4" />
            <span>Export CSV</span>
          </button>
          <button
            onClick={fetchClawbacks}
            disabled={isLoading}
            className="flex items-center space-x-2 py-2 px-4 bg-green-500 text-white rounded-xl hover:bg-green-600 transition-colors disabled:bg-green-300"
          >
            {isLoading
              ? <Loader2 className="w-4 h-4 animate-spin" />
              : <RefreshCw className="w-4 h-4" />}
            <span>Reload</span>
          </button>
        </div>
      </div>

      {/* Search + Date Filters */}
      <div className="mb-6 space-y-4">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search receipt, details, company, shortcode…"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
          />
        </div>

        <div className="flex items-end gap-3">
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Start Date</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="px-3 py-2 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">End Date</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="px-3 py-2 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
            />
          </div>
          <button
            onClick={handleApplyFilter}
            className="flex items-center gap-2 px-4 py-2 bg-slate-600 text-white rounded-xl hover:bg-slate-700 transition-colors"
          >
            <Calendar className="w-4 h-4" />
            Apply
          </button>
          {(startDate || endDate) && (
            <button
              onClick={handleClearDates}
              className="flex items-center gap-1 px-3 py-2 text-sm text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 transition-colors"
            >
              <X className="w-3 h-3" />
              Clear
            </button>
          )}
        </div>
      </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      )}

      {/* Grouped content */}
      {!isLoading && (
        <>
          {groups.length === 0 ? (
            <div className="text-center py-12">
              <AlertTriangle className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
              <p className="text-slate-500 dark:text-slate-400">No clawback records found.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {groups.map((group) => (
                <div key={group.key} className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">

                  {/* Company group header */}
                  <button
                    onClick={() => toggleGroup(group.key)}
                    className="w-full flex items-center justify-between px-4 py-3 bg-slate-50 dark:bg-slate-700/60 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      {expandedGroups.has(group.key)
                        ? <ChevronDown className="w-4 h-4 text-slate-500" />
                        : <ChevronRight className="w-4 h-4 text-slate-500" />}
                      <Building className="w-4 h-4 text-amber-500" />
                      <span className="font-bold text-slate-800 dark:text-white">{group.company_name}</span>
                      <span className="text-sm font-mono text-slate-500 dark:text-slate-400">({group.company_shortcode})</span>
                      <span className="text-xs bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-400 px-2 py-0.5 rounded-full">
                        {group.count} clawback{group.count !== 1 ? 's' : ''}
                      </span>
                    </div>
                    <span className="text-sm font-bold text-red-600 dark:text-red-400">
                      {fmtAmt(group.total_withdrawn)} total
                    </span>
                  </button>

                  {/* Sub-groups (by business shortcode) */}
                  {expandedGroups.has(group.key) && (
                    <div className="px-4 py-2 space-y-2 bg-white dark:bg-slate-900">
                      {group.subGroups.map((sub) => (
                        <div key={sub.key} className="rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden">

                          {/* Sub-group header */}
                          <button
                            onClick={() => toggleSubGroup(sub.key)}
                            className="w-full flex items-center justify-between px-3 py-2 bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                          >
                            <div className="flex items-center gap-2">
                              {expandedSubGroups.has(sub.key)
                                ? <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                                : <ChevronRight className="w-3.5 h-3.5 text-slate-400" />}
                              <Store className="w-3.5 h-3.5 text-blue-500" />
                              <span className="font-mono font-semibold text-sm text-slate-700 dark:text-slate-200">{sub.business_shortcode}</span>
                              {sub.agent_company_name && (
                                <span className="text-sm text-slate-500 dark:text-slate-400 truncate max-w-xs">{sub.agent_company_name}</span>
                              )}
                              <span className="text-xs bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-400 px-2 py-0.5 rounded-full">
                                {sub.rows.length} clawback{sub.rows.length !== 1 ? 's' : ''}
                              </span>
                            </div>
                            <span className="text-xs font-bold text-red-600 dark:text-red-400">
                              {fmtAmt(sub.total_withdrawn)}
                            </span>
                          </button>

                          {/* Rows table */}
                          {expandedSubGroups.has(sub.key) && (
                            <div className="overflow-x-auto">
                              <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-700 text-sm">
                                <thead className="bg-slate-50 dark:bg-slate-700/50">
                                  <tr>
                                    {['Receipt No.', 'Completion Time', 'Details', 'Reason Type', 'Withdrawn', 'Currency', 'Status'].map((h) => (
                                      <th
                                        key={h}
                                        className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider whitespace-nowrap"
                                      >
                                        {h}
                                      </th>
                                    ))}
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100 dark:divide-slate-700 bg-white dark:bg-slate-800">
                                  {sub.rows.map((r) => (
                                    <tr
                                      key={r.id}
                                      className="hover:bg-amber-50 dark:hover:bg-amber-900/10 transition-colors"
                                    >
                                      <td className="px-4 py-3 font-mono text-xs text-blue-600 dark:text-blue-400 whitespace-nowrap">
                                        {r.receipt_no}
                                      </td>
                                      <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-300 whitespace-nowrap">
                                        {formatDate(r.completion_time)}
                                      </td>
                                      <td className="px-4 py-3 text-xs text-slate-700 dark:text-slate-200 max-w-xs truncate">
                                        {r.details}
                                      </td>
                                      <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-300 max-w-xs truncate">
                                        {r.reason_type}
                                      </td>
                                      <td className="px-4 py-3 text-xs font-semibold text-red-600 dark:text-red-400 whitespace-nowrap">
                                        {fmtAmt(r.withdrawn)}
                                      </td>
                                      <td className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400">
                                        {r.currency}
                                      </td>
                                      <td className="px-4 py-3">
                                        <span className="text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 px-2.5 py-0.5 rounded-full whitespace-nowrap">
                                          {r.transaction_status}
                                        </span>
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default ClawbacksGrid;
