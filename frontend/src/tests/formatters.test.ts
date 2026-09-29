import { describe, it, expect } from 'vitest';
import { formatRelativeTime, formatSalary, formatDate } from '../lib/formatters';

describe('Formatters', () => {
  describe('formatRelativeTime', () => {
    it('returns "Unknown" for null, undefined, or invalid date string', () => {
      expect(formatRelativeTime(null)).toBe('Unknown');
      expect(formatRelativeTime('')).toBe('Unknown');
      expect(formatRelativeTime('invalid-date')).toBe('Unknown');
    });

    it('returns "Just now" for dates within 60 seconds', () => {
      const nowIso = new Date().toISOString();
      expect(formatRelativeTime(nowIso)).toBe('Just now');
    });

    it('formats minutes ago', () => {
      const fiveMinsAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();
      expect(formatRelativeTime(fiveMinsAgo)).toBe('5m ago');
    });

    it('formats hours ago', () => {
      const threeHoursAgo = new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString();
      expect(formatRelativeTime(threeHoursAgo)).toBe('3h ago');
    });

    it('formats days ago', () => {
      const fourDaysAgo = new Date(Date.now() - 4 * 24 * 60 * 60 * 1000).toISOString();
      expect(formatRelativeTime(fourDaysAgo)).toBe('4d ago');
    });
  });

  describe('formatSalary', () => {
    it('returns "Not specified" for null or empty string', () => {
      expect(formatSalary(null)).toBe('Not specified');
      expect(formatSalary('')).toBe('Not specified');
      expect(formatSalary('   ')).toBe('Not specified');
    });

    it('returns trimmed salary string', () => {
      expect(formatSalary(' €80,000 - €95,000 ')).toBe('€80,000 - €95,000');
    });
  });

  describe('formatDate', () => {
    it('formats valid ISO date string', () => {
      const formatted = formatDate('2026-09-20T10:00:00Z');
      expect(formatted).toContain('2026');
      expect(formatted).toContain('Sep');
    });
  });
});
