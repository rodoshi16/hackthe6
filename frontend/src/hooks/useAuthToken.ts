import { Auth0Context, type User } from '@auth0/auth0-react'
import { useCallback, useContext } from 'react'

const AUTH0_CONFIGURED = Boolean(
  import.meta.env.VITE_AUTH0_DOMAIN && import.meta.env.VITE_AUTH0_CLIENT_ID,
)

const demoUser: User = {
  name: 'Demo Trader',
  sub: 'demo-user',
  email: 'demo@alphaai.local',
}

export function useAuthToken() {
  const auth0 = useContext(Auth0Context)

  const getToken = useCallback(async (): Promise<string | undefined> => {
    if (!AUTH0_CONFIGURED || !auth0?.isAuthenticated) return undefined
    try {
      return await auth0.getAccessTokenSilently()
    } catch {
      return undefined
    }
  }, [auth0])

  if (!AUTH0_CONFIGURED || !auth0) {
    return {
      configured: false,
      isAuthenticated: true,
      isLoading: false,
      user: demoUser,
      login: () => undefined,
      logout: () => undefined,
      getToken,
    }
  }

  return {
    configured: true,
    isAuthenticated: auth0.isAuthenticated,
    isLoading: auth0.isLoading,
    user: auth0.user,
    login: () => auth0.loginWithRedirect(),
    logout: () =>
      auth0.logout({ logoutParams: { returnTo: window.location.origin } }),
    getToken,
  }
}

export { AUTH0_CONFIGURED }
