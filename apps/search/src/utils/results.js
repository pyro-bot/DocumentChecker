export function buildGroupedErrors(errors = []) {
  return {
    structural: { label: 'Структура', errors: errors.filter((error) => error.error_type === 'structural'), open: false },
    formatting: { label: 'Форматирование', errors: errors.filter((error) => error.error_type === 'formatting'), open: false },
    content: { label: 'Содержание', errors: errors.filter((error) => error.error_type === 'content'), open: false },
    typography: { label: 'Типографика', errors: errors.filter((error) => error.error_type === 'typography'), open: false },
  }
}

export function normalizeHistoryItem(item) {
  const result = item.result || { errors: [], compliance_score: item.compliance_score || 0, summary: '' }
  return {
    ...item,
    open: Boolean(item.open),
    result,
    bibliographyResult: result.bibliography_result || null,
    groupedErrors: buildGroupedErrors(result.errors || []),
  }
}
