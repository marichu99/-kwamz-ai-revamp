import {
  X,
  Calendar,
  DollarSign,
  Percent,
  User,
  Building,
  CreditCard,
  CheckCircle,
  Clock,
  Receipt,
  Link,
  Hash,
  Globe,
  Check
} from 'lucide-react';

function TransactionDetailsModal({ isOpen, onClose, transaction, transactionType }) {
  if (!isOpen || !transaction) return null;

  const formatCurrency = (amount) => {
    if (!amount) return 'KES 0.00';
    const num = parseFloat(amount);
    return `KES ${num.toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatDate = (dateString) => {
    if (!dateString) return '—';
    const date = new Date(dateString);
    return date.toLocaleString('en-KE', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const formatPercentage = (rate) => {
    if (!rate) return '0.00%';
    return `${parseFloat(rate).toFixed(2)}%`;
  };

  const getStatusIcon = (status) => (status === 'Completed' ? CheckCircle : Clock);
  const getStatusColor = (status) =>
    status === 'Completed' ? 'text-green-600 dark:text-green-400' : 'text-yellow-600 dark:text-yellow-400';

  const isDeposit = transaction.reason_type?.includes('Deposit') || transaction.details?.includes('Deposit');

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 overflow-y-auto py-8">
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-2xl w-full max-w-3xl mx-4">
        <div className="p-8">
          {/* Header */}
          <div className="flex justify-between items-center mb-8">
            <h2 className="text-2xl font-bold text-slate-800 dark:text-white flex items-center gap-3">
              {transactionType === 'float' ? (
                <DollarSign className="w-7 h-7 text-blue-600 dark:text-blue-400" />
              ) : (
                <Percent className="w-7 h-7 text-amber-600 dark:text-amber-400" />
              )}
              {transactionType === 'float' ? 'Transaction Details' : 'Commission Details'}
            </h2>
            <button
              onClick={onClose}
              className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            >
              <X className="w-6 h-6 text-slate-500 dark:text-slate-400" />
            </button>
          </div>

          <div className="space-y-8">

            {/* 1. Primary Identifiers */}
            <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="flex items-center text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">
                  <Receipt className="w-4 h-4 mr-2" />
                  Receipt Number
                </label>
                <div className="text-xl font-mono font-bold text-slate-900 dark:text-white">
                  {transaction.receipt_no || '—'}
                </div>
              </div>

              <div>
                <label className="flex items-center text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">
                  <Check className="w-4 h-4 mr-2" />
                  Status
                </label>
                <div className="flex items-center gap-2">
                  {(() => {
                    const Icon = getStatusIcon(transaction.transaction_status);
                    return <Icon className={`w-5 h-5 ${getStatusColor(transaction.transaction_status)}`} />;
                  })()}
                  <span className={`font-semibold text-lg ${getStatusColor(transaction.transaction_status)}`}>
                    {transaction.transaction_status || 'Pending'}
                  </span>
                </div>
              </div>
            </section>

            {/* 2. Key Times */}
            <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="flex items-center text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">
                  <Calendar className="w-4 h-4 mr-2" />
                  Initiation Time
                </label>
                <div className="text-slate-800 dark:text-slate-200">
                  {formatDate(transaction.initiation_time)}
                </div>
              </div>

              <div>
                <label className="flex items-center text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">
                  <Calendar className="w-4 h-4 mr-2" />
                  Completion Time
                </label>
                <div className="text-slate-800 dark:text-slate-200">
                  {formatDate(transaction.completion_time)}
                </div>
              </div>
            </section>

            {/* 3. Core Financial Info (Type-specific) */}
            {transactionType === 'float' ? (
              <section className="grid grid-cols-1 md:grid-cols-3 gap-6 py-6 border-y border-slate-200 dark:border-slate-700">
                <div>
                  <label className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-2 block">
                    Transaction Type
                  </label>
                  <span className={`px-4 py-2 rounded-full text-sm font-semibold ${
                    isDeposit
                      ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                      : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
                  }`}>
                    {transaction.reason_type || 'Unknown'}
                  </span>
                </div>

                <div>
                  <label className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-2 block">
                    Amount
                  </label>
                  <div className={`text-2xl font-bold ${
                    isDeposit ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                  }`}>
                    {isDeposit
                      ? `+${formatCurrency(transaction.paid_in)}`
                      : `-${formatCurrency(transaction.withdrawn)}`
                    }
                  </div>
                </div>

                <div>
                  <label className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-2 block">
                    Balance After
                  </label>
                  <div className="text-2xl font-bold text-slate-800 dark:text-white">
                    {formatCurrency(transaction.balance)}
                  </div>
                </div>
              </section>
            ) : (
              <section className="grid grid-cols-1 md:grid-cols-3 gap-6 py-6 border-y border-slate-200 dark:border-slate-700">
                <div>
                  <label className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-2 block">
                    Commission Type
                  </label>
                  <span className={`px-4 py-2 rounded-full text-sm font-semibold ${
                    isDeposit
                      ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                      : 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
                  }`}>
                    {transaction.details || 'Standard'}
                  </span>
                </div>

                <div>
                  <label className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-2 block">
                    Commission Amount
                  </label>
                  <div className="text-2xl font-bold text-amber-600 dark:text-amber-400">
                    {formatCurrency(transaction.commission_amount || transaction.paid_in)}
                  </div>
                </div>

                <div>
                  <label className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-2 block">
                    Rate
                  </label>
                  <div className="text-2xl font-bold text-slate-800 dark:text-white">
                    {formatPercentage(transaction.commission_rate)}
                  </div>
                </div>
              </section>
            )}

            {/* 4. Parties & Account */}
            <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="flex items-center text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">
                  <User className="w-4 h-4 mr-2" />
                  Other Party
                </label>
                <div className="text-slate-800 dark:text-slate-200">
                  {transaction.other_party_info || 'Not specified'}
                </div>
              </div>

              <div>
                <label className="flex items-center text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">
                  <CreditCard className="w-4 h-4 mr-2" />
                  Account Number
                </label>
                <div className="text-slate-800 dark:text-slate-200 font-mono">
                  {transaction.account_number || '—'}
                </div>
              </div>
            </section>

            {/* 5. Business Context */}
            <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="flex items-center text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">
                  <Building className="w-4 h-4 mr-2" />
                  Company
                </label>
                <div className="text-slate-800 dark:text-slate-200">
                  {transaction.company_name || `ID: ${transaction.company_id}` || '—'}
                </div>
              </div>

              <div>
                <label className="flex items-center text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">
                  <Hash className="w-4 h-4 mr-2" />
                  Agent ID
                </label>
                <div className="text-slate-800 dark:text-slate-200 font-mono">
                  {transaction.agent_id || '—'}
                </div>
              </div>
            </section>

            {/* 6. Additional Info */}
            <section className="space-y-4">
              {transaction.details && transactionType === 'float' && (
                <div>
                  <label className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-2 block">
                    Transaction Details
                  </label>
                  <div className="bg-slate-50 dark:bg-slate-700/50 p-4 rounded-lg text-slate-700 dark:text-slate-300">
                    {transaction.details}
                  </div>
                </div>
              )}

              {(transaction.linked_transaction_id || transactionType !== 'float') && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {transaction.linked_transaction_id && (
                    <div>
                      <label className="flex items-center text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">
                        <Link className="w-4 h-4 mr-2" />
                        Linked Transaction
                      </label>
                      <div className="font-mono text-slate-800 dark:text-slate-200">
                        {transaction.linked_transaction_id}
                      </div>
                    </div>
                  )}

                  <div>
                    <label className="flex items-center text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">
                      <Globe className="w-4 h-4 mr-2" />
                      Currency
                    </label>
                    <div className="text-slate-800 dark:text-slate-200">
                      {transaction.currency || 'KES'}
                    </div>
                  </div>
                </div>
              )}
            </section>

            {/* 7. Metadata (small footer) */}
            <section className="pt-6 border-t border-slate-200 dark:border-slate-700 text-xs text-slate-500 dark:text-slate-400 grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <span className="font-medium">Created:</span>{' '}
                {formatDate(transaction.created_at)}
              </div>
              {transaction.updated_at && (
                <div>
                  <span className="font-medium">Last Updated:</span>{' '}
                  {formatDate(transaction.updated_at)}
                </div>
              )}
            </section>
          </div>

          {/* Footer */}
          <div className="mt-10 flex justify-end">
            <button
              onClick={onClose}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default TransactionDetailsModal;