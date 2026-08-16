export function htmlToPlainText(value: string): string {
  const document = new DOMParser().parseFromString(value, 'text/html')
  return document.body.textContent?.trim() ?? ''
}
