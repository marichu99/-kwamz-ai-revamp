import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { AlertTriangle, X } from 'lucide-react';
import './App.css';
import Sidebar from './components/Layout/Sidebar';
import Header from './components/Layout/Header';
import AppRouter from './AppRouter';
import config from './Config';
import LiveScrapeFeed from './components/LiveScrapeFeed';
import ChatBubble from './components/ChatBubble';
import { useLiveFeed } from './context/LiveFeedContext';

function App() {
  const { jobId, shortCode, isOpen, closeFeed, killFeed } = useLiveFeed();
  const [sideBarCollapsed, setSideBarCollapsed] = useState(window.innerWidth < 768);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [isLoading, setIsLoading] = useState(true);
  const [billingStatus, setBillingStatus] = useState(null);
  const [showStreamEndAlert, setShowStreamEndAlert] = useState(false);
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

          const userRole = paymentData.user_role || localStorage.getItem('userRole') || 'user';
          const isAdmin = ['admin', 'administrator'].includes(userRole.toLowerCase());

          if (paymentData.status === 'NOT_PAID' && location.pathname !== '/checkout' && !isAdmin) {
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
    <>
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

    {/* Floating data assistant — persists across all routes */}
    <ChatBubble isAuthenticated={isAuthenticated} />

    {/* Global live feed — persists across all routes */}
    <LiveScrapeFeed
      isOpen={isOpen}
      jobId={jobId}
      shortCode={shortCode}
      onClose={closeFeed}
      onStreamEnd={() => { closeFeed(); setShowStreamEndAlert(true); }}
      onKill={killFeed}
    />

    {/* Stream ended — re-login prompt */}
    {showStreamEndAlert && (
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[9999] p-4">
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-md">
          <div className="p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center flex-shrink-0">
                  <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-slate-800 dark:text-white">Scraper Session Ended</h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">Action required</p>
                </div>
              </div>
              <button
                onClick={() => setShowStreamEndAlert(false)}
                className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
              >
                <X className="w-4 h-4 text-slate-400" />
              </button>
            </div>

            <p className="text-sm text-slate-700 dark:text-slate-300 mb-4 leading-relaxed">
              The live scraper feed has ended. This may be due to a session timeout on the M-Pesa portal.
              Please re-login to allow the scraper to continue gathering information.
            </p>

            <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-3 mb-5">
              <p className="text-xs text-amber-800 dark:text-amber-300">
                Log in to the M-Pesa portal, then start a new scraping session from the Company List page.
              </p>
            </div>

            <div className="flex justify-end">
              <button
                onClick={() => setShowStreamEndAlert(false)}
                className="px-4 py-2 text-sm text-white bg-amber-500 rounded-xl hover:bg-amber-600 transition-colors"
              >
                Got it
              </button>
            </div>
          </div>
        </div>
      </div>
    )}
    </>
  );
}

export default App;