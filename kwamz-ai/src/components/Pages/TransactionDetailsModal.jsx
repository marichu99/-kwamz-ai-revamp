import { X, Calendar, DollarSign, Percent, User, Building, CreditCard, CheckCircle, Clock } from 'lucide-react';

function TransactionDetailsModal({ isOpen, onClose, transaction, transactionType }) {
    if (!isOpen || !transaction) return null;

    const formatCurrency = (amount) => {
        if (!amount) return 'KES 0.00';
        const num = parseFloat(amount);
        return `KES ${num.toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    };

    const formatDate = (dateString) => {
        if (!dateString) return '';
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
        if (!rate) return '0%';
        const num = parseFloat(rate);
        return `${num.toFixed(2)}%`;
    };

    const getStatusIcon = (status) => {
        return status === 'Completed' ? CheckCircle : Clock;
    };

    const getStatusColor = (status) => {
        return status === 'Completed' ? 'text-green-600 dark:text-green-400' : 'text-yellow-600 dark:text-yellow-400';
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                <div className="p-6">
                    <div className="flex justify-between items-center mb-6">
                        <h2 className="text-xl font-bold text-slate-800 dark:text-white flex items-center">
                            {transactionType === 'float' ? (
                                <DollarSign className="w-5 h-5 mr-2 text-blue-600 dark:text-blue-400" />
                            ) : (
                                <Percent className="w-5 h-5 mr-2 text-amber-600 dark:text-amber-400" />
                            )}
                            {transactionType === 'float' ? 'Transaction Details' : 'Commission Details'}
                        </h2>
                        <button
                            onClick={onClose}
                            className="p-1 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                        >
                            <X className="w-5 h-5 text-slate-500 dark:text-slate-400" />
                        </button>
                    </div>

                    {/* Basic Information */}
                    <div className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">
                                    Receipt Number
                                </label>
                                <div className="text-lg font-mono font-bold text-slate-800 dark:text-white">
                                    {transaction.receipt_no}
                                </div>
                            </div>
                            
                            <div>
                                <label className="block text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">
                                    Status
                                </label>
                                <div className="flex items-center">
                                    {(() => {
                                        const Icon = getStatusIcon(transaction.transaction_status);
                                        return <Icon className={`w-4 h-4 mr-2 ${getStatusColor(transaction.transaction_status)}`} />;
                                    })()}
                                    <span className={`font-medium ${getStatusColor(transaction.transaction_status)}`}>
                                        {transaction.transaction_status}
                                    </span>
                                </div>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-500 dark:text-slate-400 mb-1 flex items-center">
                                    <Calendar className="w-3 h-3 mr-1" />
                                    Completion Time
                                </label>
                                <div className="text-sm text-slate-800 dark:text-white">
                                    {formatDate(transaction.completion_time)}
                                </div>
                            </div>
                            
                            <div>
                                <label className="block text-sm font-medium text-slate-500 dark:text-slate-400 mb-1 flex items-center">
                                    <Calendar className="w-3 h-3 mr-1" />
                                    Initiation Time
                                </label>
                                <div className="text-sm text-slate-800 dark:text-white">
                                    {formatDate(transaction.initiation_time)}
                                </div>
                            </div>
                        </div>

                        {/* Details */}
                        <div>
                            <label className="block text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">
                                Details
                            </label>
                            <div className="text-sm text-slate-800 dark:text-white bg-slate-50 dark:bg-slate-700/50 p-3 rounded-lg">
                                {transaction.details}
                            </div>
                        </div>

                        {/* Transaction Type Specific Information */}
                        {transactionType === 'float' ? (
                            <>
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">
                                            Transaction Type
                                        </label>
                                        <div className={`px-3 py-1 inline-block rounded-full text-xs font-medium ${
                                            transaction.reason_type.includes('Deposit')
                                                ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                                                : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                                        }`}>
                                            {transaction.reason_type}
                                        </div>
                                    </div>
                                    
                                    <div>
                                        <label className="block text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">
                                            Amount
                                        </label>
                                        <div className={`text-lg font-bold ${
                                            transaction.paid_in && parseFloat(transaction.paid_in) > 0
                                                ? 'text-green-600 dark:text-green-400'
                                                : 'text-red-600 dark:text-red-400'
                                        }`}>
                                            {transaction.paid_in && parseFloat(transaction.paid_in) > 0
                                                ? `+${formatCurrency(transaction.paid_in)}`
                                                : `-${formatCurrency(transaction.withdrawn)}`
                                            }
                                        </div>
                                    </div>
                                    
                                    <div>
                                        <label className="block text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">
                                            Balance
                                        </label>
                                        <div className="text-lg font-bold text-slate-800 dark:text-white">
                                            {formatCurrency(transaction.balance)}
                                        </div>
                                    </div>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-slate-500 dark:text-slate-400 mb-1 flex items-center">
                                            <User className="w-3 h-3 mr-1" />
                                            Other Party
                                        </label>
                                        <div className="text-sm text-slate-800 dark:text-white">
                                            {transaction.other_party_info || 'N/A'}
                                        </div>
                                    </div>
                                    
                                    <div>
                                        <label className="block text-sm font-medium text-slate-500 dark:text-slate-400 mb-1 flex items-center">
                                            <CreditCard className="w-3 h-3 mr-1" />
                                            Account Number
                                        </label>
                                        <div className="text-sm text-slate-800 dark:text-white">
                                            {transaction.account_number || 'N/A'}
                                        </div>
                                    </div>
                                </div>
                            </>
                        ) : (
                            <>
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">
                                            Commission Type
                                        </label>
                                        <div className={`px-3 py-1 inline-block rounded-full text-xs font-medium ${
                                            transaction.details.includes('Deposit')
                                                ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                                                : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                                        }`}>
                                            {transaction.details}
                                        </div>
                                    </div>
                                    
                                    <div>
                                        <label className="block text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">
                                            Commission Amount
                                        </label>
                                        <div className="text-lg font-bold text-amber-600 dark:text-amber-400">
                                            {formatCurrency(transaction.commission_amount || transaction.paid_in)}
                                        </div>
                                    </div>
                                    
                                    <div>
                                        <label className="block text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">
                                            Commission Rate
                                        </label>
                                        <div className="text-lg font-bold text-slate-800 dark:text-white">
                                            {formatPercentage(transaction.commission_rate)}
                                        </div>
                                    </div>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">
                                            Original Receipt
                                        </label>
                                        <div className="text-sm font-mono text-slate-800 dark:text-white">
                                            {transaction.linked_transaction_id || 'N/A'}
                                        </div>
                                    </div>
                                    
                                    <div>
                                        <label className="block text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">
                                            Transaction Type
                                        </label>
                                        <div className="text-sm text-slate-800 dark:text-white">
                                            {transaction.reason_type}
                                        </div>
                                    </div>
                                </div>
                            </>
                        )}

                        {/* Common Information */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-500 dark:text-slate-400 mb-1 flex items-center">
                                    <Building className="w-3 h-3 mr-1" />
                                    Company
                                </label>
                                <div className="text-sm text-slate-800 dark:text-white">
                                    {transaction.company_name || `ID: ${transaction.company_id}` || 'N/A'}
                                </div>
                            </div>
                            
                            <div>
                                <label className="block text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">
                                    Agent ID
                                </label>
                                <div className="text-sm text-slate-800 dark:text-white">
                                    {transaction.agent_id || 'N/A'}
                                </div>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">
                                    Currency
                                </label>
                                <div className="text-sm text-slate-800 dark:text-white">
                                    {transaction.currency}
                                </div>
                            </div>
                            
                            <div>
                                <label className="block text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">
                                    Balance Confirmed
                                </label>
                                <div className="text-sm text-slate-800 dark:text-white">
                                    {transaction.balance_confirmed ? (
                                        <span className="text-green-600 dark:text-green-400">Yes</span>
                                    ) : (
                                        <span className="text-yellow-600 dark:text-yellow-400">No</span>
                                    )}
                                </div>
                            </div>
                        </div>

                        {transaction.linked_transaction_id && transactionType === 'float' && (
                            <div>
                                <label className="block text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">
                                    Linked Transaction ID
                                </label>
                                <div className="text-sm text-slate-800 dark:text-white">
                                    {transaction.linked_transaction_id}
                                </div>
                            </div>
                        )}

                        {/* Timestamps */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-slate-200 dark:border-slate-700">
                            <div>
                                <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">
                                    Created At
                                </label>
                                <div className="text-xs text-slate-600 dark:text-slate-300">
                                    {formatDate(transaction.created_at)}
                                </div>
                            </div>
                            
                            {transaction.updated_at && (
                                <div>
                                    <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">
                                        Last Updated
                                    </label>
                                    <div className="text-xs text-slate-600 dark:text-slate-300">
                                        {formatDate(transaction.updated_at)}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="flex justify-end pt-6 border-t border-slate-200 dark:border-slate-700 mt-6">
                        <button
                            onClick={onClose}
                            className="px-4 py-2 bg-blue-500 text-white rounded-xl hover:bg-blue-600 transition-colors"
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