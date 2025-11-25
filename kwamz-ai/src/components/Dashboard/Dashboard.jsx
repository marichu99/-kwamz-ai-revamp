import React from 'react';
import StatsGrid from './StatsGrid';
import DashboardHeader from './DashboardHeader';
import RevenueChart from './RevenueChart';
import TrafficSourcesChart from './TrafficSourcesChart';
import OrdersChart from './OrdersChart';
import RecentActivity from './RecentActivity';
import Transactions
from '../Layout/Transactions';
import UserAgentList from '../Pages/UserAgentList';
import AgentCompanyList from '../Pages/AgentCompanyList';
import CompanyList from '../Pages/CompanyList';
import Checkout from '../Pages/Checkout';
import PaymentForm from '../Pages/PaymentForm';
import CompanyHierarchy from '../Pages/CompanyHierachy';
import NormalAgentList from '../Pages/SystemUsersList';
import SystemUsersList from '../Pages/SystemUsersList';
import AgentCompanyPaymentsGrid from '../Pages/AgentCompanyPaymentsGrid';
import BankList from '../Pages/BankList';
function Dashboard({ currentPage, setCurrentPage }) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900 p-6">
      <div className="max-w-7xl mx-auto space-y-8">

        {/* Conditional Rendering */}
        {currentPage === 'dashboard' && (
          <>
            {/* Header with navigation */}
            <DashboardHeader currentPage={currentPage} setCurrentPage={setCurrentPage} />

            <StatsGrid />
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
              <RevenueChart />
              <TrafficSourcesChart />
            </div>
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              <OrdersChart />
              <RecentActivity />
            </div>
          </>
        )}
        {currentPage === 'transactions' && <Transactions />}
        {currentPage === 'user-list' && <UserAgentList />}
        {currentPage === 'agent-list' && <AgentCompanyList />}
        {currentPage === 'company-hierarchy' && <CompanyHierarchy />}
        {currentPage === 'system-user-list' && <SystemUsersList />}
        {currentPage === 'agent-companies' && <AgentCompanyPaymentsGrid />}
        {currentPage === 'company-list' && <CompanyList />}
        {currentPage === 'bank-list' && <BankList />}
        {currentPage === 'checkout' && <Checkout />}
        {currentPage === 'pesapal' && <PaymentForm />}
      </div>
    </div>
  );
}

export default Dashboard;