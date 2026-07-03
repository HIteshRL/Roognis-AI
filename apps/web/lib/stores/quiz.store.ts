import { create } from 'zustand'

interface QuizState {
  currentQuizId: string | null
  currentAttemptId: string | null
  responses: Record<string, string>
  questionStartTime: number | null
  questionTimes: Record<string, number>

  setCurrentQuiz: (quizId: string | null, attemptId?: string | null) => void
  recordAnswer: (questionId: string, answer: string) => void
  startQuestionTimer: () => void
  recordQuestionTime: (questionId: string) => void
  reset: () => void
}

export const useQuizStore = create<QuizState>((set, get) => ({
  currentQuizId: null,
  currentAttemptId: null,
  responses: {},
  questionStartTime: null,
  questionTimes: {},

  setCurrentQuiz: (quizId, attemptId = null) =>
    set({ currentQuizId: quizId, currentAttemptId: attemptId }),

  recordAnswer: (questionId, answer) =>
    set((s) => ({ responses: { ...s.responses, [questionId]: answer } })),

  startQuestionTimer: () => set({ questionStartTime: Date.now() }),

  recordQuestionTime: (questionId) => {
    const start = get().questionStartTime
    if (!start) return
    const elapsed = Date.now() - start
    set((s) => ({
      questionTimes: { ...s.questionTimes, [questionId]: elapsed },
      questionStartTime: null,
    }))
  },

  reset: () =>
    set({
      currentQuizId: null,
      currentAttemptId: null,
      responses: {},
      questionStartTime: null,
      questionTimes: {},
    }),
}))
