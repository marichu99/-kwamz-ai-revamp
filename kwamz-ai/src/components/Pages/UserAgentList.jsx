import { useState, useEffect, useRef } from 'react';
import { Search, Filter, MoreVertical, Binoculars, Edit, Plus, Download, Upload, RefreshCw, ChevronRight } from 'lucide-react';
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
      filtered = filtered.filter(
        (u) =>
          u.firstname?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          u.lastname?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          u.idnumber?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          u.phone_number?.toLowerCase().includes(searchTerm.toLowerCase())
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

  // Pagination calculations
  const totalItems = filteredUsers.length;
  const totalPages = Math.ceil(totalItems / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const paginatedUsers = filteredUsers.slice(startIndex, endIndex);

  // Handle page change
  const handlePageChange = (page) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
      setSelectedUserIds([]);
    }
  };

  // Handle page size change
  const handlePageSizeChange = (e) => {
    setPageSize(Number(e.target.value));
    setCurrentPage(1);
    setSelectedUserIds([]);
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
    if (selectedUserIds.length === paginatedUsers.length) {
      setSelectedUserIds([]);
    } else {
      setSelectedUserIds(paginatedUsers.map((user) => user.id));
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

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-lg p-3 sm:p-4 md:p-6">
      {/* Action Buttons */}
      <div className="flex flex-wrap justify-end mb-4 gap-2 sm:gap-4">
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

      {/* Users Grid */}
      <div className="overflow-x-auto">
        <table className="w-full table-auto">
          <thead>
            <tr className="bg-slate-100 dark:bg-slate-700 text-left text-slate-600 dark:text-slate-300">
              <th className="px-4 py-3 font-semibold">
                <input
                  type="checkbox"
                  checked={selectedUserIds.length === paginatedUsers.length && paginatedUsers.length > 0}
                  onChange={handleSelectAll}
                  className="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600"
                />
              </th>
              <th className="px-4 py-3 font-semibold">ID</th>
              <th className="px-4 py-3 font-semibold">First Name</th>
              <th className="px-4 py-3 font-semibold">Last Name</th>
              <th className="px-4 py-3 font-semibold">ID Number</th>
              <th className="px-4 py-3 font-semibold">Phone Number</th>
              <th className="px-4 py-3 font-semibold">Authentic</th>
              <th className="px-4 py-3 font-semibold">Action</th>
            </tr>
          </thead>
          <tbody>
            {paginatedUsers.map((user, index) => (
              <tr
                key={user.id}
                className={`border-b border-slate-200 dark:border-slate-600 ${index % 2 === 0 ? 'bg-white dark:bg-slate-800' : 'bg-slate-50 dark:bg-slate-700/50'} hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors`}
              >
                <td className="px-4 py-3">
                  <input
                    type="checkbox"
                    checked={selectedUserIds.includes(user.id)}
                    onChange={() => handleSelectUser(user.id)}
                    className="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600"
                  />
                </td>
                <td className="px-4 py-3">{user.id}</td>
                <td className="px-4 py-3">{user.firstname}</td>
                <td className="px-4 py-3">{user.lastname}</td>
                <td className="px-4 py-3">{user.idnumber}</td>
                <td className="px-4 py-3">{user.phone_number || 'N/A'}</td>
                <td className="px-4 py-3">
                  <span
                    className={`px-2 py-1 rounded-full text-xs ${user.is_authentic ? 'bg-green-100 text-green-600 dark:bg-green-900/50 dark:text-green-400' : 'bg-red-100 text-red-600 dark:bg-red-900/50 dark:text-red-400'}`}
                  >
                    {user.is_authentic ? 'Yes' : 'No'}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => {
                      setSelectedUserIds([user.id]);
                      handleDownloadAgentDocs();
                    }}
                    className="flex items-center space-x-1 text-blue-500 hover:text-blue-600 dark:hover:text-blue-400"
                  >
                    <Download className="w-4 h-4" />
                    <span>Documents</span>
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
            Showing {startIndex + 1} - {Math.min(endIndex, totalItems)} of {totalItems} users
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
    </div>
  );
}

export default UserAgentList;