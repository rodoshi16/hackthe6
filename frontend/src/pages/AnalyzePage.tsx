import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  YAxis,
} from 'recharts'
import { api, type MarketQuote, type StockAnalysis } from '../api/client'
import { useAuthToken } from '../hooks/useAuthToken'

function formatCap(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return '—'
  if (n >= 1e12) return `$${(n / 1e12).toFixed(2)}T`
  if (n >= 1e9) return `$${(n / 1e9).toFixed(2)}B`
  if (n >= 1e6) return `$${(n / 1e6).toFixed(1)}M`
  return `$${n.toLocaleString()}`
}

export function AnalyzePage() {
  const { getToken } = useAuthToken()
  const [symbol, setSymbol] = useState('NVDA')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [analysis, setAnalysis] = useState<StockAnalysis | null>(null)
  const [market, setMarket] = useState<MarketQuote | null>(null)

  const analyze = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const token = await getToken()
      const res = await api.analyzeStock(symbol.trim(), token)
      setAnalysis(res.analysis)
      setMarket(res.market ?? null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed')
    } finally {
      setLoading(false)
    }
  }

  const recColor =
    analysis?.recommendation === 'BUY'
      ? 'text-signal'
      : analysis?.recommendation === 'SELL'
        ? 'text-danger'
        : 'text-warn'

  const changePositive = (market?.changePercent ?? 0) >= 0

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <header className="animate-rise">
        <h1 className="font-display text-3xl font-bold sm:text-4xl">Stock analysis</h1>
        <p className="mt-1 text-muted">
          Live market context plus AI-assisted research — never a certainty claim.
        </p>
      </header>

      <form onSubmit={analyze} className="animate-rise-delay-1 flex flex-wrap gap-3">
        <input
          value={symbol}
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          className="min-w-[140px] flex-1 border border-ink/15 bg-paper/60 px-4 py-2.5 font-semibold tracking-wider outline-none focus:border-signal"
          placeholder="TICKER"
          maxLength={8}
        />
        <button
          type="submit"
          disabled={loading || !symbol.trim()}
          className="bg-ink px-5 py-2.5 text-sm font-semibold text-paper hover:bg-ink-soft disabled:opacity-50 transition-colors"
        >
          {loading ? 'Analyzing…' : 'Analyze'}
        </button>
      </form>
      {error && <p className="text-sm text-danger">{error}</p>}

      <div className="flex flex-wrap gap-2 text-sm">
        {['NVDA', 'MSFT', 'AMD', 'GOOG', 'AAPL', 'TSLA'].map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setSymbol(t)}
            className="text-muted hover:text-signal transition-colors"
          >
            {t}
          </button>
        ))}
      </div>

      {analysis && (
        <article className="animate-rise space-y-6 border-t border-ink/10 pt-8">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-sm text-muted">Stock</p>
              <h2 className="font-display text-2xl font-bold">
                {analysis.stock}{' '}
                <span className="text-lg text-muted">({analysis.symbol})</span>
              </h2>
              {market?.sector && (
                <p className="mt-1 text-sm text-muted">{market.sector}</p>
              )}
            </div>
            <div className="text-right">
              <p className="text-sm text-muted">Recommendation</p>
              <p className={`font-display text-3xl font-extrabold ${recColor}`}>
                {analysis.recommendation}
              </p>
            </div>
          </div>

          {market && (
            <div className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-4">
                <div>
                  <p className="text-sm text-muted">Price</p>
                  <p className="font-display text-xl font-bold tabular-nums">
                    ${market.price.toFixed(2)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted">Daily change</p>
                  <p
                    className={`font-semibold tabular-nums ${
                      changePositive ? 'text-signal' : 'text-danger'
                    }`}
                  >
                    {market.change != null
                      ? `${changePositive ? '+' : ''}${market.change.toFixed(2)}`
                      : '—'}{' '}
                    {market.changePercent != null && (
                      <span className="text-sm">
                        ({changePositive ? '+' : ''}
                        {market.changePercent.toFixed(2)}%)
                      </span>
                    )}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted">Market cap</p>
                  <p className="font-semibold tabular-nums">{formatCap(market.marketCap)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted">Data source</p>
                  <p className="text-sm font-medium capitalize">{market.source}</p>
                </div>
              </div>

              {market.history.length > 1 && (
                <div>
                  <p className="mb-2 text-sm text-muted">Recent prices</p>
                  <div className="h-28 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={market.history}>
                        <defs>
                          <linearGradient id="pxFill" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#1fa67a" stopOpacity={0.3} />
                            <stop offset="100%" stopColor="#1fa67a" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <YAxis domain={['auto', 'auto']} hide />
                        <Tooltip
                          contentStyle={{
                            background: '#0b1f1a',
                            border: 'none',
                            color: '#f4f8f6',
                            fontSize: 12,
                          }}
                          labelFormatter={(_, payload) =>
                            String(payload?.[0]?.payload?.date ?? '')
                          }
                          formatter={(value) => [`$${Number(value).toFixed(2)}`, 'Close']}
                        />
                        <Area
                          type="monotone"
                          dataKey="close"
                          stroke="#1fa67a"
                          strokeWidth={1.5}
                          fill="url(#pxFill)"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}
            </div>
          )}

          <div>
            <p className="text-sm text-muted">
              Confidence in reasoning
              <span className="ml-1 font-normal">(not odds the price rises)</span>
            </p>
            <div className="mt-2 flex items-center gap-3">
              <div className="h-1.5 flex-1 bg-ink/10">
                <div
                  className="h-full bg-signal transition-all duration-700"
                  style={{ width: `${analysis.confidence}%` }}
                />
              </div>
              <span className="font-semibold tabular-nums">{analysis.confidence}%</span>
            </div>
          </div>

          <p className="text-sm leading-relaxed text-ink/80">{analysis.summary}</p>

          {analysis.reasoning && analysis.reasoning.length > 0 && (
            <div>
              <h3 className="text-sm font-bold text-ink">Reasoning</h3>
              <ol className="mt-2 list-decimal space-y-2 pl-5">
                {analysis.reasoning.map((r) => (
                  <li key={r} className="text-sm text-ink/80">
                    {r}
                  </li>
                ))}
              </ol>
            </div>
          )}

          <div className="grid gap-6 sm:grid-cols-2">
            <div>
              <h3 className="text-sm font-bold text-signal">Positive</h3>
              <ul className="mt-2 space-y-2">
                {analysis.positives.map((p) => (
                  <li key={p} className="text-sm text-ink/80 before:mr-2 before:content-['–']">
                    {p}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="text-sm font-bold text-danger">Risks</h3>
              <ul className="mt-2 space-y-2">
                {analysis.risks.map((r) => (
                  <li key={r} className="text-sm text-ink/80 before:mr-2 before:content-['–']">
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <Link
            to="/trade"
            state={{
              stock: analysis.symbol,
              type: analysis.recommendation === 'SELL' ? 'SELL' : 'BUY',
              confidence: analysis.confidence,
              reasoning: [
                analysis.summary,
                ...(analysis.reasoning ?? []).slice(0, 2),
                ...analysis.positives.slice(0, 1),
                `Risks: ${analysis.risks.slice(0, 2).join('; ')}`,
              ].join(' '),
              price: market?.price,
            }}
            className="inline-block bg-signal px-5 py-2.5 text-sm font-semibold text-ink hover:bg-signal-bright transition-colors"
          >
            Paper trade {analysis.symbol}
          </Link>

          <p className="text-xs text-muted">{analysis.disclaimer}</p>
        </article>
      )}
    </div>
  )
}
