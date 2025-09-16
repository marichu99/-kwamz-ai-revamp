import { Routes, Route } from 'react-router-dom';

import Dashboard from './components/Dashboard/Dashboard';
import Logout from './components/Pages/Logout';
import Signup from './components/Pages/Signup';
import Login from './components/Pages/Login'



const AppRouter = () => (
  <Routes>
    <Route path="/" element={<Login onSuccess={() => window.location.href = '/dashboard'}/>} />
    <Route path="/dashboard" element={<Dashboard />} />
    <Route path="/logout" element={<Logout />} />
    <Route path="/signup" element={<Signup onSuccess={() => window.location.href = '/dashboard'} />} />
    <Route path="/login" element={<Login onSuccess={() => window.location.href = '/dashboard'}/>} />
  </Routes>
);

export default AppRouter;