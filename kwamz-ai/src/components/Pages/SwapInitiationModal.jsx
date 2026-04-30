import { useState, useEffect, useMemo } from 'react';
import { X, ArrowRightLeft, Loader2, UserCheck, UserMinus, Search } from 'lucide-react';
import axios from 'axios';
import config from '../../Config';

function SwapInitiationModal({ isOpen, onClose, agentCompany, onSwapComplete }) {
  const [availableAgents, setAvailableAgents] = useState([]);
  const [selectedOutgoingIds, setSelectedOutgoingIds] = useState([]);
  const [selectedIncomingIds, setSelectedIncomingIds] = useState([]);
  const [outgoingSearch, setOutgoingSearch] = useState('');
  const [incomingSearch, setIncomingSearch] = useState('');
  const [notes, setNotes] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const currentAgents = agentCompany?.user_agents || [];

  useEffect(() => {
    if (isOpen && agentCompany) {
      fetchAvailableAgents();
      // Auto-select all current agents as outgoing when there's only 1
      setSelectedOutgoingIds(currentAgents.length === 1 ? [currentAgents[0].id] : []);
      setSelectedIncomingIds([]);
      setOutgoingSearch('');
      setIncomingSearch('');
      setNotes('');
      setError('');
    }
  }, [isOpen, agentCompany]);

  const fetchAvailableAgents = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${config.API_URL}/useragent`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setAvailableAgents(response.data || []);
    } catch (err) {
      console.error('Error fetching agents:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const agentLabel = (agent) =>
    `${agent.firstname || ''} ${agent.lastname || agent.fullname || ''}`.trim();

  const matchesSearch = (agent, query) => {
    if (!query) return true;
    const q = query.toLowerCase();
    return (
      agentLabel(agent).toLowerCase().includes(q) ||
      (agent.idnumber || '').toLowerCase().includes(q) ||
      (agent.phone_number || '').toLowerCase().includes(q)
    );
  };

  const currentAgentIds = useMemo(() => new Set(currentAgents.map((a) => a.id)), [currentAgents]);

  // Incoming pool: agents not currently on this till
  const incomingPool = useMemo(
    () => availableAgents.filter((a) => !currentAgentIds.has(a.id)),
    [availableAgents, currentAgentIds]
  );

  const filteredOutgoing = currentAgents.filter((a) => matchesSearch(a, outgoingSearch));
  const filteredIncoming = incomingPool.filter((a) => matchesSearch(a, incomingSearch));

  const toggleOutgoing = (id) => {
    setSelectedOutgoingIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const toggleIncoming = (id) => {
    setSelectedIncomingIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const handleSubmit = async () => {
    if (selectedOutgoingIds.length === 0) {
      setError('Select at least one outgoing agent.');
      return;
    }
    if (selectedIncomingIds.length === 0) {
      setError('Select at least one incoming agent.');
      return;
    }
    setError('');
    setIsSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${config.API_URL}/swaps`,
        {
          agent_company_id: agentCompany.id,
          outgoing_agent_ids: selectedOutgoingIds,
          new_agent_ids: selectedIncomingIds,
          notes,
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      onSwapComplete();
      onClose();
    } catch (err) {
      const msg = err.response?.data?.error || 'Failed to initiate swap. Please try again.';
      setError(msg);
      console.error('Error initiating swap:', err.response?.data || err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen || !agentCompany) return null;

  const floatBalance = (() => {
    const acc = agentCompany.accounts?.find((a) =>
      a.account_type?.toLowerCase().includes('float')
    );
    return acc?.balances?.current_balance || '0.00';
  })();
  const commissionBalance = (() => {
    const acc = agentCompany.accounts?.find((a) =>
      a.account_type?.toLowerCase().includes('commission')
    );
    return acc?.balances?.current_balance || '0.00';
  })();

  const canSubmit =
    selectedOutgoingIds.length > 0 && selectedIncomingIds.length > 0 && !isSubmitting;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-orange-100 dark:bg-orange-900/30 flex items-center justify-center">
              <ArrowRightLeft className="w-5 h-5 text-orange-600 dark:text-orange-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-800 dark:text-white">Initiate Swap</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">{agentCompany.company_name}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>

        {/* Scrollable body */}
        <div className="p-6 space-y-5 overflow-y-auto flex-1">
          {/* Balance Snapshot */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl p-4">
              <div className="text-xs text-blue-600 dark:text-blue-400 font-medium mb-1">Float Balance</div>
              <div className="text-lg font-bold text-blue-800 dark:text-blue-200">
                KES {parseFloat(floatBalance).toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </div>
            </div>
            <div className="bg-green-50 dark:bg-green-900/20 rounded-xl p-4">
              <div className="text-xs text-green-600 dark:text-green-400 font-medium mb-1">Commission Balance</div>
              <div className="text-lg font-bold text-green-800 dark:text-green-200">
                KES {parseFloat(commissionBalance).toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </div>
            </div>
          </div>

          {/* Outgoing — select who is leaving */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <UserMinus className="w-4 h-4 text-red-500" />
              <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                Outgoing Agent{currentAgents.length !== 1 ? 's' : ''}
              </h3>
              {currentAgents.length > 1 && (
                <span className="ml-auto text-xs text-slate-400">
                  {selectedOutgoingIds.length} selected
                </span>
              )}
            </div>

            {currentAgents.length === 0 ? (
              <p className="text-sm text-slate-500 dark:text-slate-400">No agents currently assigned</p>
            ) : (
              <>
                {/* Search — only show when >3 agents for clutter */}
                {currentAgents.length > 3 && (
                  <div className="relative mb-2">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input
                      type="text"
                      value={outgoingSearch}
                      onChange={(e) => setOutgoingSearch(e.target.value)}
                      placeholder="Search current agents..."
                      className="w-full pl-9 pr-3 py-2 text-sm bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg text-slate-800 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-red-400"
                    />
                  </div>
                )}

                <div className="space-y-2 max-h-44 overflow-y-auto">
                  {filteredOutgoing.length === 0 ? (
                    <p className="text-sm text-slate-400 py-2">No agents match your search</p>
                  ) : (
                    filteredOutgoing.map((agent) => {
                      const checked = selectedOutgoingIds.includes(agent.id);
                      return (
                        <label
                          key={agent.id}
                          className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all select-none ${
                            checked
                              ? 'bg-red-50 dark:bg-red-900/20 border-red-300 dark:border-red-700'
                              : 'bg-slate-50 dark:bg-slate-700/50 border-slate-200 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => toggleOutgoing(agent.id)}
                            className="w-4 h-4 text-red-500 border-slate-300 rounded focus:ring-red-400"
                          />
                          <span
                            className={`w-2 h-2 rounded-full flex-shrink-0 ${
                              agent.is_authentic ? 'bg-green-500' : 'bg-yellow-500'
                            }`}
                          />
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-medium text-slate-800 dark:text-slate-200">
                              {agentLabel(agent)}
                            </div>
                            <div className="text-xs text-slate-500 dark:text-slate-400">
                              ID: {agent.idnumber}
                              {agent.phone_number && ` | ${agent.phone_number}`}
                            </div>
                          </div>
                          {checked && (
                            <span className="text-xs font-medium text-red-500 dark:text-red-400 flex-shrink-0">
                              Leaving
                            </span>
                          )}
                        </label>
                      );
                    })
                  )}
                </div>
              </>
            )}
          </div>

          {/* Incoming — select who is coming in */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <UserCheck className="w-4 h-4 text-green-500" />
              <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                Incoming Agents
              </h3>
              {selectedIncomingIds.length > 0 && (
                <span className="ml-auto text-xs text-slate-400">
                  {selectedIncomingIds.length} selected
                </span>
              )}
            </div>

            {/* Search */}
            <div className="relative mb-2">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                value={incomingSearch}
                onChange={(e) => setIncomingSearch(e.target.value)}
                placeholder="Search by name, ID number or phone..."
                className="w-full pl-9 pr-3 py-2 text-sm bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg text-slate-800 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-green-400"
              />
            </div>

            {isLoading ? (
              <div className="flex items-center justify-center py-6">
                <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
              </div>
            ) : filteredIncoming.length === 0 ? (
              <p className="text-sm text-slate-500 dark:text-slate-400 py-2">
                {incomingSearch ? 'No agents match your search' : 'No other agents available'}
              </p>
            ) : (
              <div className="space-y-2 max-h-44 overflow-y-auto">
                {filteredIncoming.map((agent) => {
                  const checked = selectedIncomingIds.includes(agent.id);
                  return (
                    <label
                      key={agent.id}
                      className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all select-none ${
                        checked
                          ? 'bg-green-50 dark:bg-green-900/20 border-green-300 dark:border-green-700'
                          : 'bg-slate-50 dark:bg-slate-700/50 border-slate-200 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleIncoming(agent.id)}
                        className="w-4 h-4 text-green-600 border-slate-300 rounded focus:ring-green-500"
                      />
                      <span
                        className={`w-2 h-2 rounded-full flex-shrink-0 ${
                          agent.is_authentic ? 'bg-green-500' : 'bg-yellow-500'
                        }`}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-slate-800 dark:text-slate-200">
                          {agentLabel(agent)}
                        </div>
                        <div className="text-xs text-slate-500 dark:text-slate-400">
                          ID: {agent.idnumber}
                          {agent.phone_number && ` | ${agent.phone_number}`}
                        </div>
                      </div>
                      {checked && (
                        <span className="text-xs font-medium text-green-600 dark:text-green-400 flex-shrink-0">
                          Incoming
                        </span>
                      )}
                    </label>
                  );
                })}
              </div>
            )}
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
              Notes (optional)
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Reason for swap..."
              rows={3}
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all resize-none"
            />
          </div>

          {/* Error */}
          {error && (
            <p className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-lg px-3 py-2">
              {error}
            </p>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between gap-3 px-6 py-4 border-t border-slate-200 dark:border-slate-700 flex-shrink-0">
          {/* Summary pill */}
          <div className="text-xs text-slate-500 dark:text-slate-400">
            {selectedOutgoingIds.length > 0 || selectedIncomingIds.length > 0 ? (
              <span>
                {selectedOutgoingIds.length} leaving → {selectedIncomingIds.length} incoming
              </span>
            ) : (
              <span>Select agents to continue</span>
            )}
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={!canSubmit}
              className="px-4 py-2 text-sm text-white bg-orange-500 rounded-xl hover:bg-orange-600 disabled:bg-orange-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <ArrowRightLeft className="w-4 h-4" />
                  Confirm Swap
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default SwapInitiationModal;
