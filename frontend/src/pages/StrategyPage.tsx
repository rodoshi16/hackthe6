import { useState } from 'react'
import { api, type Strategy } from '../api/client'
import { useAuthToken } from '../hooks/useAuthToken'

export function StrategyPage() {
  const { getToken } = useAuthToken()
  const [prompt, setPrompt] = useState(
    'Create a medium-risk strategy focused on AI companies.',
  )
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [strategy, setStrategy] = useState<Strategy | null>(null)
  const [verification, setVerification] = useState<Record<string, unknown> | null>(null)

  const generate = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const token = await getToken()
      const res = await api.createStrategy(prompt, token)
      setStrategy(res.strategy)
      setVerification(res.verification)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Generation failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <header className="animate-rise">
        <h1 className="font-display text-3xl font-bold sm:text-4xl">Strategy generator</h1>
        <p className="mt-1 text-muted">
          Describe your goals. AlphaAI drafts rules, tickers, and risk — then anchors a hash on Solana.
        </p>
      </header>

      <form onSubmit={generate} className="animate-rise-delay-1 space-y-4">
        <label className="block">
          <span className="text-sm font-medium text-muted">Your brief</span>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={4}
            className="mt-2 w-full resize-y border border-ink/15 bg-paper/60 px-4 py-3 text-ink outline-none focus:border-signal transition-colors"
            placeholder="e.g. Medium-risk AI growth with clear sell rules"
          />
        </label>
        <button
          type="submit"
          disabled={loading || !prompt.trim()}
          className="bg-ink px-5 py-2.5 text-sm font-semibold text-paper hover:bg-ink-soft disabled:opacity-50 transition-colors"
        >
          {loading ? 'Generating…' : 'Generate strategy'}
        </button>
        {error && <p className="text-sm text-danger">{error}</p>}
      </form>

      {strategy && (
        <article className="animate-rise space-y-6 border-t border-ink/10 pt-8">
          <div>
            <p className="text-sm text-muted">Strategy name</p>
            <h2 className="font-display text-2xl font-bold">{strategy.name}</h2>
            <p className="mt-1 text-sm text-muted">{strategy.description}</p>
          </div>

          <div className="flex flex-wrap gap-6">
            <div>
              <p className="text-sm text-muted">Risk</p>
              <p className="font-semibold text-signal">{strategy.riskLevel}</p>
            </div>
            <div>
              <p className="text-sm text-muted">Stocks</p>
              <p className="font-semibold tracking-wide">{strategy.stocks.join(' · ')}</p>
            </div>
          </div>

          <div className="grid gap-6 sm:grid-cols-2">
            <RuleList title="BUY" items={strategy.rules?.buy || []} tone="buy" />
            <RuleList title="SELL" items={strategy.rules?.sell || []} tone="sell" />
          </div>

          {(strategy.verified || verification) && (
            <div className="bg-ink px-5 py-4 text-paper">
              <p className="text-xs uppercase tracking-wider text-mint">Verified · Solana</p>
              <p className="mt-2 font-mono text-sm break-all text-mint/90">
                Hash: {strategy.hash || String(verification?.hash || '')}
              </p>
              <p className="mt-1 font-mono text-xs break-all text-paper/50">
                Sig: {(strategy.solanaSignature || String(verification?.solanaSignature || '')).slice(0, 48)}…
              </p>
              <p className="mt-2 text-xs text-paper/60">
                SHA256 of strategy JSON anchored for integrity — prevents false performance claims.
              </p>
            </div>
          )}

          <p className="text-xs text-muted">
            AI-assisted strategy for paper trading only. Not financial advice.
          </p>
        </article>
      )}
    </div>
  )
}

function RuleList({
  title,
  items,
  tone,
}: {
  title: string
  items: string[]
  tone: 'buy' | 'sell'
}) {
  return (
    <div>
      <h3
        className={`text-sm font-bold tracking-wide ${
          tone === 'buy' ? 'text-signal' : 'text-danger'
        }`}
      >
        {title}
      </h3>
      <ul className="mt-2 space-y-2">
        {items.map((item) => (
          <li key={item} className="text-sm text-ink/80 before:mr-2 before:content-['–']">
            {item}
          </li>
        ))}
      </ul>
    </div>
  )
}
