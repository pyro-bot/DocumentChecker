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

export function historyModelLabel(item) {
  if (item.model_name && item.model_id && item.model_name !== item.model_id) {
    return `${item.model_name} (${item.model_id})`
  }
  return item.model_name || item.model_id || 'Не указана'
}

export function historyTemplateLabel(item) {
  const name = item.template_name || 'без названия'
  if (item.template_source === 'predefined') {
    return `по готовому шаблону: ${name}`
  }
  if (item.template_source === 'uploaded') {
    return `шаблон загружен пользователем: ${name}`
  }
  if (item.template_source === 'text_input') {
    return 'шаблон введен текстом'
  }
  return item.template_name ? `шаблон: ${item.template_name}` : 'шаблон не указан'
}
