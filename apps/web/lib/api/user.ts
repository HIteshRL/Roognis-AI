import type { ProfileDto, SettingsDto, UpdateProfileDto, UpdateSettingsDto } from '@roognis/shared'
import { apiClient } from './client'

export const userApi = {
  getProfile: () => apiClient.get<ProfileDto>('/api/v1/profile'),
  updateProfile: (data: UpdateProfileDto) => apiClient.put<ProfileDto>('/api/v1/profile', data),
  getSettings: () => apiClient.get<SettingsDto>('/api/v1/settings'),
  updateSettings: (data: UpdateSettingsDto) =>
    apiClient.put<SettingsDto>('/api/v1/settings', data),
}
