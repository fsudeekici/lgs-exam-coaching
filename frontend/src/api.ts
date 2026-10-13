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
  /** Compact label for tables and charts, e.g. "Mat". */
  short_name: string
  session: 'sozel' | 'sayisal'
  question_count: number
  topics: Topic[]
}

export interface UserRef {
  id: number
  full_name: string
}

export interface Student extends UserRef {
  email: string
  school: string | null
  class_name: string | null
  is_active: boolean
  parents: UserRef[]
}

export interface Parent extends UserRef {
  email: string
  is_active: boolean
  students: UserRef[]
}

/** Create needs every field; on update, fields left out stay unchanged. */
export interface StudentInput {
  full_name: string
  email: string
  password: string
  school: string
  class_name: string
}

export interface ParentInput {
  full_name: string
  email: string
  password: string
  student_ids: number[]
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

export const createStudent = (student: StudentInput) => request<Student>('/admin/students', json('POST', student))
export const updateStudent = (id: number, changes: Partial<StudentInput & { is_active: boolean }>) =>
  request<Student>(`/admin/students/${id}`, json('PATCH', changes))

export const fetchParents = () => request<Parent[]>('/admin/parents')
export const createParent = (parent: ParentInput) => request<Parent>('/admin/parents', json('POST', parent))
export const updateParent = (id: number, changes: Partial<ParentInput & { is_active: boolean }>) =>
  request<Parent>(`/admin/parents/${id}`, json('PATCH', changes))

export interface ExamPoint {
  exam_id: number
  name: string
  exam_date: string
  total_net: number
  nets: { subject_id: number; net: number }[]
}

export interface NetChange {
  last: number
  /** null when there is no previous exam to compare with. */
  previous: number | null
  change: number | null
}

export interface StudentAnalytics {
  student: Pick<Student, 'id' | 'full_name' | 'school' | 'class_name' | 'is_active'>
  subjects: Omit<Subject, 'topics'>[]
  /** Oldest exam first. */
  exams: ExamPoint[]
  comparison: {
    last_exam_id: number
    previous_exam_id: number | null
    total: NetChange
    subjects: (NetChange & { subject_id: number })[]
  } | null
  weak_topics: { topic_id: number; name: string; subject_id: number; count: number }[]
  averages: { subject_id: number; student_average: number; class_average: number }[]
}

export const fetchStudentAnalytics = (studentId: number) =>
  request<StudentAnalytics>(`/admin/students/${studentId}/analytics`)

export type TopicStatus = 'not_started' | 'studying' | 'done' | 'needs_review'

export interface QuestionLogInput {
  log_date: string
  subject_id: number
  /** null for mixed practice that is not about one topic. */
  topic_id: number | null
  solved: number
  correct: number
  wrong: number
}

export interface QuestionLog extends QuestionLogInput {
  id: number
}

/** Only topics the student has marked are listed; the rest are not started. */
export interface TopicProgress {
  topic_id: number
  status: TopicStatus
}

// Student panel: the logged-in student's own data.
export const fetchMySubjects = () => request<Subject[]>('/student/subjects')
export const fetchMyQuestionLogs = () => request<QuestionLog[]>('/student/question-logs')
export const addQuestionLog = (log: QuestionLogInput) => request<QuestionLog>('/student/question-logs', json('POST', log))
export const deleteQuestionLog = (id: number) => request<void>(`/student/question-logs/${id}`, { method: 'DELETE' })
export const fetchMyTopicProgress = () => request<TopicProgress[]>('/student/topic-progress')
export const setTopicStatus = (topicId: number, status: TopicStatus) =>
  request<TopicProgress>(`/student/topic-progress/${topicId}`, json('PUT', { status }))
export const fetchMyAnalytics = () => request<StudentAnalytics>('/student/analytics')

// Admin's read-only view of the same data.
export const fetchStudentQuestionLogs = (studentId: number) =>
  request<QuestionLog[]>(`/admin/students/${studentId}/question-logs`)
export const fetchStudentTopicProgress = (studentId: number) =>
  request<TopicProgress[]>(`/admin/students/${studentId}/topic-progress`)
