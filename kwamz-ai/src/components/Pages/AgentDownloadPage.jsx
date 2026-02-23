const steps = [
  {
    number: '1',
    title: 'Download for your OS',
    description: 'Click the button below that matches your operating system — Linux or Windows.',
  },
  {
    number: '2',
    title: 'Extract the zip',
    description: 'Unzip the file to a permanent folder on your computer, e.g. C:\\kwamz-agent or ~/kwamz-agent. Do not move individual files out of the folder.',
  },
  {
    number: '3',
    title: 'Create a .env file',
    description: (
      <>
        Inside the extracted folder, create a file named{' '}
        <code className="bg-gray-100 px-1 rounded text-sm">.env</code> with the
        following contents (your administrator will supply the values):
        <pre className="mt-2 bg-gray-100 rounded-lg p-3 text-xs text-gray-700 whitespace-pre leading-relaxed">
{`BACKEND_URL=https://kwamz-ai.org
AGENT_SECRET=your-secret-here
POLL_INTERVAL=30`}
        </pre>
      </>
    ),
  },
  {
    number: '4',
    title: 'Run the agent',
    description: (
      <>
        <strong>Linux:</strong> open a terminal in the folder and run{' '}
        <code className="bg-gray-100 px-1 rounded text-sm">./mpesa_agent</code>.
        <br />
        <strong>Windows:</strong> double-click{' '}
        <code className="bg-gray-100 px-1 rounded text-sm">mpesa_agent.exe</code>.
      </>
    ),
  },
  {
    number: '5',
    title: "You're ready",
    description:
      'The agent window will show "No pending jobs" while idle. When a job is submitted from the dashboard it will open a browser window automatically and process it.',
  },
];

export default function AgentDownloadPage() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center px-4 py-16">
      {/* Header */}
      <div className="text-center mb-12 max-w-xl">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-green-600 mb-5">
          <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
        </div>
        <h1 className="text-3xl font-bold text-gray-900 mb-3">Kwamz AI Desktop Agent</h1>
        <p className="text-gray-500 text-base leading-relaxed">
          A lightweight desktop app that runs Mpesa, KRA, and DCI automations on your
          machine — no browser extension required.
        </p>
      </div>

      {/* Download cards */}
      <div className="w-full max-w-lg space-y-4 mb-10">
        {/* Linux */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-semibold text-gray-700">Linux (x86-64)</span>
            <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">Ubuntu · Fedora · Debian</span>
          </div>
          <p className="text-xs text-gray-400 mb-5">Standalone folder — no Python install needed</p>
          <a
            href="/api/agent/downloads/mpesa_agent-linux.zip"
            download="mpesa_agent-linux.zip"
            className="flex items-center justify-center gap-2 w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 rounded-xl transition-colors text-sm"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Download for Linux (.zip)
          </a>
        </div>

        {/* Windows */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-semibold text-gray-700">Windows (x86-64)</span>
            <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">Windows 10 · 11</span>
          </div>
          <p className="text-xs text-gray-400 mb-5">Standalone folder — no Python install needed</p>
          <a
            href="/api/agent/downloads/mpesa_agent-windows.zip"
            download="mpesa_agent-windows.zip"
            className="flex items-center justify-center gap-2 w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 rounded-xl transition-colors text-sm"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Download for Windows (.zip)
          </a>
        </div>
      </div>

      {/* Steps */}
      <div className="w-full max-w-lg">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-5">
          Setup instructions
        </h2>
        <ol className="space-y-5">
          {steps.map((step) => (
            <li key={step.number} className="flex gap-4">
              <span className="flex-shrink-0 w-7 h-7 rounded-full bg-green-100 text-green-700 text-xs font-bold flex items-center justify-center mt-0.5">
                {step.number}
              </span>
              <div>
                <p className="font-semibold text-gray-800 text-sm mb-0.5">{step.title}</p>
                <div className="text-gray-500 text-sm leading-relaxed">{step.description}</div>
              </div>
            </li>
          ))}
        </ol>
      </div>

      {/* Footer note */}
      <p className="mt-12 text-xs text-gray-400 text-center max-w-sm">
        The agent communicates only with kwamz-ai.org using a shared secret.
        It does not send data to any third party.
      </p>
    </div>
  );
}
