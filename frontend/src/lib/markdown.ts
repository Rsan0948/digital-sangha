import { marked } from 'marked';
import DOMPurify from 'dompurify';

marked.setOptions({
  gfm: true,
  breaks: true,
});

export function renderMarkdown(content: string): string {
  if (!content) return '';
  const html = marked.parse(content);
  return DOMPurify.sanitize(html, { USE_PROFILES: { html: true } });
}
