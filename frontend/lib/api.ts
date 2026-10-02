// API client for TutorForge AI backend
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class APIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'APIError';
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const body = await response.text().catch(() => '');
    let errorMessage = body || response.statusText;
    try {
      const parsed = JSON.parse(body);
      if (parsed.detail) errorMessage = parsed.detail;
      else if (parsed.message) errorMessage = parsed.message;
      else if (parsed.error?.message) errorMessage = parsed.error.message;
    } catch (e) {
      // not JSON
    }
    throw new APIError(response.status, errorMessage);
  }

  const text = await response.text();
  if (!text) return {} as T;
  return JSON.parse(text) as T;
}

// ─── Types ───────────────────────────────────────────────────────────────────

export interface Source {
  id: number;
  name: string;
  original_filename?: string;
  source_type: string;
  file_path?: string;
  file_size?: number;
  status: string;
  chunk_count: number;
  created_at: string;
  error_message?: string;
  is_demo?: boolean;
}

export interface SourceStatus {
  id: number;
  status: string;
  chunk_count: number;
  error_message?: string;
}

export interface ChatSession {
  id: number;
  title: string;
  created_at: string;
}

export interface ChatMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  citations: Citation[];
  created_at: string;
  isError?: boolean;
}

export interface Citation {
  source_id: number;
  source_name: string;
  source_type: string;
  location: string;
  excerpt: string;
  relevance: number;
  page_number?: number | null;
  slide_number?: number | null;
  timestamp_start?: number | null;
  timestamp_end?: number | null;
}

export interface Question {
  id: number;
  text: string;
  question_type: 'mcq' | 'true_false' | 'short_answer' | 'fill_blank';
  options: string[] | null;
  correct_answer: string;
  explanation: string;
  difficulty: number;
  difficulty_label: string;
  concept_id: number | null;
  concept_name: string | null;
}

export interface Assessment {
  id: number;
  concept_id: number | null;
  questions: Question[];
  status: string;
}

export interface AnswerResult {
  is_correct: boolean;
  score: number;
  feedback: string;
  explanation: string;
  correct_answer: string;
  next_difficulty: number;
  updated_mastery: number | null;
  badges_earned: string[];
}

export interface Mastery {
  concept_id: number;
  concept_name: string;
  score: number;
  questions_seen: number;
  correct_answers: number;
  last_updated: string | null;
}

export interface LearningPathItem {
  type: string;
  title: string;
  description: string;
  duration_minutes: number;
  concept_id?: number;
  concept_name?: string;
  source_id?: number;
  source_name?: string;
  mastery_score?: number;
  priority: string;
  icon: string;
  order: number;
  completed: boolean;
}

export interface LearningPathSummary {
  weak_count: number;
  developing_count: number;
  mastered_count: number;
  unseen_count: number;
}

export interface LearningPath {
  generated_at: string;
  total_time_minutes: number;
  items: LearningPathItem[];
  summary: LearningPathSummary;
}

export interface UploadResponse {
  id: number;
  name: string;
  status: string;
  message: string;
}

export interface MessageResponse {
  session_id: number;
  message_id: number;
  response: string;
  citations: Citation[];
  retrieved_chunks: number;
  context_used: boolean;
}

// ─── Sources API ─────────────────────────────────────────────────────────────

export const sourcesApi = {
  list: () => request<Source[]>('/api/sources'),

  upload: async (file: File, onProgress?: (pct: number) => void): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', `${API_BASE}/api/sources/upload`);

      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && onProgress) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(JSON.parse(xhr.responseText));
        } else {
          reject(new APIError(xhr.status, xhr.responseText));
        }
      };

      xhr.onerror = () => reject(new Error('Network error'));
      xhr.send(formData);
    });
  },

  get: (id: number) => request<Source>(`/api/sources/${id}`),

  getStatus: (id: number) =>
    request<SourceStatus>(`/api/sources/${id}/status`),

  delete: (id: number) =>
    request<{ message: string }>(`/api/sources/${id}`, { method: 'DELETE' }),
};

// ─── Chat API (sessions-based) ───────────────────────────────────────────────

