import type { AuthResponseDto, UserDto } from '@roognis/shared'
import { apiClient } from './client'

export type SignupRole = 'student' | 'parent' | 'teacher'

export const authApi = {
  register: (email: string, username: string, password: string, role: SignupRole = 'student') =>
    apiClient.post<AuthResponseDto>('/api/v1/auth/register', { email, username, password, role }),

  login: (email: string, password: string) =>
    apiClient.post<AuthResponseDto>('/api/v1/auth/login', { email, password }),

  logout: () => apiClient.post<void>('/api/v1/auth/logout', {}),

  me: () => apiClient.get<UserDto>('/api/v1/auth/me'),
}
