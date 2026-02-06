import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import './App.css';
import Sidebar from './components/Layout/Sidebar';
import Header from './components/Layout/Header';
import AppRouter from './AppRouter';
import config from './Config';

function App() {
  const [sideBarCollapsed, setSideBarCollapsed] = useState(window.innerWidth < 768);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [isLoading, setIsLoading] = useState(true);
  const [billingStatus, setBillingStatus] = useState(null);
  const navigate = useNavigate();
  const location = useLocation();

  // Define public routes that don't require authentication
  const publicRoutes = [
    '/',
    '/login',
    '/signup',
    '/admin/signup',
    '/agent/signup',
    '/admin/login',
    '/checkout',
    '/forgot-password'
  ];

  // Landing page should never show the app shell (sidebar/header)
  const isLandingPage = location.pathname === '/';

  useEffect(() => {
    const verifyToken = async () => {
      const token = localStorage.getItem('token');
      
      // If on a public route, skip token verification
      if (publicRoutes.includes(location.pathname)) {
        if (token) {
          // User is logged in but on a public route, verify token
          try {
            await axios.get(`${config.API_URL}/users/verify-token`, {
              headers: { Authorization: `Bearer ${token}` },
            });
            setIsAuthenticated(true);
            // Redirect authenticated users away from login/signup pages (but not the landing page)
            if (['/login', '/signup', '/admin/login', '/admin/signup', '/agent/signup'].includes(location.pathname)) {
              navigate('/dashboard');
            }
          } catch (error) {
            console.error('Token verification failed:', error.response?.data || error.message);
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            localStorage.removeItem('userRole');
            localStorage.removeItem('admin');
            setIsAuthenticated(false);
          }
        } else {
          setIsAuthenticated(false);
        }
        setIsLoading(false);
        return;
      }

      // For protected routes, verify token
      if (token) {
        try {
          // Step 1: Verify token
          await axios.get(`${config.API_URL}/users/verify-token`, {
            headers: { Authorization: `Bearer ${token}` },
          });

          // Step 2: Check billing status (trial / paid / not paid)
          const paymentResponse = await axios.get(`${config.API_URL}/payment/get-latest-payment`, {
            headers: { Authorization: `Bearer ${token}` },
          });

          const paymentData = paymentResponse.data;
          setBillingStatus(paymentData);

          if (paymentData.status === 'NOT_PAID' && location.pathname !== '/checkout') {
            setIsAuthenticated(true);
            setIsLoading(false);
            navigate('/checkout');
            return;
          }

          setIsAuthenticated(true);
        } catch (error) {
          console.error('Verify token or payment check failed:', error.response?.data || error.message);
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          localStorage.removeItem('userRole');
          localStorage.removeItem('admin');
          setIsAuthenticated(false);
          navigate('/');
        }
      } else {
        // No token and trying to access protected route
        setIsAuthenticated(false);
        navigate('/');
      }
      setIsLoading(false);
    };

    verifyToken();
  }, [navigate, location.pathname]);


  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-600 dark:text-slate-400">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900 transition-all duration-500">
      <div className="flex h-screen overflow-visible">
        {isAuthenticated && !isLandingPage && (
          <Sidebar
            collapsed={sideBarCollapsed}
            onToggle={() => setSideBarCollapsed(!sideBarCollapsed)}
            currentPage={currentPage}
            onPageChange={setCurrentPage}
          />
        )}
        <div className="flex-1 flex flex-col">
          {isAuthenticated && !isLandingPage && (
            <Header
              sideBarCollapsed={sideBarCollapsed}
              onToggleSideBar={() => setSideBarCollapsed(!sideBarCollapsed)}
              currentPage={currentPage}
              setCurrentPage={setCurrentPage}
              billingStatus={billingStatus}
            />
          )}
          <main className="flex-1 overflow-y-auto bg-transparent">
            <div className={`${isAuthenticated && !isLandingPage ? 'p-3 sm:p-4 md:p-6' : 'p-0'} space-y-6`}>
              <AppRouter
                isAuthenticated={isAuthenticated}
                currentPage={currentPage}
                setCurrentPage={setCurrentPage}
              />
            </div>
          </main>
        </div>
      </div>

    </div>
  );
}

export default App;