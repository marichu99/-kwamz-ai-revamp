// components/CompanyAssignmentModal.jsx
import { useState, useEffect } from 'react';
import {
  X, Building, User, Search, Check, Plus, Link, Users, Mail, Crown, Trash2, AlertTriangle,
} from 'lucide-react';

function CompanyAssignmentModal({
  isOpen,
  onClose,
  agents,                    
  companies,                 
  assignedCompaniesMap,      
  loadingAssignments = false,
  onAssignCompanies,
  onUnassignCompany,
}) {
  const [selectedCompanyIds, setSelectedCompanyIds] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState('available'); // 'available' | 'assigned'
  const [isAssigning, setIsAssigning] = useState(false);
  const [unassigningCompanyId, setUnassigningCompanyId] = useState(null);
  const [companyToUnassign, setCompanyToUnassign] = useState(null); // Track company for confirmation

  useEffect(() => {
    if (isOpen) {
      setSelectedCompanyIds([]);
      setSearchTerm('');
      setActiveTab('available');
      setIsAssigning(false);
      setUnassigningCompanyId(null);
      setCompanyToUnassign(null);
    }
  }, [isOpen]);

  if (!isOpen || !agents || agents.length === 0) return null;

  // Derive assigned & available companies from the map
  const assignedCompanies = Object.values(assignedCompaniesMap || {});
  const assignedCompanyIds = new Set(assignedCompanies.map(c => c.id));

  const availableCompanies = companies.filter(
    company => !assignedCompanyIds.has(company.id)
  );

  // Search filtering
  const filterCompany = (company) => {
    const term = searchTerm.toLowerCase();
    return (
      company.company_name?.toLowerCase().includes(term) ||
      company.registration_number?.toLowerCase().includes(term) ||
      company.primary_owner_name?.toLowerCase().includes(term) ||
      company.primary_owner_email?.toLowerCase().includes(term)
    );
  };

  const filteredAvailable = availableCompanies.filter(filterCompany);
  const filteredAssigned = assignedCompanies.filter(filterCompany);

  const toggleCompany = (companyId) => {
    setSelectedCompanyIds(prev =>
      prev.includes(companyId)
        ? prev.filter(id => id !== companyId)
        : [...prev, companyId]
    );
  };

  const handleSubmit = async () => {
    setIsAssigning(true);
    try {
      const agentIds = agents.map(a => a.id);
      await onAssignCompanies(agentIds, selectedCompanyIds);
    } catch (error) {
      console.error('Error assigning companies:', error);
    } finally {
      setIsAssigning(false);
    }
  };

  const handleUnassignClick = (company) => {
    setCompanyToUnassign(company);
  };

  const handleConfirmUnassign = async () => {
    if (!companyToUnassign || !onUnassignCompany) return;
    
    setUnassigningCompanyId(companyToUnassign.id);
    try {
      const agentIds = agents.map(a => a.id);
      await onUnassignCompany(agentIds, companyToUnassign.id);
      setCompanyToUnassign(null); // Close confirmation dialog on success
    } catch (error) {
      console.error('Error unassigning company:', error);
    } finally {
      setUnassigningCompanyId(null);
    }
  };

  const handleCancelUnassign = () => {
    setCompanyToUnassign(null);
  };

  const formatShares = (shares) => {
    if (!shares) return '0%';
    return `${parseFloat(shares).toFixed(1)}%`;
  };

  const CompanyCard = ({ company, isSelected = false, isAssigned = false, assignedAgents = [] }) => (
    <div
      className={`p-4 border-2 rounded-lg transition-all ${
        isAssigned ? '' : 'cursor-pointer'
      } ${
        isSelected
          ? 'border-green-500 bg-green-50 dark:bg-green-900/20'
          : isAssigned
          ? 'border-blue-300 bg-blue-50 dark:bg-blue-900/20 dark:border-blue-700'
          : 'border-slate-200 dark:border-slate-700 hover:border-green-300 dark:hover:border-green-700'
      }`}
      onClick={() => !isAssigned && toggleCompany(company.id)}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3 flex-1">
          {!isAssigned && (
            <div
              className={`w-5 h-5 border-2 rounded flex items-center justify-center mt-1 flex-shrink-0 ${
                isSelected ? 'bg-green-500 border-green-500' : 'border-slate-300 dark:border-slate-600'
              }`}
            >
              {isSelected && <Check className="w-3 h-3 text-white" />}
            </div>
          )}
          {isAssigned && (
            <div className="w-5 h-5 bg-blue-500 rounded flex items-center justify-center mt-1 flex-shrink-0">
              <Link className="w-3 h-3 text-white" />
            </div>
          )}

          <div className="flex-1 min-w-0">
            {/* Header */}
            <div className="flex items-start justify-between mb-2">
              <div>
                <p className="font-semibold text-slate-800 dark:text-white text-lg">
                  {company.company_name}
                </p>
                <p className="text-sm text-slate-600 dark:text-slate-400 font-mono">
                  Reg: {company.registration_number || company.company_number}
                </p>
              </div>
              <div className="flex items-center space-x-2">
                {isAssigned && (
                  <span className="px-2 py-1 bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 rounded-full text-xs font-medium">
                    Assigned
                  </span>
                )}
                <div className="flex items-center space-x-1">
                  {isAssigned && onUnassignCompany && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleUnassignClick(company);
                      }}
                      disabled={unassigningCompanyId === company.id}
                      className="p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      title="Unassign company"
                    >
                      {unassigningCompanyId === company.id ? (
                        <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-red-500"></div>
                      ) : (
                        <Trash2 className="w-3 h-3" />
                      )}
                    </button>
                  )}
                  <Building className="w-5 h-5 text-slate-400 mt-1 flex-shrink-0" />
                </div>
              </div>
            </div>

            {/* Assigned Agents */}
            {isAssigned && assignedAgents.length > 0 && (
              <div className="mb-3 p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <div className="flex items-center space-x-2 mb-1">
                  <Users className="w-3 h-3 text-blue-500" />
                  <span className="text-sm font-medium text-blue-700 dark:text-blue-300">
                    Assigned to:
                  </span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {assignedAgents.map(agent => (
                    <span
                      key={agent.id}
                      className="inline-flex items-center px-2 py-1 bg-white dark:bg-slate-800 text-blue-600 dark:text-blue-400 rounded-full text-xs border border-blue-200 dark:border-blue-700"
                    >
                      <User className="w-2 h-2 mr-1" />
                      {agent.firstname && agent.lastname
                        ? `${agent.firstname} ${agent.lastname}`
                        : agent.username}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Owner & Details */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <Crown className="w-4 h-4 text-amber-500" />
                  <span className="font-medium text-slate-700 dark:text-slate-300">Primary Owner</span>
                </div>
                {company.primary_owner_name && (
                  <div className="flex items-center space-x-2 text-slate-600 dark:text-slate-400">
                    <User className="w-3 h-3" />
                    <span className="truncate">{company.primary_owner_name}</span>
                  </div>
                )}
                {company.primary_owner_email && (
                  <div className="flex items-center space-x-2 text-slate-600 dark:text-slate-400">
                    <Mail className="w-3 h-3" />
                    <span className="truncate">{company.primary_owner_email}</span>
                  </div>
                )}
                {company.primary_owner_shares > 0 && (
                  <div>
                    <span className="text-xs bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 px-2 py-1 rounded-full">
                      {formatShares(company.primary_owner_shares)} shares
                    </span>
                  </div>
                )}
              </div>

              <div className="space-y-2">
                {company.directors?.length > 0 && (
                  <div className="flex items-center space-x-2">
                    <Users className="w-4 h-4 text-blue-500" />
                    <span className="text-slate-600 dark:text-slate-400">
                      {company.directors.length} director{company.directors.length > 1 ? 's' : ''}
                    </span>
                  </div>
                )}
                {company.secondary_shareholders?.length > 0 && (
                  <div className="flex items-center space-x-2">
                    <User className="w-4 h-4 text-green-500" />
                    <span className="text-slate-600 dark:text-slate-400">
                      {company.secondary_shareholders.length} shareholder{company.secondary_shareholders.length > 1 ? 's' : ''}
                    </span>
                  </div>
                )}
                <div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    company.compliance_status === 'compliant'
                      ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                      : company.compliance_status === 'pending'
                      ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                      : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                  }`}>
                    {company.compliance_status || 'Unknown'}
                  </span>
                </div>
                {company.total_float_balance > 0 && (
                  <div>
                    <span className="text-xs bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 px-2 py-1 rounded-full">
                      KES {parseFloat(company.total_float_balance).toLocaleString()}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {company.address && (
              <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-700">
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  <span className="font-medium">Address:</span> {company.address}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Confirmation Dialog */}
      {companyToUnassign && (
        <div className="fixed inset-0 flex items-center justify-center bg-black/60 backdrop-blur-sm z-[60] p-4">
          <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-md">
            <div className="p-6">
              <div className="flex items-center space-x-3 mb-4">
                <div className="p-2 bg-red-100 dark:bg-red-900/30 rounded-lg">
                  <AlertTriangle className="w-6 h-6 text-red-600 dark:text-red-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-slate-800 dark:text-white">
                    Unassign Company
                  </h3>
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    Confirm unassignment action
                  </p>
                </div>
              </div>

              <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
                <p className="text-sm text-red-800 dark:text-red-300 font-medium mb-2">
                  Are you sure you want to unassign this company?
                </p>
                <p className="text-sm text-red-700 dark:text-red-400">
                  <strong>{companyToUnassign.company_name}</strong> will be removed from {agents.length} agent{agents.length > 1 ? 's' : ''}.
                </p>
                {agents.length > 0 && (
                  <div className="mt-2 text-xs text-red-600 dark:text-red-500">
                    Agents: {agents.map(a => a.firstname && a.lastname ? `${a.firstname} ${a.lastname}` : a.username).join(', ')}
                  </div>
                )}
              </div>

              <div className="flex space-x-3 justify-end">
                <button
                  onClick={handleCancelUnassign}
                  disabled={unassigningCompanyId === companyToUnassign.id}
                  className="px-4 py-2 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmUnassign}
                  disabled={unassigningCompanyId === companyToUnassign.id}
                  className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
                >
                  {unassigningCompanyId === companyToUnassign.id ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      <span>Unassigning...</span>
                    </>
                  ) : (
                    <>
                      <Trash2 className="w-4 h-4" />
                      <span>Unassign</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Modal */}
      <div className="fixed inset-0 flex items-center justify-center bg-black/60 backdrop-blur-sm z-50 p-4">
        <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
          {/* Header */}
          <div className="bg-gradient-to-r from-green-600 to-emerald-600 p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="bg-white/20 p-2 rounded-lg">
                  <Users className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white">Assign Companies to Agents</h2>
                  <p className="text-green-100 text-sm">
                    {agents.length} agent{agents.length > 1 ? 's' : ''} selected
                  </p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="text-white/80 hover:text-white hover:bg-white/20 p-2 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
            {/* Loading State */}
            {loadingAssignments && (
              <div className="text-center py-8">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-green-600"></div>
                <p className="mt-3 text-slate-600 dark:text-slate-400">Loading current assignments...</p>
              </div>
            )}

            {!loadingAssignments && (
              <>
                {/* Summary */}
                <div className="mb-6 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <Users className="w-5 h-5 text-green-600 dark:text-green-400" />
                      <div>
                        <p className="font-medium text-green-800 dark:text-green-300">Selected Agents</p>
                        <div className="text-sm text-green-600 dark:text-green-400">
                          {agents.map(a => a.firstname && a.lastname ? `${a.firstname} ${a.lastname}` : a.username).join(', ')}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-bold text-green-800 dark:text-green-300">
                        {selectedCompanyIds.length} selected
                      </p>
                      <p className="text-sm text-green-600 dark:text-green-400">
                        {filteredAvailable.length} available • {assignedCompanies.length} assigned
                      </p>
                    </div>
                  </div>
                </div>

                {/* Search */}
                <div className="mb-6">
                  <div className="relative">
                    <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
                    <input
                      type="text"
                      placeholder="Search companies..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="w-full pl-10 pr-4 py-3 border border-slate-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-green-500"
                    />
                  </div>
                </div>

                {/* Tabs */}
                <div className="mb-6">
                  <div className="flex border-b border-slate-200 dark:border-slate-700">
                    <button
                      onClick={() => setActiveTab('available')}
                      className={`flex items-center space-x-2 px-4 py-2 border-b-2 font-medium text-sm transition-colors ${
                        activeTab === 'available'
                          ? 'border-green-500 text-green-600 dark:text-green-400'
                          : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                      }`}
                    >
                      <Plus className="w-4 h-4" />
                      <span>Available</span>
                      <span className="bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400 px-2 py-1 rounded-full text-xs">
                        {filteredAvailable.length}
                      </span>
                    </button>
                    <button
                      onClick={() => setActiveTab('assigned')}
                      className={`flex items-center space-x-2 px-4 py-2 border-b-2 font-medium text-sm transition-colors ${
                        activeTab === 'assigned'
                          ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                          : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                      }`}
                    >
                      <Link className="w-4 h-4" />
                      <span>Assigned</span>
                      <span className="bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400 px-2 py-1 rounded-full text-xs">
                        {filteredAssigned.length}
                      </span>
                    </button>
                  </div>
                </div>

                {/* Company List */}
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {activeTab === 'available' && filteredAvailable.length === 0 && (
                    <div className="text-center py-8 text-slate-500 dark:text-slate-400">
                      <Building className="w-12 h-12 mx-auto mb-3 text-slate-300" />
                      <p>No available companies</p>
                    </div>
                  )}
                  {activeTab === 'available' && filteredAvailable.map(company => (
                    <CompanyCard
                      key={company.id}
                      company={company}
                      isSelected={selectedCompanyIds.includes(company.id)}
                    />
                  ))}

                  {activeTab === 'assigned' && filteredAssigned.length === 0 && (
                    <div className="text-center py-8 text-slate-500 dark:text-slate-400">
                      <Link className="w-12 h-12 mx-auto mb-3 text-slate-300" />
                      <p>No companies assigned yet</p>
                    </div>
                  )}
                  {activeTab === 'assigned' && filteredAssigned.map(item => (
                    <CompanyCard
                      key={item.id}
                      company={item}
                      isAssigned={true}
                      assignedAgents={item.assignedAgents}
                    />
                  ))}
                </div>
              </>
            )}
          </div>

          {/* Footer */}
          <div className="border-t border-slate-200 dark:border-slate-700 p-6 bg-slate-50 dark:bg-slate-900/50">
            <div className="flex items-center justify-between">
              <div className="text-sm text-slate-600 dark:text-slate-400">
                {selectedCompanyIds.length > 0
                  ? `${selectedCompanyIds.length} companies will be assigned`
                  : 'Select companies from the Available tab'}
              </div>
              <div className="flex space-x-3">
                <button
                  onClick={onClose}
                  disabled={isAssigning || unassigningCompanyId}
                  className="px-6 py-2 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={selectedCompanyIds.length === 0 || loadingAssignments || isAssigning || unassigningCompanyId}
                  className="px-6 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2 min-w-32 justify-center"
                >
                  {isAssigning ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      <span>Assigning...</span>
                    </>
                  ) : (
                    <>
                      <Check className="w-4 h-4" />
                      <span>Assign to {agents.length} Agent{agents.length > 1 ? 's' : ''}</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

export default CompanyAssignmentModal;