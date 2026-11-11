type ValidationItem = {loc?: unknown[]; msg?: unknown};

export function formatApiError(payload: unknown, fallback = 'The API rejected this request.'): string {
  if (typeof payload === 'string' && payload.trim()) return payload;
  if (!payload || typeof payload !== 'object') return fallback;

  const value = payload as {detail?: unknown; message?: unknown; error?: unknown};
  const detail = value.detail;
  if (Array.isArray(detail)) {
    const messages = detail.map((item: ValidationItem) => {
      const message = typeof item?.msg === 'string' ? item.msg : 'Validation failed';
      const location = Array.isArray(item?.loc) ? item.loc.filter(Boolean).join('.') : '';
      return location ? `${location}: ${message}` : message;
    });
    if (messages.length) return messages.join(' • ');
  }
  for (const candidate of [detail, value.message, value.error]) {
    if (typeof candidate === 'string' && candidate.trim()) return candidate;
  }
  return fallback;
}
