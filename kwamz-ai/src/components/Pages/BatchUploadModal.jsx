import { useState } from 'react';

function BatchUploadModal({ isOpen, validUsers, invalidUsers, onClose, onConfirm }) {
  const [activeTab, setActiveTab] = useState('valid');

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gradient-to-br from-black/60 via-black/50 to-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white backdrop-blur-lg rounded-2xl shadow-2xl border border-white/20 p-8 w-full max-w-2xl transform transition-all duration-300 scale-100 max-h-[90vh] overflow-y-auto">
        <h2 className="text-xl font-bold mb-4 text-slate-800 dark:text-white">Batch Upload Preview</h2>
        <div className="flex space-x-4 mb-4">
          <button
            onClick={() => setActiveTab('valid')}
            className={`py-2 px-4 rounded-xl ${activeTab === 'valid' ? 'bg-blue-500 text-white' : 'bg-slate-200 dark:bg-slate-600 text-slate-800 dark:text-white'}`}
          >
            Valid Users ({validUsers.length})
          </button>
          <button
            onClick={() => setActiveTab('invalid')}
            className={`py-2 px-4 rounded-xl ${activeTab === 'invalid' ? 'bg-blue-500 text-white' : 'bg-slate-200 dark:bg-slate-600 text-slate-800 dark:text-white'}`}
          >
            Invalid Users ({invalidUsers.length})
          </button>
        </div>
        <div className="flex-1 overflow-y-auto mb-4">
          <table className="w-full table-auto">
            <thead className="sticky top-0 bg-slate-100 dark:bg-slate-700">
              <tr className="text-left text-slate-600 dark:text-slate-300">
                <th className="px-4 py-3 font-semibold">Row</th>
                <th className="px-4 py-3 font-semibold">First Name</th>
                <th className="px-4 py-3 font-semibold">Last Name</th>
                <th className="px-4 py-3 font-semibold">ID Number</th>
                <th className="px-4 py-3 font-semibold">Phone Number</th>
                {activeTab === 'invalid' && <th className="px-4 py-3 font-semibold">Reason</th>}
              </tr>
            </thead>
            <tbody>
              {(activeTab === 'valid' ? validUsers : invalidUsers).map((item, index) => (
                <tr
                  key={index}
                  className={`border-b border-slate-200 dark:border-slate-600 ${index % 2 === 0 ? 'bg-white dark:bg-slate-800' : 'bg-slate-50 dark:bg-slate-700/50'}`}
                >
                  <td className="px-4 py-3">{item.rowIndex}</td>
                  <td className="px-4 py-3">{item.firstname || 'N/A'}</td>
                  <td className="px-4 py-3">{item.lastname || 'N/A'}</td>
                  <td className="px-4 py-3">{item.idnumber || 'N/A'}</td>
                  <td className="px-4 py-3">{item.phone_number || 'N/A'}</td>
                  {activeTab === 'invalid' && <td className="px-4 py-3">{item.reason}</td>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex justify-end space-x-4">
          <button
            onClick={onClose}
            className="py-2 px-4 bg-gray-500 text-white rounded-xl hover:bg-gray-600"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={invalidUsers.length > 0 || validUsers.length === 0}
            className="py-2 px-4 bg-blue-500 text-white rounded-xl hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            Upload
          </button>
        </div>
      </div>
    </div>
  );
}

export default BatchUploadModal;