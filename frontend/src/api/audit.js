import { apiGet } from './client.js'

/** GET /api/audit */
export const getAuditLog = () => apiGet('/api/audit')
