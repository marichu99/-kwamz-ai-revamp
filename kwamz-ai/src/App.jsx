import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import './App.css';
import Sidebar from './components/Layout/Sidebar';
import Header from './components/Layout/Header';
import AppRouter from './AppRouter';
import MpesaModal from './components/Pages/MpesaModal';
import config from './Config';

function App() {
  const [sideBarCollapsed, setSideBarCollapsed] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [isLoading, setIsLoading] = useState(true);
  const [showPaymentModal, setShowPaymentModal] = useState(false); // Control Mpesa modal
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const verifyToken = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        try {
          // Step 1: Verify token
          await axios.get(`${config.API_URL}/users/verify-token`, {
            headers: { Authorization: `Bearer ${token}` },
          });

          // // Step 2: Check if payment is made or in free trial
          // const paymentResponse = await axios.get(`${config.API_URL}/payment/get-latest-payment`, {
          //   headers: { Authorization: `Bearer ${token}` },
          // });

          // const paymentData = paymentResponse.data;
          // console.log('Payment check result:', paymentData);

          // if (paymentData.status === 'NOT_PAID') {
          //   // Show M-Pesa modal
          //   setShowPaymentModal(true);
          // }

          setIsAuthenticated(true);
          if (['/', '/login', '/signup'].includes(location.pathname)) {
            navigate('/dashboard');
          }
        } catch (error) {
          console.error('Verify token or payment check failed:', error.response?.data || error.message);
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          setIsAuthenticated(false);
          navigate('/');
        }
      } else {
        setIsAuthenticated(false);
        if (!['/', '/login', '/signup'].includes(location.pathname)) {
          navigate('/');
        }
      }
      setIsLoading(false);
    };

    verifyToken();
  }, [navigate, location.pathname]);

  // const handlePaymentSubmit = (result) => {
  //   console.log('Payment result:', result);
  //   if (result.success) {
  //     alert(result.message);
  //     setShowPaymentModal(false); // Close modal after successful payment
  //   }
  // };

  // const handleCloseModal = () => {
  //   setShowPaymentModal(false);
  // };

  if (isLoading) {
    return <div>Loading...</div>;
  }

  // Add blur effect when modal is open
  const appContentStyle = {
    filter: showPaymentModal ? 'blur(5px)' : 'none',
    transition: 'filter 0.3s ease',
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900 transition-all duration-500">
      <div className="flex h-screen overflow-visible" style={appContentStyle}>
        {isAuthenticated && (
          <Sidebar
            collapsed={sideBarCollapsed}
            onToggle={() => setSideBarCollapsed(!sideBarCollapsed)}
            currentPage={currentPage}
            onPageChange={setCurrentPage}
          />
        )}
        <div className="flex-1 flex flex-col">
          {isAuthenticated && (
            <Header
              sideBarCollapsed={sideBarCollapsed}
              onToggleSideBar={() => setSideBarCollapsed(!sideBarCollapsed)}
              currentPage={currentPage}
              setCurrentPage={setCurrentPage}
            />
          )}
          <main className="flex-1 overflow-y-auto bg-transparent">
            <div className="p-6 space-y-6">
              <AppRouter
                isAuthenticated={isAuthenticated}
                currentPage={currentPage}
                setCurrentPage={setCurrentPage}
              />
            </div>
          </main>
        </div>
      </div>

      {/* Show M-Pesa Modal when payment not done */}
      {/* {showPaymentModal && (
        <MpesaModal
          onClose={handleCloseModal}
          onSubmit={handlePaymentSubmit}
        />
      )} */}
    </div>
  );
}

export default App;
