import { useEffect, useState } from 'react'
import { useLocation, Link } from 'react-router-dom'
import { api, type MarketQuote, type Portfolio, type Trade } from '../api/client'
import { useAuthToken } from '../hooks/useAuthToken'

type TradeState = {
  stock?: string
  type?: 'BUY' | 'SELL'
  confidence?: number
  reasoning?: string
  price?: number
}

export function TradePage() {
  const location = useLocation()
  const preset = (location.state || {}) as TradeState
  const { getToken } = useAuthToken()

  const [stock, setStock] = useState(preset.stock || 'NVDA')
  const [type, setType] = useState<'BUY' | 'SELL'>(preset.type || 'BUY')
  const [amount, setAmount] = useState(1000)
  const [confidence, setConfidence] = useState(preset.confidence || 0)
  const [reasoning, setReasoning] = useState(
    preset.reasoning || 'AI-assisted paper trade based on desk research.',
  )
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [lastTrade, setLastTrade] = useState<Trade | null>(null)
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null)
  const [explanation, setExplanation] = useState<Record<string, unknown> | null>(null)
  const [quote, setQuote] = useState<MarketQuote | null>(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      if (!stock.trim()) return
      try {
        const token = await getToken()
        const res = await api.getQuote(stock.trim(), token)
        if (!cancelled) setQuote(res.quote)
      } catch {
        if (!cancelled) setQuote(null)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [stock, getToken])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const token = await getToken()
      const res = await api.trade(
        {
          stock,
          type,
          amount,
          confidence,
          reasoning,
        },
        token,
      )
      setLastTrade(res.trade)
      setPortfolio(res.portfolio)
      setExplanation(res.explanation)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Trade failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <header className="animate-rise">
        <h1 className="font-display text-3xl font-bold sm:text-4xl">Paper trade</h1>
        <p className="mt-1 text-muted">
          Simulate buys and sells with fake money at live (or fallback) market prices.
        </p>
      </header>

      <form onSubmit={submit} className="animate-rise-delay-1 space-y-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block">
            <span className="text-sm text-muted">Stock</span>
            <input
              value={stock}
              onChange={(e) => setStock(e.target.value.toUpperCase())}
              className="mt-1.5 w-full border border-ink/15 bg-paper/60 px-4 py-2.5 font-semibold tracking-wider outline-none focus:border-signal"
            />
          </label>
          <label className="block">
            <span className="text-sm text-muted">Amount (USD)</span>
            <input
              type="number"
              min={1}
              step={1}
              value={amount}
              onChange={(e) => setAmount(Number(e.target.value))}
              className="mt-1.5 w-full border border-ink/15 bg-paper/60 px-4 py-2.5 outline-none focus:border-signal"
            />
          </label>
        </div>

        {quote && (
          <p className="text-sm text-muted">
            Mark for paper fill:{' '}
            <span className="font-semibold text-ink tabular-nums">
              ${quote.price.toFixed(2)}
            </span>
            {quote.companyName && <> · {quote.companyName}</>}
            <span className="text-xs"> · {quote.source}</span>
            {amount > 0 && quote.price > 0 && (
              <>
                {' '}
                · ~{(amount / quote.price).toFixed(4)} shares
              </>
            )}
          </p>
        )}

        <div className="flex gap-2">
          {(['BUY', 'SELL'] as const).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setType(t)}
              className={`px-4 py-2 text-sm font-semibold transition-colors ${
                type === t
                  ? t === 'BUY'
                    ? 'bg-signal text-ink'
                    : 'bg-danger text-paper'
                  : 'border border-ink/15 text-muted hover:text-ink'
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        <label className="block">
          <span className="text-sm text-muted">AI confidence (%)</span>
          <input
            type="number"
            min={0}
            max={100}
            value={confidence}
            onChange={(e) => setConfidence(Number(e.target.value))}
            className="mt-1.5 w-full border border-ink/15 bg-paper/60 px-4 py-2.5 outline-none focus:border-signal sm:w-40"
          />
        </label>

        <label className="block">
          <span className="text-sm text-muted">Explanation</span>
          <textarea
            value={reasoning}
            onChange={(e) => setReasoning(e.target.value)}
            rows={4}
            className="mt-1.5 w-full border border-ink/15 bg-paper/60 px-4 py-3 outline-none focus:border-signal"
          />
        </label>

        <button
          type="submit"
          disabled={loading}
          className="bg-ink px-5 py-2.5 text-sm font-semibold text-paper hover:bg-ink-soft disabled:opacity-50 transition-colors"
        >
          {loading ? 'Executing…' : `${type} ${stock || '—'}`}
        </button>
        {error && <p className="text-sm text-danger">{error}</p>}
      </form>

      {lastTrade && (
        <article className="animate-rise space-y-4 border-t border-ink/10 pt-8">
          <h2 className="font-display text-xl font-bold">Trade decision</h2>
          <p className="text-lg font-semibold">
            <span className={lastTrade.type === 'BUY' ? 'text-signal' : 'text-danger'}>
              {lastTrade.type}
            </span>{' '}
            {lastTrade.stock}
          </p>
          <p className="text-sm text-muted">
            ${lastTrade.amount.toFixed(2)} · {lastTrade.shares.toFixed(4)} shares @ $
            {lastTrade.price.toFixed(2)}
          </p>
          {confidence > 0 && (
            <p className="text-sm">
              Confidence: <strong>{confidence}%</strong>
            </p>
          )}
          <div>
            <p className="text-sm font-semibold text-muted">Why</p>
            <p className="mt-1 text-sm leading-relaxed">{String(explanation?.why || reasoning)}</p>
          </div>
          {portfolio && (
            <p className="text-sm text-muted">
              Desk value now{' '}
              <span className="font-semibold text-ink">
                ${portfolio.currentValue.toLocaleString()}
              </span>{' '}
              ({portfolio.returnPct >= 0 ? '+' : ''}
              {portfolio.returnPct.toFixed(2)}%) ·{' '}
              <Link to="/dashboard" className="text-signal hover:underline">
                View dashboard
              </Link>
            </p>
          )}
          <p className="text-xs text-muted">No real money. Simulated paper trade only.</p>
        </article>
      )}
    </div>
  )
}
