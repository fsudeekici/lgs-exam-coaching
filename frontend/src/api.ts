export type Role = 'admin' | 'student' | 'parent'

export interface User {
  id: number
  email: string
  full_name: string
  role: Role
}

export interface Topic {
  id: number
  name: string
}

export interface Subject {
  id: number
  code: string
  name: string
  question_count: number
  topics: Topic[]
}

export interface Student {
  id: number
  full_name: string
}

export interface Exam {
  id: number
  name: string
  exam_date: string
  publisher: string | null
  student_count: number
}

export interface ResultInput {
  subject_id: number
  correct: number
  wrong: number
  blank: number
  mistake_topic_ids: number[]
}

export interface Result extends ResultInput {
  net: number
}

export interface StudentResults {
  student_id: number
  full_name: string
  total_net: number
  results: Result[]
}

export interface ExamDetail extends Exam {
  students: StudentResults[]
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
    const detail = typeof body?.detail === 'string' ? body.detail : 'Bir hata oluştu'
    throw new ApiError(response.status, detail)
  }
  return response.status === 204 ? (undefined as T) : response.json()
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

/** Message to show the user for a failed request. */
export const errorMessage = (err: unknown) =>
  err instanceof ApiError ? err.message : 'Sunucuya ulaşılamadı'

export async function login(email: string, password: string): Promise<void> {
  // The backend uses the OAuth2 password form, which names the email field "username".
  const { access_token } = await request<{ access_token: string }>('/auth/login', {
    method: 'POST',
    body: new URLSearchParams({ username: email, password }),
  })
  setToken(access_token)
}

export const fetchMe = () => request<User>('/auth/me')

export const fetchSubjects = () => request<Subject[]>('/admin/subjects')
export const fetchStudents = () => request<Student[]>('/admin/students')
export const fetchExams = () => request<Exam[]>('/admin/exams')
export const fetchExam = (examId: number) => request<ExamDetail>(`/admin/exams/${examId}`)

export const createExam = (exam: { name: string; exam_date: string; publisher: string }) =>
  request<Exam>('/admin/exams', json('POST', exam))

export const saveStudentResults = (examId: number, studentId: number, results: ResultInput[]) =>
  request<StudentResults>(`/admin/exams/${examId}/students/${studentId}/results`, json('PUT', { results }))

export const deleteStudentResults = (examId: number, studentId: number) =>
  request<void>(`/admin/exams/${examId}/students/${studentId}/results`, { method: 'DELETE' })
