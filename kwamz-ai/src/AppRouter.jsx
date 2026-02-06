import { Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from './components/Dashboard/Dashboard';
import Logout from './components/Pages/Logout';
import Signup from './components/Pages/Signup';
import Login from './components/Pages/Login';
import MpesaModal from './components/Pages/MpesaModal';
import PaymentForm from './components/Pages/PaymentForm';
import Checkout from './components/Pages/Checkout';
import AdminSignUpForm from './components/Pages/AdminSignUpForm';
import SignUpForm from './components/Pages/Signup';
import ForgotPassword from './components/Pages/ForgotPassword';
import LandingPage from './components/Pages/LandingPage';

function AppRouter({ isAuthenticated, currentPage, setCurrentPage }) {
  return (
    <Routes>
      {/* Landing page is always accessible */}
      <Route path="/" element={<LandingPage />} />

      {isAuthenticated ? (
        <>
          <Route
            path="/dashboard"
            element={<Dashboard currentPage={currentPage} setCurrentPage={setCurrentPage} />}
          />
          <Route path="/logout" element={<Logout />} />
          <Route path="/login" element={<Navigate to="/dashboard" replace />} />
          <Route path="/checkout" element={<Checkout />} />
          <Route path="/signup" element={<Navigate to="/dashboard" replace />} />

          {/* Admin routes - redirect if already authenticated */}
          <Route path="/admin/signup" element={<Navigate to="/dashboard" replace />} />
          <Route path="/admin/login" element={<Navigate to="/dashboard" replace />} />
          <Route path="/agent/signup" element={<Navigate to="/dashboard" replace />} />

          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </>
      ) : (
        <>
          {/* Regular User Routes */}
          <Route path="/login" element={<Login onSuccess={() => window.location.href = '/dashboard'} />} />
          <Route path="/signup" element={<Signup onSuccess={() => window.location.href = '/dashboard'} user_role={"user"} />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/checkout" element={<PaymentForm onSuccess={() => window.location.href = '/dashboard'}/>} />

          {/* Admin Routes */}
          <Route
            path="/admin/signup"
            element={
              <AdminSignUpForm
                onSuccess={() => window.location.href = '/dashboard'}
                onNavigateToLogin={() => window.location.href = '/admin/login'}
              />
            }
          />
          <Route
            path="/agent/signup"
            element={
              <SignUpForm
                onSuccess={() => window.location.href = '/dashboard'}
                user_role={"agent"}
              />
            }
          />
          <Route
            path="/admin/login"
            element={
              <Login
                onSuccess={() => window.location.href = '/dashboard'}
              />
            }
          />

          <Route path="*" element={<Navigate to="/" replace />} />
        </>
      )}
    </Routes>
  );
}

export default AppRouter;