import { useState, useEffect, useRef } from 'react';
import { Search, MoreVertical, Edit, Plus, Download, Upload, RefreshCw, Trash2 } from 'lucide-react';
import axios from 'axios';
import * as XLSX from 'xlsx';
import config from '../../Config';
import { useToast } from './ToastProvider';
import AgentCompanyDetailsModal from './AgentCompanyDetailsModal';
import BatchUploadModal from './BatchUploadModal';

function AgentCompanyList() {
  const [agentCompanies, setAgentCompanies] = useState([]);
  const [filteredAgentCompanies, setFilteredAgentCompanies] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedAgentCompanyIds, setSelectedAgentCompanyIds] = useState([]);
  const [isAgentCompanyModalOpen, setIsAgentCompanyModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isBatchModalOpen, setIsBatchModalOpen] = useState(false);
  const [validAgentCompanies, setValidAgentCompanies] = useState([]);
  const [invalidAgentCompanies, setInvalidAgentCompanies] = useState([]);
  const [batchFile, setBatchFile] = useState(null);
  const { showToast } = useToast();
  const fileInputRef = useRef(null);

  // Fetch agent companies from API
  const fetchAgentCompanies = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${config.API_URL}/agentcompany`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setAgentCompanies(response.data);
      setFilteredAgentCompanies(response.data);
      setSelectedAgentCompanyIds([]);
      setCurrentPage(1);
      showToast('Agent companies reloaded successfully', 'success');
    } catch (error) {
      console.error('Error fetching agent companies:', error.response?.data || error.message);
      showToast('Failed to fetch agent companies', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAgentCompanies();
  }, []);

  // Handle search
  useEffect(() => {
    const filtered = agentCompanies.filter(
      (ac) =>
        ac.company_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        ac.registration_number?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        ac.till_number?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        ac.contact_phone?.toLowerCase().includes(searchTerm.toLowerCase())
    );
    setFilteredAgentCompanies(filtered);
    setCurrentPage(1);
  }, [searchTerm, agentCompanies]);

  // Pagination calculations
  const totalItems = filteredAgentCompanies.length;
  const totalPages = Math.ceil(totalItems / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const paginatedAgentCompanies = filteredAgentCompanies.slice(startIndex, endIndex);

  // Handle page change
  const handlePageChange = (page) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
      setSelectedAgentCompanyIds([]);
    }
  };

  // Handle page size change
  const handlePageSizeChange = (e) => {
    setPageSize(Number(e.target.value));
    setCurrentPage(1);
    setSelectedAgentCompanyIds([]);
  };

  // Handle checkbox selection
  const handleSelectAgentCompany = (agentCompanyId) => {
    setSelectedAgentCompanyIds((prev) =>
      prev.includes(agentCompanyId)
        ? prev.filter((id) => id !== agentCompanyId)
        : [...prev, agentCompanyId]
    );
  };

  // Handle select all checkboxes
  const handleSelectAll = () => {
    if (selectedAgentCompanyIds.length === paginatedAgentCompanies.length) {
      setSelectedAgentCompanyIds([]);
    } else {
      setSelectedAgentCompanyIds(paginatedAgentCompanies.map((ac) => ac.id));
    }
  };

  // Handle edit agent company
  const handleEditAgentCompany = () => {
    if (selectedAgentCompanyIds.length === 0) {
      showToast('Please select an agent company to edit', 'error');
      return;
    }
    if (selectedAgentCompanyIds.length > 1) {
      showToast('Please select only one agent company to edit', 'error');
      return;
    }
    setIsAgentCompanyModalOpen(true);
    setIsDropdownOpen(false);
  };

  // Handle delete agent company
  const handleDeleteAgentCompany = async () => {
    if (selectedAgentCompanyIds.length === 0) {
      showToast('Please select at least one agent company to delete', 'error');
      return;
    }
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      await Promise.all(
        selectedAgentCompanyIds.map((id) =>
          axios.delete(`${config.API_URL}/agentcompany/${id}`, {
            headers: { Authorization: `Bearer ${token}` },
          })
        )
      );
      await fetchAgentCompanies();
      showToast('Selected agent companies deleted successfully', 'success');
    } catch (error) {
      console.error('Error deleting agent companies:', error.response?.data || error.message);
      showToast('Failed to delete agent companies', 'error');
    } finally {
      setIsLoading(false);
      setIsDropdownOpen(false);
    }
  };

  // Handle create agent company
  const handleOpenCreateModal = () => {
    setSelectedAgentCompanyIds([]);
    setIsAgentCompanyModalOpen(true);
    setIsDropdownOpen(false);
  };

  // Handle download Excel template
  const handleDownloadExcelTemplate = () => {
    const headers = ['company_name', 'registration_number', 'location', 'contact_phone', 'email', 'till_number', 'company_id'];
    const sampleData = [
      ['ABC M-Pesa', 'REG12345', 'Nairobi CBD', '+254712345678', 'abc@mpesa.com', '123456', '1'],
      ['XYZ Agents', 'REG67890', 'Mombasa', '+254798765432', 'xyz@mpesa.com', '789012', '1'],
    ];

    const ws = XLSX.utils.aoa_to_sheet([headers, ...sampleData]);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Sheet1');
    XLSX.writeFile(wb, 'agent_company_batch_template.xlsx');

    showToast('Excel template downloaded successfully', 'success');
    setIsDropdownOpen(false);
  };

  // Handle batch upload preview
  const handleBatchUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const token = localStorage.getItem('token');
      const response = await axios.post(`${config.API_URL}/agentcompany/validate-batch`, formData, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data',
        },
      });

      const { validAgentCompanies, invalidAgentCompanies } = response.data;

      if (!Array.isArray(validAgentCompanies) || !Array.isArray(invalidAgentCompanies)) {
        throw new Error('Invalid response format from server');
      }

      setValidAgentCompanies(validAgentCompanies);
      setInvalidAgentCompanies(invalidAgentCompanies);
      setBatchFile(file);
      setIsBatchModalOpen(true);
    } catch (error) {
      console.error('Error validating batch:', error.response?.data || error.message);
      showToast(error.response?.data?.error || 'Failed to validate batch', 'error');
    } finally {
      setIsLoading(false);
      fileInputRef.current.value = '';
    }
  };

  // Handle confirm batch upload
  const handleConfirmUpload = async () => {
    setIsBatchModalOpen(false);
    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', batchFile);

      const token = localStorage.getItem('token');
      const res = await axios.post(`${config.API_URL}/agentcompany/batch`, formData, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data',
        },
      });

      await fetchAgentCompanies();
      showToast(res.data.message || `${res.data.createdAgentCompanies.length} agent companies created successfully`, 'success');
    } catch (error) {
      console.error('Error processing batch upload:', error.response?.data || error.message);
      showToast(error.response?.data?.error || 'Failed to process batch upload', 'error');
    } finally {
      setIsLoading(false);
      setBatchFile(null);
      setValidAgentCompanies([]);
      setInvalidAgentCompanies([]);
    }
  };

  // Handle create or update agent company
  const handleCreateOrUpdateAgentCompany = async (formData, agentCompanyId, resetForm) => {
    setIsLoading(true);
    try {
      const data = new FormData();
      for (const key in formData) {
        if (key !== 'filePreview') {
          data.append(key, formData[key]);
        }
      }

      const token = localStorage.getItem('token');
      const url = agentCompanyId ? `${config.API_URL}/agentcompany/${agentCompanyId}` : `${config.API_URL}/agentcompany`;
      const method = agentCompanyId ? 'PUT' : 'POST';

      const res = await fetch(url, {
        method,
        headers: { Authorization: `Bearer ${token}` },
        body: data,
      });

      const result = await res.json();

      if (!res.ok) {
        throw new Error(result.error || `Failed to ${agentCompanyId ? 'update' : 'create'} agent company`);
      }

      if (agentCompanyId) {
        setAgentCompanies((prev) =>
          prev.map((ac) => (ac.id === agentCompanyId ? { ...ac, ...result.agentCompany } : ac))
        );
        setFilteredAgentCompanies((prev) =>
          prev.map((ac) => (ac.id === agentCompanyId ? { ...ac, ...result.agentCompany } : ac))
        );
      } else {
        setAgentCompanies((prev) => [...prev, result.agentCompany]);
        setFilteredAgentCompanies((prev) => [...prev, result.agentCompany]);
      }

      setIsAgentCompanyModalOpen(false);
      setSelectedAgentCompanyIds([]);
      resetForm();
      showToast(`Agent company ${agentCompanyId ? 'updated' : 'created'} successfully!`, 'success');
    } catch (error) {
      console.error(`Error ${agentCompanyId ? 'updating' : 'creating'} agent company:`, error.message);
      showToast(error.message, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-lg p-6">
      {/* Action Buttons */}
      <div className="flex justify-end mb-4 space-x-4">
        <button
          onClick={fetchAgentCompanies}
          disabled={isLoading}
          className="flex items-center space-x-2 py-2 px-4 bg-green-500 text-white rounded-xl hover:bg-green-600 transition-colors disabled:bg-green-300 disabled:cursor-not-allowed"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Reload</span>
        </button>
        <div className="relative">
          <button
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className="flex items-center space-x-2 py-2 px-4 bg-blue-500 text-white rounded-xl hover:bg-blue-600 transition-colors"
          >
            <MoreVertical className="w-4 h-4" />
            <span>Actions</span>
          </button>
          {isDropdownOpen && (
            <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-slate-700 rounded-xl shadow-lg z-10">
              <button
                onClick={handleEditAgentCompany}
                disabled={selectedAgentCompanyIds.length === 0}
                className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Edit className="w-4 h-4 mr-2" />
                Edit Selected
              </button>
              <button
                onClick={handleOpenCreateModal}
                className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600"
              >
                <Plus className="w-4 h-4 mr-2" />
                Create Agent Company
              </button>
              <button
                onClick={handleDeleteAgentCompany}
                disabled={selectedAgentCompanyIds.length === 0}
                className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Delete Selected
              </button>
              <button
                onClick={handleDownloadExcelTemplate}
                className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600"
              >
                <Download className="w-4 h-4 mr-2" />
                Download Excel Template
              </button>
              <button
                onClick={() => fileInputRef.current.click()}
                className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600"
              >
                <Upload className="w-4 h-4 mr-2" />
                Upload Batch Excel
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Hidden file input */}
      <input
        type="file"
        accept=".xlsx"
        ref={fileInputRef}
        style={{ display: 'none' }}
        onChange={handleBatchUpload}
      />

      {/* Batch Upload Modal */}
      <BatchUploadModal
        isOpen={isBatchModalOpen}
        validUsers={validAgentCompanies}
        invalidUsers={invalidAgentCompanies}
        onClose={() => {
          setIsBatchModalOpen(false);
          setBatchFile(null);
          setValidAgentCompanies([]);
          setInvalidAgentCompanies([]);
        }}
        onConfirm={handleConfirmUpload}
      />

      {/* Search Control */}
      <div className="mb-6">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by name, registration, or till number"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
          />
        </div>
      </div>

      {/* Agent Companies Grid */}
      <div className="overflow-x-auto">
        <table className="w-full table-auto">
          <thead>
            <tr className="bg-slate-100 dark:bg-slate-700 text-left text-slate-600 dark:text-slate-300">
              <th className="px-4 py-3 font-semibold">
                <input
                  type="checkbox"
                  checked={selectedAgentCompanyIds.length === paginatedAgentCompanies.length && paginatedAgentCompanies.length > 0}
                  onChange={handleSelectAll}
                  className="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600"
                />
              </th>
              <th className="px-4 py-3 font-semibold">ID</th>
              <th className="px-4 py-3 font-semibold">Company Name</th>
              <th className="px-4 py-3 font-semibold">Registration Number</th>
              <th className="px-4 py-3 font-semibold">Till Number</th>
              <th className="px-4 py-3 font-semibold">Float Balance</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">Action</th>
            </tr>
          </thead>
          <tbody>
            {paginatedAgentCompanies.map((ac, index) => (
              <tr
                key={ac.id}
                className={`border-b border-slate-200 dark:border-slate-600 ${
                  index % 2 === 0 ? 'bg-white dark:bg-slate-800' : 'bg-slate-50 dark:bg-slate-700/50'
                } hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors`}
              >
                <td className="px-4 py-3">
                  <input
                    type="checkbox"
                    checked={selectedAgentCompanyIds.includes(ac.id)}
                    onChange={() => handleSelectAgentCompany(ac.id)}
                    className="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600"
                  />
                </td>
                <td className="px-4 py-3">{ac.id}</td>
                <td className="px-4 py-3">{ac.company_name}</td>
                <td className="px-4 py-3">{ac.registration_number}</td>
                <td className="px-4 py-3">{ac.till_number || 'N/A'}</td>
                <td className="px-4 py-3">{ac.float_balance}</td>
                <td className="px-4 py-3">
                  <span
                    className={`px-2 py-1 rounded-full text-xs ${
                      ac.status === 'active'
                        ? 'bg-green-100 text-green-600 dark:bg-green-900/50 dark:text-green-400'
                        : 'bg-red-100 text-red-600 dark:bg-red-900/50 dark:text-red-400'
                    }`}
                  >
                    {ac.status}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => {
                      setSelectedAgentCompanyIds([ac.id]);
                      handleEditAgentCompany();
                    }}
                    className="flex items-center space-x-1 text-blue-500 hover:text-blue-600 dark:hover:text-blue-400"
                  >
                    <Edit className="w-4 h-4" />
                    <span>Edit</span>
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      <div className="flex flex-col sm:flex-row justify-between items-center mt-4 space-y-4 sm:space-y-0">
        <div className="flex items-center space-x-2">
          <span className="text-sm text-slate-600 dark:text-slate-300">
            Showing {startIndex + 1} - {Math.min(endIndex, totalItems)} of {totalItems} agent companies
          </span>
          <select
            value={pageSize}
            onChange={handlePageSizeChange}
            className="py-1 px-2 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="5">5 per page</option>
            <option value="10">10 per page</option>
            <option value="20">20 per page</option>
            <option value="50">50 per page</option>
          </select>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => handlePageChange(1)}
            disabled={currentPage === 1}
            className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            First
          </button>
          <button
            onClick={() => handlePageChange(currentPage - 1)}
            disabled={currentPage === 1}
            className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          <span className="text-sm text-slate-600 dark:text-slate-300">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => handlePageChange(currentPage + 1)}
            disabled={currentPage === totalPages}
            className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
          <button
            onClick={() => handlePageChange(totalPages)}
            disabled={currentPage === totalPages}
            className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Last
          </button>
        </div>
      </div>

      {/* Agent Company Details Modal */}
      <AgentCompanyDetailsModal
        isOpen={isAgentCompanyModalOpen}
        onClose={() => {
          setIsAgentCompanyModalOpen(false);
          setSelectedAgentCompanyIds([]);
        }}
        onSubmit={handleCreateOrUpdateAgentCompany}
        isLoading={isLoading}
        agentCompany={selectedAgentCompanyIds.length === 1 ? agentCompanies.find((ac) => ac.id === selectedAgentCompanyIds[0]) : null}
      />
    </div>
  );
}

export default AgentCompanyList;