export const chatApi = {
  createSession: (title?: string, studentId: string = 'default_student') =>
    request<ChatSession>('/api/chat/sessions', {
      method: 'POST',
      body: JSON.stringify({ title: title || 'New Chat', student_id: studentId }),
    }),

  listSessions: (studentId: string = 'default_student') =>
    request<ChatSession[]>(`/api/chat/sessions?student_id=${studentId}`),

  getMessages: (sessionId: number) =>
    request<ChatMessage[]>(`/api/chat/sessions/${sessionId}/messages`),

  sendMessage: (content: string, sessionId?: number, studentId: string = 'default_student') =>
    request<MessageResponse>('/api/chat/message', {
      method: 'POST',
      body: JSON.stringify({ content, session_id: sessionId, student_id: studentId }),
    }),

  deleteSession: (sessionId: number) =>
    request<{ message: string }>(`/api/chat/sessions/${sessionId}`, { method: 'DELETE' }),
};

export interface DiagnosticState {
  assessment_id: number;
  concept: { id: number, name: string };
  question: Question | null;
  mastery_before: number;
  difficulty: number;
  difficulty_label: string;
}

export interface AnswerSubmitResponse {
  is_correct: boolean;
  feedback: string;
  correct_answer: string;
  explanation: string;
  mastery_before: number;
  mastery_after: number;
  mastery_label: string;
  next_difficulty: number;
  next_difficulty_label: string;
  next_question: Question | null;
  total_questions: number;
  correct_count: number;
  source_chunks: unknown[];
  badges_earned?: string[];
}

export const assessmentApi = {
  start: (conceptId?: number, difficulty?: number, userId: string = "default_student") =>
    request<DiagnosticState>('/api/assessment/start', {
      method: 'POST',
      body: JSON.stringify({ concept_id: conceptId, student_id: userId }),
    }),

  submit: (assessmentId: number, questionId: number, answer: string, timeMs: number = 0, userId: string = "default_student") =>
    request<AnswerSubmitResponse>('/api/assessment/submit', {
      method: 'POST',
      body: JSON.stringify({ assessment_id: assessmentId, question_id: questionId, answer, time_spent: timeMs, student_id: userId }),
    }),

  mastery: (userId: string = "default_student") =>
    request<Mastery[]>(`/api/assessment/mastery?student_id=${encodeURIComponent(userId)}`),
};

// ─── Learning Path API ────────────────────────────────────────────────────────

export const learningPathApi = {
  get: (userId: string = 'default_student') =>
    request<LearningPath>(`/api/learning-path?student_id=${encodeURIComponent(userId)}`),
};

// ─── Concepts API ─────────────────────────────────────────────────────────────

export interface ConceptGraphNode {
  id: number;
  label: string;
  description: string;
  parent_id: number | null;
  subject: string;
  mastery_score: number | null;
  mastery_pct: number | null;
  status: string;
  color: string;
}

export interface ConceptGraphEdge {
  source: number;
  target: number;
  type: string;
}

export interface ConceptGraph {
  nodes: ConceptGraphNode[];
  edges: ConceptGraphEdge[];
}

export const conceptsApi = {
  graph: (userId: string = 'default_student') =>
    request<ConceptGraph>(`/api/concepts/graph?student_id=${userId}`),

  get: (conceptId: number, userId: string = 'default_student') =>
    request<ConceptGraphNode>(`/api/concepts/${conceptId}?student_id=${userId}`),
};

// ─── Analytics API ────────────────────────────────────────────────────────────

export interface ConceptMastery {
  concept_id: number;
  concept_name: string;
  score: number;
  percentage: number;
  label: string;
  questions_seen: number;
  correct_answers: number;
}

export interface AnalyticsDashboard {
  overall_mastery: number;
  overall_mastery_pct: number;
  mastered_concepts: number;
  total_concepts_attempted: number;
  total_questions_answered: number;
  correct_count: number;
  accuracy: number;
  accuracy_pct: number;
  study_time_minutes: number;
  streak_days: number;
  concept_masteries: ConceptMastery[];
}

export const analyticsApi = {
  dashboard: (userId: string = 'default_student') =>
    request<AnalyticsDashboard>(`/api/analytics/dashboard?student_id=${userId}`),

  insights: (userId: string = 'default_student') =>
    request<{ insights: string[] }>(`/api/analytics/insights?student_id=${userId}`),

  masteryHistory: (userId: string = 'default_student', days: number = 30) =>
    request<{ history: { date: string; mastery: number }[] }>(
      `/api/analytics/mastery-history?student_id=${userId}&days=${days}`
    ),
};
