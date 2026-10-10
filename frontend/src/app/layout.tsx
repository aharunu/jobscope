import type { Metadata } from 'next';
import localFont from 'next/font/local';
import { AppShell } from '@/components/layout/AppShell';
import '../styles/globals.css';

// Keep self-hosted type from swapping after the first paint on slow connections.
const GeistSans = localFont({
  src: '../../node_modules/geist/dist/fonts/geist-sans/Geist-Variable.woff2',
  variable: '--font-geist-sans', weight: '100 900', display: 'optional',
});
const GeistMono = localFont({
  src: '../../node_modules/geist/dist/fonts/geist-mono/GeistMono-Variable.woff2',
  variable: '--font-geist-mono', weight: '100 900', display: 'optional',
  adjustFontFallback: false, fallback: ['ui-monospace', 'monospace'], preload: false,
});

export const metadata: Metadata = {
  title: 'JobScope - Job Discovery & Decision Support',
  description: 'Discover, search, and evaluate job postings with evidence-based deterministic matching.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable}`} suppressHydrationWarning>
      <body><AppShell>{children}</AppShell></body>
    </html>
  );
}
