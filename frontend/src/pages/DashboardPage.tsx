import { useEffect, useState } from 'react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Link } from 'react-router-dom'
import { api, type Portfolio, type Trade } from '../api/client'
import { useAuthToken } from '../hooks/useAuthToken'

export function DashboardPage() {
  const { getToken } = useAuthToken()
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null)
  const [history, setHistory] = useState<{ date: string; value: number }[]>([])
  const [trades, setTrades] = useState<Trade[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const token = await getToken()
        const [p, t] = await Promise.all([
          api.getPortfolio(token),
          api.getTrades(token),
        ])
        if (!cancelled) {
          setPortfolio(p.portfolio)
          setHistory(
            p.history.length
              ? p.history
              : [
                  { date: 'Start', value: p.portfolio.startingBalance },
                  { date: 'Now', value: p.portfolio.currentValue },
                ],
          )
          setTrades(t.trades)
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [getToken])

  if (loading) {
    return <p className="text-muted animate-rise">Loading portfolio…</p>
  }

  if (error || !portfolio) {
    return (
      <div className="animate-rise">
        <p className="text-danger">{error || 'No portfolio'}</p>
        <p className="mt-2 text-sm text-muted">
          Start the backend on port 8000, then refresh.
        </p>
      </div>
    )
  }

  const positive = portfolio.returnPct >= 0

  return (
    <div className="space-y-10">
      <header className="animate-rise">
        <h1 className="font-display text-3xl font-bold text-ink sm:text-4xl">
          Portfolio
        </h1>
        <p className="mt-1 text-muted">Paper desk performance — simulated capital only.</p>
      </header>

      <div className="animate-rise-delay-1 grid gap-6 sm:grid-cols-3">
        <Metric label="Starting balance" value={`$${portfolio.startingBalance.toLocaleString()}`} />
        <Metric label="Current value" value={`$${portfolio.currentValue.toLocaleString()}`} />
        <Metric
          label="Return"
          value={`${positive ? '+' : ''}${portfolio.returnPct.toFixed(2)}%`}
          accent={positive ? 'signal' : 'danger'}
        />
      </div>

      <div className="animate-rise-delay-2">
        <h2 className="font-display text-xl font-bold">Growth</h2>
        <p className="mb-4 text-sm text-muted">Portfolio value over time</p>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={history}>
              <defs>
                <linearGradient id="portFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#1fa67a" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#1fa67a" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#0b1f1a15" vertical={false} />
              <XAxis dataKey="date" tick={{ fill: '#5a726a', fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis
                tick={{ fill: '#5a726a', fontSize: 12 }}
                axisLine={false}
                tickLine={false}
                domain={['auto', 'auto']}
                tickFormatter={(v) => `$${v}`}
              />
              <Tooltip
                contentStyle={{
                  background: '#0b1f1a',
                  border: 'none',
                  borderRadius: 0,
                  color: '#f4f8f6',
                  fontSize: 13,
                }}
                formatter={(value) => [`$${Number(value).toFixed(2)}`, 'Value']}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke="#1fa67a"
                strokeWidth={2}
                fill="url(#portFill)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="animate-rise-delay-3 grid gap-10 lg:grid-cols-2">
        <section>
          <div className="mb-4 flex items-baseline justify-between">
            <h2 className="font-display text-xl font-bold">Holdings</h2>
            <span className="text-sm text-muted">Cash ${portfolio.cash.toFixed(2)}</span>
          </div>
          {portfolio.holdings.length === 0 ? (
            <p className="text-sm text-muted">
              No positions yet.{' '}
              <Link to="/trade" className="text-signal hover:underline">
                Place a paper trade
              </Link>
            </p>
          ) : (
            <ul className="divide-y divide-ink/10">
              {portfolio.holdings.map((h) => {
                const value = h.shares * h.currentPrice
                const cost = h.shares * h.avgCost
                const pnl = value - cost
                return (
                  <li key={h.stock} className="flex items-center justify-between py-3">
                    <div>
                      <p className="font-semibold tracking-wide">{h.stock}</p>
                      <p className="text-sm text-muted">
                        {h.shares.toFixed(4)} shares @ ${h.currentPrice.toFixed(2)}
                      </p>
                    </div>
                    <p className={pnl >= 0 ? 'text-signal font-medium' : 'text-danger font-medium'}>
                      {pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}
                    </p>
                  </li>
                )
              })}
            </ul>
          )}
        </section>

        <section>
          <h2 className="mb-4 font-display text-xl font-bold">Trade history</h2>
          {trades.length === 0 ? (
            <p className="text-sm text-muted">No trades recorded yet.</p>
          ) : (
            <ul className="space-y-4">
              {trades.slice(0, 8).map((t) => (
                <li key={t.id || `${t.stock}-${t.timestamp}`} className="border-l-2 border-signal/40 pl-3">
                  <p className="text-sm font-semibold">
                    <span className={t.type === 'BUY' ? 'text-signal' : 'text-danger'}>
                      {t.type}
                    </span>{' '}
                    {t.stock} · ${t.amount.toFixed(2)}
                  </p>
                  <p className="mt-0.5 text-xs text-muted line-clamp-2">
                    {t.reasoning || 'Paper trade'}
                    {t.confidence ? ` · AI confidence ${t.confidence}%` : ''}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  )
}

function Metric({
  label,
  value,
  accent,
}: {
  label: string
  value: string
  accent?: 'signal' | 'danger'
}) {
  return (
    <div>
      <p className="text-sm text-muted">{label}</p>
      <p
        className={`mt-1 font-display text-2xl font-bold sm:text-3xl ${
          accent === 'signal'
            ? 'text-signal'
            : accent === 'danger'
              ? 'text-danger'
              : 'text-ink'
        }`}
      >
        {value}
      </p>
    </div>
  )
}
