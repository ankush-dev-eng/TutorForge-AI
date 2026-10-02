'use client';

import { Cpu, Database, Palette, ShieldCheck, Activity } from 'lucide-react';

export function SettingsView() {
  return (
    <div className="flex flex-col h-full w-full max-w-4xl mx-auto py-8 px-2 md:px-0 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      <header className="mb-10">
        <h1 className="text-3xl md:text-4xl font-semibold mb-3 tracking-tight">System Settings</h1>
        <p className="text-muted-foreground text-sm uppercase tracking-widest font-medium">
          Configuration & Diagnostics
        </p>
      </header>

      <div className="space-y-8">
        
        {/* AI Configuration */}
        <section className="bg-card border border-border/40 p-6 md:p-8 shadow-sm">
          <h3 className="text-sm font-semibold uppercase tracking-widest text-muted-foreground mb-6 flex items-center gap-2">
            <Cpu className="w-4 h-4" /> AI Engine Configuration
          </h3>
          
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 border border-border/30 bg-muted/20 gap-4">
              <div>
                <div className="text-sm font-semibold mb-1">Advanced Reasoning Engine</div>
                <div className="text-xs text-muted-foreground font-medium">Enable deep-reasoning mode for complex academic queries (increased latency).</div>
              </div>
              <div className="w-10 h-5 bg-primary relative cursor-pointer shrink-0">
                <div className="w-4 h-4 bg-primary-foreground absolute right-0.5 top-0.5"></div>
              </div>
            </div>
            
            <div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 border border-border/30 bg-muted/20 gap-4">
              <div>
                <div className="text-sm font-semibold mb-1">Vector Search Provider</div>
                <div className="text-xs text-muted-foreground font-medium">Currently mapped to local filesystem embeddings.</div>
              </div>
              <select className="bg-background border border-border/40 px-3 py-1.5 text-xs font-medium uppercase tracking-wider outline-hidden focus:border-primary shrink-0 cursor-not-allowed text-muted-foreground" disabled>
                <option>LocalStore (Active)</option>
              </select>
            </div>
          </div>
        </section>

        {/* Appearance (Read-only as it's managed via sidebar) */}
        <section className="bg-card border border-border/40 p-6 md:p-8 shadow-sm">
          <h3 className="text-sm font-semibold uppercase tracking-widest text-muted-foreground mb-6 flex items-center gap-2">
            <Palette className="w-4 h-4" /> Appearance
          </h3>
          <div className="p-4 border border-border/30 bg-muted/20">
            <div className="text-sm font-semibold mb-1">Theme Preferences</div>
            <div className="text-xs text-muted-foreground font-medium">Theme selection is now managed globally via the sidebar navigation menu.</div>
          </div>
        </section>

        {/* System Diagnostics */}
        <section className="bg-card border border-border/40 p-6 md:p-8 shadow-sm">
          <h3 className="text-sm font-semibold uppercase tracking-widest text-muted-foreground mb-6 flex items-center gap-2">
            <Activity className="w-4 h-4" /> System Diagnostics
          </h3>
          
          <div className="space-y-1">
            <div className="flex justify-between items-center p-3 border-b border-border/20 last:border-0 text-sm">
              <span className="font-medium text-muted-foreground">API Telemetry</span>
              <span className="text-green-700 dark:text-green-400 font-semibold flex items-center gap-2">
                <div className="w-2 h-2 bg-green-500 rounded-none animate-pulse"></div> Online
              </span>
            </div>
            
            <div className="flex justify-between items-center p-3 border-b border-border/20 last:border-0 text-sm">
              <span className="font-medium text-muted-foreground">Relational Database</span>
              <span className="text-green-700 dark:text-green-400 font-semibold flex items-center gap-2">
                <Database className="w-3.5 h-3.5" /> Connected
              </span>
            </div>
            
            <div className="flex justify-between items-center p-3 border-b border-border/20 last:border-0 text-sm">
              <span className="font-medium text-muted-foreground">Vector Store</span>
              <span className="text-green-700 dark:text-green-400 font-semibold flex items-center gap-2">
                <ShieldCheck className="w-3.5 h-3.5" /> Active
              </span>
            </div>
          </div>
        </section>
        
      </div>
    </div>
  );
}
