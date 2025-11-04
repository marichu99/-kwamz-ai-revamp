import { Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from './components/Dashboard/Dashboard';
import Logout from './components/Pages/Logout';
import Signup from './components/Pages/Signup';
import Login from './components/Pages/Login';
import MpesaModal from './components/Pages/MpesaModal';
import  PaymentForm  from './components/Pages/PaymentForm';

function AppRouter({ isAuthenticated, currentPage, setCurrentPage }) {
  return (
    <Routes>
      {isAuthenticated ? (
        <>
          <Route
            path="/dashboard"
            element={<Dashboard currentPage={currentPage} setCurrentPage={setCurrentPage} />}
          />
          <Route path="/logout" element={<Logout />} />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/login" element={<Navigate to="/dashboard" replace />} />
          <Route path="/checkout" element={<PaymentForm />} />
          <Route path="/signup" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </>
      ) : (
        <>
          <Route path="/" element={<Login onSuccess={() => window.location.href = '/dashboard'} />} />
          <Route path="/login" element={<Login onSuccess={() => window.location.href = '/dashboard'} />} />
          <Route path="/signup" element={<Signup onSuccess={() => window.location.href = '/dashboard'} />} />
          <Route path="/checkout" element={<PaymentForm onSuccess={() => window.location.href = '/dashboard'}/>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </>
      )}
    </Routes>
  );
}

export default AppRouter;