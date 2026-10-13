import { useEffect, useState, type ReactNode } from 'react'
import { clearToken, fetchMe, getToken, login as apiLogin, type User } from '../api'
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

  const login = async (email: string, password: string) => {
    await apiLogin(email, password)
    const me = await fetchMe()
    setUser(me)
    return me
  }

  const logout = () => {
    clearToken()
    setUser(null)
  }

  return <AuthContext value={{ user, loading, login, logout }}>{children}</AuthContext>
}
