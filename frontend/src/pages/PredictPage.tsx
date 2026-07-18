import { useEffect, useState } from 'react'
import { api, type PredictionResult } from '../api/client'
import { useAuthToken } from '../hooks/useAuthToken'

type Market = {
  id: string
  market: string
  question: string
  category: string
}

export function PredictPage() {
  const { getToken } = useAuthToken()
  const [markets, setMarkets] = useState<Market[]>([])
  const [selected, setSelected] = useState<Market | null>(null)
  const [context, setContext] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<PredictionResult | null>(null)

  useEffect(() => {
    api
      .predictMarkets()
      .then((r) => {
        setMarkets(r.markets)
        setSelected(r.markets[0] || null)
      })
      .catch(() => setError('Could not load markets — is the API running?'))
  }, [])

  const run = async () => {
    if (!selected) return
    setLoading(true)
    setError('')
    try {
      const token = await getToken()
      const res = await api.predictAnalyze(
        {
          market: selected.market,
          question: selected.question,
          context,
        },
        token,
      )
      setResult(res.prediction)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Prediction failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <header className="animate-rise">
        <h1 className="font-display text-3xl font-bold sm:text-4xl">Predict the 6ix</h1>
        <p className="mt-1 text-muted">
          Same strategy engine, adapted for prediction markets — YES / NO instead of BUY / SELL.
        </p>
      </header>

      <div className="animate-rise-delay-1 space-y-3">
        {markets.map((m) => (
          <button
            key={m.id}
            type="button"
            onClick={() => {
              setSelected(m)
              setResult(null)
            }}
            className={`block w-full border-l-2 px-4 py-3 text-left transition-colors ${
              selected?.id === m.id
                ? 'border-signal bg-signal/5'
                : 'border-ink/10 hover:border-ink/30'
            }`}
          >
            <p className="text-xs uppercase tracking-wide text-muted">{m.category}</p>
            <p className="mt-0.5 font-medium">{m.question}</p>
          </button>
        ))}
      </div>

      <label className="animate-rise-delay-2 block">
        <span className="text-sm text-muted">Optional context</span>
        <textarea
          value={context}
          onChange={(e) => setContext(e.target.value)}
          rows={2}
          className="mt-1.5 w-full border border-ink/15 bg-paper/60 px-4 py-3 outline-none focus:border-signal"
          placeholder="Extra signals, news, or constraints…"
        />
      </label>

      <button
        type="button"
        onClick={run}
        disabled={loading || !selected}
        className="animate-rise-delay-2 bg-ink px-5 py-2.5 text-sm font-semibold text-paper hover:bg-ink-soft disabled:opacity-50 transition-colors"
      >
        {loading ? 'Running bot…' : 'Analyze market'}
      </button>
      {error && <p className="text-sm text-danger">{error}</p>}

      {result && (
        <article className="animate-rise space-y-5 border-t border-ink/10 pt-8">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-sm text-muted">Predict</p>
              <p
                className={`font-display text-4xl font-extrabold ${
                  result.prediction === 'YES' ? 'text-signal' : 'text-danger'
                }`}
              >
                {result.prediction}
              </p>
            </div>
            <div className="text-right">
              <p className="text-sm text-muted">Confidence</p>
              <p className="font-display text-2xl font-bold">{result.confidence}%</p>
            </div>
          </div>

          <p className="text-sm text-muted">{result.question}</p>

          <div className="grid gap-6 sm:grid-cols-2">
            <div>
              <h3 className="text-sm font-bold text-signal">Reasoning</h3>
              <ul className="mt-2 space-y-2">
                {result.reasoning.map((r) => (
                  <li key={r} className="text-sm before:mr-2 before:content-['–']">
                    {r}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="text-sm font-bold text-danger">Risks</h3>
              <ul className="mt-2 space-y-2">
                {result.risks.map((r) => (
                  <li key={r} className="text-sm before:mr-2 before:content-['–']">
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <p className="text-xs text-muted">{result.disclaimer}</p>
        </article>
      )}
    </div>
  )
}
