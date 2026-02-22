import { useState } from 'react';

const steps = [
  {
    number: '1',
    title: 'Download the extension',
    description: 'Click the button below to download the Kwamz AI Verifier extension zip file.',
  },
  {
    number: '2',
    title: 'Unzip the file',
    description: 'Extract the downloaded zip file to a folder on your computer — remember where you put it.',
  },
  {
    number: '3',
    title: 'Open Chrome Extensions',
    description: (
      <>
        In Chrome, go to{' '}
        <code className="bg-gray-100 px-1 rounded text-sm">chrome://extensions</code>{' '}
        and enable <strong>Developer mode</strong> using the toggle in the top-right corner.
      </>
    ),
  },
  {
    number: '4',
    title: 'Load the extension',
    description: 'Click "Load unpacked" and select the folder you extracted in step 2.',
  },
  {
    number: '5',
    title: "You're ready",
    description:
      'Pin the Kwamz AI Verifier icon to your toolbar. It will automatically run verifications whenever you submit a request — no further setup needed.',
  },
];

export default function ExtensionDownloadPage() {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText('chrome://extensions');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center px-4 py-16">
      {/* Header */}
      <div className="text-center mb-12 max-w-xl">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-600 mb-5">
          <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
        </div>
        <h1 className="text-3xl font-bold text-gray-900 mb-3">Kwamz AI Verifier</h1>
        <p className="text-gray-500 text-base leading-relaxed">
          A Chrome extension that runs KRA PIN and Police Clearance verification
          directly in your browser — no manual steps, no waiting.
        </p>
      </div>

      {/* Download card */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 w-full max-w-lg p-8 mb-10">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-semibold text-gray-700">Kwamz AI Verifier</span>
          <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">Chrome Extension</span>
        </div>
        <p className="text-xs text-gray-400 mb-6">Manifest V3 · Works on Chrome 88+</p>

        <a
          href="/api/verification/download-extension"
          download="kwamz-verifier.zip"
          className="flex items-center justify-center gap-2 w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 rounded-xl transition-colors text-sm"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Download Extension (.zip)
        </a>
      </div>

      {/* Steps */}
      <div className="w-full max-w-lg">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-5">
          Installation steps
        </h2>
        <ol className="space-y-5">
          {steps.map((step) => (
            <li key={step.number} className="flex gap-4">
              <span className="flex-shrink-0 w-7 h-7 rounded-full bg-blue-100 text-blue-700 text-xs font-bold flex items-center justify-center mt-0.5">
                {step.number}
              </span>
              <div>
                <p className="font-semibold text-gray-800 text-sm mb-0.5">{step.title}</p>
                <p className="text-gray-500 text-sm leading-relaxed">{step.description}</p>
                {step.number === '3' && (
                  <button
                    onClick={handleCopy}
                    className="mt-2 text-xs text-blue-600 hover:underline"
                  >
                    {copied ? 'Copied!' : 'Copy chrome://extensions'}
                  </button>
                )}
              </div>
            </li>
          ))}
        </ol>
      </div>

      {/* Footer note */}
      <p className="mt-12 text-xs text-gray-400 text-center max-w-sm">
        The extension communicates only with kwamz-ai.org. It does not collect or
        store any personal data beyond what is needed to complete verification.
      </p>
    </div>
  );
}
