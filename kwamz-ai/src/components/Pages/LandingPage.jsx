import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Shield,
  BarChart3,
  Bell,
  Zap,
  Users,
  Lock,
  ChevronRight,
  Check,
  Menu,
  X,
  ArrowRight,
  Globe,
  CreditCard,
  Eye,
} from 'lucide-react';

function LandingPage() {
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const features = [
    {
      icon: Shield,
      title: 'Real-Time Fraud Detection',
      description:
        'AI-powered monitoring that identifies suspicious transactions instantly, protecting your business around the clock.',
    },
    {
      icon: BarChart3,
      title: 'Advanced Analytics',
      description:
        'Comprehensive dashboards with actionable insights into transaction trends, revenue patterns, and risk metrics.',
    },
    {
      icon: Bell,
      title: 'Instant Alerts',
      description:
        'Get notified the moment anomalies are detected. Configure thresholds and channels to match your workflow.',
    },
    {
      icon: Users,
      title: 'Role-Based Access',
      description:
        'Granular permissions for Admins, Agents, and Users ensure the right people see the right data.',
    },
    {
      icon: CreditCard,
      title: 'Payment Integration',
      description:
        'Seamless integration with M-Pesa and PesaPal for real-time transaction tracking and reconciliation.',
    },
    {
      icon: Lock,
      title: 'Enterprise Security',
      description:
        'End-to-end encryption, JWT authentication, and KYC document verification keep your platform secure.',
    },
  ];

  const pricingPlans = [
    {
      name: 'Pay As You Grow',
      price: '200',
      currency: 'KES',
      period: '/active till per month',
      description: 'Simple, transparent pricing — you only pay for the tills you actively manage.',
      features: [
        'KES 200 per active till per month',
        'Full fraud detection on all tills',
        'Real-time transaction monitoring',
        'Analytics dashboard & reports',
        'M-Pesa & PesaPal integration',
        'Role-based team access',
        'Email & SMS alerts',
      ],
      cta: 'Get Started',
      highlighted: true,
    },
  ];

  const stats = [
    { value: '99.7%', label: 'Detection Accuracy' },
    { value: '<50ms', label: 'Response Time' },
    { value: '10M+', label: 'Transactions Monitored' },
    { value: '100+', label: 'Tills Managed' },
  ];

  return (
    <div className="min-h-screen bg-black text-white overflow-x-hidden">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-yellow-900/30 bg-black/80 backdrop-blur-xl">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-yellow-400 to-yellow-600">
                <Shield className="h-5 w-5 text-black" />
              </div>
              <span className="text-xl font-bold tracking-tight">
                <span className="text-yellow-400">Kwamz</span>
                <span className="text-white">-AI</span>
              </span>
            </div>

            {/* Desktop nav */}
            <div className="hidden items-center gap-8 md:flex">
              <a href="#features" className="text-sm text-gray-400 transition hover:text-yellow-400">
                Features
              </a>
              <a href="#pricing" className="text-sm text-gray-400 transition hover:text-yellow-400">
                Pricing
              </a>
              <a href="#about" className="text-sm text-gray-400 transition hover:text-yellow-400">
                About
              </a>
              <button
                onClick={() => navigate('/login')}
                className="text-sm font-medium text-yellow-400 transition hover:text-yellow-300"
              >
                Sign In
              </button>
              <button
                onClick={() => navigate('/signup')}
                className="rounded-lg bg-gradient-to-r from-yellow-500 to-yellow-600 px-5 py-2 text-sm font-semibold text-black transition hover:from-yellow-400 hover:to-yellow-500 hover:shadow-lg hover:shadow-yellow-500/25"
              >
                Get Started
              </button>
            </div>

            {/* Mobile menu toggle */}
            <button
              className="md:hidden text-gray-400 hover:text-yellow-400"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        {mobileMenuOpen && (
          <div className="border-t border-yellow-900/30 bg-black/95 backdrop-blur-xl md:hidden">
            <div className="space-y-1 px-4 py-4">
              <a
                href="#features"
                className="block rounded-lg px-3 py-2 text-sm text-gray-400 hover:bg-yellow-900/20 hover:text-yellow-400"
                onClick={() => setMobileMenuOpen(false)}
              >
                Features
              </a>
              <a
                href="#pricing"
                className="block rounded-lg px-3 py-2 text-sm text-gray-400 hover:bg-yellow-900/20 hover:text-yellow-400"
                onClick={() => setMobileMenuOpen(false)}
              >
                Pricing
              </a>
              <a
                href="#about"
                className="block rounded-lg px-3 py-2 text-sm text-gray-400 hover:bg-yellow-900/20 hover:text-yellow-400"
                onClick={() => setMobileMenuOpen(false)}
              >
                About
              </a>
              <div className="flex flex-col gap-2 pt-3">
                <button
                  onClick={() => navigate('/login')}
                  className="rounded-lg border border-yellow-600/50 px-4 py-2 text-sm font-medium text-yellow-400 transition hover:bg-yellow-900/20"
                >
                  Sign In
                </button>
                <button
                  onClick={() => navigate('/signup')}
                  className="rounded-lg bg-gradient-to-r from-yellow-500 to-yellow-600 px-4 py-2 text-sm font-semibold text-black transition hover:from-yellow-400 hover:to-yellow-500"
                >
                  Get Started
                </button>
              </div>
            </div>
          </div>
        )}
      </nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 sm:pt-40 sm:pb-28">
        {/* Background effects */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 left-1/2 h-[600px] w-[600px] -translate-x-1/2 rounded-full bg-yellow-500/10 blur-[120px]" />
          <div className="absolute top-20 right-0 h-[400px] w-[400px] rounded-full bg-yellow-600/5 blur-[100px]" />
          <div className="absolute bottom-0 left-0 h-[300px] w-[300px] rounded-full bg-yellow-700/5 blur-[80px]" />
        </div>

        <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-3xl text-center">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-yellow-600/30 bg-yellow-900/20 px-4 py-1.5 text-sm text-yellow-400">
              <Zap className="h-4 w-4" />
              AI-Powered Fraud Detection Platform
            </div>

            <h1 className="text-4xl font-extrabold tracking-tight sm:text-6xl lg:text-7xl">
              Protect Every{' '}
              <span className="bg-gradient-to-r from-yellow-300 via-yellow-400 to-yellow-600 bg-clip-text text-transparent">
                Transaction
              </span>
            </h1>

            <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-gray-400 sm:text-xl">
              Kwamz-AI monitors your financial transactions in real time, detects fraud before it
              happens, and gives you the analytics you need to grow with confidence.
            </p>

            <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
              <button
                onClick={() => navigate('/signup')}
                className="group flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-yellow-500 to-yellow-600 px-8 py-3.5 text-base font-semibold text-black transition hover:from-yellow-400 hover:to-yellow-500 hover:shadow-xl hover:shadow-yellow-500/20 sm:w-auto"
              >
                Start Free Trial
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </button>
              <button
                onClick={() => {
                  document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' });
                }}
                className="flex w-full items-center justify-center gap-2 rounded-xl border border-gray-700 px-8 py-3.5 text-base font-medium text-gray-300 transition hover:border-yellow-600/50 hover:text-yellow-400 sm:w-auto"
              >
                Learn More
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Stats */}
          <div className="mx-auto mt-20 grid max-w-4xl grid-cols-2 gap-6 sm:grid-cols-4">
            {stats.map((stat) => (
              <div
                key={stat.label}
                className="rounded-2xl border border-yellow-900/30 bg-gradient-to-b from-yellow-900/10 to-transparent p-6 text-center"
              >
                <div className="text-3xl font-bold text-yellow-400 sm:text-4xl">{stat.value}</div>
                <div className="mt-1 text-sm text-gray-500">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="relative py-24">
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-yellow-950/5 to-transparent" />
        </div>

        <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Everything You Need to{' '}
              <span className="text-yellow-400">Stay Secure</span>
            </h2>
            <p className="mt-4 text-lg text-gray-400">
              A complete suite of tools to detect fraud, monitor transactions, and manage your
              financial operations with ease.
            </p>
          </div>

          <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((feature) => (
              <div
                key={feature.title}
                className="group rounded-2xl border border-gray-800 bg-gray-900/50 p-6 transition hover:border-yellow-600/40 hover:bg-gray-900/80"
              >
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-yellow-900/30 text-yellow-400 transition group-hover:bg-yellow-900/50">
                  <feature.icon className="h-6 w-6" />
                </div>
                <h3 className="text-lg font-semibold text-white">{feature.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-gray-400">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              How <span className="text-yellow-400">Kwamz-AI</span> Works
            </h2>
            <p className="mt-4 text-lg text-gray-400">
              Get up and running in minutes with a simple three-step process.
            </p>
          </div>

          <div className="mt-16 grid gap-8 md:grid-cols-3">
            {[
              {
                step: '01',
                icon: Globe,
                title: 'Connect Your Accounts',
                description:
                  'Integrate your payment channels — M-Pesa, PesaPal, or custom APIs — in just a few clicks.',
              },
              {
                step: '02',
                icon: Eye,
                title: 'Monitor in Real Time',
                description:
                  'Our AI engine analyzes every transaction as it flows through, flagging anomalies instantly.',
              },
              {
                step: '03',
                icon: Shield,
                title: 'Act on Insights',
                description:
                  'Review alerts, generate reports, and take action from your personalized dashboard.',
              },
            ].map((item) => (
              <div key={item.step} className="relative text-center">
                <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full border-2 border-yellow-600/40 bg-yellow-900/20">
                  <item.icon className="h-7 w-7 text-yellow-400" />
                </div>
                <div className="mb-2 text-xs font-bold uppercase tracking-widest text-yellow-600">
                  Step {item.step}
                </div>
                <h3 className="text-xl font-semibold text-white">{item.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-gray-400">{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="relative py-24">
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-yellow-950/5 to-transparent" />
        </div>

        <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Simple, <span className="text-yellow-400">Transparent</span> Pricing
            </h2>
            <p className="mt-4 text-lg text-gray-400">
              Pay only for what you use. No hidden fees, no surprises — just one flat rate per active till.
            </p>
          </div>

          <div className="mx-auto mt-16 max-w-lg">
            {pricingPlans.map((plan) => (
              <div
                key={plan.name}
                className="relative rounded-2xl border border-yellow-500/60 bg-gradient-to-b from-yellow-900/20 via-yellow-900/10 to-transparent p-8 shadow-xl shadow-yellow-500/10"
              >
                <div className="mb-6">
                  <h3 className="text-lg font-semibold text-white">{plan.name}</h3>
                  <p className="mt-1 text-sm text-gray-400">{plan.description}</p>
                </div>

                <div className="mb-6 flex items-baseline">
                  <span className="text-sm font-medium text-gray-500">{plan.currency}</span>
                  <span className="ml-1 text-5xl font-bold text-white">{plan.price}</span>
                  <span className="ml-2 text-sm text-gray-500">{plan.period}</span>
                </div>

                <ul className="mb-8 space-y-3">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-3 text-sm text-gray-300">
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-yellow-500" />
                      {feature}
                    </li>
                  ))}
                </ul>

                <button
                  onClick={() => navigate('/signup')}
                  className="w-full rounded-xl bg-gradient-to-r from-yellow-500 to-yellow-600 py-3 text-sm font-semibold text-black transition hover:from-yellow-400 hover:to-yellow-500 hover:shadow-lg hover:shadow-yellow-500/20"
                >
                  {plan.cta}
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* About / CTA Section */}
      <section id="about" className="py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="overflow-hidden rounded-3xl border border-yellow-900/30 bg-gradient-to-br from-yellow-900/20 via-black to-yellow-950/10">
            <div className="px-8 py-16 text-center sm:px-16">
              <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
                Ready to Secure Your Business?
              </h2>
              <p className="mx-auto mt-4 max-w-xl text-lg text-gray-400">
                Join hundreds of businesses across Africa that trust Kwamz-AI to protect their
                financial transactions and grow with confidence.
              </p>
              <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
                <button
                  onClick={() => navigate('/signup')}
                  className="group flex items-center gap-2 rounded-xl bg-gradient-to-r from-yellow-500 to-yellow-600 px-8 py-3.5 text-base font-semibold text-black transition hover:from-yellow-400 hover:to-yellow-500 hover:shadow-xl hover:shadow-yellow-500/20"
                >
                  Get Started for Free
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                </button>
                <a
                  href="mailto:support@kwamz-ai.org"
                  className="flex items-center gap-2 rounded-xl border border-gray-700 px-8 py-3.5 text-base font-medium text-gray-300 transition hover:border-yellow-600/50 hover:text-yellow-400"
                >
                  Contact Sales
                </a>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-800 bg-black py-12">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {/* Brand */}
            <div className="sm:col-span-2 lg:col-span-1">
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-yellow-400 to-yellow-600">
                  <Shield className="h-4 w-4 text-black" />
                </div>
                <span className="text-lg font-bold">
                  <span className="text-yellow-400">Kwamz</span>-AI
                </span>
              </div>
              <p className="mt-3 text-sm leading-relaxed text-gray-500">
                AI-powered fraud detection and transaction monitoring for businesses across Africa.
              </p>
            </div>

            {/* Product */}
            <div>
              <h4 className="text-sm font-semibold uppercase tracking-wider text-gray-400">
                Product
              </h4>
              <ul className="mt-4 space-y-2">
                {['Features', 'Pricing', 'Security', 'Integrations'].map((item) => (
                  <li key={item}>
                    <a href="#" className="text-sm text-gray-500 transition hover:text-yellow-400">
                      {item}
                    </a>
                  </li>
                ))}
              </ul>
            </div>

            {/* Company */}
            <div>
              <h4 className="text-sm font-semibold uppercase tracking-wider text-gray-400">
                Company
              </h4>
              <ul className="mt-4 space-y-2">
                {['About', 'Blog', 'Careers', 'Contact'].map((item) => (
                  <li key={item}>
                    <a href="#" className="text-sm text-gray-500 transition hover:text-yellow-400">
                      {item}
                    </a>
                  </li>
                ))}
              </ul>
            </div>

            {/* Legal */}
            <div>
              <h4 className="text-sm font-semibold uppercase tracking-wider text-gray-400">
                Legal
              </h4>
              <ul className="mt-4 space-y-2">
                {['Privacy Policy', 'Terms of Service', 'Cookie Policy'].map((item) => (
                  <li key={item}>
                    <a href="#" className="text-sm text-gray-500 transition hover:text-yellow-400">
                      {item}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="mt-12 border-t border-gray-800 pt-8 text-center text-sm text-gray-600">
            &copy; {new Date().getFullYear()} Kwamz-AI. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
}

export default LandingPage;
