import React, { useState, useRef, useEffect } from 'react'
import { RefreshCw, TrendingUp, TrendingDown, Minus, Calendar, Building2, ChevronDown, Check } from 'lucide-react'

export function CompanyDropdown({ companies, selectedCompany, onCompanyChange }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const label = selectedCompany ? selectedCompany.company_name : 'All Companies'
  const shortcode = selectedCompany?.shortcode ?? null

  return (
    <div ref={ref} className="relative">
      {/* Trigger */}
      <button
        onClick={() => setOpen(o => !o)}
        className={`
          flex items-center gap-2.5 pl-3 pr-2.5 py-2 rounded-xl border text-sm font-medium
          bg-white/90 dark:bg-slate-800/90 backdrop-blur-xl
          transition-all duration-200 min-w-[160px] max-w-[220px]
          ${open
            ? 'border-blue-400 dark:border-blue-500 shadow-lg shadow-blue-500/10 ring-2 ring-blue-400/20'
            : 'border-slate-200 dark:border-slate-700 hover:border-blue-300 dark:hover:border-blue-600 hover:shadow-md'
          }
        `}
      >
        <div className="flex items-center justify-center w-6 h-6 rounded-lg bg-gradient-to-br from-blue-500/20 to-purple-500/20 shrink-0">
          <Building2 className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
        </div>
        <div className="flex-1 text-left overflow-hidden">
          <p className="text-xs text-slate-400 dark:text-slate-500 leading-none mb-0.5">Company</p>
          <p className="text-slate-700 dark:text-slate-200 font-semibold truncate leading-tight text-[13px]">{label}</p>
        </div>
        {shortcode && (
          <span className="shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded-md bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400">
            {shortcode}
          </span>
        )}
        <ChevronDown className={`w-3.5 h-3.5 text-slate-400 shrink-0 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown panel */}
      {open && (
        <div className="
          dropdown-enter
          absolute right-0 top-full mt-2 z-50 min-w-[240px]
          bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700
          shadow-2xl shadow-slate-300/40 dark:shadow-slate-900/60
          overflow-hidden
        ">
          {/* Header */}
          <div className="px-3 pt-3 pb-2 border-b border-slate-100 dark:border-slate-700/60">
            <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Select Company</p>
          </div>

          <ul className="py-1.5 max-h-64 overflow-y-auto">
            {/* All Companies option */}
            <li>
              <button
                onClick={() => { onCompanyChange(null); setOpen(false) }}
                className={`
                  w-full flex items-center gap-3 px-3 py-2.5 text-left transition-colors duration-100
                  ${!selectedCompany
                    ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                    : 'hover:bg-slate-50 dark:hover:bg-slate-700/50 text-slate-700 dark:text-slate-200'
                  }
                `}
              >
                <div className="flex items-center justify-center w-7 h-7 rounded-lg bg-gradient-to-br from-slate-200 to-slate-300 dark:from-slate-700 dark:to-slate-600 shrink-0">
                  <Building2 className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium">All Companies</p>
                  <p className="text-xs text-slate-400 dark:text-slate-500">{companies.length} companies</p>
                </div>
                {!selectedCompany && <Check className="w-4 h-4 text-blue-500 shrink-0" />}
              </button>
            </li>

            {/* Divider */}
            <li className="mx-3 my-1 border-t border-slate-100 dark:border-slate-700/60" />

            {/* Company options */}
            {companies.map((c) => {
              const isSelected = selectedCompany?.id === c.id
              return (
                <li key={c.id}>
                  <button
                    onClick={() => { onCompanyChange(c); setOpen(false) }}
                    className={`
                      w-full flex items-center gap-3 px-3 py-2.5 text-left transition-colors duration-100
                      ${isSelected
                        ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                        : 'hover:bg-slate-50 dark:hover:bg-slate-700/50 text-slate-700 dark:text-slate-200'
                      }
                    `}
                  >
                    <div className={`
                      flex items-center justify-center w-7 h-7 rounded-lg shrink-0 text-[10px] font-bold
                      ${isSelected
                        ? 'bg-gradient-to-br from-blue-500 to-purple-500 text-white'
                        : 'bg-gradient-to-br from-blue-100 to-purple-100 dark:from-blue-900/40 dark:to-purple-900/40 text-blue-600 dark:text-blue-400'
                      }
                    `}>
                      {c.company_name.charAt(0).toUpperCase()}
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <p className="text-sm font-medium truncate">{c.company_name}</p>
                      <p className="text-xs text-slate-400 dark:text-slate-500">{c.shortcode}</p>
                    </div>
                    {isSelected && <Check className="w-4 h-4 text-blue-500 shrink-0" />}
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </div>
  )
}

function DashboardHeader({ onRefresh, selectedDays, onDaysChange, healthMetrics, companies = [], selectedCompany, onCompanyChange }) {
  const dayOptions = [
    { value: 7, label: '7 days' },
    { value: 14, label: '14 days' },
    { value: 30, label: '30 days' },
    { value: 60, label: '60 days' },
    { value: 90, label: '90 days' }
  ]

  const getMomentumBadge = () => {
    if (!healthMetrics) return null

    const momentum = healthMetrics.growth_momentum
    const successRate = healthMetrics.success_rate

    let bgColor, textColor, icon, label

    switch (momentum) {
      case 'accelerating':
        bgColor = 'bg-emerald-100 dark:bg-emerald-900/30'
        textColor = 'text-emerald-700 dark:text-emerald-400'
        icon = <TrendingUp className="w-4 h-4" />
        label = 'Growth Accelerating'
        break
      case 'declining':
        bgColor = 'bg-red-100 dark:bg-red-900/30'
        textColor = 'text-red-700 dark:text-red-400'
        icon = <TrendingDown className="w-4 h-4" />
        label = 'Declining'
        break
      default:
        bgColor = 'bg-blue-100 dark:bg-blue-900/30'
        textColor = 'text-blue-700 dark:text-blue-400'
        icon = <Minus className="w-4 h-4" />
        label = 'Stable'
    }

    return (
      <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-full ${bgColor} ${textColor}`}>
        {icon}
        <span className="text-sm font-medium">{label}</span>
        <span className="text-xs opacity-75">({successRate}% success rate)</span>
      </div>
    )
  }

  return (
    <div className='flex flex-col lg:flex-row lg:items-center justify-between gap-4'>
      <div>
        <h1 className='text-3xl md:text-4xl font-bold bg-gradient-to-r from-slate-800 via-blue-600 to-purple-600 dark:from-white dark:via-blue-400 dark:to-purple-400 bg-clip-text text-transparent mb-2'>
          Business Analytics
        </h1>
        <p className='text-slate-600 dark:text-slate-400'>
          Transaction insights and performance metrics
        </p>
      </div>

      <div className='flex flex-wrap items-center gap-3'>
        {/* Company Selector */}
        {companies.length > 0 && (
          <CompanyDropdown
            companies={companies}
            selectedCompany={selectedCompany}
            onCompanyChange={onCompanyChange}
          />
        )}

        {/* Date Range Selector */}
        <div className="flex items-center space-x-2 bg-white/80 dark:bg-slate-800/80 rounded-xl px-3 py-2 border border-slate-200 dark:border-slate-700">
          <Calendar className="w-4 h-4 text-slate-500" />
          <select
            value={selectedDays}
            onChange={(e) => onDaysChange(Number(e.target.value))}
            className="bg-transparent text-sm font-medium text-slate-700 dark:text-slate-300 focus:outline-none cursor-pointer"
          >
            {dayOptions.map(option => (
              <option key={option.value} value={option.value}>
                Last {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* Refresh Button */}
        <button
          onClick={onRefresh}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-medium transition-all duration-200 shadow-lg shadow-blue-600/30 hover:shadow-blue-600/40"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Refresh</span>
        </button>
      </div>
    </div>
  )
}

export default DashboardHeader