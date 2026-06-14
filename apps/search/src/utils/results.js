export function buildGroupedErrors(errors = []) {
  return {
    structural: { label: 'Структура', errors: errors.filter((error) => error.error_type === 'structural'), open: false },
    formatting: { label: 'Форматирование', errors: errors.filter((error) => error.error_type === 'formatting'), open: false },
    content: { label: 'Содержание', errors: errors.filter((error) => error.error_type === 'content'), open: false },
    typography: { label: 'Типографика', errors: errors.filter((error) => error.error_type === 'typography'), open: false },
  }
}

export function normalizeHistoryItem(item) {
  return {
    ...item,
    open: Boolean(item.open),
    result: item.result || { errors: [], compliance_score: item.compliance_score || 0, summary: '' },
    groupedErrors: buildGroupedErrors(item.result?.errors || []),
  }
}
