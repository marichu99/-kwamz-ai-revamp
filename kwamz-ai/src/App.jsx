import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import './App.css';
import Sidebar from './components/Layout/Sidebar';
import Header from './components/Layout/Header';
import AppRouter from './AppRouter';
import config from './Config';

function App() {
  const [sideBarCollapsed, setSideBarCollapsed] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const verifyToken = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        try {
          await axios({
            method: 'get',
            url: `${config.API_URL}/users/verify-token`,
            headers: {
              Authorization: `Bearer ${token}`,
            },
          });
          setIsAuthenticated(true);
          if (location.pathname === '/' || location.pathname === '/login' || location.pathname === '/signup') {
            navigate('/dashboard');
          }
        } catch (error) {
          console.error('Verify token failed:', error.response?.data || error.message);
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          setIsAuthenticated(false);
          navigate('/');
        }
      } else {
        setIsAuthenticated(false);
        if (location.pathname !== '/' && location.pathname !== '/login' && location.pathname !== '/signup') {
          navigate('/');
        }
      }
      setIsLoading(false);
    };
    verifyToken();
  }, [navigate, location.pathname]);

  if (isLoading) {
    return <div>Loading...</div>;
  }

  return (
    <div className='min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900 transition-all duration-500'>
      <div className='flex h-screen overflow-visible'>
        {isAuthenticated && (
          <Sidebar
            collapsed={sideBarCollapsed}
            onToggle={() => setSideBarCollapsed(!sideBarCollapsed)}
            currentPage={currentPage}
            onPageChange={setCurrentPage}
          />
        )}
        <div className='flex-1 flex flex-col'>
          {isAuthenticated && (
            <Header
              sideBarCollapsed={sideBarCollapsed}
              onToggleSideBar={() => setSideBarCollapsed(!sideBarCollapsed)}
              currentPage={currentPage}
              setCurrentPage={setCurrentPage}
            />
          )}
          <main className='flex-1 overflow-y-auto bg-transparent'>
            <div className='p-6 space-y-6'>
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