import { useState } from 'react';

function BatchUploadModal({ 
  isOpen, 
  validItems = [], 
  invalidItems = [], 
  onClose, 
  onConfirm,
  type = 'users', // 'users' or 'agentCompanies'
  columns = null // Custom column configuration
}) {
  const [activeTab, setActiveTab] = useState('valid');

  if (!isOpen) return null;

  // Default column configurations
  const defaultColumns = {
    users: {
      row: 'Row',
      fields: [
        { key: 'firstname', label: 'First Name' },
        { key: 'lastname', label: 'Last Name' },
        { key: 'idnumber', label: 'ID Number' },
        { key: 'phone_number', label: 'Phone Number' },
        { key: 'store_number', label: 'Store Number' },
      ],
      errorField: 'reason'
    },
    agentCompanies: {
      row: 'Row',
      fields: [
        { key: 'company_name', label: 'Company Name' },
        { key: 'location(County)', label: 'Location (County)' },
        { key: 'location_details', label: 'Location Details' },
        { key: 'agent_number', label: 'Agent Number' },
        { key: 'store_number', label: 'Store Number' }
      ],
      errorField: 'errors'
    }
  };

  // Use custom columns or default based on type
  const config = columns || defaultColumns[type] || defaultColumns.users;
  
  // Ensure fields array exists
  const fields = config?.fields || [];
  const errorField = config?.errorField || 'errors';
  const rowLabel = config?.row || 'Row';

  return (
    <div className="fixed inset-0 bg-gradient-to-br from-black/60 via-black/50 to-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white backdrop-blur-lg rounded-2xl shadow-2xl border border-white/20 p-8 w-full max-w-4xl transform transition-all duration-300 scale-100 max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-bold mb-4 text-slate-800 dark:text-white">
          Batch Upload Preview - {type === 'users' ? 'Users' : 'Agent Companies'}
        </h2>
        
        {/* Tabs */}
        <div className="flex space-x-4 mb-4">
          <button
            onClick={() => setActiveTab('valid')}
            className={`py-2 px-4 rounded-xl ${
              activeTab === 'valid' 
                ? 'bg-blue-500 text-white' 
                : 'bg-slate-200 dark:bg-slate-600 text-slate-800 dark:text-white'
            }`}
          >
            Valid {type === 'users' ? 'Users' : 'Companies'} ({validItems.length})
          </button>
          <button
            onClick={() => setActiveTab('invalid')}
            className={`py-2 px-4 rounded-xl ${
              activeTab === 'invalid' 
                ? 'bg-red-500 text-white' 
                : 'bg-slate-200 dark:bg-slate-600 text-slate-800 dark:text-white'
            }`}
          >
            Invalid {type === 'users' ? 'Users' : 'Companies'} ({invalidItems.length})
          </button>
        </div>

        {/* Table */}
        <div className="flex-1 overflow-y-auto mb-4">
          <table className="w-full table-auto">
            <thead className="sticky top-0 bg-slate-100 dark:bg-slate-700">
              <tr className="text-left text-slate-600 dark:text-slate-300">
                <th className="px-4 py-3 font-semibold">{rowLabel}</th>
                {fields.map((field) => (
                  <th key={field.key} className="px-4 py-3 font-semibold">
                    {field.label}
                  </th>
                ))}
                {activeTab === 'invalid' && (
                  <th className="px-4 py-3 font-semibold">Errors</th>
                )}
              </tr>
            </thead>
            <tbody>
              {(activeTab === 'valid' ? validItems : invalidItems).map((item, index) => (
                <tr
                  key={index}
                  className={`border-b border-slate-200 dark:border-slate-600 ${
                    index % 2 === 0 
                      ? 'bg-white dark:bg-slate-800' 
                      : 'bg-slate-50 dark:bg-slate-700/50'
                  }`}
                >
                  <td className="px-4 py-3">
                    {item.row || item.rowIndex || index + 1}
                  </td>
                  {fields.map((field) => (
                    <td key={field.key} className="px-4 py-3">
                      {item[field.key] || item.data?.[field.key] || 'N/A'}
                    </td>
                  ))}
                  {activeTab === 'invalid' && (
                    <td className="px-4 py-3">
                      {Array.isArray(item[errorField]) ? (
                        <ul className="list-disc list-inside text-sm text-red-600">
                          {item[errorField].map((error, errorIndex) => (
                            <li key={errorIndex}>{error}</li>
                          ))}
                        </ul>
                      ) : (
                        <span className="text-red-600 text-sm">
                          {item[errorField] || 'Unknown error'}
                        </span>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end space-x-4">
          <button
            onClick={onClose}
            className="py-2 px-4 bg-gray-500 text-white rounded-xl hover:bg-gray-600 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={invalidItems.length > 0 || validItems.length === 0}
            className={`py-2 px-4 rounded-xl transition-colors ${
              invalidItems.length > 0 || validItems.length === 0
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-blue-500 text-white hover:bg-blue-600'
            }`}
          >
            Upload {validItems.length} {type === 'users' ? 'Users' : 'Companies'}
          </button>
        </div>

        {/* Summary */}
        <div className="mt-4 text-sm text-slate-600 dark:text-slate-300">
          <p>
            Total: {validItems.length + invalidItems.length} | 
            Valid: <span className="text-green-600">{validItems.length}</span> | 
            Invalid: <span className="text-red-600">{invalidItems.length}</span>
          </p>
        </div>
      </div>
    </div>
  );
}

export default BatchUploadModal;