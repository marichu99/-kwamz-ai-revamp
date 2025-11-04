import React from 'react';
import { CheckCircle, XCircle, Clock } from 'lucide-react';

export const PaymentStatusBadge = ({ status }) => {
  const statusConfig = {
    PAID: { icon: CheckCircle, color: 'text-green-600 bg-green-100', label: 'Active' },
    NOT_PAID: { icon: XCircle, color: 'text-red-600 bg-red-100', label: 'Inactive' },
    PENDING: { icon: Clock, color: 'text-yellow-600 bg-yellow-100', label: 'Pending' },
    COMPLETED: { icon: CheckCircle, color: 'text-green-600 bg-green-100', label: 'Completed' },
    FAILED: { icon: XCircle, color: 'text-red-600 bg-red-100', label: 'Failed' },
  };

  const config = statusConfig[status] || statusConfig.PENDING;
  const Icon = config.icon;

  return (
    <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${config.color}`}>
      <Icon className="w-4 h-4" />
      {config.label}
    </span>
  );
};
