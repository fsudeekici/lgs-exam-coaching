export type Role = 'admin' | 'student' | 'parent'

export interface User {
  id: number
  email: string
  full_name: string
  role: Role
  /** null until the user accepts the KVKK privacy notice. */
  kvkk_consent_at: string | null
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
  /** Day the parent's consent was received; the student cannot log in while it is null. */
  parent_consent_date: string | null
  is_active: boolean
  /** Blocked for now after too many wrong passwords. */
  login_blocked: boolean
  parents: UserRef[]
}

export interface Parent extends UserRef {
  email: string
  is_active: boolean
  login_blocked: boolean
  students: UserRef[]
}

/** Create needs every field; on update, fields left out stay unchanged. */
export interface StudentInput {
  full_name: string
  email: string
  password: string
  school: string
  class_name: string
  /** null means consent has not been received (or has been withdrawn). */
  parent_consent_date: string | null
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
    // The session ended (expired, or the password was changed elsewhere): back to the login page.
    if (response.status === 401 && token && path !== '/auth/login') {
      clearToken()
      if (window.location.pathname !== '/login') window.location.assign('/login')
    }
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

/** With `rememberMe` the session lasts 30 days instead of the normal login time. */
export async function login(email: string, password: string, rememberMe: boolean): Promise<void> {
  // The backend uses the OAuth2 password form, which names the email field "username".
  const { access_token } = await request<{ access_token: string }>('/auth/login', {
    method: 'POST',
    body: new URLSearchParams({ username: email, password, remember_me: String(rememberMe) }),
  })
  setToken(access_token)
}

export const fetchMe = () => request<User>('/auth/me')

export const acceptPrivacyNotice = () => request<User>('/auth/consent', { method: 'POST' })

/** Changes the password and switches to the new token (older tokens stop working). */
export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  const { access_token } = await request<{ access_token: string }>(
    '/auth/change-password',
    json('POST', { current_password: currentPassword, new_password: newPassword }),
  )
  setToken(access_token)
}

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

export const unblockStudentLogin = (id: number) => request<Student>(`/admin/students/${id}/unblock-login`, { method: 'POST' })
export const unblockParentLogin = (id: number) => request<Parent>(`/admin/parents/${id}/unblock-login`, { method: 'POST' })

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
  /** Topics marked wrong in at least 2 of the last 3 exams; `count` is how many of them. Most missed first. */
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

export interface CoachNote {
  id: number
  body: string
  visible_to_parent: boolean
  created_at: string
}

export const fetchStudentNotes = (studentId: number) => request<CoachNote[]>(`/admin/students/${studentId}/notes`)
export const addStudentNote = (studentId: number, note: { body: string; visible_to_parent: boolean }) =>
  request<CoachNote>(`/admin/students/${studentId}/notes`, json('POST', note))
export const updateNote = (noteId: number, changes: Partial<{ body: string; visible_to_parent: boolean }>) =>
  request<CoachNote>(`/admin/notes/${noteId}`, json('PATCH', changes))
export const deleteNote = (noteId: number) => request<void>(`/admin/notes/${noteId}`, { method: 'DELETE' })

export interface DayQuestions {
  day: string
  solved: number
  correct: number
  wrong: number
}

/** Questions over a period; `days` has every day of it, oldest first. */
export interface QuestionsSummary {
  solved: number
  correct: number
  wrong: number
  /** Days with at least one entry. */
  active_days: number
  days: DayQuestions[]
}

/** What a parent sees for one child. */
export interface ChildSummary {
  analytics: StudentAnalytics
  /** The last 7 days. */
  week: QuestionsSummary
  /** Coach notes marked visible to parents, newest first. */
  notes: Pick<CoachNote, 'id' | 'body' | 'created_at'>[]
}

export const fetchMyChildren = () => request<ChildSummary[]>('/parent/children')

/** One active student on the admin home page. */
export interface OverviewRow {
  student_id: number
  full_name: string
  class_name: string | null
  /** `change` is against the previous exam; null when this is the first. */
  last_exam: { exam_id: number; name: string; exam_date: string; total_net: number; change: number | null } | null
  /** Questions solved in the last 7 days. */
  week_solved: number
  /** Topics marked wrong in at least 2 of the student's last 3 exams. */
  weak_topic_count: number
  last_log_date: string | null
  /** No question log in the last 3 days. */
  no_recent_log: boolean
}

export const fetchOverview = () => request<OverviewRow[]>('/admin/overview')

export interface MeetingNote {
  id: number
  meeting_date: string
  body: string
}

/** Everything the parent meeting page shows for one student. */
export interface MeetingPageData {
  analytics: StudentAnalytics
  /** The last 30 days. */
  questions: QuestionsSummary
  questions_by_subject: { subject_id: number; solved: number; correct: number; wrong: number }[]
  /** Topic counts per status for every subject, in booklet order. */
  topic_progress: ({ subject_id: number; total: number } & Record<TopicStatus, number>)[]
  /** Coach notes marked visible to parents, newest first. */
  notes: Pick<CoachNote, 'id' | 'body' | 'created_at'>[]
  /** Latest meeting first. */
  meeting_notes: MeetingNote[]
}

export const fetchMeetingPage = (studentId: number) => request<MeetingPageData>(`/admin/students/${studentId}/meeting`)
export const addMeetingNote = (studentId: number, note: { meeting_date: string; body: string }) =>
  request<MeetingNote>(`/admin/students/${studentId}/meeting-notes`, json('POST', note))
export const deleteMeetingNote = (noteId: number) => request<void>(`/admin/meeting-notes/${noteId}`, { method: 'DELETE' })
