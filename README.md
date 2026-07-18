# AlphaAI

AI-powered stock research and paper trading platform for Hack the 6ix 2026.

AlphaAI is a simulated AI hedge fund desk: generate strategies, analyze stocks with explainable recommendations, paper-trade with fake money, track portfolio performance, and verify strategy hashes on Solana. Includes a **Predict the 6ix** module that adapts the same engine to YES/NO prediction markets.

> Not financial advice. No real money. AI never claims certainty.

## Stack

| Layer | Tech |
|-------|------|
| Frontend | React, TypeScript, Tailwind CSS, Recharts |
| Backend | Python, FastAPI |
| Database | MongoDB Atlas (in-memory fallback for demo) |
| Auth | Auth0 (optional — demo mode works without it) |
| AI | Gemini API (rich mock responses when key missing) |
| Market data | Finnhub (optional key) → Yahoo Finance → demo fallback |
| Blockchain | Solana strategy hash verification |

## Quick start

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example ../.env.example  # or edit backend/.env
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173

Without Auth0 / Gemini / MongoDB configured, the app runs in **demo mode** with in-memory storage and mock AI — enough for the full hackathon walkthrough.

## Demo flow

1. Open the landing page → **Open dashboard**
2. **Strategy** → generate from a natural-language brief (hash verified on Solana)
3. **Analyze** → e.g. `NVDA` → BUY/HOLD/SELL with confidence + risks
4. **Trade** → paper BUY with AI explanation
5. **Dashboard** → holdings, return %, Recharts growth, trade history
6. **Predict 6ix** → YES/NO prediction market bot

## API routes

```
POST /strategy/create
GET  /strategy/list
POST /stock/analyze
GET  /stock/quote/{symbol}
POST /trade
GET  /portfolio
GET  /trades
POST /predict/analyze
GET  /predict/markets
```

## Market data

Paper fills and research quotes use live prices when available:

1. **Finnhub** — if `FINNHUB_API_KEY` is set (free at [finnhub.io](https://finnhub.io))
2. **Yahoo Finance** — no key required
3. **Demo marks** — offline fallback so the app never breaks

`POST /stock/analyze` still returns the same `analysis` object; it also adds an optional `market` payload (price, company name, market cap, sector, daily change, history, source).
## Environment

See `.env.example` and `frontend/.env.example`.

| Variable | Purpose |
|----------|---------|
| `MONGODB_URI` | MongoDB Atlas connection string |
| `GEMINI_API_KEY` | Google Gemini for live AI |
| `FINNHUB_API_KEY` | Optional Finnhub key for quotes/profile (Yahoo used if empty) |
| `AUTH0_DOMAIN` / `AUTH0_AUDIENCE` | Backend JWT validation |
| `VITE_AUTH0_*` | Frontend Auth0 login |
| `VITE_API_URL` | Backend base URL |

## Project structure

```
AlphaAI/
  frontend/src/
    components/
    pages/
    api/
    hooks/
  backend/app/
    main.py
    routes/
    models/
    services/
    database/
  README.md
```

## Solana verification

On strategy create, AlphaAI:

1. Serializes the strategy to canonical JSON  
2. Computes a SHA256 hash  
3. Records a verification signature (devnet-aware demo anchor)  

Displayed in the UI as **Verified · Solana** with the hash — a tamper-evident trail so users cannot rewrite claimed strategy performance after the fact.

## Predict the 6ix

`POST /predict/analyze` reuses the Gemini/strategy engine for prediction markets (`YES`/`NO` + confidence + reasoning/risks). Built for the “Best Predict the 6ix Trading Bot” track.

## License

MIT — hackathon prototype.
