import React, { useState, useEffect, useCallback } from 'react';
import {
    Download,
    X,
    FileText,
    FileSpreadsheet,
    FileBarChart,
    Printer,
    Filter,
    Calendar,
    TrendingUp,
    TrendingDown,
    DollarSign,
    BarChart3,
    PieChart,
    Eye,
    ExternalLink,
    RefreshCw,
    ChevronDown,
    CalendarDays,
    AlertCircle,
    TrendingUp as TrendingUpIcon,
    Calendar as CalendarIcon,
    Loader2,
    Users,
    Activity
} from 'lucide-react';
import axios from 'axios';
import config from '../../Config';
import { useToast } from './ToastProvider';

function CommissionsReportModal({ isOpen, onClose, filters, transactionType = 'commission', companyId }) {
    const { showToast } = useToast();
    const [isLoading, setIsLoading] = useState(false);
    const [isExporting, setIsExporting] = useState(false);
    const [reportData, setReportData] = useState(null);
    const [exportFormat, setExportFormat] = useState('pdf');

    // Date range state
    const [dateRange, setDateRange] = useState('this_month');
    const [customStartDate, setCustomStartDate] = useState('');
    const [customEndDate, setCustomEndDate] = useState('');
    const [showDatePicker, setShowDatePicker] = useState(false);

    // Helper function to get weeks in a month
    const getWeeksInMonth = (year, month) => {
        const weeks = [];
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        
        let currentDate = new Date(firstDay);
        while (currentDate <= lastDay) {
            const weekStart = new Date(currentDate);
            const dayOfWeek = weekStart.getDay();
            const diff = weekStart.getDate() - dayOfWeek + (dayOfWeek === 0 ? -6 : 1);
            const monday = new Date(weekStart.setDate(diff));
            monday.setHours(0, 0, 0, 0);
            
            const weekEnd = new Date(monday);
            weekEnd.setDate(monday.getDate() + 6);
            weekEnd.setHours(23, 59, 59, 999);
            
            if (weekEnd > firstDay && monday <= lastDay) {
                const startDate = monday < firstDay ? firstDay : monday;
                const endDate = weekEnd > lastDay ? lastDay : weekEnd;
                
                if (startDate <= endDate) {
                    weeks.push({
                        start: startDate,
                        end: endDate,
                        label: `Week ${weeks.length + 1} (${formatWeekDate(startDate, endDate)})`
                    });
                }
            }
            
            currentDate.setDate(currentDate.getDate() + 7);
        }
        
        return weeks;
    };

    // Helper function to format week dates
    const formatWeekDate = (start, end) => {
        const format = (date) => date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        return `${format(start)} - ${format(end)}`;
    };

    // Helper function to get days in a week
    const getDaysInWeek = (startDate) => {
        const days = [];
        const current = new Date(startDate);
        
        for (let i = 0; i < 7; i++) {
            const day = new Date(current);
            days.push({
                date: day,
                label: day.toLocaleDateString('en-US', { weekday: 'short', day: 'numeric' })
            });
            current.setDate(current.getDate() + 1);
        }
        
        return days;
    };

    // Predefined ranges with trend analysis periods
    const predefinedRanges = [
        {
            value: 'today',
            label: 'Today',
            trendPeriod: 'last_30_days',
            trendGroupBy: 'day',
            getDates: () => {
                const today = new Date();
                today.setHours(0, 0, 0, 0);
                const end = new Date(today);
                end.setHours(23, 59, 59, 999);
                return { start: today, end };
            }
        },
        {
            value: 'yesterday',
            label: 'Yesterday',
            trendPeriod: 'last_30_days',
            trendGroupBy: 'day',
            getDates: () => {
                const yesterday = new Date();
                yesterday.setDate(yesterday.getDate() - 1);
                yesterday.setHours(0, 0, 0, 0);
                const end = new Date(yesterday);
                end.setHours(23, 59, 59, 999);
                return { start: yesterday, end };
            }
        },
        {
            value: 'this_week',
            label: 'This Week',
            trendPeriod: 'last_12_weeks',
            trendGroupBy: 'day', // Changed from week to day for daily bars
            getDates: () => {
                const today = new Date();
                const start = new Date(today);
                start.setDate(today.getDate() - today.getDay() + (today.getDay() === 0 ? -6 : 1));
                start.setHours(0, 0, 0, 0);
                const end = new Date(today);
                end.setHours(23, 59, 59, 999);
                return { start, end };
            }
        },
        {
            value: 'last_week',
            label: 'Last Week',
            trendPeriod: 'last_12_weeks',
            trendGroupBy: 'day', // Changed from week to day for daily bars
            getDates: () => {
                const today = new Date();
                const end = new Date(today);
                end.setDate(today.getDate() - today.getDay() + (today.getDay() === 0 ? -6 : 1) - 1);
                end.setHours(23, 59, 59, 999);
                const start = new Date(end);
                start.setDate(end.getDate() - 6);
                start.setHours(0, 0, 0, 0);
                return { start, end };
            }
        },
        {
            value: 'this_month',
            label: 'This Month',
            trendPeriod: 'last_12_months',
            trendGroupBy: 'week', // Changed from month to week for weekly bars
            getDates: () => {
                const today = new Date();
                const start = new Date(today.getFullYear(), today.getMonth(), 1);
                start.setHours(0, 0, 0, 0);
                const end = new Date(today);
                end.setHours(23, 59, 59, 999);
                return { start, end };
            }
        },
        {
            value: 'last_month',
            label: 'Last Month',
            trendPeriod: 'last_12_months',
            trendGroupBy: 'week', // Changed from month to week for weekly bars
            getDates: () => {
                const today = new Date();
                const start = new Date(today.getFullYear(), today.getMonth() - 1, 1);
                start.setHours(0, 0, 0, 0);
                const end = new Date(today.getFullYear(), today.getMonth(), 0);
                end.setHours(23, 59, 59, 999);
                return { start, end };
            }
        },
        {
            value: 'last_3_months',
            label: 'Last 3 Months',
            trendPeriod: 'last_12_months',
            trendGroupBy: 'week',
            getDates: () => {
                const end = new Date();
                end.setHours(23, 59, 59, 999);
                const start = new Date(end);
                start.setMonth(start.getMonth() - 3);
                start.setHours(0, 0, 0, 0);
                return { start, end };
            }
        },
        {
            value: 'last_6_months',
            label: 'Last 6 Months',
            trendPeriod: 'last_2_years',
            trendGroupBy: 'month',
            getDates: () => {
                const end = new Date();
                end.setHours(23, 59, 59, 999);
                const start = new Date(end);
                start.setMonth(start.getMonth() - 6);
                start.setHours(0, 0, 0, 0);
                return { start, end };
            }
        },
        {
            value: 'this_year',
            label: 'This Year',
            trendPeriod: 'last_3_years',
            trendGroupBy: 'quarter',
            getDates: () => {
                const today = new Date();
                const start = new Date(today.getFullYear(), 0, 1);
                start.setHours(0, 0, 0, 0);
                const end = new Date(today);
                end.setHours(23, 59, 59, 999);
                return { start, end };
            }
        },
        {
            value: 'last_year',
            label: 'Last Year',
            trendPeriod: 'last_3_years',
            trendGroupBy: 'quarter',
            getDates: () => {
                const today = new Date();
                const start = new Date(today.getFullYear() - 1, 0, 1);
                start.setHours(0, 0, 0, 0);
                const end = new Date(today.getFullYear() - 1, 11, 31);
                end.setHours(23, 59, 59, 999);
                return { start, end };
            }
        },
        {
            value: 'custom',
            label: 'Custom Range',
            trendPeriod: 'auto',
            trendGroupBy: 'auto'
        }
    ];

    // Initialize dates when modal opens
    useEffect(() => {
        if (isOpen) {
            setDateRange('this_month');
            const range = predefinedRanges.find(r => r.value === 'this_month');
            if (range && range.getDates) {
                const { start, end } = range.getDates();
                const formatDate = (date) => date.toISOString().split('T')[0];
                setCustomStartDate(formatDate(start));
                setCustomEndDate(formatDate(end));
            }
        }
    }, [isOpen]);

    // Auto-generate report when dates change
    useEffect(() => {
        if (isOpen && customStartDate && customEndDate && !isLoading) {
            const timer = setTimeout(() => {
                if (validateDates().valid) {
                    fetchCommissionReport();
                }
            }, 500);

            return () => clearTimeout(timer);
        }
    }, [customStartDate, customEndDate, dateRange, isOpen]);

    // Apply predefined range
    const applyPredefinedRange = (rangeValue) => {
        const range = predefinedRanges.find(r => r.value === rangeValue);
        if (range && range.getDates) {
            const { start, end } = range.getDates();
            const formatDate = (date) => date.toISOString().split('T')[0];
            setCustomStartDate(formatDate(start));
            setCustomEndDate(formatDate(end));
        }
    };

    // Handle date range change
    const handleDateRangeChange = (rangeValue) => {
        setDateRange(rangeValue);
        applyPredefinedRange(rangeValue);
    };

    // Format date for display
    const formatDisplayDate = (dateString) => {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    };

    // Calculate days between dates
    const calculateDaysDifference = () => {
        if (!customStartDate || !customEndDate) return 0;
        const start = new Date(customStartDate);
        const end = new Date(customEndDate);
        const diffTime = Math.abs(end - start);
        return Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
    };

    // Validate dates
    const validateDates = () => {
        if (!customStartDate || !customEndDate) {
            return { valid: false, error: 'Please select both start and end dates' };
        }

        const start = new Date(customStartDate);
        const end = new Date(customEndDate);

        if (start > end) {
            return { valid: false, error: 'Start date cannot be after end date' };
        }

        const daysDiff = calculateDaysDifference();
        if (daysDiff > 365) {
            return { valid: true, warning: 'Date range exceeds 1 year. Consider narrowing your search for better performance.' };
        }

        return { valid: true };
    };

    // Get trend analysis period based on selected range
    const getTrendAnalysisPeriod = useCallback(() => {
        const selectedRange = predefinedRanges.find(r => r.value === dateRange);
        if (!selectedRange) return 'last_year';
        return selectedRange.trendPeriod;
    }, [dateRange]);

    // Get trend analysis grouping
    const getTrendGroupBy = useCallback(() => {
        const selectedRange = predefinedRanges.find(r => r.value === dateRange);
        if (!selectedRange) return 'month';

        if (selectedRange.value === 'custom') {
            const daysDiff = calculateDaysDifference();
            if (daysDiff <= 7) return 'day';
            if (daysDiff <= 30) return 'day';
            if (daysDiff <= 90) return 'week';
            if (daysDiff <= 365) return 'month';
            return 'quarter';
        }

        return selectedRange.trendGroupBy;
    }, [dateRange, customStartDate, customEndDate]);

    // Fetch commission report data
    const fetchCommissionReport = async () => {
        const validation = validateDates();
        if (!validation.valid) {
            return;
        }

        setIsLoading(true);
        try {
            const token = localStorage.getItem('token');

            const params = {
                company_id: companyId,
                transaction_type: transactionType,
                report_type: 'commissions',
                date_range: dateRange,
                start_date: customStartDate,
                end_date: customEndDate,
                trend_analysis_period: getTrendAnalysisPeriod(),
                trend_group_by: getTrendGroupBy(),
                // Special flags for weekly/monthly breakdowns
                breakdown_by: dateRange === 'this_week' || dateRange === 'last_week' ? 'day' : 
                              (dateRange === 'this_month' || dateRange === 'last_month' ? 'week' : 'auto')
            };

            if (filters) {
                if (filters.reasonType) params.reason_type = filters.reasonType;
                if (filters.transactionStatus) params.transaction_status = filters.transactionStatus;
            }

            const response = await axios.get(`${config.API_URL}/transactions/commissions-report`, {
                headers: { Authorization: `Bearer ${token}` },
                params
            });

            if (response.data.success) {
                setReportData(response.data.report);
                if (!isLoading) {
                    showToast('Commission report updated', 'success');
                }
            } else {
                showToast(response.data.error || 'Failed to load commission report', 'error');
            }
        } catch (error) {
            console.error('Error fetching commission report:', error);
            showToast('Failed to fetch commission report. Please try again.', 'error');
        } finally {
            setIsLoading(false);
        }
    };

    // Handle export - FIXED version
    const handleExport = async (format) => {
        setIsExporting(true);
        try {
            const token = localStorage.getItem('token');

            const params = {
                company_id: companyId,
                format: format,
                transaction_type: transactionType,
                report_type: 'commissions',
                date_range: dateRange,
                start_date: customStartDate,
                end_date: customEndDate,
                trend_analysis_period: getTrendAnalysisPeriod(),
                trend_group_by: getTrendGroupBy()
            };

            if (filters) {
                if (filters.reasonType) params.reason_type = filters.reasonType;
                if (filters.transactionStatus) params.transaction_status = filters.transactionStatus;
            }

            const response = await axios({
                method: 'GET',
                url: `${config.API_URL}/transactions/export-commissions`,
                headers: { 
                    Authorization: `Bearer ${token}`,
                    'Accept': format === 'pdf' ? 'application/pdf' : 
                             format === 'excel' ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' :
                             'text/csv'
                },
                params,
                responseType: 'blob'
            });

            // Check if response is actually a blob
            if (!(response.data instanceof Blob)) {
                throw new Error('Invalid response format');
            }

            const timestamp = new Date().toISOString().split('T')[0];
            let filename = `commissions_report_${timestamp}`;
            let mimeType = '';

            switch (format) {
                case 'pdf':
                    filename += '.pdf';
                    mimeType = 'application/pdf';
                    break;
                case 'excel':
                    filename += '.xlsx';
                    mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
                    break;
                case 'csv':
                    filename += '.csv';
                    mimeType = 'text/csv';
                    break;
            }

            // Create a Blob with proper MIME type
            const blob = new Blob([response.data], { type: mimeType });
            
            // Create download link
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', filename);
            
            // Append to body, click, and remove
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            // Clean up
            window.URL.revokeObjectURL(url);

            showToast(`Commission report exported as ${format.toUpperCase()}`, 'success');
        } catch (error) {
            console.error('Error exporting commission report:', error);
            showToast('Failed to export commission report. Please try again.', 'error');
            
            // If it's a JSON error (server returned error instead of file)
            if (error.response && error.response.data instanceof Blob) {
                try {
                    const text = await error.response.data.text();
                    const errorData = JSON.parse(text);
                    showToast(errorData.error || 'Export failed', 'error');
                } catch (parseError) {
                    showToast('Export failed with unknown error', 'error');
                }
            }
        } finally {
            setIsExporting(false);
        }
    };

    // Handle print
    const handlePrint = () => {
        const printContent = document.getElementById('commissions-report-content');
        if (printContent) {
            const printWindow = window.open('', '_blank');
            printWindow.document.write(`
                <html>
                    <head>
                        <title>Commissions Report</title>
                        <style>
                            body { font-family: Arial, sans-serif; margin: 20px; }
                            .header { text-align: center; margin-bottom: 30px; }
                            .header h1 { color: #1a5d1a; }
                            .summary { display: flex; justify-content: space-around; margin: 20px 0; }
                            .stat-card { background: #f1f8e9; padding: 15px; border-radius: 8px; text-align: center; }
                            .stat-value { font-size: 24px; font-weight: bold; color: #1b5e20; }
                            table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                            th { background-color: #2e7d32; color: white; padding: 12px; text-align: left; }
                            td { padding: 10px; border-bottom: 1px solid #ddd; }
                            tr:nth-child(even) { background-color: #f9f9f9; }
                            .trend-chart { margin: 20px 0; }
                            .trend-bar { display: flex; align-items: flex-end; height: 200px; }
                            .trend-item { flex: 1; margin: 0 2px; display: flex; flex-direction: column; align-items: center; }
                            .trend-bar-item { width: 80%; background: #4caf50; border-radius: 4px 4px 0 0; }
                            .trend-label { margin-top: 5px; font-size: 12px; text-align: center; }
                            @media print {
                                .no-print { display: none; }
                                @page { margin: 0.5in; }
                                body { margin: 0; }
                            }
                        </style>
                    </head>
                    <body>
                        <div class="header">
                            <h1>Commissions Report</h1>
                            <p>Generated on: ${new Date().toLocaleString()}</p>
                            ${reportData?.period ? `<p>Period: ${reportData.period}</p>` : ''}
                            ${reportData?.trend_period ? `<p>Trend Analysis: ${reportData.trend_period}</p>` : ''}
                        </div>
                        ${printContent.innerHTML}
                    </body>
                </html>
            `);
            printWindow.document.close();
            printWindow.focus();
            
            // Wait for content to load before printing
            setTimeout(() => {
                printWindow.print();
                printWindow.close();
            }, 500);
        }
    };

    // Quick date actions
    const handleQuickAction = (action) => {
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        switch (action) {
            case 'today':
                const todayStr = today.toISOString().split('T')[0];
                setCustomStartDate(todayStr);
                setCustomEndDate(todayStr);
                setDateRange('custom');
                break;

            case 'yesterday':
                const yesterday = new Date(today);
                yesterday.setDate(yesterday.getDate() - 1);
                const yesterdayStr = yesterday.toISOString().split('T')[0];
                setCustomStartDate(yesterdayStr);
                setCustomEndDate(yesterdayStr);
                setDateRange('custom');
                break;

            case 'thisMonth':
                const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
                const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
                setCustomStartDate(firstDay.toISOString().split('T')[0]);
                setCustomEndDate(lastDay.toISOString().split('T')[0]);
                setDateRange('custom');
                break;

            case 'lastMonth':
                const lastMonthFirst = new Date(today.getFullYear(), today.getMonth() - 1, 1);
                const lastMonthLast = new Date(today.getFullYear(), today.getMonth(), 0);
                setCustomStartDate(lastMonthFirst.toISOString().split('T')[0]);
                setCustomEndDate(lastMonthLast.toISOString().split('T')[0]);
                setDateRange('custom');
                break;

            case 'last90Days':
                const ninetyDaysAgo = new Date(today);
                ninetyDaysAgo.setDate(ninetyDaysAgo.getDate() - 89);
                setCustomStartDate(ninetyDaysAgo.toISOString().split('T')[0]);
                setCustomEndDate(today.toISOString().split('T')[0]);
                setDateRange('custom');
                break;
        }
    };

    // Get trend period label
    const getTrendPeriodLabel = () => {
        const selectedRange = predefinedRanges.find(r => r.value === dateRange);
        if (!selectedRange) return 'Trend Analysis';

        switch (selectedRange.value) {
            case 'today':
            case 'yesterday':
                return 'Daily Commission Trend (Last 30 Days)';
            case 'this_week':
            case 'last_week':
                return 'Daily Commission Trend (This Week)';
            case 'this_month':
            case 'last_month':
                return 'Weekly Commission Trend (This Month)';
            case 'last_3_months':
                return 'Weekly Commission Trend (Last 3 Months)';
            case 'last_6_months':
                return 'Monthly Commission Trend (Last 6 Months)';
            case 'this_year':
                return 'Quarterly Commission Trend (This Year)';
            case 'last_year':
                return 'Quarterly Commission Trend (Last Year)';
            case 'custom':
                const daysDiff = calculateDaysDifference();
                if (daysDiff <= 7) return 'Daily Commission Trend';
                if (daysDiff <= 30) return 'Daily Commission Trend';
                if (daysDiff <= 90) return 'Weekly Commission Trend';
                if (daysDiff <= 365) return 'Monthly Commission Trend';
                return 'Quarterly Commission Trend';
            default:
                return 'Commission Trend Analysis';
        }
    };

    // Get bar labels based on date range
    const getBarLabels = () => {
        if (!reportData?.trends) return [];

        if (dateRange === 'this_week' || dateRange === 'last_week') {
            // For weeks, show day names
            const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
            return reportData.trends.map((trend, index) => ({
                ...trend,
                displayPeriod: days[index] || trend.period
            }));
        } else if (dateRange === 'this_month' || dateRange === 'last_month') {
            // For months, show week numbers
            return reportData.trends.map((trend, index) => ({
                ...trend,
                displayPeriod: `Week ${index + 1}`
            }));
        }
        
        return reportData.trends;
    };

    // Get validation state
    const validation = validateDates();

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 overflow-y-auto py-8">
            {/* Exporting Loader Overlay */}
            {isExporting && (
                <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-60">
                    <div className="bg-white dark:bg-slate-800 rounded-2xl p-8 max-w-md w-full mx-4 shadow-2xl">
                        <div className="flex flex-col items-center">
                            <div className="relative">
                                <div className="w-20 h-20 border-4 border-emerald-100 rounded-full"></div>
                                <div className="absolute top-0 left-0 w-20 h-20 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
                                <Download className="w-8 h-8 text-emerald-500 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2" />
                            </div>
                            <h3 className="text-xl font-semibold text-slate-800 dark:text-white mt-6 mb-2">
                                Exporting Report
                            </h3>
                            <p className="text-slate-600 dark:text-slate-400 text-center">
                                Please wait while we prepare your {exportFormat.toUpperCase()} report...
                            </p>
                            <div className="mt-4 text-sm text-slate-500 dark:text-slate-500">
                                This may take a few moments
                            </div>
                        </div>
                    </div>
                </div>
            )}

            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-2xl w-full max-w-6xl mx-4">
                {/* Header */}
                <div className="sticky top-0 z-10 bg-gradient-to-r from-emerald-600 to-green-600 p-6">
                    <div className="flex justify-between items-center">
                        <div className="flex items-center space-x-4">
                            <div className="p-3 bg-white/20 rounded-xl">
                                <DollarSign className="w-8 h-8 text-white" />
                            </div>
                            <div>
                                <h1 className="text-2xl font-bold text-white">Commissions Report</h1>
                                <p className="text-emerald-100">
                                    Detailed analysis of commission transactions
                                </p>
                            </div>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-2 hover:bg-white/20 rounded-xl transition-colors"
                        >
                            <X className="w-6 h-6 text-white" />
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="p-6 overflow-y-auto max-h-[calc(90vh-80px)]">
                    {/* Date Range Selection */}
                    <div className="mb-6 bg-slate-50 dark:bg-slate-700/50 rounded-xl p-4">
                        <div className="flex justify-between items-center mb-4">
                            <h2 className="text-lg font-semibold text-slate-800 dark:text-white">
                                <Calendar className="w-5 h-5 inline mr-2" />
                                Select Date Range
                            </h2>
                            <div className="flex items-center space-x-2">
                                {isLoading && (
                                    <div className="flex items-center text-sm text-emerald-600 dark:text-emerald-400">
                                        <RefreshCw className="w-4 h-4 animate-spin mr-2" />
                                        <span>Updating report...</span>
                                    </div>
                                )}
                                <div className="relative">
                                    <button
                                        onClick={() => setShowDatePicker(!showDatePicker)}
                                        className="flex items-center space-x-2 px-4 py-2 bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-600"
                                    >
                                        <CalendarDays className="w-4 h-4" />
                                        <span>Quick Actions</span>
                                        <ChevronDown className={`w-4 h-4 transition-transform ${showDatePicker ? 'rotate-180' : ''}`} />
                                    </button>

                                    {showDatePicker && (
                                        <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-slate-700 rounded-xl shadow-lg z-20 border border-slate-200 dark:border-slate-600">
                                            <div className="py-2">
                                                <button
                                                    onClick={() => { handleQuickAction('today'); setShowDatePicker(false); }}
                                                    className="w-full text-left px-4 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-600"
                                                >
                                                    Today
                                                </button>
                                                <button
                                                    onClick={() => { handleQuickAction('yesterday'); setShowDatePicker(false); }}
                                                    className="w-full text-left px-4 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-600"
                                                >
                                                    Yesterday
                                                </button>
                                                <button
                                                    onClick={() => { handleQuickAction('thisMonth'); setShowDatePicker(false); }}
                                                    className="w-full text-left px-4 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-600"
                                                >
                                                    This Month
                                                </button>
                                                <button
                                                    onClick={() => { handleQuickAction('lastMonth'); setShowDatePicker(false); }}
                                                    className="w-full text-left px-4 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-600"
                                                >
                                                    Last Month
                                                </button>
                                                <button
                                                    onClick={() => { handleQuickAction('last90Days'); setShowDatePicker(false); }}
                                                    className="w-full text-left px-4 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-600"
                                                >
                                                    Last 90 Days
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Predefined Ranges */}
                        <div className="mb-6">
                            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">
                                Quick Select Presets
                            </label>
                            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                                {predefinedRanges.map((range) => (
                                    <button
                                        key={range.value}
                                        onClick={() => handleDateRangeChange(range.value)}
                                        className={`px-4 py-3 rounded-xl text-sm font-medium transition-all flex flex-col items-center ${dateRange === range.value
                                            ? 'bg-emerald-500 text-white shadow-lg'
                                            : 'bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-600'
                                            }`}
                                    >
                                        <span>{range.label}</span>
                                        {range.value === 'custom' && customStartDate && customEndDate && (
                                            <span className="text-xs mt-1 opacity-75">
                                                {formatDisplayDate(customStartDate)} - {formatDisplayDate(customEndDate)}
                                            </span>
                                        )}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Custom Date Range */}
                        <div className="p-4 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
                            <h3 className="text-md font-semibold text-slate-800 dark:text-white mb-4">
                                Custom Date Range
                            </h3>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div>
                                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                                        Start Date
                                    </label>
                                    <div className="relative">
                                        <input
                                            type="date"
                                            value={customStartDate}
                                            onChange={(e) => {
                                                setCustomStartDate(e.target.value);
                                                setDateRange('custom');
                                            }}
                                            max={customEndDate || undefined}
                                            className="w-full px-4 py-3 bg-slate-100 dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                                        />
                                        {!customStartDate && (
                                            <div className="absolute right-3 top-3">
                                                <AlertCircle className="w-5 h-5 text-amber-500" />
                                            </div>
                                        )}
                                    </div>
                                    {customStartDate && (
                                        <div className="mt-2 text-sm text-slate-600 dark:text-slate-400">
                                            Selected: {formatDisplayDate(customStartDate)}
                                        </div>
                                    )}
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                                        End Date
                                    </label>
                                    <div className="relative">
                                        <input
                                            type="date"
                                            value={customEndDate}
                                            onChange={(e) => {
                                                setCustomEndDate(e.target.value);
                                                setDateRange('custom');
                                            }}
                                            min={customStartDate}
                                            className="w-full px-4 py-3 bg-slate-100 dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                                        />
                                        {!customEndDate && (
                                            <div className="absolute right-3 top-3">
                                                <AlertCircle className="w-5 h-5 text-amber-500" />
                                            </div>
                                        )}
                                    </div>
                                    {customEndDate && (
                                        <div className="mt-2 text-sm text-slate-600 dark:text-slate-400">
                                            Selected: {formatDisplayDate(customEndDate)}
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Validation and Summary */}
                            <div className="mt-6">
                                {validation.error ? (
                                    <div className="p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg">
                                        <div className="flex items-center">
                                            <AlertCircle className="w-5 h-5 text-red-500 mr-2" />
                                            <span className="text-red-700 dark:text-red-300">{validation.error}</span>
                                        </div>
                                    </div>
                                ) : validation.warning ? (
                                    <div className="p-3 bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800 rounded-lg">
                                        <div className="flex items-center">
                                            <AlertCircle className="w-5 h-5 text-amber-500 mr-2" />
                                            <span className="text-amber-700 dark:text-amber-300">{validation.warning}</span>
                                        </div>
                                    </div>
                                ) : customStartDate && customEndDate ? (
                                    <div className="p-4 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg">
                                        <div className="flex flex-col md:flex-row md:items-center justify-between">
                                            <div>
                                                <div className="text-sm font-medium text-slate-700 dark:text-slate-300">
                                                    Selected Date Range
                                                </div>
                                                <div className="text-lg font-semibold text-emerald-700 dark:text-emerald-300 mt-1">
                                                    {formatDisplayDate(customStartDate)} to {formatDisplayDate(customEndDate)}
                                                </div>
                                                <div className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                                                    {dateRange === 'this_week' || dateRange === 'last_week' ? 'Daily breakdown' : 
                                                     dateRange === 'this_month' || dateRange === 'last_month' ? 'Weekly breakdown' : 
                                                     getTrendPeriodLabel()}
                                                </div>
                                            </div>
                                            <div className="mt-2 md:mt-0">
                                                <div className="inline-flex items-center px-3 py-1.5 rounded-full bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-300 text-sm">
                                                    <Calendar className="w-4 h-4 mr-1" />
                                                    {calculateDaysDifference()} days
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="p-3 bg-slate-100 dark:bg-slate-700 rounded-lg">
                                        <div className="flex items-center">
                                            <AlertCircle className="w-5 h-5 text-slate-500 mr-2" />
                                            <span className="text-slate-600 dark:text-slate-400">
                                                Please select both start and end dates
                                            </span>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Loading State */}
                    {isLoading && (
                        <div className="text-center py-12">
                            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500"></div>
                            <div className="mt-4 text-slate-600 dark:text-slate-400">
                                Updating commission report...
                            </div>
                            <div className="mt-2 text-sm text-slate-500 dark:text-slate-500">
                                Analyzing data for the selected period
                            </div>
                        </div>
                    )}

                    {/* Report Content */}
                    {!isLoading && reportData && (
                        <div id="commissions-report-content">
                            {/* Summary Stats - REMOVED Top Agent Card */}
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                                <div className="bg-gradient-to-br from-emerald-50 to-green-50 dark:from-emerald-900/30 dark:to-green-900/30 rounded-xl p-5">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <div className="text-sm text-emerald-600 dark:text-emerald-400 font-medium">
                                                Total Commission
                                            </div>
                                            <div className="text-3xl font-bold text-slate-800 dark:text-white mt-2">
                                                KES {reportData.summary?.total_commission?.toLocaleString('en-KE', { minimumFractionDigits: 2 }) || '0.00'}
                                            </div>
                                            <div className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                                                from {reportData.summary?.total_transactions || 0} transactions
                                            </div>
                                        </div>
                                        <div className="p-3 bg-emerald-100 dark:bg-emerald-800 rounded-xl">
                                            <DollarSign className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
                                        </div>
                                    </div>
                                </div>

                                <div className="bg-gradient-to-br from-blue-50 to-cyan-50 dark:from-blue-900/30 dark:to-cyan-900/30 rounded-xl p-5">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <div className="text-sm text-blue-600 dark:text-blue-400 font-medium">
                                                Avg Commission
                                            </div>
                                            <div className="text-3xl font-bold text-slate-800 dark:text-white mt-2">
                                                KES {reportData.summary?.average_commission?.toLocaleString('en-KE', { minimumFractionDigits: 2 }) || '0.00'}
                                            </div>
                                            <div className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                                                per transaction
                                            </div>
                                        </div>
                                        <div className="p-3 bg-blue-100 dark:bg-blue-800 rounded-xl">
                                            <Activity className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                                        </div>
                                    </div>
                                </div>

                                <div className="bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-900/30 dark:to-pink-900/30 rounded-xl p-5">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <div className="text-sm text-purple-600 dark:text-purple-400 font-medium">
                                                Commission Growth
                                            </div>
                                            <div className="text-3xl font-bold text-slate-800 dark:text-white mt-2">
                                                {reportData.summary?.growth_percentage || 0}%
                                            </div>
                                            <div className="flex items-center text-sm mt-1">
                                                {reportData.summary?.growth_percentage >= 0 ? (
                                                    <>
                                                        <TrendingUp className="w-4 h-4 text-green-500 mr-1" />
                                                        <span className="text-green-600 dark:text-green-400">
                                                            vs previous period
                                                        </span>
                                                    </>
                                                ) : (
                                                    <>
                                                        <TrendingDown className="w-4 h-4 text-red-500 mr-1" />
                                                        <span className="text-red-600 dark:text-red-400">
                                                            vs previous period
                                                        </span>
                                                    </>
                                                )}
                                            </div>
                                        </div>
                                        <div className="p-3 bg-purple-100 dark:bg-purple-800 rounded-xl">
                                            <TrendingUpIcon className="w-6 h-6 text-purple-600 dark:text-purple-400" />
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Commission by Category */}
                            {reportData.categories && reportData.categories.length > 0 && (
                                <div className="mb-6">
                                    <h3 className="text-lg font-semibold text-slate-800 dark:text-white mb-4">
                                        <PieChart className="w-5 h-5 inline mr-2" />
                                        Commission by Category
                                    </h3>
                                    <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
                                        <table className="w-full">
                                            <thead>
                                                <tr className="bg-slate-100 dark:bg-slate-700">
                                                    <th className="px-4 py-3 text-left font-medium text-slate-600 dark:text-slate-300">
                                                        Category
                                                    </th>
                                                    <th className="px-4 py-3 text-left font-medium text-slate-600 dark:text-slate-300">
                                                        Transactions
                                                    </th>
                                                    <th className="px-4 py-3 text-left font-medium text-slate-600 dark:text-slate-300">
                                                        Total Commission
                                                    </th>
                                                    <th className="px-4 py-3 text-left font-medium text-slate-600 dark:text-slate-300">
                                                        Percentage
                                                    </th>
                                                    <th className="px-4 py-3 text-left font-medium text-slate-600 dark:text-slate-300">
                                                        Avg Commission
                                                    </th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {reportData.categories.map((category, index) => (
                                                    <tr
                                                        key={index}
                                                        className={`border-b border-slate-200 dark:border-slate-700 ${index % 2 === 0
                                                            ? 'bg-white dark:bg-slate-800'
                                                            : 'bg-slate-50 dark:bg-slate-700/50'
                                                            }`}
                                                    >
                                                        <td className="px-4 py-3 font-medium">
                                                            {category.name}
                                                        </td>
                                                        <td className="px-4 py-3">
                                                            {category.count.toLocaleString()}
                                                        </td>
                                                        <td className="px-4 py-3 font-bold text-emerald-600 dark:text-emerald-400">
                                                            KES {category.total_commission?.toLocaleString('en-KE', { minimumFractionDigits: 2 })}
                                                        </td>
                                                        <td className="px-4 py-3">
                                                            <div className="flex items-center">
                                                                <div className="w-24 bg-slate-200 dark:bg-slate-600 rounded-full h-2 mr-3">
                                                                    <div
                                                                        className="bg-emerald-500 h-2 rounded-full"
                                                                        style={{ width: `${category.percentage}%` }}
                                                                    ></div>
                                                                </div>
                                                                <span>{category.percentage}%</span>
                                                            </div>
                                                        </td>
                                                        <td className="px-4 py-3">
                                                            KES {category.average_commission?.toLocaleString('en-KE', { minimumFractionDigits: 2 })}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            )}

                            {/* Trend Analysis with Dynamic Bar Chart */}
                            {reportData.trends && reportData.trends.length > 0 && (
                                <div className="mb-6">
                                    <h3 className="text-lg font-semibold text-slate-800 dark:text-white mb-4">
                                        <TrendingUpIcon className="w-5 h-5 inline mr-2" />
                                        {getTrendPeriodLabel()}
                                    </h3>
                                    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
                                        {/* Bar Chart Visualization */}
                                        <div className="mb-6">
                                            {(() => {
                                                const maxValue = Math.max(...reportData.trends.map(t => t.total_commission || 0));
                                                const minValue = Math.min(...reportData.trends.map(t => t.total_commission || 0));
                                                const effectiveMax = maxValue === 0 ? 100 : maxValue;
                                                const barLabels = getBarLabels();

                                                return (
                                                    <>
                                                        <div className="flex items-end h-64 mt-8 mb-4 px-4">
                                                            {barLabels.map((trend, index) => {
                                                                const height = effectiveMax > 0
                                                                    ? ((trend.total_commission || 0) / effectiveMax) * 100
                                                                    : 0;

                                                                const isCurrent = index === barLabels.length - 1;
                                                                const barColor = isCurrent ? 'bg-emerald-500' : 'bg-emerald-400';

                                                                return (
                                                                    <div key={index} className="flex-1 flex flex-col items-center mx-1 group h-full">
                                                                        <div className="relative w-full h-full flex items-end">
                                                                            <div className="relative w-full h-full">
                                                                                {/* Actual bar with hover effect */}
                                                                                <div
                                                                                    className={`w-full rounded-t-lg transition-all duration-300 ${barColor} 
                                                                                        group-hover:scale-105 group-hover:shadow-lg group-hover:brightness-110
                                                                                        hover:!scale-110 hover:!shadow-xl hover:!brightness-125
                                                                                        transform origin-bottom`}
                                                                                    style={{
                                                                                        height: `${height}%`,
                                                                                        minHeight: '4px',
                                                                                        transition: 'all 0.3s ease',
                                                                                    }}
                                                                                >
                                                                                    {/* Tooltip */}
                                                                                    <div className="absolute left-1/2 -top-12 transform -translate-x-1/2 
                                                                                        px-3 py-2 bg-slate-900 text-white text-xs rounded-lg 
                                                                                        opacity-0 group-hover:opacity-100 transition-all duration-200 
                                                                                        whitespace-nowrap z-10 pointer-events-none
                                                                                        shadow-xl">
                                                                                        <div className="font-semibold">{trend.period}</div>
                                                                                        <div>Commission: KES {trend.total_commission?.toLocaleString('en-KE', { minimumFractionDigits: 2 }) || '0.00'}</div>
                                                                                        <div>Transactions: {trend.transaction_count}</div>
                                                                                        <div className={`${trend.growth >= 0 ? 'text-green-300' : 'text-red-300'}`}>
                                                                                            Growth: {trend.growth >= 0 ? '+' : ''}{trend.growth}%
                                                                                        </div>
                                                                                        <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2 translate-y-1/2 rotate-45 w-2 h-2 bg-slate-900"></div>
                                                                                    </div>
                                                                                </div>
                                                                            </div>
                                                                        </div>

                                                                        {/* X-axis label */}
                                                                        <div className="text-xs text-slate-600 dark:text-slate-400 mt-2 text-center h-8 w-full overflow-hidden">
                                                                            <div className="transform -rotate-45 origin-top-left whitespace-nowrap">
                                                                                {trend.displayPeriod || trend.period}
                                                                            </div>
                                                                        </div>
                                                                    </div>
                                                                );
                                                            })}
                                                        </div>

                                                        {/* Y-axis labels */}
                                                        <div className="flex justify-between items-start h-6 px-4">
                                                            <div className="text-xs text-slate-500 dark:text-slate-500">
                                                                KES {minValue.toLocaleString('en-KE', { minimumFractionDigits: 0 })}
                                                            </div>
                                                            <div className="text-xs text-slate-500 dark:text-slate-500">
                                                                KES {effectiveMax.toLocaleString('en-KE', { minimumFractionDigits: 0 })}
                                                            </div>
                                                        </div>

                                                        {/* X-axis start/end */}
                                                        <div className="flex justify-between text-sm text-slate-600 dark:text-slate-400 px-4 mt-2">
                                                            <span>{barLabels[0]?.period || 'Start'}</span>
                                                            <span>{barLabels[barLabels.length - 1]?.period || 'End'}</span>
                                                        </div>
                                                    </>
                                                );
                                            })()}
                                        </div>

                                        {/* Trends Table */}
                                        <div className="overflow-x-auto">
                                            <table className="w-full">
                                                <thead>
                                                    <tr className="bg-slate-100 dark:bg-slate-700">
                                                        <th className="px-4 py-3 text-left font-medium text-slate-600 dark:text-slate-300">
                                                            Period
                                                        </th>
                                                        <th className="px-4 py-3 text-left font-medium text-slate-600 dark:text-slate-300">
                                                            Transactions
                                                        </th>
                                                        <th className="px-4 py-3 text-left font-medium text-slate-600 dark:text-slate-300">
                                                            Total Commission
                                                        </th>
                                                        <th className="px-4 py-3 text-left font-medium text-slate-600 dark:text-slate-300">
                                                            Growth
                                                        </th>
                                                        <th className="px-4 py-3 text-left font-medium text-slate-600 dark:text-slate-300">
                                                            {dateRange === 'this_week' || dateRange === 'last_week' ? 'Daily Avg' : 'Avg Daily'}
                                                        </th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {getBarLabels().map((trend, index) => (
                                                        <tr
                                                            key={index}
                                                            className={`border-b border-slate-200 dark:border-slate-700 ${index % 2 === 0
                                                                ? 'bg-white dark:bg-slate-800'
                                                                : 'bg-slate-50 dark:bg-slate-700/50'
                                                                }`}
                                                        >
                                                            <td className="px-4 py-3 font-medium">
                                                                {trend.displayPeriod || trend.period}
                                                            </td>
                                                            <td className="px-4 py-3">
                                                                {trend.transaction_count}
                                                            </td>
                                                            <td className="px-4 py-3 font-bold">
                                                                KES {trend.total_commission?.toLocaleString('en-KE', { minimumFractionDigits: 2 })}
                                                            </td>
                                                            <td className="px-4 py-3">
                                                                <span className={`flex items-center ${trend.growth >= 0
                                                                    ? 'text-green-600 dark:text-green-400'
                                                                    : 'text-red-600 dark:text-red-400'
                                                                    }`}>
                                                                    {trend.growth >= 0 ? (
                                                                        <TrendingUp className="w-4 h-4 mr-1" />
                                                                    ) : (
                                                                        <TrendingDown className="w-4 h-4 mr-1" />
                                                                    )}
                                                                    {Math.abs(trend.growth)}%
                                                                </span>
                                                            </td>
                                                            <td className="px-4 py-3">
                                                                KES {trend.average_daily?.toLocaleString('en-KE', { minimumFractionDigits: 2 })}
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>

                                        {/* Trend Summary */}
                                        <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                                            <div className="flex items-center">
                                                <CalendarIcon className="w-5 h-5 text-blue-600 dark:text-blue-400 mr-2" />
                                                <div>
                                                    <div className="text-sm font-medium text-slate-700 dark:text-slate-300">
                                                        {dateRange === 'this_week' || dateRange === 'last_week' 
                                                            ? 'Daily breakdown for the week' 
                                                            : dateRange === 'this_month' || dateRange === 'last_month'
                                                            ? 'Weekly breakdown for the month'
                                                            : `Analysis Period: ${reportData.trend_period || getTrendPeriodLabel()}`
                                                        }
                                                    </div>
                                                    <div className="text-xs text-slate-600 dark:text-slate-400">
                                                        {dateRange === 'this_week' || dateRange === 'last_week' 
                                                            ? 'Showing daily commission trends' 
                                                            : dateRange === 'this_month' || dateRange === 'last_month'
                                                            ? 'Showing weekly commission trends'
                                                            : `Comparing ${reportData.trends?.length || 0} periods for trend analysis`
                                                        }
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Top Agents */}
                            {reportData.top_agents && reportData.top_agents.length > 0 && (
                                <div className="mb-6">
                                    <h3 className="text-lg font-semibold text-slate-800 dark:text-white mb-4">
                                        <Users className="w-5 h-5 inline mr-2" />
                                        Top 10 Agents by Commission
                                    </h3>
                                    <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
                                        <table className="w-full">
                                            <thead>
                                                <tr className="bg-slate-100 dark:bg-slate-700">
                                                    <th className="px-4 py-3 text-left font-medium text-slate-600 dark:text-slate-300">
                                                        Rank
                                                    </th>
                                                    <th className="px-4 py-3 text-left font-medium text-slate-600 dark:text-slate-300">
                                                        Agent Name
                                                    </th>
                                                    <th className="px-4 py-3 text-left font-medium text-slate-600 dark:text-slate-300">
                                                        Agent Code
                                                    </th>
                                                    <th className="px-4 py-3 text-left font-medium text-slate-600 dark:text-slate-300">
                                                        Transactions
                                                    </th>
                                                    <th className="px-4 py-3 text-left font-medium text-slate-600 dark:text-slate-300">
                                                        Total Commission
                                                    </th>
                                                    <th className="px-4 py-3 text-left font-medium text-slate-600 dark:text-slate-300">
                                                        Avg Commission
                                                    </th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {reportData.top_agents.map((agent, index) => (
                                                    <tr
                                                        key={agent.id}
                                                        className={`border-b border-slate-200 dark:border-slate-700 ${index % 2 === 0
                                                            ? 'bg-white dark:bg-slate-800'
                                                            : 'bg-slate-50 dark:bg-slate-700/50'
                                                            }`}
                                                    >
                                                        <td className="px-4 py-3">
                                                            <span className={`inline-flex items-center justify-center w-8 h-8 rounded-full ${index < 3
                                                                ? 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200'
                                                                : 'bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-300'
                                                                }`}>
                                                                #{index + 1}
                                                            </span>
                                                        </td>
                                                        <td className="px-4 py-3 font-medium">
                                                            {agent.name}
                                                        </td>
                                                        <td className="px-4 py-3 font-mono text-sm">
                                                            {agent.code}
                                                        </td>
                                                        <td className="px-4 py-3">
                                                            {agent.transaction_count}
                                                        </td>
                                                        <td className="px-4 py-3 font-bold text-emerald-600 dark:text-emerald-400">
                                                            KES {agent.total_commission?.toLocaleString('en-KE', { minimumFractionDigits: 2 })}
                                                        </td>
                                                        <td className="px-4 py-3">
                                                            KES {agent.average_commission?.toLocaleString('en-KE', { minimumFractionDigits: 2 })}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* No Data State */}
                    {!isLoading && !reportData && !validation.error && (
                        <div className="text-center py-12">
                            <FileBarChart className="w-16 h-16 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
                            <h3 className="text-lg font-semibold text-slate-700 dark:text-slate-300 mb-2">
                                No Commission Data Found
                            </h3>
                            <p className="text-slate-500 dark:text-slate-400 mb-6 max-w-md mx-auto">
                                No commission transactions match the selected criteria. Try adjusting your date range or filters.
                            </p>
                        </div>
                    )}
                </div>

                {/* Footer with Export Options */}
                <div className="sticky bottom-0 bg-white dark:bg-slate-800 border-t border-slate-200 dark:border-slate-700 p-4">
                    <div className="flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0">
                        <div className="flex items-center space-x-2 text-sm text-slate-600 dark:text-slate-400">
                            <FileText className="w-4 h-4" />
                            <span>Ready to export</span>
                            {reportData?.period && (
                                <span className="ml-2 px-2 py-1 bg-slate-100 dark:bg-slate-700 rounded text-xs">
                                    {reportData.period}
                                </span>
                            )}
                        </div>
                        <div className="flex flex-wrap items-center justify-center gap-3">
                            <div className="flex items-center space-x-2 bg-slate-100 dark:bg-slate-700 rounded-xl px-3 py-2">
                                <span className="text-sm text-slate-600 dark:text-slate-300">Format:</span>
                                <select
                                    value={exportFormat}
                                    onChange={(e) => setExportFormat(e.target.value)}
                                    disabled={isExporting}
                                    className="bg-transparent border-none focus:ring-0 text-sm text-slate-800 dark:text-white disabled:opacity-50"
                                >
                                    <option value="pdf">PDF Report</option>
                                    <option value="excel">Excel (.xlsx)</option>
                                    <option value="csv">CSV Data</option>
                                </select>
                            </div>
                            <button
                                onClick={() => handleExport(exportFormat)}
                                disabled={!reportData || isLoading || isExporting}
                                className={`px-4 py-2 rounded-xl flex items-center space-x-2 transition-all ${!reportData || isLoading || isExporting
                                    ? 'bg-slate-300 dark:bg-slate-700 text-slate-500 dark:text-slate-400 cursor-not-allowed'
                                    : 'bg-emerald-500 hover:bg-emerald-600 text-white shadow-md hover:shadow-lg'
                                    }`}
                            >
                                {isExporting ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        <span>Exporting...</span>
                                    </>
                                ) : (
                                    <>
                                        <Download className="w-4 h-4" />
                                        <span>Export {exportFormat.toUpperCase()}</span>
                                    </>
                                )}
                            </button>
                            <button
                                onClick={handlePrint}
                                disabled={!reportData || isLoading || isExporting}
                                className={`px-4 py-2 rounded-xl flex items-center space-x-2 transition-all ${!reportData || isLoading || isExporting
                                    ? 'bg-slate-300 dark:bg-slate-700 text-slate-500 dark:text-slate-400 cursor-not-allowed'
                                    : 'bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-300'
                                    }`}
                            >
                                <Printer className="w-4 h-4" />
                                <span>Print</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default CommissionsReportModal;