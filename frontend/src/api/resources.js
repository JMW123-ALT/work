import { apiGet, apiPost, apiDelete, apiUpload } from './client.js'

/** GET /api/documents  — v2 PostgreSQL list */
export const listDocuments = () => apiGet('/api/documents')

/** GET /api/documents/:id — single document status */
export const getDocument = (id) => apiGet(`/api/documents/${id}`)

/** DELETE /api/documents/:id */
export const deleteDocument = (id) => apiDelete(`/api/documents/${id}`)

/** POST /api/documents/:id/retry — re-index failed document */
export const retryDocument = (id) => apiPost(`/api/documents/${id}/retry`, {})

/** GET /api/v1/resource-categories */
export const getCategories = () => apiGet('/api/v1/resource-categories')

/**
 * 文本入库
 * POST /api/v1/ingest/text
 */
export function ingestText({ title, content, objectType = 'other', permissionLevel = 'internal', ingestRole = 'admin', operator = 'local-admin', modality = 'text' }) {
  return apiPost('/api/v1/ingest/text', {
    title,
    content,
    object_type: objectType,
    permission_level: permissionLevel,
    ingest_role: ingestRole,
    operator,
    modality,
  })
}

/**
 * 文件入库
 * POST /api/v1/ingest/file
 */
export function ingestFile(formPayload) {
  return apiUpload('/api/v1/ingest/file', formPayload)
}
