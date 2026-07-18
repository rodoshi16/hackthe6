import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Auth0Provider } from '@auth0/auth0-react'
import { Layout } from './components/Layout'
import { LandingPage } from './pages/LandingPage'
import { DashboardPage } from './pages/DashboardPage'
import { StrategyPage } from './pages/StrategyPage'
import { AnalyzePage } from './pages/AnalyzePage'
import { TradePage } from './pages/TradePage'
import { PredictPage } from './pages/PredictPage'
import { AUTH0_CONFIGURED } from './hooks/useAuthToken'

function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<LandingPage />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="strategy" element={<StrategyPage />} />
          <Route path="analyze" element={<AnalyzePage />} />
          <Route path="trade" element={<TradePage />} />
          <Route path="predict" element={<PredictPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default function App() {
  if (AUTH0_CONFIGURED) {
    return (
      <Auth0Provider
        domain={import.meta.env.VITE_AUTH0_DOMAIN}
        clientId={import.meta.env.VITE_AUTH0_CLIENT_ID}
        authorizationParams={{
          redirect_uri: window.location.origin,
          audience: import.meta.env.VITE_AUTH0_AUDIENCE,
        }}
        cacheLocation="localstorage"
      >
        <AppRoutes />
      </Auth0Provider>
    )
  }

  return <AppRoutes />
}
