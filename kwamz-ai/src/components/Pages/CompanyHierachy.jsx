import React, { useState, useEffect } from 'react';
import { ChevronRight, ChevronDown, Building2, Store, Users, User, FileText, Shield, MapPin, Phone, Hash } from 'lucide-react';
import config from '../../Config';
import { useToast } from './ToastProvider';


function CompanyHierarchy() {
    const [hierarchyData, setHierarchyData] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [expandedCompanies, setExpandedCompanies] = useState(new Set());
    const [expandedAgentCompanies, setExpandedAgentCompanies] = useState(new Set());
    const { showToast } = useToast();

    useEffect(() => {
        fetchHierarchy();
    }, []);

    const fetchHierarchy = async () => {
        setIsLoading(true);
        try {
            const token = localStorage.getItem('token');
            const response = await fetch(`${config.API_URL}/company/company-hierarchy`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) throw new Error('Failed to fetch hierarchy');

            const data = await response.json();
            setHierarchyData(data.data || []);
        } catch (error) {
            showToast( 'Error fetching company hierarchy','error');
            console.error('Error fetching hierarchy:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const toggleCompany = (companyId) => {
        setExpandedCompanies(prev => {
            const newSet = new Set(prev);
            if (newSet.has(companyId)) {
                newSet.delete(companyId);
            } else {
                newSet.add(companyId);
            }
            return newSet;
        });
    };

    const toggleAgentCompany = (agentCompanyId) => {
        setExpandedAgentCompanies(prev => {
            const newSet = new Set(prev);
            if (newSet.has(agentCompanyId)) {
                newSet.delete(agentCompanyId);
            } else {
                newSet.add(agentCompanyId);
            }
            return newSet;
        });
    };

    if (isLoading) {
        return (
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-lg p-6 flex items-center justify-center min-h-[400px]">
                <div className="text-center">
                    <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                    <p className="text-slate-600 dark:text-slate-400">Loading hierarchy...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-lg p-6">
            <div className="mb-6">
                <h2 className="text-2xl font-bold text-slate-800 dark:text-white mb-2">Company Hierarchy Report</h2>
                <p className="text-sm text-slate-600 dark:text-slate-400">
                    Total Companies: {hierarchyData.length}
                </p>
            </div>

            <div className="space-y-2">
                {hierarchyData.map((company) => (
                    <div key={company.id} className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden">
                        {/* Company Level */}
                        <div
                            className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-slate-700 dark:to-slate-800 p-4 cursor-pointer hover:from-blue-100 hover:to-indigo-100 dark:hover:from-slate-600 dark:hover:to-slate-700 transition-colors"
                            onClick={() => toggleCompany(company.id)}
                        >
                            <div className="flex items-center justify-between">
                                <div className="flex items-center space-x-3 flex-1">
                                    <button className="text-blue-600 dark:text-blue-400">
                                        {expandedCompanies.has(company.id) ? (
                                            <ChevronDown className="w-5 h-5" />
                                        ) : (
                                            <ChevronRight className="w-5 h-5" />
                                        )}
                                    </button>
                                    <Building2 className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                                    <div className="flex-1">
                                        <h3 className="font-bold text-slate-800 dark:text-white">{company.company_name}</h3>
                                        <div className="flex items-center space-x-4 text-sm text-slate-600 dark:text-slate-400 mt-1">
                                            <span className="flex items-center space-x-1">
                                                <Hash className="w-4 h-4" />
                                                <span>{company.registration_number}</span>
                                            </span>
                                            <span className="flex items-center space-x-1">
                                                <MapPin className="w-4 h-4" />
                                                <span>{company.address}</span>
                                            </span>
                                        </div>
                                    </div>
                                </div>
                                <div className="flex items-center space-x-4">
                                    <div className="text-right">
                                        <p className="text-sm font-semibold text-slate-800 dark:text-white">
                                            {company.agent_company_count} Tills
                                        </p>
                                        <p className="text-xs text-slate-600 dark:text-slate-400">
                                            {company.total_agent_count} Agents
                                        </p>
                                    </div>
                                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${company.compliance_status === 'compliant'
                                            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                            : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                                        }`}>
                                        {company.compliance_status}
                                    </span>
                                </div>
                            </div>
                        </div>

                        {/* Agent Companies Level */}
                        {expandedCompanies.has(company.id) && (
                            <div className="bg-slate-50 dark:bg-slate-900/50">
                                {company.agent_companies.length === 0 ? (
                                    <div className="p-4 text-center text-slate-500 dark:text-slate-400">
                                        No agent companies found
                                    </div>
                                ) : (
                                    company.agent_companies.map((agentCompany) => (
                                        <div key={agentCompany.id} className="border-t border-slate-200 dark:border-slate-700">
                                            <div
                                                className="p-4 pl-12 cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                                                onClick={() => toggleAgentCompany(agentCompany.id)}
                                            >
                                                <div className="flex items-center justify-between">
                                                    <div className="flex items-center space-x-3 flex-1">
                                                        <button className="text-indigo-600 dark:text-indigo-400">
                                                            {expandedAgentCompanies.has(agentCompany.id) ? (
                                                                <ChevronDown className="w-4 h-4" />
                                                            ) : (
                                                                <ChevronRight className="w-4 h-4" />
                                                            )}
                                                        </button>
                                                        <Store className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
                                                        <div className="flex-1">
                                                            <h4 className="font-semibold text-slate-800 dark:text-white">
                                                                {agentCompany.company_name}
                                                            </h4>
                                                            <div className="flex items-center space-x-3 text-sm text-slate-600 dark:text-slate-400 mt-1">
                                                                <span>Store: {agentCompany.store_number}</span>
                                                                {agentCompany.location && (
                                                                    <span className="flex items-center space-x-1">
                                                                        <MapPin className="w-3 h-3" />
                                                                        <span>{agentCompany.location}</span>
                                                                    </span>
                                                                )}
                                                            </div>
                                                        </div>
                                                    </div>
                                                    <span className="px-3 py-1 bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400 rounded-full text-xs font-medium">
                                                        {agentCompany.agent_count} Agents
                                                    </span>
                                                </div>
                                            </div>

                                            {/* User Agents Level */}
                                            {expandedAgentCompanies.has(agentCompany.id) && (
                                                <div className="bg-white dark:bg-slate-800">
                                                    {agentCompany.user_agents.length === 0 ? (
                                                        <div className="p-4 pl-20 text-center text-slate-500 dark:text-slate-400">
                                                            No agents found
                                                        </div>
                                                    ) : (
                                                        agentCompany.user_agents.map((agent) => (
                                                            <div
                                                                key={agent.id}
                                                                className="p-3 pl-20 border-t border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
                                                            >
                                                                <div className="flex items-center justify-between">
                                                                    <div className="flex items-center space-x-3 flex-1">
                                                                        <User className="w-4 h-4 text-slate-400" />
                                                                        <div className="flex-1">
                                                                            <p className="font-medium text-slate-800 dark:text-white">
                                                                                {agent.fullname}
                                                                            </p>
                                                                            <div className="flex items-center space-x-4 text-xs text-slate-600 dark:text-slate-400 mt-1">
                                                                                <span className="flex items-center space-x-1">
                                                                                    <Hash className="w-3 h-3" />
                                                                                    <span>{agent.idnumber}</span>
                                                                                </span>
                                                                                {agent.phone_number && (
                                                                                    <span className="flex items-center space-x-1">
                                                                                        <Phone className="w-3 h-3" />
                                                                                        <span>{agent.phone_number}</span>
                                                                                    </span>
                                                                                )}
                                                                                <span className="flex items-center space-x-1">
                                                                                    <FileText className="w-3 h-3" />
                                                                                    <span>{agent.document_count} docs</span>
                                                                                </span>
                                                                            </div>
                                                                        </div>
                                                                    </div>
                                                                    <div className="flex items-center space-x-2">
                                                                        {agent.is_authentic ? (
                                                                            <span className="flex items-center space-x-1 px-2 py-1 bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded-full text-xs">
                                                                                <Shield className="w-3 h-3" />
                                                                                <span>Verified</span>
                                                                            </span>
                                                                        ) : (
                                                                            <span className="px-2 py-1 bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400 rounded-full text-xs">
                                                                                Pending
                                                                            </span>
                                                                        )}
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        ))
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    ))
                                )}
                            </div>
                        )}
                    </div>
                ))}
            </div>

            {hierarchyData.length === 0 && (
                <div className="text-center py-12 text-slate-500 dark:text-slate-400">
                    No companies found
                </div>
            )}
        </div>
    );
}

export default CompanyHierarchy;