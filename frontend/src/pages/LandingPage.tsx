import { Link } from 'react-router-dom'
import { AUTH0_CONFIGURED, useAuthToken } from '../hooks/useAuthToken'

export function LandingPage() {
  const { login, isAuthenticated } = useAuthToken()

  return (
    <section className="relative -mx-5 -mt-8 min-h-[calc(100vh-4rem)] overflow-hidden px-5">
      {/* Full-bleed atmospheric plane */}
      <div
        className="pointer-events-none absolute inset-0 -z-10"
        aria-hidden
      >
        <div className="absolute inset-0 bg-[linear-gradient(135deg,#0b1f1a_0%,#14352c_45%,#1a4a3a_100%)]" />
        <svg
          className="absolute inset-0 h-full w-full opacity-40"
          viewBox="0 0 1200 700"
          preserveAspectRatio="xMidYMid slice"
        >
          <defs>
            <linearGradient id="lineGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#1fa67a" stopOpacity="0" />
              <stop offset="40%" stopColor="#2dd4a0" stopOpacity="0.9" />
              <stop offset="100%" stopColor="#8fe3c4" stopOpacity="0.2" />
            </linearGradient>
          </defs>
          <path
            d="M0 480 C180 420 260 520 400 400 C520 300 580 340 720 280 C880 200 980 320 1200 220"
            fill="none"
            stroke="url(#lineGrad)"
            strokeWidth="3"
            strokeDasharray="8 10"
            style={{ animation: 'pulse-line 4s ease-in-out infinite' }}
          />
          <path
            d="M0 520 C200 480 300 560 450 460 C600 360 700 400 850 340 C1000 280 1100 360 1200 300"
            fill="none"
            stroke="#8fe3c4"
            strokeOpacity="0.25"
            strokeWidth="1.5"
          />
          <circle cx="720" cy="280" r="6" fill="#2dd4a0" className="animate-rise-delay-2" />
        </svg>
      </div>

      <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-6xl flex-col justify-center py-16 text-paper">
        <p className="animate-rise font-display text-5xl font-extrabold tracking-tight sm:text-7xl md:text-8xl">
          AlphaAI
        </p>
        <h1 className="animate-rise-delay-1 mt-5 max-w-xl text-xl font-medium text-mint/95 sm:text-2xl">
          Your AI hedge fund desk — research, explain, paper-trade.
        </h1>
        <p className="animate-rise-delay-2 mt-4 max-w-md text-sm leading-relaxed text-paper/70">
          Generate strategies, analyze equities with clear reasoning, and simulate
          trades with fake money. Strategies verified on Solana.
        </p>
        <div className="animate-rise-delay-3 mt-8 flex flex-wrap gap-3">
          {AUTH0_CONFIGURED && !isAuthenticated ? (
            <button
              type="button"
              onClick={() => login()}
              className="bg-signal px-6 py-3 text-sm font-semibold text-ink hover:bg-signal-bright transition-colors"
            >
              Log in to open desk
            </button>
          ) : (
            <Link
              to="/dashboard"
              className="bg-signal px-6 py-3 text-sm font-semibold text-ink hover:bg-signal-bright transition-colors"
            >
              Open dashboard
            </Link>
          )}
          <Link
            to="/strategy"
            className="border border-paper/30 px-6 py-3 text-sm font-medium text-paper hover:border-mint hover:text-mint transition-colors"
          >
            Generate strategy
          </Link>
        </div>
      </div>
    </section>
  )
}
