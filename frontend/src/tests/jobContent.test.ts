import { describe, it, expect } from 'vitest';
import {
  sanitizeJobHtml,
  hasHtmlTags,
  cleanHtmlToText,
  parseJobContent,
} from '../lib/jobContent';

describe('jobContent utilities', () => {
  describe('sanitizeJobHtml', () => {
    it('returns empty string for empty or whitespace input', () => {
      expect(sanitizeJobHtml('')).toBe('');
      expect(sanitizeJobHtml('   ')).toBe('');
    });

    it('strips dangerous tags like script, iframe, and form', () => {
      const malicious =
        '<p>Good text</p><script>alert("hack")</script><iframe src="evil.com"></iframe><form action="/steal"></form>';
      const cleaned = sanitizeJobHtml(malicious);
      expect(cleaned).toContain('<p>Good text</p>');
      expect(cleaned).not.toContain('<script');
      expect(cleaned).not.toContain('alert');
      expect(cleaned).not.toContain('<iframe');
      expect(cleaned).not.toContain('<form');
    });

    it('removes inline event handlers from tags', () => {
      const input = '<a href="https://example.com" onclick="doEvil()" onmouseover="steal()">Link</a>';
      const cleaned = sanitizeJobHtml(input);
      expect(cleaned).not.toContain('onclick');
      expect(cleaned).not.toContain('onmouseover');
      expect(cleaned).toContain('href="https://example.com"');
    });

    it('strips javascript: and data: URIs in links', () => {
      const input = '<a href="javascript:alert(1)">Click me</a>';
      const cleaned = sanitizeJobHtml(input);
      expect(cleaned).not.toContain('javascript:');
    });

    it('ensures safe target and rel attributes on anchor tags', () => {
      const input = '<a href="https://jobscope.io">JobScope</a>';
      const cleaned = sanitizeJobHtml(input);
      expect(cleaned).toContain('target="_blank"');
      expect(cleaned).toContain('rel="noopener noreferrer"');
    });

    it('replaces &nbsp; entities with normal spaces', () => {
      const input = 'Hello&nbsp;World&nbsp;Wide';
      const cleaned = sanitizeJobHtml(input);
      expect(cleaned).toBe('Hello World Wide');
    });
  });

  describe('hasHtmlTags', () => {
    it('accurately identifies HTML tags vs plain text', () => {
      expect(hasHtmlTags('<p>test</p>')).toBe(true);
      expect(hasHtmlTags('<div>hello</div>')).toBe(true);
      expect(hasHtmlTags('<br/>')).toBe(true);
      expect(hasHtmlTags('Just regular text')).toBe(false);
      expect(hasHtmlTags('5 < 10 and 20 > 15')).toBe(false);
      expect(hasHtmlTags(null)).toBe(false);
      expect(hasHtmlTags('')).toBe(false);
    });
  });

  describe('cleanHtmlToText', () => {
    it('converts li tags to bullet points and unescapes entities', () => {
      const input = '<li>First &quot;item&quot;</li><li>Second item&nbsp;&amp; more</li>';
      const text = cleanHtmlToText(input);
      expect(text).toContain('- First "item"');
      expect(text).toContain('- Second item & more');
    });
  });

  describe('parseJobContent', () => {
    it('handles null, undefined, and empty string', () => {
      const res = parseJobContent(null, null);
      expect(res.description).toBe('');
      expect(res.responsibilities).toBeNull();
      expect(res.requirements).toBeNull();
      expect(res.isHtml).toBe(false);
    });

    it('preserves plain text without HTML', () => {
      const desc = 'We are hiring a Senior Engineer.\nBuild APIs.';
      const res = parseJobContent(desc, 'Mentor engineers.');
      expect(res.description).toBe(desc);
      expect(res.responsibilities).toBe('Mentor engineers.');
      expect(res.requirements).toBeNull();
      expect(res.isHtml).toBe(false);
    });

    it('identifies HTML description', () => {
      const html = '<p>Company description</p>';
      const res = parseJobContent(html, null);
      expect(res.description).toBe(html);
      expect(res.isHtml).toBe(true);
    });

    it('unpacks serialized JSON payload and extracts structured sections', () => {
      const jsonPayload = JSON.stringify({
        descriptionPlain: 'Core team mission.',
        lists: [
          { text: 'Responsibilities', content: '<li>Feature development</li>' },
          { text: 'Requirements', content: '<li>TypeScript experience</li>' },
        ],
      });

      const res = parseJobContent(jsonPayload, null);
      expect(res.description).toContain('Core team mission.');
      expect(res.responsibilities).toBe('<li>Feature development</li>');
      expect(res.requirements).toBe('<li>TypeScript experience</li>');
    });
  });
});
