import React, { useState } from 'react'
import { Folder, Plus, Search, Filter, Calendar, Users, MoreVertical, Star } from 'lucide-react'

function Projects() {
  const [searchTerm, setSearchTerm] = useState('')
  const [filterStatus, setFilterStatus] = useState('all')

  const projects = [
    {
      id: 1,
      name: 'E-commerce Website',
      description: 'Modern e-commerce platform with React and Node.js',
      status: 'active',
      progress: 75,
      team: 5,
      deadline: '2024-12-15',
      priority: 'high',
      color: 'bg-blue-500'
    },
    {
      id: 2,
      name: 'Mobile App Design',
      description: 'UI/UX design for fitness tracking application',
      status: 'completed',
      progress: 100,
      team: 3,
      deadline: '2024-11-30',
      priority: 'medium',
      color: 'bg-green-500'
    },
    {
      id: 3,
      name: 'Marketing Campaign',
      description: 'Q4 digital marketing strategy and implementation',
      status: 'planning',
      progress: 25,
      team: 7,
      deadline: '2025-01-20',
      priority: 'high',
      color: 'bg-purple-500'
    },
    {
      id: 4,
      name: 'Database Migration',
      description: 'Migrate legacy database to cloud infrastructure',
      status: 'active',
      progress: 60,
      team: 4,
      deadline: '2024-12-30',
      priority: 'low',
      color: 'bg-orange-500'
    },
    {
      id: 5,
      name: 'API Documentation',
      description: 'Comprehensive API documentation and testing suite',
      status: 'on-hold',
      progress: 40,
      team: 2,
      deadline: '2025-02-15',
      priority: 'medium',
      color: 'bg-red-500'
    }
  ]

  const getStatusColor = (status) => {
    switch(status) {
      case 'active': return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
      case 'completed': return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400'
      case 'planning': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
      case 'on-hold': return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400'
    }
  }

  const getPriorityColor = (priority) => {
    switch(priority) {
      case 'high': return 'bg-red-500'
      case 'medium': return 'bg-yellow-500'
      case 'low': return 'bg-green-500'
      default: return 'bg-gray-500'
    }
  }

  const filteredProjects = projects.filter(project => {
    const matchesSearch = project.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         project.description.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesStatus = filterStatus === 'all' || project.status === filterStatus
    return matchesSearch && matchesStatus
  })

  return (
    <div className='min-h-screen bg-transparent'>
      <div className='max-w-7xl mx-auto space-y-8'>
        
        {/* Page Header */}
        <div className='bg-white/70 dark:bg-slate-800/70 backdrop-blur-xl rounded-2xl p-8 border border-slate-200/50 dark:border-slate-700/50'>
          <div className='flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0'>
            <div className='flex items-center space-x-4'>
              <div className='p-3 bg-gradient-to-br from-purple-500 to-pink-600 rounded-xl'>
                <Folder className='w-8 h-8 text-white' />
              </div>
              <div>
                <h1 className='text-3xl font-bold text-slate-800 dark:text-white'>Projects</h1>
                <p className='text-slate-600 dark:text-slate-300 mt-1'>Manage and track all your projects</p>
              </div>
            </div>
            
            <button className='flex items-center space-x-2 bg-gradient-to-r from-purple-500 to-pink-600 text-white px-6 py-3 rounded-xl hover:shadow-lg transition-all'>
              <Plus className='w-5 h-5' />
              <span className='font-medium'>New Project</span>
            </button>
          </div>
        </div>

        {/* Filters and Search */}
        <div className='bg-white/70 dark:bg-slate-800/70 backdrop-blur-xl rounded-2xl p-6 border border-slate-200/50 dark:border-slate-700/50'>
          <div className='flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0'>
            {/* Search */}
            <div className='relative max-w-md'>
              <Search className='w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400' />
              <input 
                type='text'
                placeholder='Search projects...'
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className='w-full pl-10 pr-4 py-2.5 bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-slate-800 dark:text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all'
              />
            </div>

            {/* Status Filter */}
            <div className='flex items-center space-x-4'>
              <div className='flex items-center space-x-2'>
                <Filter className='w-5 h-5 text-slate-400' />
                <select 
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                  className='bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-2 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-purple-500'
                >
                  <option value='all'>All Status</option>
                  <option value='active'>Active</option>
                  <option value='completed'>Completed</option>
                  <option value='planning'>Planning</option>
                  <option value='on-hold'>On Hold</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Projects Grid */}
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6'>
          {filteredProjects.map((project) => (
            <div key={project.id} className='bg-white/70 dark:bg-slate-800/70 backdrop-blur-xl rounded-2xl p-6 border border-slate-200/50 dark:border-slate-700/50 hover:shadow-lg transition-all duration-300 group'>
              
              {/* Project Header */}
              <div className='flex items-start justify-between mb-4'>
                <div className='flex items-center space-x-3'>
                  <div className={`w-3 h-3 rounded-full ${project.color}`}></div>
                  <div className={`w-2 h-2 rounded-full ${getPriorityColor(project.priority)}`}></div>
                </div>
                <div className='flex items-center space-x-2'>
                  <Star className='w-4 h-4 text-slate-400 hover:text-yellow-500 cursor-pointer transition-colors' />
                  <MoreVertical className='w-4 h-4 text-slate-400 hover:text-slate-600 cursor-pointer transition-colors' />
                </div>
              </div>

              {/* Project Info */}
              <div className='mb-4'>
                <h3 className='text-lg font-bold text-slate-800 dark:text-white mb-2 group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors'>
                  {project.name}
                </h3>
                <p className='text-slate-600 dark:text-slate-300 text-sm leading-relaxed'>
                  {project.description}
                </p>
              </div>

              {/* Progress Bar */}
              <div className='mb-4'>
                <div className='flex items-center justify-between mb-2'>
                  <span className='text-sm font-medium text-slate-700 dark:text-slate-300'>Progress</span>
                  <span className='text-sm font-bold text-slate-800 dark:text-white'>{project.progress}%</span>
                </div>
                <div className='w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden'>
                  <div 
                    className={`h-full ${project.color} transition-all duration-500`}
                    style={{ width: `${project.progress}%` }}
                  ></div>
                </div>
              </div>

              {/* Project Meta */}
              <div className='flex items-center justify-between text-sm text-slate-600 dark:text-slate-300'>
                <div className='flex items-center space-x-4'>
                  <div className='flex items-center space-x-1'>
                    <Users className='w-4 h-4' />
                    <span>{project.team}</span>
                  </div>
                  <div className='flex items-center space-x-1'>
                    <Calendar className='w-4 h-4' />
                    <span>{new Date(project.deadline).toLocaleDateString()}</span>
                  </div>
                </div>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(project.status)}`}>
                  {project.status.charAt(0).toUpperCase() + project.status.slice(1)}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Empty State */}
        {filteredProjects.length === 0 && (
          <div className='bg-white/70 dark:bg-slate-800/70 backdrop-blur-xl rounded-2xl p-12 border border-slate-200/50 dark:border-slate-700/50 text-center'>
            <Folder className='w-16 h-16 text-slate-400 mx-auto mb-4' />
            <h3 className='text-xl font-semibold text-slate-600 dark:text-slate-300 mb-2'>No projects found</h3>
            <p className='text-slate-500 dark:text-slate-400'>Try adjusting your search or filter criteria</p>
          </div>
        )}

      </div>
    </div>
  )
}

export default Projects