'use client';
import { ReactNode, useState, useEffect } from 'react';
import { Map, MessageSquare, LayoutDashboard, Settings, Activity, BarChart3, Network, BookMarked, Layers, Sun, Moon, Monitor } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Dialog } from '@base-ui/react';
import { Logo } from './Logo';
const navGroups = [
  {
    title: 'LEARN',
    items: [
      { id: 'overview', label: 'Dashboard', icon: LayoutDashboard },
      { id: 'tutor', label: 'AI Tutor', icon: MessageSquare },
      { id: 'sources', label: 'Library', icon: BookMarked },
      { id: 'assessment', label: 'Assessments', icon: Activity },
    ]
  },
  {
    title: 'UNDERSTAND',
    items: [
      { id: 'path', label: 'Learning Path', icon: Map },
      { id: 'concept-map', label: 'Concept Map', icon: Network },
      { id: 'analytics', label: 'Analytics', icon: BarChart3 },
    ]
  },
  {
    title: 'SYSTEM',
    items: [
      { id: 'settings', label: 'Settings', icon: Settings },
    ]
  }
];

import { useTheme } from 'next-themes';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (t: string) => void;
  setIsMobileOpen: (open: boolean) => void;
  theme: string | undefined;
  cycleTheme: () => void;
}

function SidebarContent({ activeTab, setActiveTab, setIsMobileOpen, theme, cycleTheme }: SidebarProps) {
  return (
    <div className="flex flex-col h-full bg-surface-2 border-r border-border w-60 shrink-0">
      <div className="p-6 pb-4">
        <div className="flex items-center gap-3 mb-1">
          {/* Logo Placeholder - should be replaced with TF SVG later */}
          <Logo className="w-8 h-8 text-accent" variant="icon" />
          <span className="font-heading font-bold text-lg tracking-tight">TutorForge AI</span>
        </div>
        <p className="text-[10px] font-mono text-text-muted uppercase tracking-wider ml-11">
          Personal Learning System
        </p>
      </div>

      <nav className="flex-1 overflow-y-auto py-4 px-4 space-y-6 custom-scrollbar">
        {navGroups.map(group => (
          <div key={group.title}>
            <h4 className="text-xs font-mono text-text-muted uppercase tracking-wider mb-2 px-3">
              {group.title}
            </h4>
            <ul className="space-y-0.5">
              {group.items.map(item => {
                const Icon = item.icon;
                const active = activeTab === item.id;
                return (
                  <li key={item.id}>
                    <button
                      onClick={() => { setActiveTab(item.id); setIsMobileOpen(false); }}
                      className={cn(
                        "w-full flex items-center gap-3 px-3 py-2 rounded-md transition-colors text-sm font-medium relative group",
                        active 
                          ? "text-text-primary bg-surface-3" 
                          : "text-text-secondary hover:text-text-primary hover:bg-surface-3/50"
                      )}
                    >
                      {active && (
                        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-4 bg-accent rounded-r-full" />
                      )}
                      <Icon className={cn("w-[18px] h-[18px] stroke-[1.75px]", active ? "text-accent" : "text-text-muted group-hover:text-text-primary")} />
                      <span>{item.label}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      <div className="p-4 border-t border-border">
        <button 
          onClick={cycleTheme}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-md transition-colors text-sm font-medium text-text-secondary hover:text-text-primary hover:bg-surface-3/50"
        >
          {theme === 'light' ? <Sun className="w-[18px] h-[18px] stroke-[1.75px] text-text-muted" /> : 
           theme === 'dark' ? <Moon className="w-[18px] h-[18px] stroke-[1.75px] text-text-muted" /> : 
           <Monitor className="w-[18px] h-[18px] stroke-[1.75px] text-text-muted" />}
          <span className="capitalize">{theme} Theme</span>
        </button>
      </div>
    </div>
  );
}

export function AppLayout({ children, activeTab, setActiveTab }: { children: ReactNode, activeTab: string, setActiveTab: (t: string) => void }) {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true);
  }, []);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(min-width: 768px)');
    const handleBreakpoint = (e: MediaQueryListEvent) => {
      if (e.matches) setIsMobileOpen(false);
    };
    mediaQuery.addEventListener('change', handleBreakpoint);
    return () => mediaQuery.removeEventListener('change', handleBreakpoint);
  }, []);

  // Only cycleTheme needs the resolved `theme` value; everything else renders immediately.
  const resolvedTheme = mounted ? theme : undefined;
  const cycleTheme = () => {
    const nextTheme = resolvedTheme === 'light' ? 'dark' : resolvedTheme === 'dark' ? 'system' : 'light';
    setTheme(nextTheme);
  };

  return (
    <div className="flex h-screen bg-background font-sans overflow-hidden">
      
      {/* Desktop Sidebar */}
      <aside className="hidden md:block z-40">
        <SidebarContent 
          activeTab={activeTab} 
          setActiveTab={setActiveTab} 
          setIsMobileOpen={setIsMobileOpen} 
          theme={theme} 
          cycleTheme={cycleTheme} 
        />
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto bg-background relative z-10 scroll-smooth pt-16 md:pt-0">
        <div className="max-w-[1400px] mx-auto min-h-full p-4 md:px-10 md:py-10">
          {children}
        </div>
      </main>

      {/* Mobile Top Nav */}
      <div className="md:hidden fixed top-0 left-0 right-0 h-16 bg-surface border-b border-border z-50 flex items-center justify-between px-4">
        <div className="flex items-center gap-2">
           <Logo className="w-6 h-6 text-accent" variant="icon" />
           <span className="font-heading font-bold text-lg">TutorForge</span>
        </div>
        <button onClick={() => setIsMobileOpen(!isMobileOpen)} className="p-2 border border-border rounded-md">
          <Layers className="w-5 h-5 text-text-secondary" />
        </button>
      </div>

      {/* Mobile Sidebar Overlay */}
      <Dialog.Root open={isMobileOpen} onOpenChange={setIsMobileOpen}>
        <Dialog.Portal>
          <Dialog.Backdrop className="md:hidden fixed inset-0 bg-black/20 z-40" />
          <Dialog.Popup className="md:hidden fixed top-0 left-0 bottom-0 z-50 shadow-xl focus:outline-none">
            <SidebarContent 
              activeTab={activeTab} 
              setActiveTab={setActiveTab} 
              setIsMobileOpen={setIsMobileOpen} 
              theme={theme} 
              cycleTheme={cycleTheme} 
            />
          </Dialog.Popup>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
