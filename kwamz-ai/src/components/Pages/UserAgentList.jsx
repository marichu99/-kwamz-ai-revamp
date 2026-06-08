import { useState, useEffect, useRef, useMemo } from 'react';
import { Search, Filter, MoreVertical, Binoculars, Edit, Plus, Download, Upload, RefreshCw, ChevronRight, ChevronDown, Database, Building2, Users, ChevronsUpDown, Trash2, AlertTriangle, X, Loader2 } from 'lucide-react';
import axios from 'axios';
import * as XLSX from 'xlsx';
import config from '../../Config';
import { useToast } from './ToastProvider';
import UserDetailsModal from './UserDetailsModal';
import KYCDocumentUploadPage from './KYCDocumentUploadPage';
import BatchUploadModal from './BatchUploadModal';

function UserAgentList() {
  const [users, setUsers] = useState([]);
  const [filteredUsers, setFilteredUsers] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filter, setFilter] = useState('all');
  const [selectedUserIds, setSelectedUserIds] = useState([]);
  const [isUserModalOpen, setIsUserModalOpen] = useState(false);
  const [isKYCModalOpen, setIsKYCModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isTemplatesSubMenuOpen, setIsTemplatesSubMenuOpen] = useState(false);
  const [isBatchModalOpen, setIsBatchModalOpen] = useState(false);
  const [validUsers, setValidUsers] = useState([]);
  const [invalidUsers, setInvalidUsers] = useState([]);
  const [batchFile, setBatchFile] = useState(null);
  const [loadingDownload, setLoadingDownload] = useState(false);
  const [expandedCompanies, setExpandedCompanies] = useState(() => new Set());
  const [expandedTills, setExpandedTills] = useState(() => new Set());
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const { showToast } = useToast();
  const fileInputRef = useRef(null);
  const dropdownRef = useRef(null);

  // Fetch users from API
  const fetchUsers = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${config.API_URL}/useragent`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      setUsers(response.data);
      setFilteredUsers(response.data);
      setSelectedUserIds([]);
      setCurrentPage(1);
      showToast('Users reloaded successfully', 'success');
    } catch (error) {
      console.error('Error fetching users:', error.response?.data || error.message);
      showToast('Failed to fetch users', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
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

  // Handle search and filter
  useEffect(() => {
    let filtered = users;

    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(
        (u) =>
          u.firstname?.toLowerCase().includes(term) ||
          u.lastname?.toLowerCase().includes(term) ||
          u.idnumber?.toLowerCase().includes(term) ||
          u.phone_number?.toLowerCase().includes(term) ||
          u.primary_company?.short_code?.toLowerCase().includes(term) ||
          u.primary_company?.company_name?.toLowerCase().includes(term)
      );
    }

    if (filter === 'authentic') {
      filtered = filtered.filter((u) => u.is_authentic);
    } else if (filter === 'not-authentic') {
      filtered = filtered.filter((u) => !u.is_authentic);
    }

    setFilteredUsers(filtered);
    setCurrentPage(1);
  }, [searchTerm, filter, users]);

  const totalItems = filteredUsers.length;
  const totalPages = Math.ceil(totalItems / pageSize) || 1;
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;

  const handlePageChange = (page) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
      setSelectedUserIds([]);
    }
  };

  const handlePageSizeChange = (e) => {
    setPageSize(Number(e.target.value));
    setCurrentPage(1);
    setSelectedUserIds([]);
  };

  // Build two-level grouped structure from the current page slice
  const groupedData = useMemo(() => {
    const pagedUsers = filteredUsers.slice(startIndex, endIndex);
    const byCompany = {};
    pagedUsers.forEach(user => {
      const pc = user.primary_company;
      const companyKey = pc?.top_organization ||
        (pc?.company_name ? pc.company_name.split(' ').slice(0, 3).join(' ') : 'Unknown Company');
      const tillKey = pc ? `${pc.company_name}||${pc.short_code || ''}` : '__no_till__';

      if (!byCompany[companyKey]) {
        byCompany[companyKey] = { tills: {}, userCount: 0, displayName: pc?.top_organization_name || null };
      }
      byCompany[companyKey].userCount++;

      if (!byCompany[companyKey].tills[tillKey]) {
        byCompany[companyKey].tills[tillKey] = {
          till_key: tillKey,
          till_name: pc?.company_name || 'No Till Assigned',
          short_code: pc?.short_code || null,
          is_scraped: pc?.is_scraped ?? false,
          users: []
        };
      }
      byCompany[companyKey].tills[tillKey].users.push(user);
    });

    return Object.entries(byCompany)
      .map(([companyName, data]) => ({
        company_key: companyName,
        company_name: companyName,
        display_name: data.displayName,
        tills: Object.values(data.tills),
        user_count: data.userCount
      }))
      .sort((a, b) => a.company_name.localeCompare(b.company_name));
  }, [filteredUsers, startIndex, endIndex]);

  // Auto-expand all groups whenever the page's data changes
  useEffect(() => {
    setExpandedCompanies(new Set(groupedData.map(g => g.company_key)));
    setExpandedTills(new Set(groupedData.flatMap(g => g.tills.map(t => t.till_key))));
  }, [groupedData]);

  const toggleCompany = (key) => {
    setExpandedCompanies(prev => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  };

  const toggleTill = (key) => {
    setExpandedTills(prev => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  };

  const toggleExpandAll = () => {
    const allCompanyKeys = groupedData.map(g => g.company_key);
    const allTillKeys = groupedData.flatMap(g => g.tills.map(t => t.till_key));
    if (expandedCompanies.size === groupedData.length) {
      setExpandedCompanies(new Set());
      setExpandedTills(new Set());
    } else {
      setExpandedCompanies(new Set(allCompanyKeys));
      setExpandedTills(new Set(allTillKeys));
    }
  };

  // Handle checkbox selection
  const handleSelectUser = (userId) => {
    setSelectedUserIds((prev) =>
      prev.includes(userId)
        ? prev.filter((id) => id !== userId)
        : [...prev, userId]
    );
  };

  // Handle select all checkboxes
  const handleSelectAll = () => {
    if (selectedUserIds.length === filteredUsers.length) {
      setSelectedUserIds([]);
    } else {
      setSelectedUserIds(filteredUsers.map((user) => user.id));
    }
  };

  // Handle edit user
  const handleEditUser = () => {
    if (selectedUserIds.length === 0) {
      showToast('Please select a user to edit', 'error');
      return;
    }
    if (selectedUserIds.length > 1) {
      showToast('Please select only one user to edit', 'error');
      return;
    }
    setIsUserModalOpen(true);
    setIsDropdownOpen(false);
  };

  const handleDownloadAgentDocs = async () => {
    try {
      const agentId = selectedUserIds[0];
      if (!agentId) {
        showToast("Kindly select the record first", "error");
        return;
      }
      setLoadingDownload(true);

      const downloadResponse = await fetch(
        `${config.API_URL}/document/download-all/${agentId}`
      );

      // Check content type
      const contentType = downloadResponse.headers.get("content-type");

      if (!downloadResponse.ok) {
        setLoadingDownload(false);
        // Server returned an error status
        const errorText = await downloadResponse.text();
        let errorJson;
        try {
          errorJson = JSON.parse(errorText);
        } catch {
          errorJson = { error: errorText };
        }
        showToast(errorJson.error || "Download failed", "error");
        return;
      }

      if (contentType && contentType.includes("application/json")) {
        setLoadingDownload(false);
        // Response is JSON (error message)
        const responseJson = await downloadResponse.json();
        showToast(responseJson.error || "Download failed", "error");
        return;
      }

      // Otherwise, assume it's a binary file (ZIP)
      const blob = await downloadResponse.blob();
      const url = window.URL.createObjectURL(blob);

      const link = document.createElement("a");
      link.href = url;
      link.download = `${agentId}.zip`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      setLoadingDownload(false);

      showToast(`Downloaded ${agentId}.zip`, "success");
    } catch (err) {
      setLoadingDownload(false);
      console.error("Download error:", err);
      showToast("Unexpected error occurred", "error");
    }
  };


  // Handle KYC authentication
  const handlePerformKYC = () => {
    if (selectedUserIds.length === 0) {
      showToast('Please select a user for KYC authentication', 'error');
      return;
    }
    if (selectedUserIds.length > 1) {
      showToast('Please select only one user for KYC authentication', 'error');
      return;
    }
    setIsKYCModalOpen(true);
    setIsDropdownOpen(false);
  };

  // Handle create user
  const handleOpenCreateModal = () => {
    setSelectedUserIds([]);
    setIsUserModalOpen(true);
    setIsDropdownOpen(false);
  };

  // Handle download Excel template
  const handleDownloadExcelTemplate = () => {
    const headers = ['firstname', 'lastname', 'idnumber', 'phone_number', 'store_number'];
    const sampleData = [
      ['John', 'Doe', '123456789', '1234567890', 'agent001'],
      ['Jane', 'Smith', '987654321', '0987654321', 'agent001']
    ];

    const ws = XLSX.utils.aoa_to_sheet([headers, ...sampleData]);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Sheet1');
    XLSX.writeFile(wb, 'user_batch_template.xlsx');

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
      const response = await axios.post(`${config.API_URL}/useragent/validate-batch`, formData, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data',
        },
      });

      const { validUsers, invalidUsers } = response.data;

      if (!Array.isArray(validUsers) || !Array.isArray(invalidUsers)) {
        throw new Error('Invalid response format from server');
      }

      setValidUsers(validUsers);
      setInvalidUsers(invalidUsers);
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
      const res = await axios.post(`${config.API_URL}/useragent/batch`, formData, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data',
        },
      });

      await fetchUsers();
      showToast(res.data.message || `${res.data.createdUsers.length} users created successfully from batch upload`, 'success');
    } catch (error) {
      console.error('Error processing batch upload:', error.response?.data || error.message);
      showToast(error.response?.data?.error || 'Failed to process batch upload', 'error');
    } finally {
      setIsLoading(false);
      setBatchFile(null);
      setValidUsers([]);
      setInvalidUsers([]);
    }
  };

  const handleCreateOrUpdateUser = async (formData, userId) => {
    setIsLoading(true);
    try {

      const token = localStorage.getItem('token');
      const url = userId ? `${config.API_URL}/useragent/${userId}` : `${config.API_URL}/useragent`;
      const method = userId ? 'PUT' : 'POST';

      const res = await fetch(url, {
        method,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const result = await res.json();

      if (!res.ok) {
        throw new Error(result.error || `Failed to ${userId ? 'update' : 'create'} user`);
      }

      if (userId) {
        setUsers((prev) =>
          prev.map((u) => (u.id === userId ? { ...u, ...result.user } : u))
        );
        setFilteredUsers((prev) =>
          prev.map((u) => (u.id === userId ? { ...u, ...result.user } : u))
        );
      } else {
        setUsers((prev) => [...prev, result.user]);
        setFilteredUsers((prev) => [...prev, result.user]);
      }

      setIsUserModalOpen(false);
      setSelectedUserIds([]);
      showToast(`User ${userId ? 'updated' : 'created'} successfully!`, 'success');
    } catch (error) {
      console.error(`Error ${userId ? 'updating' : 'creating'} user:`, error.message);
      showToast(error.message, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirmDelete = async () => {
    setIsDeleting(true);
    try {
      const token = localStorage.getItem('token');
      await Promise.all(
        selectedUserIds.map((id) =>
          axios.delete(`${config.API_URL}/useragent/${id}`, {
            headers: { Authorization: `Bearer ${token}` },
          })
        )
      );
      showToast(`Deleted ${selectedUserIds.length} agent${selectedUserIds.length !== 1 ? 's' : ''}`, 'success');
      setDeleteConfirm(false);
      setSelectedUserIds([]);
      fetchUsers();
    } catch (error) {
      showToast(error.response?.data?.error || 'Failed to delete agent(s)', 'error');
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-lg p-3 sm:p-4 md:p-6">
      <div className="sticky top-0 z-20 bg-white dark:bg-slate-800">
      {/* Action Buttons */}
      <div className="flex flex-wrap justify-between mb-4 gap-2 sm:gap-4">
        <button
          onClick={toggleExpandAll}
          disabled={groupedData.length === 0}
          className="flex items-center space-x-2 py-2 px-4 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ChevronsUpDown className="w-4 h-4" />
          <span>{expandedCompanies.size === groupedData.length && groupedData.length > 0 ? 'Collapse All' : 'Expand All'}</span>
        </button>
        <div className="flex gap-2 sm:gap-4">
        <button
          onClick={fetchUsers}
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
                  onClick={handlePerformKYC}
                  disabled={selectedUserIds.length === 0}
                  className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  role="menuitem"
                >
                  <Binoculars className="w-4 h-4 mr-3" />
                  KYC Authentication
                </button>
                <button
                  onClick={handleEditUser}
                  disabled={selectedUserIds.length === 0}
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
                  Create User
                </button>
                <button
                  onClick={() => { handleDownloadAgentDocs(); setIsDropdownOpen(false); }}
                  disabled={selectedUserIds.length === 0}
                  className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  role="menuitem"
                >
                  <Download className="w-4 h-4 mr-3" />
                  Download Documents
                </button>
                <button
                  onClick={() => { setDeleteConfirm(true); setIsDropdownOpen(false); }}
                  disabled={selectedUserIds.length === 0}
                  className="w-full flex items-center px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
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
        validItems={validUsers}
        invalidItems={invalidUsers}
        onClose={() => {
          setIsBatchModalOpen(false);
          setBatchFile(null);
          setValidUsers([]);
          setInvalidUsers([]);
        }}
        onConfirm={handleConfirmUpload}
        type="users"
      />

      {/* Search and Filter Controls */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by name, ID, or phone"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
          />
        </div>
        <div className="relative">
          <Filter className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="pl-10 pr-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
          >
            <option value="all">All Users</option>
            <option value="authentic">Authentic</option>
            <option value="not-authentic">Not Authentic</option>
          </select>
        </div>
      </div>
      </div>

      {loadingDownload && (
        <div className="fixed inset-0 bg-gradient-to-br from-black/60 via-black/50 to-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white backdrop-blur-lg rounded-2xl shadow-2xl border border-white/20 p-6 sm:p-8 w-full max-w-[90vw] sm:max-w-2xl transform transition-all duration-300 scale-100 max-h-[90vh] overflow-y-auto">
            <div className="loader mb-3"></div>
            <p className="text-gray-700 font-medium">Preparing your download...</p>
          </div>
        </div>
      )}

      {/* Simple CSS loader */}
      <style>{`
        .loader {
          border: 4px solid #f3f3f3;
          border-top: 4px solid #3498db;
          border-radius: 50%;
          width: 40px;
          height: 40px;
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>

      {/* Grouped Users Grid */}
      <div className="text-sm text-slate-500 dark:text-slate-400 mb-3 flex items-center gap-2">
        <Users className="w-4 h-4" />
        <span>{totalItems} agent{totalItems !== 1 ? 's' : ''} across {groupedData.length} compan{groupedData.length !== 1 ? 'ies' : 'y'}</span>
        <label className="ml-auto flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={selectedUserIds.length === filteredUsers.length && filteredUsers.length > 0}
            onChange={handleSelectAll}
            className="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600"
          />
          <span className="text-xs">Select all</span>
        </label>
      </div>

      {groupedData.length === 0 ? (
        <div className="text-center py-12">
          <Users className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
          <p className="text-slate-500 dark:text-slate-400">No agents found.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {groupedData.map(company => (
            <div key={company.company_key} className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
              {/* Company header */}
              <button
                onClick={() => toggleCompany(company.company_key)}
                className="w-full flex items-center justify-between px-4 py-3 bg-slate-700 dark:bg-slate-900 text-white hover:bg-slate-600 dark:hover:bg-slate-800 transition-colors"
              >
                <div className="flex items-center gap-3">
                  {expandedCompanies.has(company.company_key)
                    ? <ChevronDown className="w-4 h-4 text-slate-300" />
                    : <ChevronRight className="w-4 h-4 text-slate-300" />}
                  <Building2 className="w-4 h-4 text-blue-400" />
                  <span className="font-semibold text-sm">{company.company_name}</span>
                  {company.display_name && company.display_name !== company.company_name && (
                    <span className="text-xs text-slate-300 font-normal">· {company.display_name}</span>
                  )}
                </div>
                <div className="flex items-center gap-2 text-xs text-slate-300">
                  <span>{company.tills.length} till{company.tills.length !== 1 ? 's' : ''}</span>
                  <span className="bg-blue-500/30 text-blue-200 px-2 py-0.5 rounded-full">
                    {company.user_count} agent{company.user_count !== 1 ? 's' : ''}
                  </span>
                </div>
              </button>

              {expandedCompanies.has(company.company_key) && (
                <div className="divide-y divide-slate-100 dark:divide-slate-700">
                  {company.tills.map(till => (
                    <div key={till.till_key}>
                      {/* Till header */}
                      <button
                        onClick={() => toggleTill(till.till_key)}
                        className="w-full flex items-center justify-between px-6 py-2.5 bg-slate-100 dark:bg-slate-700/60 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          {expandedTills.has(till.till_key)
                            ? <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
                            : <ChevronRight className="w-3.5 h-3.5 text-slate-500" />}
                          <Database className={`w-3.5 h-3.5 ${till.is_scraped ? 'text-green-500' : 'text-amber-500'}`} />
                          <span className="text-sm font-medium text-slate-700 dark:text-slate-200">{till.till_name}</span>
                          {till.short_code && (
                            <span className="text-xs text-slate-400 dark:text-slate-500">[{till.short_code}]</span>
                          )}
                          <span className={`text-xs ${till.is_scraped ? 'text-green-600 dark:text-green-400' : 'text-amber-500 dark:text-amber-400'}`}>
                            {till.is_scraped ? '· Scraped' : '· Not scraped'}
                          </span>
                        </div>
                        <span className="text-xs text-slate-500 dark:text-slate-400 bg-slate-200 dark:bg-slate-600 px-2 py-0.5 rounded-full">
                          {till.users.length} agent{till.users.length !== 1 ? 's' : ''}
                        </span>
                      </button>

                      {expandedTills.has(till.till_key) && (
                        <div className="overflow-x-auto">
                          <table className="w-full table-auto">
                            <thead>
                              <tr className="bg-slate-50 dark:bg-slate-800 text-left text-slate-500 dark:text-slate-400 text-xs border-b border-slate-200 dark:border-slate-700">
                                <th className="px-4 py-2 font-medium">
                                  <input
                                    type="checkbox"
                                    checked={till.users.every(u => selectedUserIds.includes(u.id))}
                                    onChange={() => {
                                      const ids = till.users.map(u => u.id);
                                      const allSelected = ids.every(id => selectedUserIds.includes(id));
                                      setSelectedUserIds(prev =>
                                        allSelected
                                          ? prev.filter(id => !ids.includes(id))
                                          : [...new Set([...prev, ...ids])]
                                      );
                                    }}
                                    className="w-3.5 h-3.5 text-blue-600 border-slate-300 rounded focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600"
                                  />
                                </th>
                                <th className="px-4 py-2 font-medium">ID</th>
                                <th className="px-4 py-2 font-medium">First Name</th>
                                <th className="px-4 py-2 font-medium">Last Name</th>
                                <th className="px-4 py-2 font-medium">ID Number</th>
                                <th className="px-4 py-2 font-medium">Phone Number</th>
                                <th className="px-4 py-2 font-medium">Role</th>
                                <th className="px-4 py-2 font-medium">Authentic</th>
                              </tr>
                            </thead>
                            <tbody>
                              {till.users.map((user, idx) => (
                                <tr
                                  key={user.id}
                                  className={`border-b border-slate-100 dark:border-slate-700/50 ${idx % 2 === 0 ? 'bg-white dark:bg-slate-800' : 'bg-slate-50/50 dark:bg-slate-800/50'} hover:bg-blue-50 dark:hover:bg-slate-700 transition-colors`}
                                >
                                  <td className="px-4 py-2.5">
                                    <input
                                      type="checkbox"
                                      checked={selectedUserIds.includes(user.id)}
                                      onChange={() => handleSelectUser(user.id)}
                                      className="w-3.5 h-3.5 text-blue-600 border-slate-300 rounded focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600"
                                    />
                                  </td>
                                  <td className="px-4 py-2.5 text-sm text-slate-600 dark:text-slate-400">{user.id}</td>
                                  <td className="px-4 py-2.5 text-sm font-medium text-slate-800 dark:text-slate-200">{user.firstname}</td>
                                  <td className="px-4 py-2.5 text-sm text-slate-800 dark:text-slate-200">{user.lastname}</td>
                                  <td className="px-4 py-2.5 text-sm text-slate-600 dark:text-slate-400">{user.idnumber}</td>
                                  <td className="px-4 py-2.5 text-sm text-slate-600 dark:text-slate-400">{user.phone_number || 'N/A'}</td>
                                  <td className="px-4 py-2.5">
                                    {user.operator_role ? (
                                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap
                                        ${user.operator_role === 'Agent Primary Till Operator'
                                          ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300'
                                          : 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'}`}>
                                        {user.operator_role === 'Agent Primary Till Operator' ? 'Primary Operator' : 'Till Operator'}
                                      </span>
                                    ) : (
                                      <span className="text-xs text-slate-400">—</span>
                                    )}
                                  </td>
                                  <td className="px-4 py-2.5">
                                    <span className={`px-2 py-0.5 rounded-full text-xs ${user.is_authentic ? 'bg-green-100 text-green-600 dark:bg-green-900/50 dark:text-green-400' : 'bg-red-100 text-red-600 dark:bg-red-900/50 dark:text-red-400'}`}>
                                      {user.is_authentic ? 'Yes' : 'No'}
                                    </span>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Pagination Controls */}
      <div className="flex flex-col sm:flex-row justify-between items-center mt-4 gap-3">
        <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
          <span>Showing {Math.min(startIndex + 1, totalItems)}–{Math.min(endIndex, totalItems)} of {totalItems} agents</span>
          <select
            value={pageSize}
            onChange={handlePageSizeChange}
            className="py-1 px-2 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="10">10 per page</option>
            <option value="20">20 per page</option>
            <option value="50">50 per page</option>
            <option value="100">100 per page</option>
          </select>
          {selectedUserIds.length > 0 && (
            <span className="text-blue-600 dark:text-blue-400 font-medium">{selectedUserIds.length} selected</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button onClick={() => handlePageChange(1)} disabled={currentPage === 1} className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-sm">First</button>
          <button onClick={() => handlePageChange(currentPage - 1)} disabled={currentPage === 1} className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-sm">Previous</button>
          <span className="text-sm text-slate-600 dark:text-slate-300 px-2">Page {currentPage} of {totalPages}</span>
          <button onClick={() => handlePageChange(currentPage + 1)} disabled={currentPage === totalPages} className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-sm">Next</button>
          <button onClick={() => handlePageChange(totalPages)} disabled={currentPage === totalPages} className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-sm">Last</button>
        </div>
      </div>

      {/* User Details Modal */}
      <UserDetailsModal
        isOpen={isUserModalOpen}
        onClose={() => {
          setIsUserModalOpen(false);
          setSelectedUserIds([]);
        }}
        onSubmit={handleCreateOrUpdateUser}
        isLoading={isLoading}
        user={selectedUserIds.length === 1 ? users.find((user) => user.id === selectedUserIds[0]) : null}
      />

      {/* KYC Document Upload Modal */}
      <KYCDocumentUploadPage
        isOpen={isKYCModalOpen}
        onClose={() => {
          setIsKYCModalOpen(false);
          setSelectedUserIds([]);
        }}
        user={selectedUserIds.length === 1 ? users.find((user) => user.id === selectedUserIds[0]) : null}
        onSubmitSuccess={() => {
          fetchUsers();
          setIsKYCModalOpen(false);
          setSelectedUserIds([]);
        }}
      />

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-md">
            <div className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
                  <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-slate-800 dark:text-white">Delete Agent{selectedUserIds.length !== 1 ? 's' : ''}</h3>
                  <p className="text-sm text-slate-500 dark:text-slate-400">{selectedUserIds.length} agent{selectedUserIds.length !== 1 ? 's' : ''} selected</p>
                </div>
                <button onClick={() => setDeleteConfirm(false)} className="ml-auto p-1 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg">
                  <X className="w-4 h-4 text-slate-400" />
                </button>
              </div>
              <p className="text-sm text-slate-600 dark:text-slate-400 mb-6">
                This will permanently delete <span className="font-semibold text-red-600">{selectedUserIds.length} agent{selectedUserIds.length !== 1 ? 's' : ''}</span> and all associated data. This action cannot be undone.
              </p>
              <div className="flex items-center justify-end gap-3">
                <button
                  onClick={() => setDeleteConfirm(false)}
                  disabled={isDeleting}
                  className="px-4 py-2 text-sm text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmDelete}
                  disabled={isDeleting}
                  className="px-4 py-2 text-sm text-white bg-red-500 rounded-xl hover:bg-red-600 transition-colors flex items-center gap-2 disabled:bg-red-300"
                >
                  {isDeleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                  {isDeleting ? 'Deleting...' : `Delete ${selectedUserIds.length} Agent${selectedUserIds.length !== 1 ? 's' : ''}`}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default UserAgentList;