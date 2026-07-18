const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export type Strategy = {
  id?: string
  userId: string
  name: string
  description: string
  riskLevel: string
  stocks: string[]
  rules: { buy: string[]; sell: string[] }
  createdAt: string
  hash?: string
  solanaSignature?: string
  verified?: boolean
  network?: string
}

export type StockAnalysis = {
  stock: string
  symbol: string
  recommendation: 'BUY' | 'HOLD' | 'SELL'
  confidence: number
  positives: string[]
  risks: string[]
  summary: string
  disclaimer: string
}

export type Holding = {
  stock: string
  shares: number
  avgCost: number
  currentPrice: number
}

export type Portfolio = {
  userId: string
  cash: number
  holdings: Holding[]
  startingBalance: number
  currentValue: number
  returnPct: number
}

export type Trade = {
  id?: string
  userId: string
  strategyId?: string
  stock: string
  type: 'BUY' | 'SELL'
  amount: number
  shares: number
  price: number
  confidence: number
  reasoning: string
  timestamp: string
}

export type PredictionResult = {
  market: string
  question: string
  prediction: 'YES' | 'NO'
  confidence: number
  reasoning: string[]
  risks: string[]
  disclaimer: string
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  if (token) headers.Authorization = `Bearer ${token}`

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

export const api = {
  createStrategy: (description: string, token?: string) =>
    request<{ strategy: Strategy; verification: Record<string, unknown>; disclaimer: string }>(
      '/strategy/create',
      { method: 'POST', body: JSON.stringify({ description }) },
      token,
    ),

  listStrategies: (token?: string) =>
    request<{ strategies: Strategy[] }>('/strategy/list', {}, token),

  analyzeStock: (symbol: string, token?: string) =>
    request<{ analysis: StockAnalysis; disclaimer: string }>(
      '/stock/analyze',
      { method: 'POST', body: JSON.stringify({ symbol }) },
      token,
    ),

  trade: (
    payload: {
      stock: string
      type: 'BUY' | 'SELL'
      amount: number
      confidence?: number
      reasoning?: string
      strategyId?: string
    },
    token?: string,
  ) =>
    request<{ trade: Trade; portfolio: Portfolio; explanation: Record<string, unknown> }>(
      '/trade',
      { method: 'POST', body: JSON.stringify(payload) },
      token,
    ),

  getPortfolio: (token?: string) =>
    request<{ portfolio: Portfolio; history: { date: string; value: number }[] }>(
      '/portfolio',
      {},
      token,
    ),

  getTrades: (token?: string) =>
    request<{ trades: Trade[] }>('/trades', {}, token),

  predictMarkets: () =>
    request<{ markets: { id: string; market: string; question: string; category: string }[] }>(
      '/predict/markets',
    ),

  predictAnalyze: (
    payload: { market: string; question: string; context?: string },
    token?: string,
  ) =>
    request<{ prediction: PredictionResult; rules: Record<string, string[]>; disclaimer: string }>(
      '/predict/analyze',
      { method: 'POST', body: JSON.stringify(payload) },
      token,
    ),
}
