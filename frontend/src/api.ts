export type Role = 'admin' | 'student' | 'parent'

export interface User {
  id: number
  email: string
  full_name: string
  role: Role
}

const TOKEN_KEY = 'lgs_token'

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (token: string) => localStorage.setItem(TOKEN_KEY, token)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(`/api${path}`, { ...init, headers })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = typeof body?.detail === 'string' ? body.detail : 'Something went wrong'
    throw new ApiError(response.status, detail)
  }
  return response.json()
}

export async function login(email: string, password: string): Promise<void> {
  // The backend uses the OAuth2 password form, which names the email field "username".
  const { access_token } = await request<{ access_token: string }>('/auth/login', {
    method: 'POST',
    body: new URLSearchParams({ username: email, password }),
  })
  setToken(access_token)
}

export const fetchMe = () => request<User>('/auth/me')
