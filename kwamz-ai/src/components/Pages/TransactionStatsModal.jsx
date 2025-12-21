import { X, TrendingUp, TrendingDown, BarChart, Calendar, Download } from 'lucide-react';

function TransactionStatsModal({ isOpen, onClose, stats, transactionType }) {
    if (!isOpen || !stats) return null;

    const formatCurrency = (amount) => {
        if (!amount) return 'KES 0.00';
        const num = parseFloat(amount);
        return `KES ${num.toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    };

    const getTitle = () => {
        return transactionType === 'float' ? 'Float Transaction Statistics' : 'Commission Statistics';
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
                <div className="p-6">
                    <div className="flex justify-between items-center mb-6">
                        <h2 className="text-xl font-bold text-slate-800 dark:text-white flex items-center">
                            <BarChart className="w-5 h-5 mr-2" />
                            {getTitle()}
                        </h2>
                        <button
                            onClick={onClose}
                            className="p-1 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                        >
                            <X className="w-5 h-5 text-slate-500 dark:text-slate-400" />
                        </button>
                    </div>

                    {/* Summary Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                        <div className={`rounded-xl p-4 ${
                            transactionType === 'float' ? 'bg-blue-50 dark:bg-slate-700' : 'bg-amber-50 dark:bg-slate-700'
                        }`}>
                            <div className={`text-sm font-medium ${
                                transactionType === 'float' ? 'text-blue-600 dark:text-blue-400' : 'text-amber-600 dark:text-amber-400'
                            }`}>
                                Total {transactionType === 'float' ? 'Transactions' : 'Commissions'}
                            </div>
                            <div className="text-2xl font-bold text-slate-800 dark:text-white">
                                {stats.total_transactions}
                            </div>
                        </div>
                        
                        {transactionType === 'float' ? (
                            <>
                                <div className="bg-green-50 dark:bg-slate-700 rounded-xl p-4">
                                    <div className="text-sm text-green-600 dark:text-green-400 font-medium">Total Deposits</div>
                                    <div className="text-2xl font-bold text-slate-800 dark:text-white">
                                        {formatCurrency(stats.total_paid_in)}
                                    </div>
                                    <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                                        Avg: {formatCurrency(stats.avg_deposit)}
                                    </div>
                                </div>
                                <div className="bg-red-50 dark:bg-slate-700 rounded-xl p-4">
                                    <div className="text-sm text-red-600 dark:text-red-400 font-medium">Total Withdrawals</div>
                                    <div className="text-2xl font-bold text-slate-800 dark:text-white">
                                        {formatCurrency(stats.total_withdrawn)}
                                    </div>
                                    <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                                        Avg: {formatCurrency(stats.avg_withdrawal)}
                                    </div>
                                </div>
                                <div className={`rounded-xl p-4 ${
                                    parseFloat(stats.net_flow) >= 0 
                                        ? 'bg-green-50 dark:bg-slate-700' 
                                        : 'bg-red-50 dark:bg-slate-700'
                                }`}>
                                    <div className="flex items-center text-sm font-medium">
                                        {parseFloat(stats.net_flow) >= 0 ? (
                                            <TrendingUp className="w-4 h-4 mr-1 text-green-600 dark:text-green-400" />
                                        ) : (
                                            <TrendingDown className="w-4 h-4 mr-1 text-red-600 dark:text-red-400" />
                                        )}
                                        <span className={
                                            parseFloat(stats.net_flow) >= 0 
                                                ? 'text-green-600 dark:text-green-400' 
                                                : 'text-red-600 dark:text-red-400'
                                        }>
                                            Net Flow
                                        </span>
                                    </div>
                                    <div className="text-2xl font-bold text-slate-800 dark:text-white">
                                        {formatCurrency(stats.net_flow)}
                                    </div>
                                </div>
                            </>
                        ) : (
                            <>
                                <div className="bg-green-50 dark:bg-slate-700 rounded-xl p-4">
                                    <div className="text-sm text-green-600 dark:text-green-400 font-medium">Total Commission</div>
                                    <div className="text-2xl font-bold text-slate-800 dark:text-white">
                                        {formatCurrency(stats.total_commission_amount)}
                                    </div>
                                    <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                                        Avg: {formatCurrency(stats.avg_commission)}
                                    </div>
                                </div>
                                <div className="bg-blue-50 dark:bg-slate-700 rounded-xl p-4">
                                    <div className="text-sm text-blue-600 dark:text-blue-400 font-medium">Total Deposits</div>
                                    <div className="text-2xl font-bold text-slate-800 dark:text-white">
                                        {formatCurrency(stats.total_paid_in)}
                                    </div>
                                </div>
                                <div className="bg-red-50 dark:bg-slate-700 rounded-xl p-4">
                                    <div className="text-sm text-red-600 dark:text-red-400 font-medium">Total Withdrawals</div>
                                    <div className="text-2xl font-bold text-slate-800 dark:text-white">
                                        {formatCurrency(stats.total_withdrawn)}
                                    </div>
                                </div>
                            </>
                        )}
                    </div>

                    {/* Type Breakdown */}
                    <div className="mb-6">
                        <h3 className="text-lg font-semibold text-slate-800 dark:text-white mb-4">
                            {transactionType === 'float' ? 'Transaction Type Breakdown' : 'Commission Type Breakdown'}
                        </h3>
                        <div className="space-y-3">
                            {stats.type_breakdown.map((item, index) => (
                                <div key={index} className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-700 rounded-xl">
                                    <div>
                                        <div className="font-medium text-slate-800 dark:text-white">
                                            {transactionType === 'float' ? item.reason_type : item.details}
                                        </div>
                                        <div className="text-sm text-slate-500 dark:text-slate-400">
                                            {item.count} {transactionType === 'float' ? 'transactions' : 'commissions'}
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <div className="font-medium text-slate-800 dark:text-white">
                                            {transactionType === 'float' 
                                                ? formatCurrency(parseFloat(item.total_paid_in || '0') + parseFloat(item.total_withdrawn || '0'))
                                                : formatCurrency(item.total_commission)
                                            }
                                        </div>
                                        {transactionType === 'float' && (
                                            <div className="text-sm">
                                                <span className="text-green-600 dark:text-green-400 mr-2">
                                                    +{formatCurrency(item.total_paid_in)}
                                                </span>
                                                <span className="text-red-600 dark:text-red-400">
                                                    -{formatCurrency(item.total_withdrawn)}
                                                </span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Daily Trends */}
                    <div>
                        <h3 className="text-lg font-semibold text-slate-800 dark:text-white mb-4 flex items-center">
                            <Calendar className="w-5 h-5 mr-2" />
                            Daily Trends
                        </h3>
                        <div className="overflow-x-auto">
                            <table className="w-full table-auto">
                                <thead>
                                    <tr className="bg-slate-100 dark:bg-slate-700 text-left text-slate-600 dark:text-slate-300">
                                        <th className="px-4 py-3 font-semibold rounded-l-xl">Date</th>
                                        <th className="px-4 py-3 font-semibold">
                                            {transactionType === 'float' ? 'Transactions' : 'Commissions'}
                                        </th>
                                        <th className="px-4 py-3 font-semibold">Total Deposits</th>
                                        <th className="px-4 py-3 font-semibold">Total Withdrawals</th>
                                        {transactionType === 'commission' && (
                                            <th className="px-4 py-3 font-semibold">Total Commission</th>
                                        )}
                                        <th className="px-4 py-3 font-semibold rounded-r-xl">Net Flow</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {stats.daily_stats.map((day, index) => {
                                        const netFlow = transactionType === 'float'
                                            ? parseFloat(day.total_paid_in || '0') - parseFloat(day.total_withdrawn || '0')
                                            : parseFloat(day.total_paid_in || '0') - parseFloat(day.total_withdrawn || '0');
                                        
                                        return (
                                            <tr
                                                key={index}
                                                className={`border-b border-slate-200 dark:border-slate-600 ${
                                                    index % 2 === 0 ? 'bg-white dark:bg-slate-800' : 'bg-slate-50 dark:bg-slate-700/50'
                                                }`}
                                            >
                                                <td className="px-4 py-3 font-medium">
                                                    {day.date}
                                                </td>
                                                <td className="px-4 py-3">
                                                    {day.count}
                                                </td>
                                                <td className="px-4 py-3 text-green-600 dark:text-green-400">
                                                    {formatCurrency(day.total_paid_in)}
                                                </td>
                                                <td className="px-4 py-3 text-red-600 dark:text-red-400">
                                                    {formatCurrency(day.total_withdrawn)}
                                                </td>
                                                {transactionType === 'commission' && (
                                                    <td className="px-4 py-3 text-amber-600 dark:text-amber-400">
                                                        {formatCurrency(netFlow)}
                                                    </td>
                                                )}
                                                <td className="px-4 py-3 font-medium">
                                                    <span className={netFlow >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}>
                                                        {formatCurrency(netFlow.toString())}
                                                    </span>
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
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

export default TransactionStatsModal;