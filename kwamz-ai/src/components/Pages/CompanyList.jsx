import { useState, useEffect, useRef } from 'react';
import { Search, MoreVertical, Edit, Plus, Download, Upload, RefreshCw, Trash2, ChevronRight } from 'lucide-react';
import axios from 'axios';
import * as XLSX from 'xlsx';
import config from '../../Config';
import { useToast } from './ToastProvider';
import CompanyDetailsModal from './CompanyDetailsModal.jsx';
import BatchUploadModal from './BatchUploadModal';

function CompanyList() {
  const [companies, setCompanies] = useState([]);
  const [filteredCompanies, setFilteredCompanies] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCompanyIds, setSelectedCompanyIds] = useState([]);
  const [isCompanyModalOpen, setIsCompanyModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isTemplatesSubMenuOpen, setIsTemplatesSubMenuOpen] = useState(false);
  const [isBatchModalOpen, setIsBatchModalOpen] = useState(false);
  const [validCompanies, setValidCompanies] = useState([]);
  const [invalidCompanies, setInvalidCompanies] = useState([]);
  const [batchFile, setBatchFile] = useState(null);
  const { showToast } = useToast();
  const fileInputRef = useRef(null);
  const dropdownRef = useRef(null);

  // Fetch companies from API
  const fetchCompanies = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${config.API_URL}/company`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setCompanies(response.data);
      setFilteredCompanies(response.data);
      setSelectedCompanyIds([]);
      setCurrentPage(1);
      showToast('Companies reloaded successfully', 'success');
    } catch (error) {
      console.error('Error fetching companies:', error.response?.data || error.message);
      showToast('Failed to fetch companies', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCompanies();
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
        setIsTemplatesSubMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Handle search
  useEffect(() => {
    const filtered = companies.filter(
      (c) =>
        c.company_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.registration_number?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.primary_owner_name?.toLowerCase().includes(searchTerm.toLowerCase())
    );
    setFilteredCompanies(filtered);
    setCurrentPage(1);
  }, [searchTerm, companies]);

  // Pagination calculations
  const totalItems = filteredCompanies.length;
  const totalPages = Math.ceil(totalItems / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const paginatedCompanies = filteredCompanies.slice(startIndex, endIndex);

  // Handle page change
  const handlePageChange = (page) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
      setSelectedCompanyIds([]);
    }
  };

  // Handle page size change
  const handlePageSizeChange = (e) => {
    setPageSize(Number(e.target.value));
    setCurrentPage(1);
    setSelectedCompanyIds([]);
  };

  // Handle checkbox selection
  const handleSelectCompany = (companyId) => {
    setSelectedCompanyIds((prev) =>
      prev.includes(companyId)
        ? prev.filter((id) => id !== companyId)
        : [...prev, companyId]
    );
  };

  // Handle select all checkboxes
  const handleSelectAll = () => {
    if (selectedCompanyIds.length === paginatedCompanies.length) {
      setSelectedCompanyIds([]);
    } else {
      setSelectedCompanyIds(paginatedCompanies.map((c) => c.id));
    }
  };

  // Handle edit company
  const handleEditCompany = () => {
    if (selectedCompanyIds.length === 0) {
      showToast('Please select a company to edit', 'error');
      return;
    }
    if (selectedCompanyIds.length > 1) {
      showToast('Please select only one company to edit', 'error');
      return;
    }
    setIsCompanyModalOpen(true);
    setIsDropdownOpen(false);
  };

  // Handle delete company
  const handleDeleteCompany = async () => {
    if (selectedCompanyIds.length === 0) {
      showToast('Please select at least one company to delete', 'error');
      return;
    }
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      await Promise.all(
        selectedCompanyIds.map((id) =>
          axios.delete(`${config.API_URL}/company/${id}`, {
            headers: { Authorization: `Bearer ${token}` },
          })
        )
      );
      await fetchCompanies();
      showToast('Selected companies deleted successfully', 'success');
    } catch (error) {
      console.error('Error deleting companies:', error.response?.data || error.message);
      showToast('Failed to delete companies', 'error');
    } finally {
      setIsLoading(false);
      setIsDropdownOpen(false);
      setIsTemplatesSubMenuOpen(false);
    }
  };

  // Handle create company
  const handleOpenCreateModal = () => {
    setSelectedCompanyIds([]);
    setIsCompanyModalOpen(true);
    setIsDropdownOpen(false);
  };

  // Handle download Excel template
  const handleDownloadExcelTemplate = () => {
    const headers = ['company_name', 'registration_number', 'address', 'primary_owner_name', 'primary_owner_id'];
    const sampleData = [
      ['Global M-Pesa Ltd', 'REG12345', 'Nairobi CBD', 'John Doe', 'ID123456'],
      ['Regional Agents', 'REG67890', 'Mombasa', 'Jane Smith', 'ID789012'],
    ];

    const ws = XLSX.utils.aoa_to_sheet([headers, ...sampleData]);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Sheet1');
    XLSX.writeFile(wb, 'company_batch_template.xlsx');

    showToast('Excel template downloaded successfully', 'success');
    setIsDropdownOpen(false);
    setIsTemplatesSubMenuOpen(false);
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
      const response = await axios.post(`${config.API_URL}/company/validate-batch`, formData, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data',
        },
      });

      const { validCompanies, invalidCompanies } = response.data;

      if (!Array.isArray(validCompanies) || !Array.isArray(invalidCompanies)) {
        throw new Error('Invalid response format from server');
      }

      setValidCompanies(validCompanies);
      setInvalidCompanies(invalidCompanies);
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
      const res = await axios.post(`${config.API_URL}/company/batch`, formData, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data',
        },
      });

      await fetchCompanies();
      showToast(res.data.message || `${res.data.createdCompanies.length} companies created successfully`, 'success');
    } catch (error) {
      console.error('Error processing batch upload:', error.response?.data || error.message);
      showToast(error.response?.data?.error || 'Failed to process batch upload', 'error');
    } finally {
      setIsLoading(false);
      setBatchFile(null);
      setValidCompanies([]);
      setInvalidCompanies([]);
    }
  };

  // Handle create or update company
  const handleCreateOrUpdateCompany = async (formData, companyId, resetForm) => {
    setIsLoading(true);
    try {
      const data = new FormData();

      // Append simple fields
      data.append('company_name', formData.company_name);
      data.append('company_number', formData.company_number);
      data.append('address', formData.address);
      data.append('primary_owner_name', formData.primary_owner_name);
      data.append('primary_owner_email', formData.primary_owner_email);
      data.append('primary_owner_shares', formData.primary_owner_shares.toString());

      if (formData.registration_date) {
        data.append('registration_date', formData.registration_date);
      }

      // Append arrays as JSON strings
      if (formData.secondary_shareholders && formData.secondary_shareholders.length > 0) {
        data.append('secondary_shareholders', JSON.stringify(formData.secondary_shareholders));
      }

      if (formData.directors && formData.directors.length > 0) {
        data.append('directors', JSON.stringify(formData.directors));
      }

      // Append file if exists
      if (formData.cr12_file) {
        data.append('cr12_file', formData.cr12_file);
      }

      const token = localStorage.getItem('token');
      const url = companyId ? `${config.API_URL}/company/${companyId}` : `${config.API_URL}/company`;
      const method = companyId ? 'PUT' : 'POST';

      const res = await fetch(url, {
        method,
        headers: { Authorization: `Bearer ${token}` },
        body: data,
      });

      const result = await res.json();

      if (!res.ok) {
        throw new Error(result.error || `Failed to ${companyId ? 'update' : 'create'} company`);
      }

      if (companyId) {
        await fetchCompanies();
      } else {
        setCompanies((prev) => [...prev, result.company]);
        setFilteredCompanies((prev) => [...prev, result.company]);
      }

      setIsCompanyModalOpen(false);
      setSelectedCompanyIds([]);
      resetForm();
      showToast(`Company ${companyId ? 'updated' : 'created'} successfully!`, 'success');
    } catch (error) {
      console.error(`Error ${companyId ? 'updating' : 'creating'} company:`, error.message);
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
          onClick={fetchCompanies}
          disabled={isLoading}
          className="flex items-center space-x-2 py-2 px-4 bg-green-500 text-white rounded-xl hover:bg-green-600 transition-colors disabled:bg-green-300 disabled:cursor-not-allowed"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Reload</span>
        </button>
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className="flex items-center space-x-2 py-2 px-4 bg-blue-500 text-white rounded-xl hover:bg-blue-600 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-slate-800"
            aria-haspopup="true"
            aria-expanded={isDropdownOpen}
          >
            <MoreVertical className="w-4 h-4" />
            <span>Actions</span>
          </button>
          {isDropdownOpen && (
            <div
              className="absolute right-0 mt-2 w-72 bg-white dark:bg-slate-700 rounded-xl shadow-lg z-10 border border-slate-200 dark:border-slate-600 overflow-visible transition-all duration-200"
              role="menu"
            >
              {/* Main Actions */}
              <div className="py-2">
                <button
                  onClick={handleEditCompany}
                  disabled={selectedCompanyIds.length === 0 || selectedCompanyIds.length > 1}
                  className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  role="menuitem"
                >
                  <Edit className="w-4 h-4 mr-3" />
                  Edit Selected
                </button>
                <button
                  onClick={handleOpenCreateModal}
                  className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 transition-colors"
                  role="menuitem"
                >
                  <Plus className="w-4 h-4 mr-3" />
                  Create Company
                </button>
                <button
                  onClick={handleDeleteCompany}
                  disabled={selectedCompanyIds.length === 0}
                  className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  role="menuitem"
                >
                  <Trash2 className="w-4 h-4 mr-3" />
                  Delete Selected
                </button>
              </div>

              {/* Templates submenu */}
              <div className="relative">
                <button
                  onClick={() => setIsTemplatesSubMenuOpen(!isTemplatesSubMenuOpen)}
                  onMouseEnter={() => setIsTemplatesSubMenuOpen(true)}
                  className="w-full flex items-center justify-between px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 transition-colors"
                >
                  <div className="flex items-center">
                    <Download className="w-4 h-4 mr-3" />
                    Templates
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                </button>

                {isTemplatesSubMenuOpen && (
                  <div
                    className="absolute right-full top-0 mr-1 w-56 bg-white dark:bg-slate-700 rounded-xl shadow-lg border border-slate-200 dark:border-slate-600 z-[60]"
                    onMouseEnter={() => setIsTemplatesSubMenuOpen(true)}
                    onMouseLeave={() => setIsTemplatesSubMenuOpen(false)}
                  >
                    <button
                      onClick={handleDownloadExcelTemplate}
                      className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 transition-colors rounded-t-xl"
                    >
                      <Download className="w-4 h-4 mr-3" />
                      Download Template
                    </button>
                    <button
                      onClick={() => {
                        fileInputRef.current.click();
                        setIsDropdownOpen(false);
                        setIsTemplatesSubMenuOpen(false);
                      }}
                      className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 transition-colors rounded-b-xl"
                    >
                      <Upload className="w-4 h-4 mr-3" />
                      Upload Batch
                    </button>
                  </div>
                )}
              </div>
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
        validUsers={validCompanies}
        invalidUsers={invalidCompanies}
        onClose={() => {
          setIsBatchModalOpen(false);
          setBatchFile(null);
          setValidCompanies([]);
          setInvalidCompanies([]);
        }}
        onConfirm={handleConfirmUpload}
      />

      {/* Search Control */}
      <div className="mb-6">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by name, registration, or owner"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
          />
        </div>
      </div>

      {/* Companies Grid */}
      <div className="overflow-x-auto">
        <table className="w-full table-auto">
          <thead>
            <tr className="bg-slate-100 dark:bg-slate-700 text-left text-slate-600 dark:text-slate-300">
              <th className="px-4 py-3 font-semibold">
                <input
                  type="checkbox"
                  checked={selectedCompanyIds.length === paginatedCompanies.length && paginatedCompanies.length > 0}
                  onChange={handleSelectAll}
                  className="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600"
                />
              </th>
              <th className="px-4 py-3 font-semibold">ID</th>
              <th className="px-4 py-3 font-semibold">Company Name</th>
              <th className="px-4 py-3 font-semibold">Registration Number</th>
              <th className="px-4 py-3 font-semibold">Primary Owner</th>
            </tr>
          </thead>
          <tbody>
            {paginatedCompanies.map((c, index) => (
              <tr
                key={c.id}
                className={`border-b border-slate-200 dark:border-slate-600 ${index % 2 === 0 ? 'bg-white dark:bg-slate-800' : 'bg-slate-50 dark:bg-slate-700/50'
                  } hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors`}
              >
                <td className="px-4 py-3">
                  <input
                    type="checkbox"
                    checked={selectedCompanyIds.includes(c.id)}
                    onChange={() => handleSelectCompany(c.id)}
                    className="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600"
                  />
                </td>
                <td className="px-4 py-3">{c.id}</td>
                <td className="px-4 py-3">{c.company_name}</td>
                <td className="px-4 py-3">{c.company_number}</td>
                <td className="px-4 py-3">{c.primary_owner_name}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      <div className="flex flex-col sm:flex-row justify-between items-center mt-4 space-y-4 sm:space-y-0">
        <div className="flex items-center space-x-2">
          <span className="text-sm text-slate-600 dark:text-slate-300">
            Showing {startIndex + 1} - {Math.min(endIndex, totalItems)} of {totalItems} companies
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

      {/* Company Details Modal */}
      <CompanyDetailsModal
        isOpen={isCompanyModalOpen}
        onClose={() => {
          setIsCompanyModalOpen(false);
          setSelectedCompanyIds([]);
        }}
        onSubmit={handleCreateOrUpdateCompany}
        isLoading={isLoading}
        company={selectedCompanyIds.length === 1 ? companies.find((c) => c.id === selectedCompanyIds[0]) : null}
      />
    </div>
  );
}

export default CompanyList;