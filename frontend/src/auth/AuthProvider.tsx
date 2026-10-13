import { useEffect, useState, type ReactNode } from 'react'
import { acceptPrivacyNotice as apiAccept, clearToken, fetchMe, getToken, login as apiLogin, type User } from '../api'
import { AuthContext } from './useAuth'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(() => getToken() !== null)

  // Restore the session from a stored token on first load.
  useEffect(() => {
    if (!getToken()) return
    fetchMe()
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setLoading(false))
  }, [])

  const login = async (email: string, password: string, rememberMe: boolean) => {
    await apiLogin(email, password, rememberMe)
    const me = await fetchMe()
    setUser(me)
    return me
  }

  const logout = () => {
    clearToken()
    setUser(null)
  }

  const acceptPrivacyNotice = async () => setUser(await apiAccept())

  return <AuthContext value={{ user, loading, login, logout, acceptPrivacyNotice }}>{children}</AuthContext>
}
