import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import * as XLSX from 'xlsx';
import { MessageCircle, X, Send, Bot, User, Loader2, Download, Table2 } from 'lucide-react';
import config from '../Config';

/* ── helpers ─────────────────────────────────────────────── */

function exportExcel(datasets, filename = 'chat-export') {
  const wb = XLSX.utils.book_new();
  const usedNames = new Set();
  datasets.forEach(({ label, rows }) => {
    // Excel sheet names max 31 chars, must be unique
    let name = (label || 'Data').slice(0, 31);
    if (usedNames.has(name)) name = name.slice(0, 28) + (usedNames.size + 1);
    usedNames.add(name);
    const ws = XLSX.utils.json_to_sheet(rows);
    XLSX.utils.book_append_sheet(wb, ws, name);
  });
  XLSX.writeFile(wb, `${filename}.xlsx`);
}

function prettify(key) {
  return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function fmt(val) {
  if (val === null || val === undefined) return '—';
  if (typeof val === 'number') return val.toLocaleString();
  if (typeof val === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(val))
    return new Date(val).toLocaleString();
  return String(val);
}

/* ── SingleTable ─────────────────────────────────────────── */

function SingleTable({ label, rows }) {
  const [show, setShow] = useState(false);
  if (!rows?.length) return null;
  const cols = Object.keys(rows[0]);

  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-600 overflow-hidden text-xs">
      <button
        onClick={() => setShow(s => !s)}
        className="w-full flex items-center justify-between px-3 py-2 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
      >
        <span className="flex items-center gap-1.5 text-slate-600 dark:text-slate-300 font-medium">
          <Table2 size={12} />
          {label} <span className="text-slate-400 font-normal">({rows.length} row{rows.length !== 1 ? 's' : ''})</span>
        </span>
        <span className="text-slate-400 text-[10px]">{show ? '▲' : '▼'}</span>
      </button>

      {show && (
        <div className="overflow-x-auto max-h-48">
          <table className="w-full border-collapse text-left">
            <thead className="bg-slate-50 dark:bg-slate-800 sticky top-0">
              <tr>
                {cols.map(c => (
                  <th key={c} className="px-3 py-2 font-semibold text-slate-600 dark:text-slate-300 whitespace-nowrap border-b border-slate-200 dark:border-slate-600">
                    {prettify(c)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i} className={i % 2 === 0 ? 'bg-white dark:bg-slate-900' : 'bg-slate-50 dark:bg-slate-800'}>
                  {cols.map(c => (
                    <td key={c} className="px-3 py-1.5 text-slate-700 dark:text-slate-200 whitespace-nowrap border-b border-slate-100 dark:border-slate-700">
                      {fmt(row[c])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/* ── DataPanel (multiple tables + export) ────────────────── */

function DataPanel({ datasets, onExport }) {
  if (!datasets?.length) return null;
  const totalRows = datasets.reduce((s, d) => s + d.rows.length, 0);

  return (
    <div className="mt-2 rounded-xl border border-slate-200 dark:border-slate-600 overflow-hidden text-xs">
      {/* export toolbar */}
      <div className="flex items-center justify-between px-3 py-2 bg-indigo-50 dark:bg-indigo-900/30 border-b border-slate-200 dark:border-slate-600">
        <span className="text-slate-500 dark:text-slate-400">
          {datasets.length} dataset{datasets.length !== 1 ? 's' : ''} · {totalRows} rows total
        </span>
        <button
          onClick={onExport}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium transition-colors"
        >
          <Download size={12} />
          Download Excel ({datasets.length} sheet{datasets.length !== 1 ? 's' : ''})
        </button>
      </div>

      {/* individual tables */}
      <div className="divide-y divide-slate-100 dark:divide-slate-700">
        {datasets.map((d, i) => (
          <SingleTable key={i} label={d.label} rows={d.rows} />
        ))}
      </div>
    </div>
  );
}

/* ── Message ─────────────────────────────────────────────── */

function Message({ role, content, data, msgIndex }) {
  const isUser = role === 'user';
  return (
    <div className={`flex gap-2 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      <div className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-white text-xs
        ${isUser ? 'bg-blue-500' : 'bg-indigo-600'}`}>
        {isUser ? <User size={13} /> : <Bot size={13} />}
      </div>
      <div className={`max-w-[85%] ${isUser ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
        <div className={`rounded-2xl px-3 py-2 text-sm leading-relaxed whitespace-pre-wrap
          ${isUser
            ? 'bg-blue-500 text-white rounded-tr-sm'
            : 'bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100 rounded-tl-sm shadow-sm border border-slate-100 dark:border-slate-600'
          }`}>
          {content}
        </div>
        {data?.length > 0 && (
          <DataPanel
            datasets={data}
            onExport={() => exportExcel(data, `kwamz-export-${msgIndex}`)}
          />
        )}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex gap-2">
      <div className="w-7 h-7 rounded-full bg-indigo-600 flex items-center justify-center text-white">
        <Bot size={13} />
      </div>
      <div className="bg-white dark:bg-slate-700 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm border border-slate-100 dark:border-slate-600">
        <div className="flex gap-1 items-center h-4">
          {[0, 1, 2].map(i => (
            <div key={i} className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce"
              style={{ animationDelay: `${i * 0.15}s` }} />
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── Main component ──────────────────────────────────────── */

export default function ChatBubble({ isAuthenticated }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hi! I can help you analyse your M-Pesa data — transactions, swaps, tills, fraud alerts and more. What would you like to know?', data: null }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
      inputRef.current?.focus();
    }
  }, [isOpen, messages]);

  if (!isAuthenticated) return null;

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg = { role: 'user', content: text, data: null };
    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    setInput('');
    setLoading(true);

    try {
      const token = localStorage.getItem('token');
      const history = nextMessages
        .slice(1, -1)
        .slice(-20)
        .map(m => ({ role: m.role, content: m.content }));

      const { data } = await axios.post(
        `${config.API_URL}/chat/message`,
        { message: text, history },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.reply,
        data: data.data || null,
      }]);
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, something went wrong. Please try again.',
        data: null,
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKey = e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  };

  const SUGGESTIONS = [
    'Which till has the most transactions?',
    'What are my total float balances?',
    'Show recent operator swaps',
    'Any fraud alerts this month?',
  ];

  return (
    <>
      {/* Floating button — sits above the LiveScrapeFeed dock (bottom-5) */}
      <button
        onClick={() => setIsOpen(o => !o)}
        className="fixed bottom-20 right-6 z-[9990] w-14 h-14 rounded-full bg-indigo-600 hover:bg-indigo-700
          shadow-lg hover:shadow-xl flex items-center justify-center text-white transition-all duration-200
          hover:scale-105 active:scale-95"
        title="Chat with your data"
      >
        {isOpen ? <X size={22} /> : <MessageCircle size={22} />}
        {!isOpen && (
          <span className="absolute -top-1 -right-1 w-3 h-3 bg-green-400 rounded-full border-2 border-white" />
        )}
      </button>

      {/* Chat panel */}
      {isOpen && (
        <div className="fixed bottom-36 right-6 z-[9989] w-[420px] max-h-[580px] flex flex-col
          bg-slate-50 dark:bg-slate-800 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700
          overflow-hidden">

          {/* Header */}
          <div className="flex items-center gap-3 px-4 py-3 bg-indigo-600 text-white flex-shrink-0">
            <div className="w-8 h-8 rounded-full bg-indigo-500 flex items-center justify-center">
              <Bot size={16} />
            </div>
            <div>
              <p className="font-semibold text-sm">Data Assistant</p>
              <p className="text-xs text-indigo-200">Ask anything · export to Excel</p>
            </div>
            <button onClick={() => setIsOpen(false)} className="ml-auto text-indigo-200 hover:text-white">
              <X size={16} />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">
            {messages.map((m, i) => (
              <Message key={i} role={m.role} content={m.content} data={m.data} msgIndex={i} />
            ))}
            {loading && <TypingIndicator />}
            <div ref={bottomRef} />
          </div>

          {/* Suggestions */}
          {messages.length === 1 && !loading && (
            <div className="px-4 pb-2 flex flex-wrap gap-2">
              {SUGGESTIONS.map(s => (
                <button key={s} onClick={() => { setInput(s); inputRef.current?.focus(); }}
                  className="text-xs px-3 py-1.5 rounded-full bg-white dark:bg-slate-700 border border-slate-200
                    dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:border-indigo-400
                    hover:text-indigo-600 transition-colors">
                  {s}
                </button>
              ))}
            </div>
          )}

          {/* Input */}
          <div className="flex items-end gap-2 px-3 py-3 border-t border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 flex-shrink-0">
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask about your data… (Enter to send)"
              rows={1}
              className="flex-1 resize-none rounded-xl border border-slate-200 dark:border-slate-600
                bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-sm px-3 py-2
                focus:outline-none focus:ring-2 focus:ring-indigo-400 max-h-28 overflow-y-auto"
              style={{ minHeight: '38px' }}
            />
            <button
              onClick={send}
              disabled={!input.trim() || loading}
              className="flex-shrink-0 w-9 h-9 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40
                disabled:cursor-not-allowed flex items-center justify-center text-white transition-colors"
            >
              {loading ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
            </button>
          </div>
        </div>
      )}
    </>
  );
}
