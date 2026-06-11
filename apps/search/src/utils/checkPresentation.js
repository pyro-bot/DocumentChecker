export const severityOrder = ['critical', 'high', 'medium', 'low']

export const sevEmoji = (severity) => ({
  critical: '🔴',
  high: '🟠',
  medium: '🟡',
  low: '🟢',
}[severity] ?? '⚪')

export const bySev = (errors, severity) => (errors || []).filter((error) => error.severity === severity)

export const sevBorderClass = (severity) => ({
  critical: 'border-l-red-500',
  high: 'border-l-orange-400',
  medium: 'border-l-yellow-400',
  low: 'border-l-green-400',
}[severity] ?? 'border-l-gray-300')

export function getMetrics(result = {}) {
  const errors = result.errors ?? []
  return [
    { label: 'Ошибок всего', value: errors.length },
    { label: 'Структурных', value: errors.filter((error) => error.error_type === 'structural').length },
    { label: 'Форматирования', value: errors.filter((error) => error.error_type === 'formatting').length },
  ]
}

export function formatDate(value) {
  if (!value) return ''
  return new Date(value).toLocaleString()
}
