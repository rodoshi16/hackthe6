import { NavLink, Outlet } from 'react-router-dom'
import { useAuthToken, AUTH0_CONFIGURED } from '../hooks/useAuthToken'

const links = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/strategy', label: 'Strategy' },
  { to: '/analyze', label: 'Analyze' },
  { to: '/trade', label: 'Trade' },
  { to: '/predict', label: 'Predict 6ix' },
]

export function Layout() {
  const { isAuthenticated, isLoading, user, login, logout } = useAuthToken()

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-ink/8 bg-paper/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-3">
          <NavLink to="/" className="group flex items-baseline gap-2">
            <span className="font-display text-xl font-extrabold tracking-tight text-ink group-hover:text-signal transition-colors">
              AlphaAI
            </span>
            <span className="hidden text-xs text-muted sm:inline">paper desk</span>
          </NavLink>

          <nav className="hidden items-center gap-1 md:flex">
            {links.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                className={({ isActive }) =>
                  `px-3 py-1.5 text-sm transition-colors ${
                    isActive ? 'text-signal font-semibold' : 'text-muted hover:text-ink'
                  }`
                }
              >
                {l.label}
              </NavLink>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            {!isLoading && isAuthenticated && (
              <span className="hidden text-sm text-muted sm:inline">
                {user?.name?.split(' ')[0] || 'Trader'}
              </span>
            )}
            {AUTH0_CONFIGURED ? (
              isAuthenticated ? (
                <button
                  type="button"
                  onClick={() => logout()}
                  className="text-sm text-muted hover:text-ink transition-colors"
                >
                  Log out
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => login()}
                  className="bg-ink px-3.5 py-1.5 text-sm font-medium text-paper hover:bg-ink-soft transition-colors"
                >
                  Log in
                </button>
              )
            ) : (
              <span className="text-xs text-signal">Demo mode</span>
            )}
          </div>
        </div>

        <nav className="flex gap-1 overflow-x-auto border-t border-ink/5 px-3 py-2 md:hidden">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              className={({ isActive }) =>
                `shrink-0 px-3 py-1 text-sm ${
                  isActive ? 'text-signal font-semibold' : 'text-muted'
                }`
              }
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
      </header>

      <main className="mx-auto max-w-6xl px-5 py-8">
        <Outlet />
      </main>
    </div>
  )
}
