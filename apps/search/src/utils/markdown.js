function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function sanitizeMarkdownUrl(value) {
  const trimmed = String(value || '').trim()
  if (/^(https?:\/\/|mailto:|#)/i.test(trimmed)) return escapeHtml(trimmed)
  return ''
}

function renderInlineMarkdown(value) {
  const placeholders = []
  const stash = (html) => {
    const key = `%%MDPH${placeholders.length}%%`
    placeholders.push([key, html])
    return key
  }

  let text = String(value ?? '')
    .replace(/`([^`]+)`/g, (_, code) => stash(`<code>${escapeHtml(code)}</code>`))
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (match, label, href) => {
      const safeHref = sanitizeMarkdownUrl(href)
      if (!safeHref) return match
      return stash(`<a href="${safeHref}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`)
    })

  text = escapeHtml(text)
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/__([^_]+)__/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/_([^_]+)_/g, '<em>$1</em>')

  for (const [key, html] of placeholders) {
    text = text.replaceAll(key, html)
  }
  return text
}

function renderMarkdownTable(lines) {
  const cells = (line) => line.trim().replace(/^\||\|$/g, '').split('|').map((cell) => cell.trim())
  const headers = cells(lines[0])
  const rows = lines.slice(2).map(cells)
  return [
    '<table>',
    '<thead><tr>',
    headers.map((cell) => `<th>${renderInlineMarkdown(cell)}</th>`).join(''),
    '</tr></thead>',
    '<tbody>',
    rows.map((row) => `<tr>${row.map((cell) => `<td>${renderInlineMarkdown(cell)}</td>`).join('')}</tr>`).join(''),
    '</tbody></table>',
  ].join('')
}

export function renderMarkdown(markdown) {
  const lines = String(markdown ?? '').replace(/\r\n/g, '\n').split('\n')
  const html = []
  let paragraph = []
  let listType = null
  let listItems = []
  let quoteLines = []
  let codeLines = []
  let inCode = false

  const flushParagraph = () => {
    if (!paragraph.length) return
    html.push(`<p>${renderInlineMarkdown(paragraph.join(' '))}</p>`)
    paragraph = []
  }
  const flushList = () => {
    if (!listType) return
    html.push(`<${listType}>${listItems.map((item) => `<li>${renderInlineMarkdown(item)}</li>`).join('')}</${listType}>`)
    listType = null
    listItems = []
  }
  const flushQuote = () => {
    if (!quoteLines.length) return
    html.push(`<blockquote>${quoteLines.map((line) => `<p>${renderInlineMarkdown(line)}</p>`).join('')}</blockquote>`)
    quoteLines = []
  }
  const flushCode = () => {
    html.push(`<pre><code>${escapeHtml(codeLines.join('\n'))}</code></pre>`)
    codeLines = []
  }

  for (let i = 0; i < lines.length; i += 1) {
    const raw = lines[i]
    const trimmed = raw.trim()

    if (trimmed.startsWith('```')) {
      if (inCode) {
        flushCode()
        inCode = false
      } else {
        flushParagraph()
        flushList()
        flushQuote()
        inCode = true
      }
      continue
    }

    if (inCode) {
      codeLines.push(raw)
      continue
    }

    const next = lines[i + 1]?.trim() || ''
    if (trimmed.includes('|') && /^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$/.test(next)) {
      flushParagraph()
      flushList()
      flushQuote()
      const tableLines = [trimmed, next]
      i += 2
      while (i < lines.length && lines[i].trim().includes('|')) {
        tableLines.push(lines[i].trim())
        i += 1
      }
      i -= 1
      html.push(renderMarkdownTable(tableLines))
      continue
    }

    if (!trimmed) {
      flushParagraph()
      flushList()
      flushQuote()
      continue
    }

    const heading = trimmed.match(/^(#{1,6})\s+(.+)$/)
    if (heading) {
      flushParagraph()
      flushList()
      flushQuote()
      const level = heading[1].length
      html.push(`<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`)
      continue
    }

    if (/^---+$/.test(trimmed)) {
      flushParagraph()
      flushList()
      flushQuote()
      html.push('<hr />')
      continue
    }

    const quote = trimmed.match(/^>\s?(.*)$/)
    if (quote) {
      flushParagraph()
      flushList()
      quoteLines.push(quote[1])
      continue
    }

    const unordered = trimmed.match(/^[-*+]\s+(.+)$/)
    const ordered = trimmed.match(/^\d+[.)]\s+(.+)$/)
    if (unordered || ordered) {
      flushParagraph()
      flushQuote()
      const currentType = unordered ? 'ul' : 'ol'
      if (listType && listType !== currentType) flushList()
      listType = currentType
      listItems.push((unordered || ordered)[1])
      continue
    }

    flushList()
    flushQuote()
    paragraph.push(trimmed)
  }

  if (inCode) flushCode()
  flushParagraph()
  flushList()
  flushQuote()

  return html.join('\n') || '<p class="text-gray-400">РЁР°Р±Р»РѕРЅ РїСѓСЃС‚.</p>'
}
