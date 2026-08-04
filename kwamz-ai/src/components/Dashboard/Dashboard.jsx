import React, { useState, useEffect, useCallback } from 'react';
import StatsGrid from './StatsGrid';
import DashboardHeader from './DashboardHeader';
import RevenueChart from './RevenueChart';
import CommissionTransferChart from './CommissionTransferChart';
import CommissionRollupChart from './CommissionRollupChart';
import TrafficSourcesChart from './TrafficSourcesChart';
import OrdersChart from './OrdersChart';
import RecentActivity from './RecentActivity';
import Transactions from '../Layout/Transactions';
import UserAgentList from '../Pages/UserAgentList';
import AgentCompanyList from '../Pages/AgentCompanyList';
import CompanyList from '../Pages/CompanyList';
import CompanyHierarchy from '../Pages/CompanyHierachy';
import SystemUsersList from '../Pages/SystemUsersList';
import AgentCompanyPaymentsGrid from '../Pages/AgentCompanyPaymentsGrid';
import BankList from '../Pages/BankList';
import TransactionsGrid from '../Pages/TransactionsGrid';
import ConfigGrid from '../Pages/ConfigGrid';
import UserReportConfigGrid from '../Pages/UserReportConfigGrid';
import FraudAlertsGrid from '../Pages/FraudAlertsGrid';
import SwapHistoryGrid from '../Pages/SwapHistoryGrid';
import ClawbacksGrid from '../Pages/ClawbacksGrid';
import AgentDownloadPage from '../Pages/AgentDownloadPage';
import AdminBillingPage from '../Pages/AdminBillingPage';
import { analyticsApi } from '../../service/AnalyticsApi';
import { Loader2, AlertCircle, RefreshCw } from 'lucide-react';

function Dashboard({ currentPage, setCurrentPage }) {
  const [analyticsData, setAnalyticsData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedDays, setSelectedDays] = useState(30);
  const [companies, setCompanies] = useState([]);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [commissionBalance, setCommissionBalance] = useState(null);

  useEffect(() => {
    analyticsApi.getUserCompanies()
      .then(res => {
        if (res.success) setCompanies(res.data);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (selectedCompany?.shortcode) {
      analyticsApi.getCommissionClosingBalance(selectedCompany.shortcode)
        .then(res => { if (res.success) setCommissionBalance(res.data.balance); })
        .catch(() => setCommissionBalance(null));
    } else {
      analyticsApi.getCommissionClosingBalanceTotal()
        .then(res => { if (res.success) setCommissionBalance(res.data.balance); })
        .catch(() => setCommissionBalance(null));
    }
  }, [selectedCompany]);

  const fetchAnalytics = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = { days: selectedDays };
      if (selectedCompany?.id) params.company_id = selectedCompany.id;
      const response = await analyticsApi.getDashboardAnalytics(params);
      if (response.success) {
        setAnalyticsData(response.data);
      } else {
        setError(response.error || 'Failed to load analytics');
      }
    } catch (err) {
      console.error('Error fetching analytics:', err);
      setError(err.message || 'Failed to load analytics data');
    } finally {
      setIsLoading(false);
    }
  }, [selectedDays, selectedCompany]);

  useEffect(() => {
    if (currentPage === 'dashboard') {
      fetchAnalytics();
    }
  }, [currentPage, fetchAnalytics]);

  const handleRefresh = () => {
    fetchAnalytics();
  };

  const handleDaysChange = (days) => {
    setSelectedDays(days);
  };

  const handleCompanyChange = (company) => {
    setSelectedCompany(company);
  };

  const renderDashboardContent = () => {
    if (isLoading) {
      return (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="w-12 h-12 text-blue-500 animate-spin mb-4" />
          <p className="text-slate-600 dark:text-slate-400">Loading analytics data...</p>
        </div>
      );
    }

    if (error) {
      return (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="bg-red-50 dark:bg-red-900/20 rounded-2xl p-8 text-center max-w-md">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-red-700 dark:text-red-400 mb-2">
              Failed to load analytics
            </h3>
            <p className="text-red-600 dark:text-red-300 mb-4">{error}</p>
            <button
              onClick={handleRefresh}
              className="inline-flex items-center px-4 py-2 bg-red-100 dark:bg-red-800 text-red-700 dark:text-red-200 rounded-lg hover:bg-red-200 dark:hover:bg-red-700 transition-colors"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Try Again
            </button>
          </div>
        </div>
      );
    }

    return (
      <>
        <DashboardHeader
          currentPage={currentPage}
          setCurrentPage={setCurrentPage}
          onRefresh={handleRefresh}
          selectedDays={selectedDays}
          onDaysChange={handleDaysChange}
          healthMetrics={analyticsData?.health_metrics}
          companies={companies}
          selectedCompany={selectedCompany}
          onCompanyChange={handleCompanyChange}
        />

        {(() => {
          const trends = analyticsData?.monthly_trends || [];
          const recent = analyticsData?.recent_transactions || [];
          const totalTx = analyticsData?.kpis?.total_transactions?.value || 0;
          const isOnboarding = trends.length === 0 && recent.length === 0 && totalTx === 0;

          return (
            <>
              <StatsGrid kpis={analyticsData?.kpis} isLoading={isLoading} isOnboarding={isOnboarding} commissionBalance={commissionBalance} selectedCompany={selectedCompany} />

              <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                <CommissionTransferChart
                  data={analyticsData?.mmf_transfer_trends || []}
                  growth={analyticsData?.mmf_transfer_growth || 0}
                  isOnboarding={isOnboarding}
                />
                <CommissionRollupChart
                  data={analyticsData?.commission_rollup_trends || []}
                  growth={analyticsData?.commission_rollup_growth || 0}
                  isOnboarding={isOnboarding}
                />
              </div>

              <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                <RevenueChart
                  data={trends}
                  healthMetrics={analyticsData?.health_metrics}
                  isOnboarding={isOnboarding}
                />
                <TrafficSourcesChart data={analyticsData?.type_distribution || []} />
              </div>

              <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                <OrdersChart data={trends} isOnboarding={isOnboarding} />
                <RecentActivity transactions={recent} isOnboarding={isOnboarding} />
              </div>
            </>
          );
        })()}
      </>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900 p-2 sm:p-4 md:p-6">
      <div className="max-w-7xl mx-auto space-y-4 sm:space-y-6 md:space-y-8">
        {currentPage === 'dashboard' && renderDashboardContent()}
        {currentPage === 'transactions' && <Transactions />}
        {currentPage === 'user-list' && <UserAgentList />}
        {currentPage === 'agent-list' && <AgentCompanyList />}
        {currentPage === 'company-hierarchy' && <CompanyHierarchy />}
        {currentPage === 'system-user-list' && <SystemUsersList />}
        {currentPage === 'agent-companies' && <AgentCompanyPaymentsGrid />}
        {currentPage === 'company-list' && <CompanyList />}
        {currentPage === 'transactions-list' && <TransactionsGrid />}
        {currentPage === 'bank-list' && <BankList />}
        {currentPage === 'configs' && <ConfigGrid />}
        {currentPage === 'report-schedules' && <UserReportConfigGrid />}
        {currentPage === 'fraud-alerts' && <FraudAlertsGrid />}
        {currentPage === 'swap-history' && <SwapHistoryGrid />}
        {currentPage === 'clawbacks' && <ClawbacksGrid />}
        {currentPage === 'agent-download' && <AgentDownloadPage />}
        {currentPage === 'admin-billing' && <AdminBillingPage />}
      </div>
    </div>
  );
}

export default Dashboard;