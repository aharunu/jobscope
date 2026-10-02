import type { Metadata } from 'next';
import Link from 'next/link';
import '../styles/globals.css';

export const metadata: Metadata = {
  title: 'JobScope — Job Discovery & Decision Support',
  description: 'Discover, search, and evaluate job postings with evidence-based deterministic matching.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        {/* Sticky App Header */}
        <header className="app-header">
          <div className="container header-content">
            <Link href="/jobs" className="logo-group">
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.25"
                strokeLinecap="round"
                strokeLinejoin="round"
                style={{ color: 'var(--primary-light)' }}
              >
                <circle cx="12" cy="12" r="10" />
                <line x1="2" y1="12" x2="22" y2="12" />
                <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
              </svg>
              <span>JobScope</span>
              <span className="logo-badge">Discovery</span>
            </Link>

            <nav style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', flexWrap: 'wrap' }}>
              <Link href="/applications" style={{fontSize: '0.875rem', fontWeight: 600}}>Applications</Link>
              <Link href="/profile" style={{fontSize: '0.875rem', fontWeight: 600}}>Profile</Link>
              <Link
                href="/jobs"
                style={{
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  color: 'var(--text-primary)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
                  <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
                </svg>
                <span>Jobs</span>
              </Link>
              <Link
                href="/search-profiles"
                style={{
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  color: 'var(--text-secondary)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
                <span>Search Profiles</span>
              </Link>
            </nav>
          </div>
        </header>

        {/* Main Content Area */}
        <main style={{ flex: 1, paddingBottom: '3rem' }}>
          {children}
        </main>

        {/* Minimal Footer */}
        <footer
          style={{
            borderTop: '1px solid var(--border-subtle)',
            padding: '1.5rem 0',
            textAlign: 'center',
            fontSize: '0.8125rem',
            color: 'var(--text-muted)',
            backgroundColor: 'rgba(8, 12, 20, 0.5)',
          }}
        >
          <div className="container">
            JobScope — Evidence-Based Job Discovery & Decision Support System
          </div>
        </footer>
      </body>
    </html>
  );
}
