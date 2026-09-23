import React from 'react';
import { Sun, Moon, RefreshCw, User, LogOut } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

export default function Header({
  theme,
  onToggleTheme,
  onRefreshAll,
  isRefreshing,
  currentUser,
  onOpenAuth,
  onLogout,
}) {
  const location = useLocation();
  const currentPath = location.pathname;

  const userInitial = currentUser?.full_name
    ? currentUser.full_name.charAt(0).toUpperCase()
    : null;

  return (
    <header className="top-bar">
      <div className="top-bar-left">
        <Link to="/" className="brand-badge" aria-label="WealthHub Dashboard">
          <span className="logo-symbol" />
          <span className="brand-name">WealthHub</span>
        </Link>

        {/* Navigation Links */}
        <nav className="header-nav" aria-label="Main Navigation">
          <Link
            to="/"
            className={`nav-link ${currentPath === '/' || currentPath.startsWith('/platforms') ? 'active' : ''}`}
          >
            Dashboard
          </Link>
          <Link
            to="/"
            onClick={(e) => {
              e.preventDefault();
              const el = document.querySelector('.investments-section');
              if (el) el.scrollIntoView({ behavior: 'smooth' });
            }}
            className="nav-link"
          >
            Portfolio
          </Link>
          <Link
            to="/"
            onClick={(e) => {
              e.preventDefault();
              const el = document.querySelector('.graph-card');
              if (el) el.scrollIntoView({ behavior: 'smooth' });
            }}
            className="nav-link"
          >
            Analytics
          </Link>
        </nav>
      </div>

      <div className="top-bar-actions">
        {/* Sync All Button */}
        <button
          className="icon-btn sync-btn"
          onClick={onRefreshAll}
          title="Sync all connected platforms"
          disabled={isRefreshing}
          aria-label={isRefreshing ? 'Syncing platforms' : 'Sync All'}
        >
          <RefreshCw size={13} className={isRefreshing ? 'spin-anim' : ''} />
          <span className="btn-text">{isRefreshing ? 'Syncing...' : 'Sync All'}</span>
        </button>

        {/* User Avatar / Auth */}
        {currentUser ? (
          <div className="user-profile-menu">
            <div
              className="user-avatar-initial"
              title={`Logged in as ${currentUser.full_name} (${currentUser.email})`}
            >
              {userInitial}
            </div>
            <span className="user-firstname">
              {currentUser.full_name.split(' ')[0]}
            </span>
            <button
              className="icon-btn logout-btn"
              onClick={onLogout}
              title="Sign Out"
              aria-label="Sign Out"
            >
              <LogOut size={13} />
            </button>
          </div>
        ) : (
          <button
            className="icon-btn auth-btn"
            onClick={onOpenAuth}
            title="Sign in to WealthHub"
          >
            <User size={13} />
            <span className="btn-text">Sign In</span>
          </button>
        )}

        {/* Theme Toggle */}
        <button
          className="icon-btn theme-toggle-btn"
          onClick={onToggleTheme}
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
        </button>
      </div>
    </header>
  );
}
