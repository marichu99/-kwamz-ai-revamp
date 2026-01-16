import config from "../Config";
const API_BASE_URL = config.API_URL || 'http://localhost:5000';

export const analyticsApi = {
  getAuthToken: () => localStorage.getItem('token'),

  async request(endpoint, options = {}) {
    const token = this.getAuthToken();
    const headers = {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
      ...options.headers,
    };

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Request failed' }));
      throw new Error(error.error || error.message || 'Something went wrong');
    }

    return response.json();
  },

  /**
   * Get comprehensive dashboard analytics data
   * @param {Object} params - Query parameters
   * @param {number} params.days - Number of days to look back (default 30)
   * @param {number} params.company_id - Optional company ID filter
   * @param {number} params.agent_id - Optional agent ID filter
   * @returns {Promise<Object>} Analytics data including KPIs, trends, distribution, and recent activity
   */
  getDashboardAnalytics: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.days) queryParams.append('days', params.days);
    if (params.company_id) queryParams.append('company_id', params.company_id);
    if (params.agent_id) queryParams.append('agent_id', params.agent_id);

    const queryString = queryParams.toString();
    const endpoint = `/transactions/dashboard-analytics${queryString ? `?${queryString}` : ''}`;

    return analyticsApi.request(endpoint, { method: 'GET' });
  },

  /**
   * Get transaction statistics
   * @param {Object} params - Query parameters
   * @returns {Promise<Object>} Transaction statistics
   */
  getTransactionStats: (params = {}) => {
    const queryParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        queryParams.append(key, value);
      }
    });

    const queryString = queryParams.toString();
    const endpoint = `/transactions/stats${queryString ? `?${queryString}` : ''}`;

    return analyticsApi.request(endpoint, { method: 'GET' });
  },
};
