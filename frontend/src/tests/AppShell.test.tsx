import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { AppShell } from '@/components/layout/AppShell';

const route = vi.hoisted(() => ({ pathname: '/jobs' }));
vi.mock('next/navigation', () => ({ usePathname: () => route.pathname }));
vi.mock('next/link', () => ({ default: ({ children, onClick, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => <a {...props} onClick={event => {event.preventDefault(); onClick?.(event);}}>{children}</a> }));

beforeEach(() => { route.pathname = '/jobs'; localStorage.clear(); delete document.documentElement.dataset.theme; });
afterEach(() => { cleanup(); vi.restoreAllMocks(); delete document.documentElement.dataset.theme; });

describe('Responsive product shell', () => {
  it('keeps every existing route and marks nested routes as active', () => {
    route.pathname = '/search-profiles/new';
    render(<AppShell><h1>Create Search Profile</h1></AppShell>);
    const nav = within(screen.getByRole('navigation', { name: 'Main navigation' }));
    expect(nav.getAllByRole('link')).toHaveLength(6);
    const destinations = { Jobs: '/jobs', 'Search Profiles': '/search-profiles', Applications: '/applications', Profile: '/profile', Ingestion: '/ingestion', 'Duplicate Review': '/dedup' };
    for (const [name, href] of Object.entries(destinations)) expect(nav.getByRole('link', { name })).toHaveAttribute('href', href);
    expect(nav.getByRole('link', { name: 'Search Profiles' })).toHaveAttribute('aria-current', 'page');
    expect(nav.getByRole('link', { name: 'Jobs' })).not.toHaveAttribute('aria-current');
  });

  it('opens mobile navigation and closes it on Escape with focus restored', () => {
    render(<AppShell>Content</AppShell>);
    fireEvent.click(screen.getByRole('button', { name: 'Open navigation' }));
    expect(screen.getByRole('navigation', { name: 'Mobile navigation' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Close navigation' })).toHaveAttribute('aria-expanded', 'true');
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('navigation', { name: 'Mobile navigation' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Open navigation' })).toHaveFocus();
  });

  it('closes the mobile menu after choosing a destination', () => {
    render(<AppShell>Content</AppShell>);
    fireEvent.click(screen.getByRole('button', { name: 'Open navigation' }));
    fireEvent.click(within(screen.getByRole('navigation', { name: 'Mobile navigation' })).getByRole('link', { name: 'Profile' }));
    expect(screen.queryByRole('navigation', { name: 'Mobile navigation' })).not.toBeInTheDocument();
  });

  it('persists explicit appearance, restores it on remount, and allows system mode', () => {
    const view = render(<AppShell>Content</AppShell>);
    fireEvent.change(screen.getByRole('combobox', { name: 'Appearance' }), { target: { value: 'dark' } });
    expect(document.documentElement).toHaveAttribute('data-theme', 'dark');
    expect(localStorage.getItem('jobscope_appearance')).toBe('dark');
    view.unmount(); delete document.documentElement.dataset.theme;
    render(<AppShell>Content</AppShell>);
    expect(screen.getByRole('combobox', { name: 'Appearance' })).toHaveValue('dark');
    expect(document.documentElement).toHaveAttribute('data-theme', 'dark');
    fireEvent.change(screen.getByRole('combobox', { name: 'Appearance' }), { target: { value: 'light' } });
    expect(document.documentElement).toHaveAttribute('data-theme', 'light');
    fireEvent.change(screen.getByRole('combobox', { name: 'Appearance' }), { target: { value: 'system' } });
    expect(document.documentElement).not.toHaveAttribute('data-theme');
  });

  it('keeps appearance usable when preference storage fails', () => {
    vi.spyOn(window.localStorage, 'setItem').mockImplementation(() => { throw new Error('Unavailable'); });
    render(<AppShell><input aria-label="Existing draft" defaultValue="Preserved" /></AppShell>);
    fireEvent.change(screen.getByRole('combobox', { name: 'Appearance' }), { target: { value: 'dark' } });
    expect(document.documentElement).toHaveAttribute('data-theme', 'dark');
    expect(screen.getByRole('textbox', { name: 'Existing draft' })).toHaveValue('Preserved');
  });

  it('offers a keyboard skip link to the focusable content landmark', () => {
    render(<AppShell><h1>Job Discovery</h1></AppShell>);
    expect(screen.getByRole('link', { name: 'Skip to content' })).toHaveAttribute('href', '#main-content');
    expect(screen.getByRole('main')).toHaveAttribute('id', 'main-content');
    expect(screen.getByRole('main')).toHaveAttribute('tabindex', '-1');
  });
});
