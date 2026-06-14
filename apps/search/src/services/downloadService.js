export function downloadBlob(blob, filename) {
  const anchor = Object.assign(document.createElement('a'), {
    href: URL.createObjectURL(blob),
    download: filename,
  })
  anchor.click()
  URL.revokeObjectURL(anchor.href)
}

export function downloadJson(data, filename) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  downloadBlob(blob, filename)
}
