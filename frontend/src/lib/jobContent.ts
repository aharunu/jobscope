/**
 * Utilities for cleaning, parsing, and sanitizing job descriptions,
 * responsibilities, and structured requirements for JobScope frontend.
 */

export interface ParsedJobContent {
  description: string;
  responsibilities: string | null;
  requirements: string | null;
  isHtml: boolean;
}

/**
 * Sanitizes HTML content for secure presentation.
 *
 * Strips active script tags, styles, iframes, form controls, and inline event
 * handlers. Ensures all anchor links have safe target and rel attributes.
 */
export function sanitizeJobHtml(rawHtml: string): string {
  if (!rawHtml || !rawHtml.trim()) return '';

  let html = rawHtml;

  // 1. Remove dangerous executable/embed elements and their contents
  html = html.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
  html = html.replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, '');
  html = html.replace(/<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi, '');
  html = html.replace(/<object\b[^<]*(?:(?!<\/object>)<[^<]*)*<\/object>/gi, '');
  html = html.replace(/<embed\b[^>]*>/gi, '');
  html = html.replace(/<form\b[^<]*(?:(?!<\/form>)<[^<]*)*<\/form>/gi, '');
  html = html.replace(/<svg\b[^<]*(?:(?!<\/svg>)<[^<]*)*<\/svg>/gi, '');
  html = html.replace(/<base\b[^>]*>/gi, '');

  // 2. Remove inline event handlers (onclick, onload, onerror, etc.)
  html = html.replace(/\s+on\w+\s*=\s*(?:'[^']*'|"[^"]*"|[^\s>]+)/gi, '');

  // 3. Remove javascript:, data:, and vbscript: URIs from href/src
  html = html.replace(/\s+(href|src)\s*=\s*['"]\s*(?:javascript|data|vbscript):[^'"]*['"]/gi, '');

  // 4. Ensure all anchor tags have safe external link attributes
  html = html.replace(/<a\b([^>]*)>/gi, (match, attrs) => {
    // Check if target and rel already exist
    let cleanAttrs = attrs
      .replace(/\s+target\s*=\s*['"][^'"]*['"]/gi, '')
      .replace(/\s+rel\s*=\s*['"][^'"]*['"]/gi, '');
    return `<a${cleanAttrs} target="_blank" rel="noopener noreferrer">`;
  });

  // 5. Replace non-breaking space entities for clean formatting
  html = html.replace(/&nbsp;/g, ' ');

  return html.trim();
}

/**
 * Checks whether a given string contains HTML tags.
 */
export function hasHtmlTags(text: string | null | undefined): boolean {
  if (!text) return false;
  return /<[a-z][\s\S]*>/i.test(text);
}

/**
 * Converts HTML list items into clean text bullet points if needed.
 */
export function cleanHtmlToText(content: string): string {
  if (!content) return '';
  let text = content.replace(/<\s*li[^>]*>(.*?)(?:<\s*\/\s*li\s*>|$)/gis, '- $1\n');
  text = text.replace(/<[^>]+>/g, ' ');
  text = text.replace(/&nbsp;/g, ' ');
  text = text.replace(/&quot;/g, '"');
  text = text.replace(/&amp;/g, '&');
  text = text.replace(/&lt;/g, '<');
  text = text.replace(/&gt;/g, '>');
  text = text.replace(/&#39;/g, "'");
  return text
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l && l !== '-')
    .join('\n');
}

/**
 * Parses raw description and responsibilities into structured, human-readable sections.
 *
 * Handles:
 * - Raw ATS JSON objects (such as Lever dumps): extracts descriptionBodyPlain,
 *   responsibilities from lists, and requirements.
 * - HTML markup: flags isHtml for safe formatted rendering.
 * - Plain text: preserves spacing, breaks, and structure.
 */
export function parseJobContent(
  rawDescription: string | null | undefined,
  rawResponsibilities?: string | null
): ParsedJobContent {
  let resp = rawResponsibilities?.trim() || null;
  let reqs: string | null = null;

  if (!rawDescription || !rawDescription.trim()) {
    return {
      description: '',
      responsibilities: resp,
      requirements: reqs,
      isHtml: false,
    };
  }

  let desc = rawDescription.trim();

  // Handle case where description is a serialized JSON object (e.g. Lever ATS payload)
  if (desc.startsWith('{') && desc.endsWith('}')) {
    try {
      const data = JSON.parse(desc);
      if (data && typeof data === 'object' && !Array.isArray(data)) {
        const parts: string[] = [];
        const opening = data.openingPlain || data.opening || '';
        const bodyPlain = data.descriptionPlain || data.descriptionBodyPlain || '';
        const bodyHtml = data.description || data.descriptionBody || '';
        const additional = data.additionalPlain || data.additional || '';

        if (opening && typeof opening === 'string' && opening.trim()) {
          parts.push(opening.trim());
        }
        if (bodyPlain && typeof bodyPlain === 'string' && bodyPlain.trim()) {
          parts.push(bodyPlain.trim());
        } else if (bodyHtml && typeof bodyHtml === 'string' && bodyHtml.trim()) {
          parts.push(bodyHtml.trim());
        }
        if (additional && typeof additional === 'string' && additional.trim()) {
          parts.push(additional.trim());
        }

        // Extract structured sections from lists (e.g. Responsibilities, Requirements)
        if (Array.isArray(data.lists)) {
          for (const lst of data.lists) {
            if (!lst || typeof lst !== 'object') continue;
            const sectionTitle = String(lst.text || '').trim();
            const sectionContent = String(lst.content || '').trim();
            if (!sectionContent) continue;

            const isResp = /responsibilit/i.test(sectionTitle);
            const isReq = /requirement|qualification/i.test(sectionTitle);

            if (isResp && !resp) {
              resp = sectionContent;
            } else if (isReq && !reqs) {
              reqs = sectionContent;
            } else {
              const cleanContent = cleanHtmlToText(sectionContent);
              if (sectionTitle) {
                parts.push(`${sectionTitle}:\n${cleanContent}`);
              } else {
                parts.push(cleanContent);
              }
            }
          }
        }

        if (parts.length > 0) {
          desc = parts.join('\n\n').trim();
        } else if (bodyPlain || bodyHtml) {
          desc = String(bodyPlain || bodyHtml).trim();
        }
      }
    } catch {
      // If JSON parsing fails, retain original description string
    }
  }

  const isHtml = hasHtmlTags(desc);

  return {
    description: desc,
    responsibilities: resp,
    requirements: reqs,
    isHtml,
  };
}
