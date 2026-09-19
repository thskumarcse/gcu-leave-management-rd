import apiClient from './apiClient'

/**
 * Calls GET /api/v1/health/ and returns the parsed response body.
 * Throws on network failure or non-2xx status so callers can branch on it.
 */
export async function fetchHealthStatus() {
  const response = await apiClient.get('/health/')
  return response.data
}
