import React from 'react';
import { Sparkles, Moon, Sun } from 'lucide-react';

export const Navbar: React.FC = () => {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-white/5 bg-darkBg/80 backdrop-blur-md">
      <div className="flex h-16 items-center justify-between px-6">
        {/* Logo and Badge */}
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-tr from-primaryPurple to-secondaryBlue text-white shadow-lg shadow-primaryPurple/25">
            <span className="text-lg font-bold">⚡</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-base font-semibold tracking-tight text-white font-sans">
              Smart DevTool
            </span>
            <span className="text-xs font-medium text-accentCyan border border-accentCyan/20 bg-accentCyan/10 px-1.5 py-0.5 rounded-full flex items-center gap-1 shadow-sm shadow-accentCyan/5">
              <Sparkles className="h-3 w-3 animate-pulse" />
              AI Powered
            </span>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="hidden md:flex items-center gap-6">
          <a
            href="#dashboard"
            className="text-sm font-medium text-gray-300 hover:text-white transition-colors"
          >
            Dashboard
          </a>
          <a
            href="#documentation"
            className="text-sm font-medium text-gray-300 hover:text-white transition-colors"
          >
            Documentation
          </a>
          <a
            href="#about"
            className="text-sm font-medium text-gray-300 hover:text-white transition-colors"
          >
            About
          </a>
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-sm font-medium text-gray-300 hover:text-white transition-colors"
          >
            <svg className="h-4 w-4 fill-current" viewBox="0 0 24 24">
              <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/>
            </svg>
            GitHub
          </a>
        </nav>


        {/* Header Actions */}
        <div className="flex items-center gap-4">
          {/* Theme switcher representation (Static dark since the goal is dark-mode only) */}
          <div className="flex h-8 items-center rounded-lg bg-zinc-900 border border-white/5 p-0.5">
            <button
              className="flex h-7 w-7 items-center justify-center rounded-md text-zinc-400"
              title="Light mode (disabled)"
              disabled
            >
              <Sun className="h-4 w-4" />
            </button>
            <button
              className="flex h-7 w-7 items-center justify-center rounded-md bg-zinc-800 text-white shadow-sm"
              title="Dark mode only"
            >
              <Moon className="h-4 w-4" />
            </button>
          </div>

          {/* User Profile Avatar */}
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primaryPurple/20 border border-primaryPurple/50 text-xs font-semibold text-primaryPurple select-none hover:bg-primaryPurple hover:text-white transition-all cursor-pointer">
            SD
          </div>
        </div>
      </div>
    </header>
  );
};
