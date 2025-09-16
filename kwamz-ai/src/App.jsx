import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom' // Add useLocation
import axios from 'axios' // Make sure to import axios
import './App.css'
import Sidebar from './components/Layout/Sidebar'
import Header from './components/Layout/Header'
import Dashboard from './components/Dashboard/Dashboard'
import AppRouter from './AppRouter'

function App() {
  const [count, setCount] = useState(0);
  const navigate = useNavigate();
  const location = useLocation(); // Add this hook
  const [sideBarCollapsed, setSideBarCollapsed] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentPage, setCurrentPage] = useState("dashboard");
  const [isLoading, setIsLoading] = useState(true); // Add loading state

  useEffect(() => {
    const verifyToken = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        try {
          await axios({
            method: 'get',
            url: `${process.env.REACT_APP_API_URL}/users/verify-token`,
            headers: {
              Authorization: `Bearer ${token}`
            }
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

  // Show loading state while verifying token
  if (isLoading) {
    return <div>Loading...</div>;
  }

  return (
    <div className='min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 dark:from-slate-900 dark:via-slate-80 dark:to-slate-900 transition-all duration-500'>
      <div className='flex h-screen overflow-hidden'>
        {isAuthenticated  && <Sidebar 
          collapsed={sideBarCollapsed}
          onToggle={() => setSideBarCollapsed(!sideBarCollapsed)}
          currentPage={currentPage}
          onPageChange={setCurrentPage}
        />}
        <div className='flex-1 flex flex-col overflow-hidden'>
          {isAuthenticated  && <Header sideBarCollapsed={sideBarCollapsed} 
                  onToggleSideBar = {()=> setSideBarCollapsed(!sideBarCollapsed)}/>}
          <main className='flex-1 overflow-y-auto bg-transparent'>
            <div className='p-6 space-y-6'>
              <AppRouter/>
            </div>
          </main>
        </div>
      </div>
    </div>
  )
}

export default App