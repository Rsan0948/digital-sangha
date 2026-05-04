import { describe, it, expect } from 'vitest';
import { renderMarkdown } from '../markdown';

describe('renderMarkdown', () => {
  it('returns empty string for empty input', () => {
    expect(renderMarkdown('')).toBe('');
  });

  it('renders basic markdown to HTML', () => {
    const html = renderMarkdown('# Heading\n\nSome **bold** text.');
    expect(html).toContain('<h1');
    expect(html).toContain('Heading');
    expect(html).toContain('<strong>bold</strong>');
  });

  it('strips inline <script> tags from XSS payloads', () => {
    const html = renderMarkdown('Hello <script>alert(1)</script> world');
    expect(html).not.toMatch(/<script/i);
    expect(html).not.toContain('alert(1)');
    expect(html).toContain('Hello');
    expect(html).toContain('world');
  });

  it('strips on* event handlers from inline HTML', () => {
    const html = renderMarkdown('<img src="x" onerror="alert(1)" />');
    expect(html).not.toMatch(/onerror/i);
    expect(html).not.toContain('alert(1)');
  });

  it('removes javascript: URIs from links', () => {
    const html = renderMarkdown('[click](javascript:alert(1))');
    expect(html).not.toMatch(/javascript:/i);
  });
});
