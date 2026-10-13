import { createContext, useContext } from 'react'
import type { User } from '../api'

export interface AuthState {
  user: User | null
  loading: boolean
  login: (email: string, password: string, rememberMe: boolean) => Promise<User>
  logout: () => void
  /** Records that the user accepted the KVKK privacy notice. */
  acceptPrivacyNotice: () => Promise<void>
}

export const AuthContext = createContext<AuthState | null>(null)

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
