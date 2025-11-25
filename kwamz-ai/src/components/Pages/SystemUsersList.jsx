// components/UserList.jsx
import { useState, useEffect, useRef } from 'react';
import { Search, Filter, MoreVertical, Edit, Plus, Download, Upload, RefreshCw, ChevronRight, User, Shield, Briefcase, Mail, Phone, Calendar, IdCard, Crown } from 'lucide-react';
import axios from 'axios';
import * as XLSX from 'xlsx';
import config from '../../Config';
import { useToast } from './ToastProvider';
import UserDetailsModal from './UserDetailsModal';
import BatchUploadModal from './BatchUploadModal';

function SystemUsersList() {
  const [users, setUsers] = useState([]);
  const [filteredUsers,   setFilteredUsers] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filter, setFilter] = useState('all');
  const [selectedUserIds, setSelectedUserIds] = useState([]);
  const [isUserModalOpen, setIsUserModalOpen] = useState(false);
  const [isRoleModalOpen, setIsRoleModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isTemplatesSubMenuOpen, setIsTemplatesSubMenuOpen] = useState(false);
  const [isBatchModalOpen, setIsBatchModalOpen] = useState(false);
  const [validUsers, setValidUsers] = useState([]);
  const [invalidUsers, setInvalidUsers] = useState([]);
  const [batchFile, setBatchFile] = useState(null);
  const [commissionRate, setCommissionRate] = useState(10.0);
  const { showToast } = useToast();
  const fileInputRef = useRef(null);
  const dropdownRef = useRef(null);

  // Fetch users
  const fetchUsers = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const [usersResponse, commissionResponse] = await Promise.all([
        axios.get(`${config.API_URL}/users`, {
          headers: { Authorization: `Bearer ${token}` },
        })
      ]);

      console.log("The user response is:", usersResponse);
      setUsers(usersResponse.data);
      setFilteredUsers(usersResponse.data);
      // setCommissionRate(commissionResponse.data.commission_rate);  
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

  useEffect(() => {
    fetchUsers();
  }, []);

  // Handle search and filter
  useEffect(() => {
    let filtered = users;

    if (searchTerm) {
      filtered = filtered.filter(
        (user) =>
          user.username?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          user.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          user.firstname?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          user.lastname?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          user.phone_number?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          user.role?.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    if (filter === 'admin') {
      filtered = filtered.filter((user) => user.role === 'admin');
    } else if (filter === 'agent') {
      filtered = filtered.filter((user) => user.role === 'agent');
    } else if (filter === 'user') {
      filtered = filtered.filter((user) => user.role === 'user');
    } else if (filter === 'active') {
      filtered = filtered.filter((user) => user.is_active);
    } else if (filter === 'inactive') {
      filtered = filtered.filter((user) => !user.is_active);
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

  // Handle role update
  const handleUpdateRole = async (userId, newRole) => {
    try {
      const token = localStorage.getItem('token');
      await axios.patch(
        `${config.API_URL}/users/${userId}/role`,
        { role: newRole },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      showToast(`User role updated to ${newRole}`, 'success');
      fetchUsers();
      setIsRoleModalOpen(false);
    } catch (error) {
      console.error('Error updating role:', error.response?.data || error.message);
      showToast('Failed to update user role', 'error');
    }
  };

  // Handle status toggle
  const handleToggleStatus = async (userId, currentStatus) => {
    try {
      const token = localStorage.getItem('token');
      await axios.patch(
        `${config.API_URL}/users/${userId}/status`,
        { is_active: !currentStatus },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      showToast(`User ${!currentStatus ? 'activated' : 'deactivated'} successfully`, 'success');
      fetchUsers();
    } catch (error) {
      console.error('Error updating status:', error.response?.data || error.message);
      showToast('Failed to update user status', 'error');
    }
  };

  // Update commission rate
  const handleUpdateCommissionRate = async (newRate) => {
    try {
      const token = localStorage.getItem('token');
      await axios.put(
        `${config.API_URL}/users/commission-rate`,
        { commission_rate: newRate },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setCommissionRate(newRate);
      showToast('Commission rate updated successfully', 'success');
    } catch (error) {
      console.error('Error updating commission rate:', error.response?.data || error.message);
      showToast('Failed to update commission rate', 'error');
    }
  };

  const getRoleIcon = (role) => {
    switch (role) {
      case 'admin':
        return <Crown className="w-4 h-4 text-purple-500" />;
      case 'agent':
        return <Briefcase className="w-4 h-4 text-green-500" />;
      case 'moderator':
        return <Shield className="w-4 h-4 text-blue-500" />;
      default:
        return <User className="w-4 h-4 text-gray-500" />;
    }
  };

  const getRoleColor = (role) => {
    switch (role) {
      case 'admin':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900/50 dark:text-purple-300';
      case 'agent':
        return 'bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-300';
      case 'moderator':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-300';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/50 dark:text-gray-300';
    }
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-lg p-6">

      {/* Action Buttons */}
      <div className="flex justify-end mb-4 space-x-4">
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
          >
            <MoreVertical className="w-4 h-4" />
            <span>Actions</span>
          </button>
          {isDropdownOpen && (
            <div className="absolute right-0 mt-2 w-64 bg-white dark:bg-slate-700 rounded-xl shadow-lg z-10 border border-slate-200 dark:border-slate-600">
              <div className="py-2">
                <button
                  onClick={() => {
                    if (selectedUserIds.length === 1) {
                      setIsRoleModalOpen(true);
                    } else {
                      showToast('Please select one user to update role', 'error');
                    }
                    setIsDropdownOpen(false);
                  }}
                  disabled={selectedUserIds.length !== 1}
                  className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <Shield className="w-4 h-4 mr-3" />
                  Update Role
                </button>
                <button
                  onClick={() => {
                    setSelectedUserIds([]);
                    setIsUserModalOpen(true);
                    setIsDropdownOpen(false);
                  }}
                  className="w-full flex items-center px-4 py-2 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-600 transition-colors"
                >
                  <Plus className="w-4 h-4 mr-3" />
                  Create User
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Search and Filter Controls */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by name, email, username, or role"
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
            className="pl-10 pr-8 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
          >
            <option value="all">All Users</option>
            <option value="admin">Admins</option>
            <option value="agent">Agents</option>
            <option value="user">Users</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>
      </div>

      {/* Users Grid */}
      <div className="overflow-x-auto">
        <table className="w-full table-auto">
          <thead>
            <tr className="bg-slate-100 dark:bg-slate-700 text-left text-slate-600 dark:text-slate-300">
              <th className="px-4 py-3 font-semibold">ID</th>
              <th className="px-4 py-3 font-semibold">User</th>
              <th className="px-4 py-3 font-semibold">Contact</th>
              <th className="px-4 py-3 font-semibold">Personal Info</th>
              <th className="px-4 py-3 font-semibold">Role</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody>
            {paginatedUsers.map((user, index) => (
              <tr
                key={user.id}
                className={`border-b border-slate-200 dark:border-slate-600 ${
                  index % 2 === 0 ? 'bg-white dark:bg-slate-800' : 'bg-slate-50 dark:bg-slate-700/50'
                } hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors`}
              >
                <td className="px-4 py-3 font-mono text-sm">{user.id}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center space-x-3">
                    {user.image_loc ? (
                      <img
                        src={user.image_loc}
                        alt={user.username}
                        className="w-10 h-10 rounded-full object-cover"
                      />
                    ) : (
                      <div className="w-10 h-10 bg-slate-200 dark:bg-slate-600 rounded-full flex items-center justify-center">
                        <User className="w-5 h-5 text-slate-500" />
                      </div>
                    )}
                    <div>
                      <div className="font-medium">
                        {user.firstname && user.lastname 
                          ? `${user.firstname} ${user.lastname}`
                          : user.username
                        }
                      </div>
                      <div className="text-sm text-slate-500 dark:text-slate-400">
                        @{user.username}
                      </div>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-col space-y-1">
                    <div className="flex items-center space-x-1 text-sm">
                      <Mail className="w-3 h-3 text-slate-400" />
                      <span className="truncate max-w-[150px]">{user.email}</span>
                    </div>
                    {user.phone_number && (
                      <div className="flex items-center space-x-1 text-sm">
                        <Phone className="w-3 h-3 text-slate-400" />
                        <span>{user.phone_number}</span>
                      </div>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-col space-y-1 text-sm">
                    {user.idnumber && (
                      <div className="flex items-center space-x-1">
                        <IdCard className="w-3 h-3 text-slate-400" />
                        <span className="font-mono">{user.idnumber}</span>
                      </div>
                    )}
                    {user.date_of_birth && (
                      <div className="flex items-center space-x-1">
                        <Calendar className="w-3 h-3 text-slate-400" />
                        <span>{new Date(user.date_of_birth).toLocaleDateString()}</span>
                      </div>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center space-x-2">
                    {getRoleIcon(user.role)}
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRoleColor(user.role)}`}>
                      {user.role}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`px-2 py-1 rounded-full text-xs ${
                      user.is_active
                        ? 'bg-green-100 text-green-600 dark:bg-green-900/50 dark:text-green-400'
                        : 'bg-red-100 text-red-600 dark:bg-red-900/50 dark:text-red-400'
                    }`}
                  >
                    {user.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex space-x-2">
                    <button
                      onClick={() => handleToggleStatus(user.id, user.is_active)}
                      className={`px-3 py-1 rounded-lg text-xs font-medium ${
                        user.is_active
                          ? 'bg-red-100 text-red-600 hover:bg-red-200 dark:bg-red-900/50 dark:hover:bg-red-900'
                          : 'bg-green-100 text-green-600 hover:bg-green-200 dark:bg-green-900/50 dark:hover:bg-green-900'
                      } transition-colors`}
                    >
                      {user.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                    <button
                      onClick={() => {
                        setSelectedUserIds([user.id]);
                        setIsRoleModalOpen(true);
                      }}
                      className="px-3 py-1 bg-blue-100 text-blue-600 rounded-lg text-xs font-medium hover:bg-blue-200 dark:bg-blue-900/50 dark:hover:bg-blue-900 transition-colors"
                    >
                      Change Role
                    </button>
                  </div>
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
            onChange={(e) => setPageSize(Number(e.target.value))}
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
            onClick={() => setCurrentPage(1)}
            disabled={currentPage === 1}
            className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            First
          </button>
          <button
            onClick={() => setCurrentPage(currentPage - 1)}
            disabled={currentPage === 1}
            className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          <span className="text-sm text-slate-600 dark:text-slate-300">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => setCurrentPage(currentPage + 1)}
            disabled={currentPage === totalPages}
            className="py-1 px-3 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
          <button
            onClick={() => setCurrentPage(totalPages)}
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
    </div>
  );
}

export default SystemUsersList;