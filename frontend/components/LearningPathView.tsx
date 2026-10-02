'use client';

import { LearningPath } from '@/lib/api';
import { Map as MapIcon, Compass, BookOpen, Clock, Target, CheckCircle2, TrendingUp, AlertCircle, CircleDashed } from 'lucide-react';

export function LearningPathView({ path, setActiveTab }: { path: LearningPath | null; setActiveTab?: (tab: string) => void }) {
  if (!path) {
    return (
      <div className="flex flex-col items-center justify-center h-full max-w-2xl mx-auto space-y-8 animate-in fade-in duration-700">
        <div className="w-16 h-16 bg-muted/30 flex items-center justify-center rounded-lg border border-border/40">
          <MapIcon className="w-8 h-8 text-primary/80" />
        </div>
        <div className="text-center">
          <h2 className="text-3xl font-semibold mb-4 tracking-tight">Curriculum Map</h2>
          <p className="text-muted-foreground text-base mb-8 leading-relaxed max-w-lg mx-auto">
            Your personalized learning trajectory is currently being generated. Upload relevant study materials or complete a diagnostic assessment to synthesize your map.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full w-full max-w-6xl mx-auto py-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <header className="mb-10 flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <h1 className="text-3xl md:text-4xl font-semibold mb-3 tracking-tight">Curriculum Map</h1>
          <p className="text-muted-foreground text-base max-w-2xl leading-relaxed">
            A sequenced progression designed to construct mastery through targeted interventions.
          </p>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12">
        {/* Left Column - Journey */}
        <div className="lg:col-span-8 space-y-8 relative">
          <div className="absolute top-4 bottom-4 left-9 w-px bg-border/60 z-0 hidden md:block"></div>
          
          {path.items.map((topic, index) => {
            const isActive = index === 0;
            return (
              <div key={topic.order} className="relative z-10 flex flex-col md:flex-row gap-6">
                
                {/* Node indicator */}
                <div className="hidden md:flex flex-col items-center">
                  <div className={`w-18 h-18 flex items-center justify-center border-4 border-background shrink-0 ${
                    isActive 
                      ? 'bg-primary text-primary-foreground' 
                      : 'bg-muted text-muted-foreground border-border/40'
                  }`}>
                    <span className="font-semibold text-lg">{index + 1}</span>
                  </div>
                </div>
                
                {/* Topic Card */}
                <div className={`flex-1 bg-card border p-6 md:p-8 flex flex-col ${
                  isActive 
                    ? 'border-primary shadow-sm' 
                    : 'border-border/40 opacity-80 hover:opacity-100 transition-opacity'
                }`}>
                  
                  <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-4 mb-4">
                    <h3 className="text-xl font-medium leading-tight">{topic.title}</h3>
                    <span className={`px-2.5 py-1 text-xs uppercase tracking-wider font-medium whitespace-nowrap border ${
                      topic.priority === 'high' ? 'border-red-500/30 text-red-600 dark:text-red-400 bg-red-500/5' : 
                      topic.priority === 'medium' ? 'border-amber-500/30 text-amber-600 dark:text-amber-400 bg-amber-500/5' : 
                      'border-blue-500/30 text-blue-600 dark:text-blue-400 bg-blue-500/5'
                    }`}>
                      {topic.priority} Priority
                    </span>
                  </div>
                  
                  <p className="text-foreground/80 leading-relaxed mb-6 text-sm md:text-base">{topic.description}</p>
                  
                  <div className="mt-auto">
                    <div className="flex items-center gap-4 mb-2">
                      <div className="text-xs uppercase tracking-widest font-medium text-muted-foreground">Mastery</div>
                      <div className="text-sm font-semibold ml-auto">{Math.round((topic.mastery_score || 0) * 100)}%</div>
                    </div>
                    <div className="h-1.5 w-full bg-muted overflow-hidden">
                      <div 
                        className={`h-full transition-all duration-1000 ${isActive ? 'bg-primary' : 'bg-primary/40'}`} 
                        style={{ width: `${Math.max(5, (topic.mastery_score || 0) * 100)}%` }}
                      />
                    </div>
                  </div>
                  
                  {isActive && (
                    <div className="mt-8 flex flex-wrap gap-4 pt-6 border-t border-border/40">
                      <button 
                        onClick={() => setActiveTab?.('tutor')}
                        className="flex-1 bg-primary text-primary-foreground px-6 py-2.5 text-sm font-medium hover:bg-primary/90 transition-colors flex items-center justify-center gap-2 min-w-35"
                      >
                        <BookOpen className="w-4 h-4" />
                        Study Material
                      </button>
                      <button 
                        onClick={() => setActiveTab?.('assessment')}
                        className="flex-1 bg-background text-foreground border border-border px-6 py-2.5 text-sm font-medium hover:bg-muted transition-colors flex items-center justify-center gap-2 min-w-35"
                      >
                        <Target className="w-4 h-4" />
                        Verify Knowledge
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Right Column - Stats & Plan */}
        <div className="lg:col-span-4 space-y-6">
          
          {/* Status Panel */}
          <div className="bg-card border border-border/40 p-6 shadow-sm">
            <h3 className="text-sm font-semibold uppercase tracking-widest text-muted-foreground mb-6 flex items-center gap-2">
              <TrendingUp className="w-4 h-4" /> System Status
            </h3>
            
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 border border-border/30 bg-muted/20">
                <div className="flex items-center gap-3">
                  <CheckCircle2 className="w-4 h-4 text-green-600 dark:text-green-400" />
                  <span className="text-sm font-medium">Mastered</span>
                </div>
                <span className="text-base font-semibold">{path.summary.mastered_count}</span>
              </div>
              
              <div className="flex items-center justify-between p-3 border border-border/30 bg-muted/20">
                <div className="flex items-center gap-3">
                  <Compass className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                  <span className="text-sm font-medium">Developing</span>
                </div>
                <span className="text-base font-semibold">{path.summary.developing_count}</span>
              </div>
              
              <div className="flex items-center justify-between p-3 border border-border/30 bg-muted/20">
                <div className="flex items-center gap-3">
                  <AlertCircle className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                  <span className="text-sm font-medium">Needs Work</span>
                </div>
                <span className="text-base font-semibold">{path.summary.weak_count}</span>
              </div>
              
              <div className="flex items-center justify-between p-3 border border-border/30 bg-muted/20 text-muted-foreground">
                <div className="flex items-center gap-3">
                  <CircleDashed className="w-4 h-4" />
                  <span className="text-sm font-medium">Not Started</span>
                </div>
                <span className="text-base font-semibold">{path.summary.unseen_count}</span>
              </div>
            </div>
          </div>

          {/* Schedule Panel */}
          <div className="bg-card border border-border/40 p-6 shadow-sm">
            <h3 className="text-sm font-semibold uppercase tracking-widest text-muted-foreground mb-6 flex items-center gap-2">
              <Clock className="w-4 h-4" /> Execution Plan
            </h3>
            
            <div className="space-y-4">
              {path.items.map((item, idx) => (
                <div key={item.order} className="flex gap-4">
                  <div className={`w-10 h-10 border flex items-center justify-center shrink-0 ${
                    idx === 0 ? 'bg-primary/5 border-primary/30 text-primary' : 'bg-muted/30 border-border/40 text-muted-foreground'
                  }`}>
                    <span className="text-xs font-semibold">{item.duration_minutes}m</span>
                  </div>
                  <div className="flex flex-col justify-center">
                    <span className="text-sm font-medium leading-tight mb-1 line-clamp-1">{item.title}</span>
                    <span className="text-xs text-muted-foreground uppercase tracking-wider">{item.priority} priority</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
          
        </div>
      </div>
    </div>
  );
}
