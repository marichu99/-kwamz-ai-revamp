import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import Sidebar from './components/Layout/Sidebar'
import Header from './components/Layout/Header'

function App() {
  const [count, setCount] = useState(0);
  const [sideBarCollapsed, setSideBarCollapsed] = useState(false);
  const [currentPage, setCurrentPage] = useState("dashboard");

  return (
    <div className='min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 dark:from-slate-900 dark:via-slate-80 dark:to-slate-900 transition-all duration-500'>
      <div className='flex h-screen overflow-hidden'>
        <Sidebar 
          collapsed={sideBarCollapsed}
          onToggle={() => setSideBarCollapsed(!sideBarCollapsed)}
          currentPage={currentPage}
          onPageChange={setCurrentPage} // Fixed the typo here
        />
        <div className='flex-1 flex flex-col overflow-hidden'>
          <Header sideBarCollapsed={sideBarCollapsed} 
                  onToggleSideBar = {()=> setSideBarCollapsed(!sideBarCollapsed)}/>
          {/* Main content would go here */}
        </div>
      </div>
    </div>
  )
}

export default App