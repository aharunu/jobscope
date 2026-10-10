'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { BriefcaseIcon, UserCircleIcon, SlidersHorizontalIcon, TrayIcon, StackIcon, CopyIcon, ListIcon, XIcon, CaretRightIcon } from '@/components/ui/icons';

const navigation = [
  { href: '/jobs', label: 'Jobs', icon: BriefcaseIcon },
  { href: '/search-profiles', label: 'Search Profiles', icon: SlidersHorizontalIcon },
  { href: '/applications', label: 'Applications', icon: TrayIcon },
  { href: '/profile', label: 'Profile', icon: UserCircleIcon },
  { href: '/ingestion', label: 'Ingestion', icon: StackIcon },
  { href: '/dedup', label: 'Duplicate Review', icon: CopyIcon },
];
type Appearance = 'system' | 'light' | 'dark';
const themeKey = 'jobscope_appearance';

function Logo({ mobile = false }: { mobile?: boolean }) {
  return <Link href="/jobs" className={`logo-group${mobile ? ' mobile-logo' : ''}`} aria-label="JobScope Jobs">
    {/* Preserve the existing JobScope globe mark and wordmark. */}
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.25" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10" /><line x1="2" y1="12" x2="22" y2="12" />
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
    </svg><span>JobScope</span>
  </Link>;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const [appearance, setAppearance] = useState<Appearance>('system');
  const menuButton = useRef<HTMLButtonElement>(null);
  const current = navigation.find(item => pathname === item.href || pathname.startsWith(item.href + '/'));

  useEffect(() => {
    try {
      const saved = localStorage.getItem(themeKey);
      if (saved === 'light' || saved === 'dark') {
        setAppearance(saved);
        document.documentElement.dataset.theme = saved;
      }
    } catch { /* Appearance still works when browser storage is unavailable. */ }
  }, []);

  useEffect(() => { setMenuOpen(false); }, [pathname]);
  useEffect(() => {
    if (!menuOpen) return;
    const dismiss = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { setMenuOpen(false); menuButton.current?.focus(); }
    };
    document.addEventListener('keydown', dismiss);
    return () => document.removeEventListener('keydown', dismiss);
  }, [menuOpen]);

  function changeAppearance(value: Appearance) {
    setAppearance(value);
    if (value === 'system') delete document.documentElement.dataset.theme;
    else document.documentElement.dataset.theme = value;
    try { localStorage.setItem(themeKey, value); } catch { /* Local-only preference. */ }
  }

  function links() {
    return navigation.map(({ href, label, icon: Icon }) => <Link key={href} href={href}
      className="nav-link" aria-current={current?.href === href ? 'page' : undefined}
      onClick={() => setMenuOpen(false)}>
      <Icon size={19} aria-hidden="true" /><span>{label}</span>
    </Link>);
  }

  return <>
    <a href="#main-content" className="skip-link">Skip to content</a>
    <div className="app-shell">
      <aside className="app-sidebar">
        <Logo />
        <nav className="app-nav" aria-label="Main navigation">{links()}</nav>
        <div className="sidebar-note">Evidence-based job discovery<br />and decision support.</div>
      </aside>
      <div className="app-workspace">
        <header className="app-header">
          <div className="container header-content">
            <Logo mobile />
            <div className="header-context"><span>JobScope</span><CaretRightIcon size={12} aria-hidden="true" /><strong>{current?.label || 'Workspace'}</strong></div>
            <div className="header-tools">
              <select className="appearance-select" aria-label="Appearance" value={appearance} onChange={e => changeAppearance(e.target.value as Appearance)}>
                <option value="system">System</option><option value="light">Light</option><option value="dark">Dark</option>
              </select>
              <button ref={menuButton} className="nav-toggle" type="button" aria-label={menuOpen ? 'Close navigation' : 'Open navigation'} aria-expanded={menuOpen} aria-controls="mobile-navigation" onClick={() => setMenuOpen(open => !open)}>
                {menuOpen ? <XIcon size={22} aria-hidden="true" /> : <ListIcon size={22} aria-hidden="true" />}
              </button>
            </div>
          </div>
        </header>
        {menuOpen && <nav id="mobile-navigation" className="mobile-nav app-nav" aria-label="Mobile navigation">{links()}</nav>}
        <main id="main-content" tabIndex={-1} className="app-main">{children}</main>
        <footer className="app-footer"><div className="container">JobScope<span aria-hidden="true">/</span>Evidence-Based Job Discovery &amp; Decision Support System</div></footer>
      </div>
    </div>
  </>;
}
