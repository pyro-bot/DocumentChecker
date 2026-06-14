export const TEMPLATE_FILE_ACCEPT = '.docx,.md,.markdown'
export const TEMPLATE_FILE_HINT = '.docx, .md, .markdown'

export function isTemplateFileName(name) {
  return /\.(docx|md|markdown)$/i.test(name || '')
}

export function isMarkdownTemplate(template) {
  return template?.kind === 'markdown' || /\.(md|markdown)$/i.test(template?.id || '')
}
