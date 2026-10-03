/** Extract a customer reply only from a successful n8n response envelope. */
export function extractN8nReply(httpStatus, body) {
  if (!Number.isInteger(httpStatus) || httpStatus < 200 || httpStatus >= 300) return null;
  if (!body || typeof body !== 'object' || Array.isArray(body)) return null;

  const status = String(body.status || '').trim().toLowerCase();
  if (['error', 'failed', 'failure'].includes(status)) return null;

  for (const field of ['response', 'final_reply', 'reply']) {
    const value = body[field];
    if (typeof value === 'string' && value.trim()) return value.trim();
  }
  return null;
}
