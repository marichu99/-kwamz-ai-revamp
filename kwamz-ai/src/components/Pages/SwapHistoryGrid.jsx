import { useState, useEffect, useRef } from 'react';
import { Search, ChevronDown, ChevronRight, ChevronsUpDown, MoreVertical, FileText, Download, Calendar, ArrowRightLeft, Users, X, Loader2, Undo2, AlertTriangle, Eye, Banknote, CheckCircle2, Clock, XCircle } from 'lucide-react';
import axios from 'axios';
import config from '../../Config';
import { useToast } from './ToastProvider';

function SwapHistoryGrid() {
  const [groupedData, setGroupedData] = useState([]);
  const [filteredData, setFilteredData] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedCompanies, setExpandedCompanies] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [reportData, setReportData] = useState(null);
  const [isReportLoading, setIsReportLoading] = useState(false);
  const [revertConfirm, setRevertConfirm] = useState(null);
  const [swapDetail, setSwapDetail] = useState(null);
  const [selectedSwapIds, setSelectedSwapIds] = useState([]);
  const [payoutModal, setPayoutModal] = useState(null);
  const [payoutAmounts, setPayoutAmounts] = useState({});
  const [isPayoutLoading, setIsPayoutLoading] = useState(false);
  const [swapPayouts, setSwapPayouts] = useState({});
  const { showToast } = useToast();
  const dropdownRef = useRef(null);

  const fetchSwapHistory = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams();
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);

      const response = await axios.get(`${config.API_URL}/swaps/by-company?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setGroupedData(response.data || []);
      showToast('Swap history loaded', 'success');
    } catch (error) {
      console.error('Error fetching swap history:', error);
      showToast('Failed to load swap history', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSwapHistory();
  }, []);

  // Search filter
  useEffect(() => {
    if (!searchTerm) {
      setFilteredData(groupedData);
    } else {
      const term = searchTerm.toLowerCase();
      setFilteredData(
        groupedData.filter(
          (group) =>
            group.company_name?.toLowerCase().includes(term) ||
            group.till_name?.toLowerCase().includes(term) ||
            group.till_number?.toLowerCase().includes(term)
        )
      );
    }
    setCurrentPage(1);
  }, [searchTerm, groupedData]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const toggleCompany = (companyId) => {
    setExpandedCompanies((prev) => ({ ...prev, [companyId]: !prev[companyId] }));
  };

  const allExpanded = filteredData.length > 0 && filteredData.every((g) => expandedCompanies[g.agent_company_id]);

  const toggleExpandAll = () => {
    if (allExpanded) {
      setExpandedCompanies({});
    } else {
      const all = {};
      filteredData.forEach((g) => { all[g.agent_company_id] = true; });
      setExpandedCompanies(all);
    }
  };

  // Selection helpers
  const handleSelectSwap = (swapId) => {
    setSelectedSwapIds((prev) =>
      prev.includes(swapId) ? prev.filter((id) => id !== swapId) : [...prev, swapId]
    );
  };

  const handleSelectAllInGroup = (group) => {
    const groupSwapIds = group.swaps.map((s) => s.id);
    const allSelected = groupSwapIds.every((id) => selectedSwapIds.includes(id));
    if (allSelected) {
      setSelectedSwapIds((prev) => prev.filter((id) => !groupSwapIds.includes(id)));
    } else {
      setSelectedSwapIds((prev) => [...new Set([...prev, ...groupSwapIds])]);
    }
  };

  const getSelectedSwap = () => {
    if (selectedSwapIds.length !== 1) return null;
    for (const group of groupedData) {
      const found = group.swaps.find((s) => s.id === selectedSwapIds[0]);
      if (found) return found;
    }
    return null;
  };

  const handleViewSelected = () => {
    const swap = getSelectedSwap();
    if (!swap) {
      showToast('Please select exactly one swap to view', 'error');
      return;
    }
    setSwapDetail(swap);
    setIsDropdownOpen(false);
  };

  const handleRevertSelected = () => {
    const swap = getSelectedSwap();
    if (!swap) {
      showToast('Please select exactly one swap to revert', 'error');
      return;
    }
    setRevertConfirm(swap);
    setIsDropdownOpen(false);
  };

  // Pagination
  const totalItems = filteredData.length;
  const totalPages = Math.ceil(totalItems / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const paginatedData = filteredData.slice(startIndex, startIndex + pageSize);

  const handlePageChange = (page) => {
    if (page >= 1 && page <= totalPages) setCurrentPage(page);
  };

  // Generate report
  const handleGenerateReport = async () => {
    setIsReportLoading(true);
    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams();
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);

      const response = await axios.get(`${config.API_URL}/swaps/report?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setReportData(response.data);
    } catch (error) {
      console.error('Error generating report:', error);
      showToast('Failed to generate report', 'error');
    } finally {
      setIsReportLoading(false);
    }
  };

  // Export report
  const handleExportReport = async () => {
    try {
      const token = localStorage.getItem('token');
      const params = new URLSearchParams();
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      params.append('format', 'csv');

      const response = await axios.get(`${config.API_URL}/swaps/report/export?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `swap_report_${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      showToast('Report exported successfully', 'success');
    } catch (error) {
      console.error('Error exporting report:', error);
      showToast('Failed to export report', 'error');
    }
  };

  // Revert a swap
  const handleConfirmRevert = async () => {
    if (!revertConfirm) return;
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${config.API_URL}/swaps/${revertConfirm.id}/revert`, {}, {
        headers: { Authorization: `Bearer ${token}` },
      });
      showToast('Swap reverted successfully', 'success');
      setRevertConfirm(null);
      fetchSwapHistory();
    } catch (error) {
      const msg = error.response?.data?.error || 'Failed to revert swap';
      console.error('Error reverting swap:', msg);
      showToast(msg, 'error');
    }
  };

  const handleApplyDateFilter = () => {
    fetchSwapHistory();
  };

  // Payout helpers
  const handleInitiatePayout = () => {
    const swap = getSelectedSwap();
    if (!swap) {
      showToast('Please select exactly one swap to initiate payout', 'error');
      return;
    }
    const agents = swap.previous_agents || [];
    if (agents.length === 0) {
      showToast('No outgoing agents found for this swap', 'error');
      return;
    }
    const commission = parseFloat(swap.commission_balance_at_swap || 0);
    if (commission <= 0) {
      showToast('No commission balance to pay out', 'error');
      return;
    }
    const perAgent = Math.floor((commission / agents.length) * 100) / 100;
    const amounts = {};
    agents.forEach((a, i) => { amounts[i] = perAgent; });
    setPayoutAmounts(amounts);
    setPayoutModal(swap);
    setIsDropdownOpen(false);
  };

  const handleConfirmPayout = async () => {
    if (!payoutModal) return;
    setIsPayoutLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(`${config.API_URL}/mpesa/b2c/payout`, {
        swap_id: payoutModal.id,
      }, {
        headers: { Authorization: `Bearer ${token}` },
      });
      showToast('Payout initiated successfully', 'success');
      setPayoutModal(null);
      // Refresh payout status for this swap
      fetchPayoutStatus(payoutModal.id);
    } catch (error) {
      const msg = error.response?.data?.error || 'Failed to initiate payout';
      showToast(msg, 'error');
    } finally {
      setIsPayoutLoading(false);
    }
  };

  const fetchPayoutStatus = async (swapId) => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${config.API_URL}/mpesa/b2c/payouts/${swapId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setSwapPayouts((prev) => ({ ...prev, [swapId]: response.data }));
    } catch (error) {
      console.error('Error fetching payout status:', error);
    }
  };

  // Fetch payout status for all visible swaps
  useEffect(() => {
    if (groupedData.length > 0) {
      groupedData.forEach((group) => {
        group.swaps?.forEach((swap) => {
          fetchPayoutStatus(swap.id);
        });
      });
    }
  }, [groupedData]);

  const getPayoutStatusIcon = (swapId) => {
    const payouts = swapPayouts[swapId];
    if (!payouts || payouts.length === 0) return null;
    const allCompleted = payouts.every((p) => p.status === 'completed');
    const anyFailed = payouts.some((p) => p.status === 'failed');
    const anyPending = payouts.some((p) => p.status === 'pending');
    if (allCompleted) return <CheckCircle2 className="w-4 h-4 text-green-500" title="Payout completed" />;
    if (anyFailed && !anyPending) return <XCircle className="w-4 h-4 text-red-500" title="Payout failed" />;
    return <Clock className="w-4 h-4 text-amber-500 animate-pulse" title="Payout pending" />;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-lg p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-orange-100 dark:bg-orange-900/30 flex items-center justify-center">
            <ArrowRightLeft className="w-5 h-5 text-orange-600 dark:text-orange-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-800 dark:text-white">Swap History</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">Agent rotation tracking across tills</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={toggleExpandAll}
            disabled={filteredData.length === 0}
            className="flex items-center space-x-2 py-2 px-4 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronsUpDown className="w-4 h-4" />
            <span>{allExpanded ? 'Collapse All' : 'Expand All'}</span>
          </button>
          <button
            onClick={fetchSwapHistory}
            disabled={isLoading}
            className="flex items-center space-x-2 py-2 px-4 bg-green-500 text-white rounded-xl hover:bg-green-600 transition-colors disabled:bg-green-300"
          >
            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRightLeft className="w-4 h-4" />}
            <span>Reload</span>
          </button>

          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              className="flex items-center space-x-2 py-2 px-4 bg-blue-500 text-white rounded-xl hover:bg-blue-600 transition-colors"
            >
              <MoreVertical className="w-4 h-4" />
              <span>Actions</span>
            </button>
            {isDropdownOpen && (
              <div className="absolute right-0 mt-2 w-56 bg-white dark:bg-slate-800 rounded-lg shadow-2xl border border-slate-200 dark:border-slate-700 z-50">
                <button
                  onClick={handleViewSelected}
                  disabled={selectedSwapIds.length !== 1}
                  className="w-full flex items-center px-4 py-3 text-sm text-slate-800 dark:text-slate-200 hover:bg-blue-50 dark:hover:bg-blue-900/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors rounded-t-lg"
                >
                  <Eye className="w-4 h-4 mr-2" />
                  View Selected
                </button>
                <button
                  onClick={handleRevertSelected}
                  disabled={selectedSwapIds.length !== 1}
                  className="w-full flex items-center px-4 py-3 text-sm text-slate-800 dark:text-slate-200 hover:bg-orange-50 dark:hover:bg-orange-900/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <Undo2 className="w-4 h-4 mr-2" />
                  Revert Selected
                </button>
                <button
                  onClick={handleInitiatePayout}
                  disabled={selectedSwapIds.length !== 1}
                  className="w-full flex items-center px-4 py-3 text-sm text-slate-800 dark:text-slate-200 hover:bg-green-50 dark:hover:bg-green-900/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <Banknote className="w-4 h-4 mr-2" />
                  Initiate Payout
                </button>
                <div className="border-t border-slate-200 dark:border-slate-700" />
                <button
                  onClick={() => { setIsReportModalOpen(true); setReportData(null); setIsDropdownOpen(false); }}
                  className="w-full flex items-center px-4 py-3 text-sm text-slate-800 dark:text-slate-200 hover:bg-blue-50 dark:hover:bg-blue-900/30 transition-colors"
                >
                  <FileText className="w-4 h-4 mr-2" />
                  Generate Swap Report
                </button>
                <button
                  onClick={() => { handleExportReport(); setIsDropdownOpen(false); }}
                  className="w-full flex items-center px-4 py-3 text-sm text-slate-800 dark:text-slate-200 hover:bg-blue-50 dark:hover:bg-blue-900/30 transition-colors rounded-b-lg"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Export to CSV
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Search and Date Filters */}
      <div className="mb-6 space-y-4">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search by company name or till number..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
            />
          </div>
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
            onClick={handleApplyDateFilter}
            className="flex items-center gap-2 px-4 py-2 bg-slate-600 text-white rounded-xl hover:bg-slate-700 transition-colors"
          >
            <Calendar className="w-4 h-4" />
            Apply
          </button>
          {(startDate || endDate) && (
            <button
              onClick={() => { setStartDate(''); setEndDate(''); setTimeout(fetchSwapHistory, 0); }}
              className="flex items-center gap-1 px-3 py-2 text-sm text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 transition-colors"
            >
              <X className="w-3 h-3" />
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      )}

      {/* Grouped Swap Grid */}
      {!isLoading && (
        <div className="space-y-3">
          {paginatedData.length === 0 ? (
            <div className="text-center py-12">
              <ArrowRightLeft className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
              <p className="text-slate-500 dark:text-slate-400">No swap history found</p>
            </div>
          ) : (
            paginatedData.map((group) => (
              <div key={group.agent_company_id} className="border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden">
                {/* Company Header Row */}
                <button
                  onClick={() => toggleCompany(group.agent_company_id)}
                  className="w-full flex items-center justify-between px-4 py-3 bg-slate-50 dark:bg-slate-700/50 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    {expandedCompanies[group.agent_company_id] ? (
                      <ChevronDown className="w-4 h-4 text-slate-500" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-slate-500" />
                    )}
                    <div className="text-left">
                      <div className="font-semibold text-slate-800 dark:text-white">{group.company_name || group.till_name}</div>
                      <div className="text-xs text-slate-500 dark:text-slate-400">
                        {group.till_name && <span>Till: {group.till_name}</span>}
                        {group.till_number && <span className="ml-2">#{group.till_number}</span>}
                      </div>
                    </div>
                  </div>
                  <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400">
                    {group.total_swaps} swap{group.total_swaps !== 1 ? 's' : ''}
                  </span>
                </button>

                {/* Expanded Swap Rows */}
                {expandedCompanies[group.agent_company_id] && (
                  <div className="divide-y divide-slate-100 dark:divide-slate-700">
                    {/* Sub-header */}
                    <div className="grid grid-cols-[auto_1fr_1fr_1fr_1fr_1fr_1fr_1fr_auto] gap-2 px-4 py-2 bg-slate-100/50 dark:bg-slate-700/30 text-xs font-semibold text-slate-600 dark:text-slate-400">
                      <div className="flex items-center">
                        <input
                          type="checkbox"
                          checked={group.swaps.length > 0 && group.swaps.every((s) => selectedSwapIds.includes(s.id))}
                          onChange={() => handleSelectAllInGroup(group)}
                          className="w-3.5 h-3.5 text-blue-600 border-slate-300 rounded focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600"
                        />
                      </div>
                      <div>Swap Date</div>
                      <div>Previous Agents</div>
                      <div>New Agents</div>
                      <div className="text-right">Float at Swap</div>
                      <div className="text-right">Commission at Swap</div>
                      <div>Initiated By</div>
                      <div>Notes</div>
                      <div className="text-center">Payout</div>
                    </div>

                    {group.swaps.map((swap) => (
                      <div
                        key={swap.id}
                        className={`grid grid-cols-[auto_1fr_1fr_1fr_1fr_1fr_1fr_1fr_auto] gap-2 px-4 py-3 text-sm hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors cursor-pointer ${
                          selectedSwapIds.includes(swap.id) ? 'bg-blue-50/50 dark:bg-blue-900/10' : ''
                        }`}
                        onClick={() => handleSelectSwap(swap.id)}
                      >
                        <div className="flex items-center" onClick={(e) => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            checked={selectedSwapIds.includes(swap.id)}
                            onChange={() => handleSelectSwap(swap.id)}
                            className="w-3.5 h-3.5 text-blue-600 border-slate-300 rounded focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600"
                          />
                        </div>
                        <div className="text-slate-700 dark:text-slate-300">
                          {formatDate(swap.swap_date)}
                        </div>
                        <div className="space-y-1">
                          {(swap.previous_agents || []).map((a, i) => (
                            <div key={i} className="text-xs text-red-600 dark:text-red-400">
                              <div className="flex items-center gap-1 font-medium">
                                <Users className="w-3 h-3 flex-shrink-0" />
                                <span className="truncate">{a.name}</span>
                              </div>
                              <div className="ml-4 text-[10px] text-red-500/70 dark:text-red-400/60">
                                {a.idnumber && <span>ID: {a.idnumber}</span>}
                                {a.phone_number && <span className="ml-1">| {a.phone_number}</span>}
                              </div>
                            </div>
                          ))}
                          {(!swap.previous_agents || swap.previous_agents.length === 0) && (
                            <span className="text-xs text-slate-400">None</span>
                          )}
                        </div>
                        <div className="space-y-1">
                          {(swap.new_agents || []).map((a, i) => (
                            <div key={i} className="text-xs text-green-600 dark:text-green-400">
                              <div className="flex items-center gap-1 font-medium">
                                <Users className="w-3 h-3 flex-shrink-0" />
                                <span className="truncate">{a.name}</span>
                              </div>
                              <div className="ml-4 text-[10px] text-green-500/70 dark:text-green-400/60">
                                {a.idnumber && <span>ID: {a.idnumber}</span>}
                                {a.phone_number && <span className="ml-1">| {a.phone_number}</span>}
                              </div>
                            </div>
                          ))}
                        </div>
                        <div className="text-right font-medium text-blue-700 dark:text-blue-400">
                          KES {parseFloat(swap.float_balance_at_swap || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                        </div>
                        <div className="text-right font-medium text-green-700 dark:text-green-400">
                          KES {parseFloat(swap.commission_balance_at_swap || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                        </div>
                        <div className="text-xs text-slate-600 dark:text-slate-400 truncate">
                          {swap.initiator_name || 'N/A'}
                        </div>
                        <div className="text-xs text-slate-500 dark:text-slate-400 truncate" title={swap.notes}>
                          {swap.notes || '-'}
                        </div>
                        <div className="flex items-center justify-center">
                          {getPayoutStatusIcon(swap.id)}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {/* Pagination */}
      {paginatedData.length > 0 && (
        <div className="flex flex-col sm:flex-row justify-between items-center mt-4 space-y-4 sm:space-y-0">
          <div className="flex items-center space-x-2">
            <span className="text-sm text-slate-600 dark:text-slate-300">
              Showing {startIndex + 1} - {Math.min(startIndex + pageSize, totalItems)} of {totalItems} companies
            </span>
            <select
              value={pageSize}
              onChange={(e) => { setPageSize(Number(e.target.value)); setCurrentPage(1); }}
              className="py-1 px-2 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="5">5 per page</option>
              <option value="10">10 per page</option>
              <option value="20">20 per page</option>
              <option value="50">50 per page</option>
            </select>
          </div>
          <div className="flex items-center space-x-2">
            <button onClick={() => handlePageChange(1)} disabled={currentPage === 1} className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed">First</button>
            <button onClick={() => handlePageChange(currentPage - 1)} disabled={currentPage === 1} className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed">Previous</button>
            <span className="text-sm text-slate-600 dark:text-slate-300">Page {currentPage} of {totalPages || 1}</span>
            <button onClick={() => handlePageChange(currentPage + 1)} disabled={currentPage === totalPages || totalPages === 0} className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed">Next</button>
            <button onClick={() => handlePageChange(totalPages)} disabled={currentPage === totalPages || totalPages === 0} className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed">Last</button>
          </div>
        </div>
      )}

      {/* Swap Detail Modal */}
      {swapDetail && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                  <ArrowRightLeft className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-slate-800 dark:text-white">Swap Details</h2>
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    #{swapDetail.id} — {swapDetail.company_name || swapDetail.till_name}
                    {swapDetail.till_name && swapDetail.company_name && <span className="ml-1 text-slate-400">· {swapDetail.till_name}</span>}
                  </p>
                </div>
              </div>
              <button onClick={() => setSwapDetail(null)} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors">
                <X className="w-5 h-5 text-slate-500" />
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Timestamps */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-4">
                  <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Swap Date</div>
                  <div className="text-sm font-semibold text-slate-800 dark:text-white">{formatDate(swapDetail.swap_date)}</div>
                </div>
                <div className="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-4">
                  <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Record Created</div>
                  <div className="text-sm font-semibold text-slate-800 dark:text-white">{formatDate(swapDetail.created_at)}</div>
                </div>
              </div>

              {/* Financial Snapshot */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl p-4">
                  <div className="text-xs text-blue-600 dark:text-blue-400 font-medium mb-1">Float Balance at Swap</div>
                  <div className="text-xl font-bold text-blue-800 dark:text-blue-200">
                    KES {parseFloat(swapDetail.float_balance_at_swap || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </div>
                </div>
                <div className="bg-green-50 dark:bg-green-900/20 rounded-xl p-4">
                  <div className="text-xs text-green-600 dark:text-green-400 font-medium mb-1">Commission Balance at Swap</div>
                  <div className="text-xl font-bold text-green-800 dark:text-green-200">
                    KES {parseFloat(swapDetail.commission_balance_at_swap || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </div>
                </div>
              </div>

              {/* Initiator & Status */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-4">
                  <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Initiated By</div>
                  <div className="text-sm font-semibold text-slate-800 dark:text-white">{swapDetail.initiator_name || 'N/A'}</div>
                </div>
                <div className="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-4">
                  <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Status</div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    swapDetail.status === 'completed'
                      ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                      : 'bg-slate-100 text-slate-600 dark:bg-slate-600 dark:text-slate-300'
                  }`}>
                    {swapDetail.status?.charAt(0).toUpperCase() + swapDetail.status?.slice(1)}
                  </span>
                </div>
              </div>

              {/* Previous Agents */}
              <div>
                <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2 flex items-center gap-2">
                  <Users className="w-4 h-4 text-red-500" />
                  Previous Agents (Outgoing)
                </h3>
                {(!swapDetail.previous_agents || swapDetail.previous_agents.length === 0) ? (
                  <p className="text-sm text-slate-500 dark:text-slate-400">None</p>
                ) : (
                  <div className="space-y-2">
                    {swapDetail.previous_agents.map((agent, i) => (
                      <div key={i} className="flex items-center gap-3 p-3 bg-red-50 dark:bg-red-900/10 rounded-lg border border-red-100 dark:border-red-900/30">
                        <div className="flex-1">
                          <div className="text-sm font-medium text-slate-800 dark:text-slate-200">{agent.name}</div>
                          <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                            {agent.idnumber && <span>ID: {agent.idnumber}</span>}
                            {agent.phone_number && <span className="ml-2">Phone: {agent.phone_number}</span>}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* New Agents */}
              <div>
                <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2 flex items-center gap-2">
                  <Users className="w-4 h-4 text-green-500" />
                  New Agents (Incoming)
                </h3>
                {(!swapDetail.new_agents || swapDetail.new_agents.length === 0) ? (
                  <p className="text-sm text-slate-500 dark:text-slate-400">None</p>
                ) : (
                  <div className="space-y-2">
                    {swapDetail.new_agents.map((agent, i) => (
                      <div key={i} className="flex items-center gap-3 p-3 bg-green-50 dark:bg-green-900/10 rounded-lg border border-green-100 dark:border-green-900/30">
                        <div className="flex-1">
                          <div className="text-sm font-medium text-slate-800 dark:text-slate-200">{agent.name}</div>
                          <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                            {agent.idnumber && <span>ID: {agent.idnumber}</span>}
                            {agent.phone_number && <span className="ml-2">Phone: {agent.phone_number}</span>}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Payout Status */}
              {swapPayouts[swapDetail.id] && swapPayouts[swapDetail.id].length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2 flex items-center gap-2">
                    <Banknote className="w-4 h-4 text-green-500" />
                    Payout Status
                  </h3>
                  <div className="space-y-2">
                    {swapPayouts[swapDetail.id].map((payout) => (
                      <div key={payout.id} className={`flex items-center justify-between p-3 rounded-lg border ${
                        payout.status === 'completed'
                          ? 'bg-green-50 dark:bg-green-900/10 border-green-100 dark:border-green-900/30'
                          : payout.status === 'failed'
                          ? 'bg-red-50 dark:bg-red-900/10 border-red-100 dark:border-red-900/30'
                          : 'bg-amber-50 dark:bg-amber-900/10 border-amber-100 dark:border-amber-900/30'
                      }`}>
                        <div>
                          <div className="text-sm font-medium text-slate-800 dark:text-slate-200">{payout.agent_name}</div>
                          <div className="text-xs text-slate-500 dark:text-slate-400">{payout.phone_number}</div>
                          {payout.mpesa_receipt && (
                            <div className="text-xs text-green-600 dark:text-green-400 mt-0.5">Receipt: {payout.mpesa_receipt}</div>
                          )}
                          {payout.result_desc && payout.status === 'failed' && (
                            <div className="text-xs text-red-500 mt-0.5">{payout.result_desc}</div>
                          )}
                        </div>
                        <div className="text-right">
                          <div className="text-sm font-bold text-slate-800 dark:text-slate-200">
                            KES {parseFloat(payout.amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                          </div>
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                            payout.status === 'completed'
                              ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                              : payout.status === 'failed'
                              ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                              : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
                          }`}>
                            {payout.status === 'completed' && <CheckCircle2 className="w-3 h-3" />}
                            {payout.status === 'failed' && <XCircle className="w-3 h-3" />}
                            {payout.status === 'pending' && <Clock className="w-3 h-3" />}
                            {payout.status.charAt(0).toUpperCase() + payout.status.slice(1)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Notes */}
              {swapDetail.notes && (
                <div className="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-4">
                  <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Notes</div>
                  <div className="text-sm text-slate-700 dark:text-slate-300">{swapDetail.notes}</div>
                </div>
              )}
            </div>

            <div className="flex items-center justify-end px-6 py-4 border-t border-slate-200 dark:border-slate-700">
              <button
                onClick={() => setSwapDetail(null)}
                className="px-4 py-2 text-sm text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Revert Confirmation Modal */}
      {revertConfirm && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-md">
            <div className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
                  <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400" />
                </div>
                <h3 className="text-lg font-semibold text-slate-800 dark:text-white">Confirm Revert</h3>
              </div>
              <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
                Are you sure you want to revert this swap? This will:
              </p>
              <ul className="text-sm text-slate-600 dark:text-slate-400 space-y-2 mb-4 ml-4">
                <li className="flex items-start gap-2">
                  <span className="text-red-500 mt-0.5">&#8226;</span>
                  Remove current agents: {(revertConfirm.new_agents || []).map(a => a.name).join(', ') || 'None'}
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-green-500 mt-0.5">&#8226;</span>
                  Restore previous agents: {(revertConfirm.previous_agents || []).map(a => a.name).join(', ') || 'None'}
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-amber-500 mt-0.5">&#8226;</span>
                  Delete the swap record permanently
                </li>
              </ul>
              <p className="text-xs text-slate-500 dark:text-slate-500 mb-6">
                This action cannot be undone.
              </p>
              <div className="flex items-center justify-end gap-3">
                <button
                  onClick={() => setRevertConfirm(null)}
                  className="px-4 py-2 text-sm text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmRevert}
                  className="px-4 py-2 text-sm text-white bg-amber-500 rounded-xl hover:bg-amber-600 transition-colors flex items-center gap-2"
                >
                  <Undo2 className="w-4 h-4" />
                  Revert Swap
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Payout Confirmation Modal */}
      {payoutModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                  <Banknote className="w-5 h-5 text-green-600 dark:text-green-400" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-slate-800 dark:text-white">Initiate Payout</h2>
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    Swap #{payoutModal.id} — {payoutModal.company_name || payoutModal.till_name}
                    {payoutModal.till_name && payoutModal.company_name && <span className="ml-1 text-slate-400">· {payoutModal.till_name}</span>}
                  </p>
                </div>
              </div>
              <button onClick={() => setPayoutModal(null)} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors">
                <X className="w-5 h-5 text-slate-500" />
              </button>
            </div>

            <div className="p-6 space-y-5">
              {/* Summary */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-3">
                  <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Swap Date</div>
                  <div className="text-sm font-semibold text-slate-800 dark:text-white">{formatDate(payoutModal.swap_date)}</div>
                </div>
                <div className="bg-green-50 dark:bg-green-900/20 rounded-xl p-3">
                  <div className="text-xs text-green-600 dark:text-green-400 mb-1">Commission Balance</div>
                  <div className="text-lg font-bold text-green-800 dark:text-green-200">
                    KES {parseFloat(payoutModal.commission_balance_at_swap || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </div>
                </div>
              </div>

              {/* Agent Payout Breakdown */}
              <div>
                <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">Outgoing Agents — Payout Amounts</h3>
                <div className="space-y-3">
                  {(payoutModal.previous_agents || []).map((agent, i) => (
                    <div key={i} className="flex items-center gap-3 p-3 bg-slate-50 dark:bg-slate-700/30 rounded-xl border border-slate-200 dark:border-slate-600">
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-slate-800 dark:text-slate-200">{agent.name}</div>
                        <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                          {agent.idnumber && <span>ID: {agent.idnumber}</span>}
                          {agent.phone_number && <span className="ml-2">Phone: {agent.phone_number}</span>}
                          {!agent.phone_number && <span className="text-red-500">No phone number</span>}
                        </div>
                      </div>
                      <div className="flex items-center gap-1">
                        <span className="text-xs text-slate-500">KES</span>
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={payoutAmounts[i] || 0}
                          onChange={(e) => setPayoutAmounts((prev) => ({ ...prev, [i]: parseFloat(e.target.value) || 0 }))}
                          className="w-28 px-2 py-1.5 text-sm text-right bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-500 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                        />
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-3 flex justify-between items-center text-sm">
                  <span className="text-slate-600 dark:text-slate-400">Total Payout:</span>
                  <span className="font-bold text-slate-800 dark:text-white">
                    KES {Object.values(payoutAmounts).reduce((sum, v) => sum + (v || 0), 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </span>
                </div>
              </div>

              {/* Warning */}
              <div className="flex items-start gap-2 p-3 bg-amber-50 dark:bg-amber-900/10 rounded-xl border border-amber-200 dark:border-amber-900/30">
                <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
                <p className="text-xs text-amber-700 dark:text-amber-400">
                  This will send M-Pesa B2C payments to each agent's phone number. Commission will be split as shown above. Amounts are sent to the M-Pesa API as displayed. This action cannot be undone.
                </p>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-200 dark:border-slate-700">
              <button
                onClick={() => setPayoutModal(null)}
                disabled={isPayoutLoading}
                className="px-4 py-2 text-sm text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmPayout}
                disabled={isPayoutLoading}
                className="px-4 py-2 text-sm text-white bg-green-500 rounded-xl hover:bg-green-600 transition-colors flex items-center gap-2 disabled:bg-green-300"
              >
                {isPayoutLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Banknote className="w-4 h-4" />}
                {isPayoutLoading ? 'Processing...' : 'Confirm Payout'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Report Modal */}
      {isReportModalOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
              <div className="flex items-center gap-3">
                <FileText className="w-5 h-5 text-blue-600" />
                <h2 className="text-lg font-semibold text-slate-800 dark:text-white">Swap Report</h2>
              </div>
              <button onClick={() => setIsReportModalOpen(false)} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg">
                <X className="w-5 h-5 text-slate-500" />
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Report Parameters */}
              <div className="flex items-end gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Start Date</label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="px-3 py-2 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">End Date</label>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="px-3 py-2 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <button
                  onClick={handleGenerateReport}
                  disabled={isReportLoading}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-xl hover:bg-blue-600 disabled:bg-blue-300 transition-colors"
                >
                  {isReportLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />}
                  Generate
                </button>
              </div>

              {/* Report Results */}
              {reportData && (
                <div className="space-y-6">
                  {/* Summary Cards */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-4">
                      <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Total Swaps</div>
                      <div className="text-2xl font-bold text-slate-800 dark:text-white">{reportData.summary.total_swaps}</div>
                    </div>
                    <div className="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-4">
                      <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Companies Involved</div>
                      <div className="text-2xl font-bold text-slate-800 dark:text-white">{reportData.summary.companies_involved}</div>
                    </div>
                    <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl p-4">
                      <div className="text-xs text-blue-600 dark:text-blue-400 mb-1">Avg Float at Swap</div>
                      <div className="text-lg font-bold text-blue-800 dark:text-blue-200">
                        KES {parseFloat(reportData.summary.avg_float_at_swap || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </div>
                    </div>
                    <div className="bg-green-50 dark:bg-green-900/20 rounded-xl p-4">
                      <div className="text-xs text-green-600 dark:text-green-400 mb-1">Avg Commission at Swap</div>
                      <div className="text-lg font-bold text-green-800 dark:text-green-200">
                        KES {parseFloat(reportData.summary.avg_commission_at_swap || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </div>
                    </div>
                  </div>

                  {/* Per-Company Breakdown */}
                  {reportData.companies && reportData.companies.length > 0 && (
                    <div>
                      <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">Company Breakdown</h3>
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="bg-slate-100 dark:bg-slate-700 text-left text-slate-600 dark:text-slate-300">
                              <th className="px-3 py-2 font-semibold">Company</th>
                              <th className="px-3 py-2 font-semibold">Till</th>
                              <th className="px-3 py-2 font-semibold text-center">Swaps</th>
                              <th className="px-3 py-2 font-semibold text-right">Avg Float</th>
                              <th className="px-3 py-2 font-semibold text-right">Avg Commission</th>
                              <th className="px-3 py-2 font-semibold">First Swap</th>
                              <th className="px-3 py-2 font-semibold">Last Swap</th>
                            </tr>
                          </thead>
                          <tbody>
                            {reportData.companies.map((company, idx) => (
                              <tr key={company.agent_company_id} className={`border-b border-slate-100 dark:border-slate-700 ${idx % 2 === 0 ? '' : 'bg-slate-50 dark:bg-slate-700/30'}`}>
                                <td className="px-3 py-2 font-medium">{company.company_name || '—'}</td>
                                <td className="px-3 py-2 text-slate-500">
                                  <div>{company.till_name || '—'}</div>
                                  {company.till_number && <div className="text-xs text-slate-400">#{company.till_number}</div>}
                                </td>
                                <td className="px-3 py-2 text-center">
                                  <span className="px-2 py-0.5 rounded-full text-xs bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400">{company.swap_count}</span>
                                </td>
                                <td className="px-3 py-2 text-right text-blue-700 dark:text-blue-400">
                                  KES {parseFloat(company.avg_float_at_swap || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                                </td>
                                <td className="px-3 py-2 text-right text-green-700 dark:text-green-400">
                                  KES {parseFloat(company.avg_commission_at_swap || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                                </td>
                                <td className="px-3 py-2 text-slate-500 text-xs">{formatDate(company.first_swap)}</td>
                                <td className="px-3 py-2 text-slate-500 text-xs">{formatDate(company.last_swap)}</td>
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

            {/* Modal Footer */}
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-200 dark:border-slate-700">
              {reportData && (
                <button
                  onClick={handleExportReport}
                  className="flex items-center gap-2 px-4 py-2 text-sm text-white bg-green-500 rounded-xl hover:bg-green-600 transition-colors"
                >
                  <Download className="w-4 h-4" />
                  Export CSV
                </button>
              )}
              <button
                onClick={() => setIsReportModalOpen(false)}
                className="px-4 py-2 text-sm text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default SwapHistoryGrid;
