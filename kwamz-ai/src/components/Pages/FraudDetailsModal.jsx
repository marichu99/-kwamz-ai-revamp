import { X, AlertTriangle, FileText, Clock, DollarSign, Hash, User, ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';

function FraudDetailsModal({ isOpen, onClose, agentCompany }) {
  const [expandedAlerts, setExpandedAlerts] = useState({});

  if (!isOpen || !agentCompany) return null;

  const toggleAlertExpanded = (alertId) => {
    setExpandedAlerts(prev => ({
      ...prev,
      [alertId]: !prev[alertId]
    }));
  };

  const getRiskLevelColor = (level) => {
    switch (level?.toUpperCase()) {
      case 'HIGH':
        return 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-400';
      case 'MEDIUM':
        return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-400';
      case 'LOW':
        return 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-400';
      default:
        return 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300';
    }
  };

  const getFraudTypeIcon = (type) => {
    switch (type) {
      case 'split_transaction':
        return <Hash className="w-4 h-4" />;
      case 'rollover_fraud':
        return <Clock className="w-4 h-4" />;
      case 'rapid_back_forth':
        return <DollarSign className="w-4 h-4" />;
      default:
        return <AlertTriangle className="w-4 h-4" />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden m-4">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-200 dark:border-slate-700 bg-red-50 dark:bg-red-900/20">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-100 dark:bg-red-900/50 rounded-lg">
              <AlertTriangle className="w-6 h-6 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-800 dark:text-white">
                Fraud Detection Details
              </h2>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                {agentCompany.company_name}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-180px)]">
          {/* Summary Stats */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-4 text-center">
              <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                {agentCompany.fraud_alerts_count || 0}
              </div>
              <div className="text-sm text-slate-600 dark:text-slate-400">Total Alerts</div>
            </div>
            <div className="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-4 text-center">
              <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
                {agentCompany.unresolved_fraud_count || 0}
              </div>
              <div className="text-sm text-slate-600 dark:text-slate-400">Unresolved</div>
            </div>
            <div className="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-4 text-center">
              <div className={`text-2xl font-bold ${
                agentCompany.fraud_risk_level === 'high' ? 'text-red-600 dark:text-red-400' :
                agentCompany.fraud_risk_level === 'medium' ? 'text-yellow-600 dark:text-yellow-400' :
                'text-green-600 dark:text-green-400'
              }`}>
                {agentCompany.fraud_risk_level?.toUpperCase() || 'LOW'}
              </div>
              <div className="text-sm text-slate-600 dark:text-slate-400">Risk Level</div>
            </div>
          </div>

          {/* Fraud Alerts List */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-slate-800 dark:text-white flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Fraud Alerts
            </h3>

            {agentCompany.fraud_alerts && agentCompany.fraud_alerts.length > 0 ? (
              agentCompany.fraud_alerts.map((alert) => (
                <div
                  key={alert.id}
                  className="border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden"
                >
                  {/* Alert Header */}
                  <button
                    onClick={() => toggleAlertExpanded(alert.id)}
                    className="w-full flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-700/50 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${getRiskLevelColor(alert.risk_level)}`}>
                        {getFraudTypeIcon(alert.fraud_type)}
                      </div>
                      <div className="text-left">
                        <div className="font-medium text-slate-800 dark:text-white">
                          {alert.fraud_type_display || alert.fraud_type}
                        </div>
                        <div className="text-sm text-slate-500">
                          {alert.created_at}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRiskLevelColor(alert.risk_level)}`}>
                        {alert.risk_level}
                      </span>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        alert.resolved
                          ? 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-400'
                          : 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-400'
                      }`}>
                        {alert.resolved ? 'Resolved' : 'Unresolved'}
                      </span>
                      {expandedAlerts[alert.id] ? (
                        <ChevronUp className="w-5 h-5 text-slate-400" />
                      ) : (
                        <ChevronDown className="w-5 h-5 text-slate-400" />
                      )}
                    </div>
                  </button>

                  {/* Alert Details (Expanded) */}
                  {expandedAlerts[alert.id] && (
                    <div className="p-4 space-y-4 border-t border-slate-200 dark:border-slate-700">
                      {/* Basic Info */}
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <div className="text-xs text-slate-500 uppercase tracking-wide mb-1">Account</div>
                          <div className="font-medium text-slate-800 dark:text-white">
                            {alert.account_name || 'Unknown'}
                          </div>
                          <div className="text-sm text-slate-500">{alert.account_phone}</div>
                        </div>
                        <div>
                          <div className="text-xs text-slate-500 uppercase tracking-wide mb-1">Fraud Score</div>
                          <div className="font-medium text-slate-800 dark:text-white">
                            {alert.fraud_score}/100
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-slate-500 uppercase tracking-wide mb-1">Transactions</div>
                          <div className="font-medium text-slate-800 dark:text-white">
                            {alert.transaction_count} transactions
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-slate-500 uppercase tracking-wide mb-1">Total Amount</div>
                          <div className="font-medium text-slate-800 dark:text-white">
                            KES {parseFloat(alert.total_amount || 0).toLocaleString()}
                          </div>
                        </div>
                      </div>

                      {/* Receipt Numbers */}
                      {alert.receipt_nos && alert.receipt_nos.length > 0 && (
                        <div>
                          <div className="text-xs text-slate-500 uppercase tracking-wide mb-2">Receipt Numbers</div>
                          <div className="flex flex-wrap gap-2">
                            {alert.receipt_nos.map((receipt, idx) => (
                              <span
                                key={idx}
                                className="px-2 py-1 bg-slate-100 dark:bg-slate-700 rounded text-xs font-mono"
                              >
                                {receipt}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Transaction Details */}
                      {alert.detection_details?.transaction_details && (
                        <div>
                          <div className="text-xs text-slate-500 uppercase tracking-wide mb-2">Transaction Breakdown</div>
                          <div className="bg-slate-50 dark:bg-slate-900/50 rounded-lg overflow-hidden">
                            <table className="w-full text-sm">
                              <thead>
                                <tr className="border-b border-slate-200 dark:border-slate-700">
                                  <th className="px-3 py-2 text-left text-xs font-medium text-slate-500">Receipt</th>
                                  <th className="px-3 py-2 text-left text-xs font-medium text-slate-500">Type</th>
                                  <th className="px-3 py-2 text-right text-xs font-medium text-slate-500">Amount</th>
                                  <th className="px-3 py-2 text-left text-xs font-medium text-slate-500">Time</th>
                                </tr>
                              </thead>
                              <tbody>
                                {alert.detection_details.transaction_details.slice(0, 10).map((txn, idx) => (
                                  <tr key={idx} className="border-b border-slate-100 dark:border-slate-800 last:border-0">
                                    <td className="px-3 py-2 font-mono text-xs">{txn.receipt_no}</td>
                                    <td className="px-3 py-2">
                                      <span className={`px-2 py-0.5 rounded text-xs ${
                                        txn.type === 'Deposit'
                                          ? 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-400'
                                          : 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-400'
                                      }`}>
                                        {txn.type}
                                      </span>
                                    </td>
                                    <td className="px-3 py-2 text-right font-medium">
                                      KES {parseFloat(txn.amount || 0).toLocaleString()}
                                    </td>
                                    <td className="px-3 py-2 text-slate-500 text-xs">{txn.time}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                            {alert.detection_details.transaction_details.length > 10 && (
                              <div className="px-3 py-2 text-center text-xs text-slate-500 border-t border-slate-200 dark:border-slate-700">
                                +{alert.detection_details.transaction_details.length - 10} more transactions
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Explanation */}
                      {alert.detection_details?.explanation && (
                        <div>
                          <div className="text-xs text-slate-500 uppercase tracking-wide mb-2">Explanation</div>
                          <p className="text-sm text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-900/50 p-3 rounded-lg">
                            {alert.detection_details.explanation}
                          </p>
                        </div>
                      )}

                      {/* Resolution Notes */}
                      {alert.resolved && alert.resolution_notes && (
                        <div>
                          <div className="text-xs text-slate-500 uppercase tracking-wide mb-2">Resolution Notes</div>
                          <p className="text-sm text-slate-600 dark:text-slate-400 bg-green-50 dark:bg-green-900/20 p-3 rounded-lg">
                            {alert.resolution_notes}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-slate-500">
                No fraud alerts found for this agent company.
              </div>
            )}
          </div>

          {/* User Agents Section */}
          {agentCompany.user_agents && agentCompany.user_agents.length > 0 && (
            <div className="mt-6 space-y-4">
              <h3 className="text-lg font-semibold text-slate-800 dark:text-white flex items-center gap-2">
                <User className="w-5 h-5" />
                Associated Personnel
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {agentCompany.user_agents.map((ua) => (
                  <div
                    key={ua.id}
                    className="flex items-center gap-3 p-4 bg-slate-50 dark:bg-slate-700/50 rounded-xl"
                  >
                    <div className="p-2 bg-slate-200 dark:bg-slate-600 rounded-full">
                      <User className="w-5 h-5 text-slate-600 dark:text-slate-300" />
                    </div>
                    <div>
                      <div className="font-medium text-slate-800 dark:text-white">{ua.name}</div>
                      <div className="text-sm text-slate-500">{ua.phone_number || 'No phone'}</div>
                      <div className="text-xs text-slate-400">ID: {ua.idnumber}</div>
                    </div>
                    <div className="ml-auto">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        ua.is_authentic
                          ? 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-400'
                          : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-400'
                      }`}>
                        {ua.is_authentic ? 'Verified' : 'Unverified'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 p-6 border-t border-slate-200 dark:border-slate-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default FraudDetailsModal;
