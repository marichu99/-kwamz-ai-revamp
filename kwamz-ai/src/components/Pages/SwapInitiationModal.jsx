import { useState, useEffect } from 'react';
import { X, ArrowRightLeft, Loader2, UserCheck, UserMinus } from 'lucide-react';
import axios from 'axios';
import config from '../../Config';

function SwapInitiationModal({ isOpen, onClose, agentCompany, onSwapComplete }) {
  const [availableAgents, setAvailableAgents] = useState([]);
  const [selectedNewAgentIds, setSelectedNewAgentIds] = useState([]);
  const [notes, setNotes] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (isOpen && agentCompany) {
      fetchAvailableAgents();
      setSelectedNewAgentIds([]);
      setNotes('');
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
    } catch (error) {
      console.error('Error fetching agents:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleAgent = (agentId) => {
    setSelectedNewAgentIds((prev) =>
      prev.includes(agentId)
        ? prev.filter((id) => id !== agentId)
        : [...prev, agentId]
    );
  };

  const handleSubmit = async () => {
    if (selectedNewAgentIds.length === 0) return;

    setIsSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${config.API_URL}/swaps`,
        {
          agent_company_id: agentCompany.id,
          new_agent_ids: selectedNewAgentIds,
          notes,
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      onSwapComplete();
      onClose();
    } catch (error) {
      console.error('Error initiating swap:', error.response?.data || error.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen || !agentCompany) return null;

  const currentAgents = agentCompany.user_agents || [];
  const floatBalance = (() => {
    const acc = agentCompany.accounts?.find(a => a.account_type?.toLowerCase().includes('float'));
    return acc?.balances?.current_balance || '0.00';
  })();
  const commissionBalance = (() => {
    const acc = agentCompany.accounts?.find(a => a.account_type?.toLowerCase().includes('commission'));
    return acc?.balances?.current_balance || '0.00';
  })();

  // Filter out current agents from available list
  const currentAgentIds = currentAgents.map(a => a.id);
  const selectableAgents = availableAgents.filter(a => !currentAgentIds.includes(a.id));

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-orange-100 dark:bg-orange-900/30 flex items-center justify-center">
              <ArrowRightLeft className="w-5 h-5 text-orange-600 dark:text-orange-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-800 dark:text-white">Initiate Swap</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">{agentCompany.company_name}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors">
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>

        <div className="p-6 space-y-6">
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

          {/* Current Agents (Outgoing) */}
          <div>
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2 flex items-center gap-2">
              <UserMinus className="w-4 h-4 text-red-500" />
              Current Agents (Outgoing)
            </h3>
            {currentAgents.length === 0 ? (
              <p className="text-sm text-slate-500 dark:text-slate-400">No agents currently assigned</p>
            ) : (
              <div className="space-y-2">
                {currentAgents.map((agent) => (
                  <div key={agent.id} className="flex items-center gap-3 p-3 bg-red-50 dark:bg-red-900/10 rounded-lg border border-red-100 dark:border-red-900/30">
                    <span className={`w-2 h-2 rounded-full flex-shrink-0 ${agent.is_authentic ? 'bg-green-500' : 'bg-yellow-500'}`} />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-slate-800 dark:text-slate-200">{agent.fullname || `${agent.firstname} ${agent.lastname}`}</div>
                      <div className="text-xs text-slate-500 dark:text-slate-400">ID: {agent.idnumber} {agent.phone_number && `| ${agent.phone_number}`}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Select New Agents (Incoming) */}
          <div>
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2 flex items-center gap-2">
              <UserCheck className="w-4 h-4 text-green-500" />
              Select New Agents (Incoming)
            </h3>
            {isLoading ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
              </div>
            ) : selectableAgents.length === 0 ? (
              <p className="text-sm text-slate-500 dark:text-slate-400">No other agents available</p>
            ) : (
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {selectableAgents.map((agent) => (
                  <label
                    key={agent.id}
                    className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                      selectedNewAgentIds.includes(agent.id)
                        ? 'bg-green-50 dark:bg-green-900/20 border-green-300 dark:border-green-700'
                        : 'bg-slate-50 dark:bg-slate-700/50 border-slate-200 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedNewAgentIds.includes(agent.id)}
                      onChange={() => handleToggleAgent(agent.id)}
                      className="w-4 h-4 text-green-600 border-slate-300 rounded focus:ring-green-500"
                    />
                    <span className={`w-2 h-2 rounded-full flex-shrink-0 ${agent.is_authentic ? 'bg-green-500' : 'bg-yellow-500'}`} />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-slate-800 dark:text-slate-200">
                        {agent.firstname} {agent.lastname}
                      </div>
                      <div className="text-xs text-slate-500 dark:text-slate-400">
                        ID: {agent.idnumber} {agent.phone_number && `| ${agent.phone_number}`}
                      </div>
                    </div>
                  </label>
                ))}
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
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-200 dark:border-slate-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={selectedNewAgentIds.length === 0 || isSubmitting}
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
  );
}

export default SwapInitiationModal;
