import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type StockAnalysis } from '../api/client'
import { useAuthToken } from '../hooks/useAuthToken'

export function AnalyzePage() {
  const { getToken } = useAuthToken()
  const [symbol, setSymbol] = useState('NVDA')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [analysis, setAnalysis] = useState<StockAnalysis | null>(null)

  const analyze = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const token = await getToken()
      const res = await api.analyzeStock(symbol.trim(), token)
      setAnalysis(res.analysis)
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

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <header className="animate-rise">
        <h1 className="font-display text-3xl font-bold sm:text-4xl">Stock analysis</h1>
        <p className="mt-1 text-muted">
          AI-assisted research with explicit risk assessment — never a certainty claim.
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
            </div>
            <div className="text-right">
              <p className="text-sm text-muted">Recommendation</p>
              <p className={`font-display text-3xl font-extrabold ${recColor}`}>
                {analysis.recommendation}
              </p>
            </div>
          </div>

          <div>
            <p className="text-sm text-muted">Confidence</p>
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
                ...analysis.positives.slice(0, 2),
                `Risks: ${analysis.risks.slice(0, 2).join('; ')}`,
              ].join(' '),
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
