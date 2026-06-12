import { useState, useEffect, useRef } from 'react';
import { ArrowUp, TrendingUp, ChevronDown, Calendar, Loader2 } from 'lucide-react';
import { analyticsApi } from '../../service/AnalyticsApi';

const MONTHS = [
  'Jan','Feb','Mar','Apr','May','Jun',
  'Jul','Aug','Sep','Oct','Nov','Dec'
];

const MONTHS_FULL = [
  'January','February','March','April','May','June',
  'July','August','September','October','November','December'
];

function formatCurrency(value) {
  if (value == null) return '—';
  return `KES ${value.toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function buildYearOptions() {
  const current = new Date().getFullYear();
  return [current, current - 1, current - 2];
}

function PillDropdown({ value, options, onChange, renderLabel, renderOption, width = 'w-36' }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    function onClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(o => !o)}
        className={`
          flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold
          bg-purple-50 dark:bg-purple-900/30
          text-purple-700 dark:text-purple-300
          border border-purple-200 dark:border-purple-700/50
          hover:bg-purple-100 dark:hover:bg-purple-800/40
          transition-colors duration-150 cursor-pointer select-none
        `}
      >
        <Calendar className="w-3 h-3 opacity-70" />
        {renderLabel(value)}
        <ChevronDown className={`w-3 h-3 opacity-60 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className={`
          absolute z-[200] top-full mt-1.5 left-0 ${width}
          bg-white dark:bg-slate-800
          border border-slate-200 dark:border-slate-700
          rounded-xl shadow-xl shadow-slate-200/50 dark:shadow-slate-900/50
          overflow-hidden
          animate-in fade-in slide-in-from-top-1 duration-150
        `}>
          {options.map(opt => (
            <button
              key={opt.value}
              onClick={() => { onChange(opt.value); setOpen(false); }}
              className={`
                w-full text-left px-3 py-2 text-xs font-medium transition-colors duration-100
                ${opt.value === value
                  ? 'bg-purple-500 text-white'
                  : 'text-slate-700 dark:text-slate-300 hover:bg-purple-50 dark:hover:bg-purple-900/20 hover:text-purple-700 dark:hover:text-purple-300'
                }
              `}
            >
              {renderOption ? renderOption(opt) : opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function CommissionsCard({ commissionBalance, selectedCompany, index }) {
  const now = new Date();
  const defaultMonth = now.getMonth() === 0 ? 12 : now.getMonth();
  const defaultYear  = now.getMonth() === 0 ? now.getFullYear() - 1 : now.getFullYear();

  const [month, setMonth] = useState(defaultMonth);
  const [year,  setYear]  = useState(defaultYear);
  const [transferData, setTransferData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setIsVisible(true), index * 100);
    return () => clearTimeout(t);
  }, [index]);

  useEffect(() => {
    setLoading(true);
    const request = selectedCompany?.shortcode
      ? analyticsApi.getCommissionMonthlyTransfer(selectedCompany.shortcode, month, year)
      : analyticsApi.getCommissionMonthlyTransferTotal(month, year);

    request
      .then(res => setTransferData(res.success ? res.data : null))
      .catch(() => setTransferData(null))
      .finally(() => setLoading(false));
  }, [selectedCompany, month, year]);

  const monthOptions = MONTHS.map((m, i) => ({ value: i + 1, label: MONTHS_FULL[i], short: m }));
  const yearOptions  = buildYearOptions().map(y => ({ value: y, label: String(y) }));

  const previousValue = loading
    ? null
    : transferData?.amount != null ? formatCurrency(transferData.amount) : '—';

  const subLabel = transferData?.amount != null
    ? transferData.as_of
      ? `MMF transfer · ${new Date(transferData.as_of).toLocaleDateString('en-KE', { day: 'numeric', month: 'short', year: 'numeric' })}`
      : `${transferData.company_count ?? ''} company transfer(s) to MMF`
    : loading ? '' : 'No transfer recorded for this period';

  return (
    <div className={`relative z-20 transform transition-all duration-500 ${isVisible ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'}`}>
      <div className="bg-white/90 dark:bg-slate-800/90 backdrop-blur-xl rounded-2xl border border-slate-200/50 dark:border-slate-700/50 hover:shadow-2xl hover:shadow-slate-200/30 dark:hover:shadow-slate-900/30 transition-all duration-300 group hover:-translate-y-1">

        {/* ── Current Balance ──────────────────────────────────────── */}
        <div className="p-6 pb-4">
          <div className="flex items-start justify-between mb-3">
            <div className="flex-1">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500 mb-1">
                Current Balance
              </p>
              <p className="text-3xl font-bold text-slate-800 dark:text-white mb-2">
                {commissionBalance != null ? formatCurrency(commissionBalance) : '—'}
              </p>
              <div className="flex items-center space-x-1">
                <ArrowUp className="w-3 h-3 text-emerald-500" />
                <span className="text-xs text-slate-400">closing balance</span>
              </div>
            </div>
            <div className="p-3 rounded-xl bg-gradient-to-br from-purple-500/20 to-pink-500/20 group-hover:scale-110 transition-transform duration-300">
              <TrendingUp className="w-6 h-6 text-purple-600" />
            </div>
          </div>
        </div>

        {/* Divider */}
        <div className="mx-6 border-t border-slate-100 dark:border-slate-700/60" />

        {/* ── Previous Period ──────────────────────────────────────── */}
        <div className="p-6 pt-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500 mb-3">
            Previous Period
          </p>

          {/* Custom pill dropdowns */}
          <div className="flex gap-2 mb-4 flex-wrap">
            <PillDropdown
              value={month}
              options={monthOptions}
              onChange={setMonth}
              renderLabel={v => MONTHS_FULL[v - 1]}
              renderOption={opt => opt.label}
              width="w-36"
            />
            <PillDropdown
              value={year}
              options={yearOptions}
              onChange={setYear}
              renderLabel={v => String(v)}
              width="w-20"
            />
          </div>

          {/* Amount */}
          <div className="min-h-[3rem]">
            {loading ? (
              <div className="flex items-center gap-2 text-slate-400">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-sm">Loading...</span>
              </div>
            ) : (
              <>
                <p className={`text-2xl font-bold mb-1 ${
                  transferData?.amount != null
                    ? 'text-slate-800 dark:text-white'
                    : 'text-slate-300 dark:text-slate-600'
                }`}>
                  {previousValue}
                </p>
                <p className="text-xs text-slate-400 dark:text-slate-500">{subLabel}</p>
              </>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
