import { useState, useEffect } from 'react';
import { LearningPath, analyticsApi, AnalyticsDashboard } from '@/lib/api';
import { motion } from 'framer-motion';

export function DashboardView({ path }: { path: LearningPath | null }) {
  const [analytics, setAnalytics] = useState<AnalyticsDashboard | null>(null);

  useEffect(() => {
    const t = setTimeout(() => {
      analyticsApi.dashboard().then(setAnalytics).catch(console.error);
    }, 0);
    return () => clearTimeout(t);
  }, []);

  return (
    <div className="space-y-12 md:space-y-16 animate-in fade-in duration-700 max-w-5xl mx-auto">
      <header className="space-y-6 pt-4">
        <motion.div 
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
          className="font-mono text-[10px] tracking-widest text-text-muted uppercase"
        >
          Overview
        </motion.div>
        
        <motion.h1 
          initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
          className="text-4xl md:text-5xl font-heading font-medium tracking-tight text-text-primary"
        >
          {new Date().getHours() < 12 ? 'Good morning' : new Date().getHours() < 18 ? 'Good afternoon' : 'Good evening'}, Learner.
        </motion.h1>
        
        <motion.p 
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
          className="text-lg md:text-xl text-text-secondary font-light max-w-2xl leading-relaxed"
        >
          Review your recent performance metrics and continue navigating your selected learning modules.
        </motion.p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 md:gap-12">
        
        {/* Core Stats */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}
          className="lg:col-span-1 space-y-8"
        >
          <div>
            <div className="text-[10px] text-text-muted font-mono uppercase tracking-widest mb-2">Overall Mastery</div>
            <div className="text-5xl font-heading font-medium tracking-tighter text-accent">
              {analytics?.overall_mastery_pct != null ? `${analytics.overall_mastery_pct}%` : '—'}
            </div>
          </div>
          
          <div className="w-full h-px bg-border" />

          <div>
            <div className="text-[10px] text-text-muted font-mono uppercase tracking-widest mb-2">Questions Answered</div>
            <div className="text-3xl font-heading font-light tracking-tight text-text-primary">
              {analytics?.total_questions_answered != null ? analytics.total_questions_answered : '—'}
            </div>
          </div>
          
          <div className="w-full h-px bg-border" />

          <div>
            <div className="text-[10px] text-text-muted font-mono uppercase tracking-widest mb-2">Study Time</div>
            <div className="text-3xl font-heading font-light tracking-tight text-brass">
              {analytics?.study_time_minutes != null ? `${Math.floor(analytics.study_time_minutes / 60)}h ${Math.round(analytics.study_time_minutes % 60)}m` : '—'}
            </div>
          </div>

          <div className="w-full h-px bg-border" />
          
          <div>
            <div className="text-[10px] text-text-muted font-mono uppercase tracking-widest mb-2">Concepts Mastered</div>
            <div className="text-3xl font-heading font-light tracking-tight text-sage">
              {analytics?.mastered_concepts != null ? analytics.mastered_concepts : '—'}
            </div>
          </div>
        </motion.div>

        {/* Current Path Highlights */}
        <motion.div 
          initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.5, duration: 0.6 }}
          className="lg:col-span-2 relative"
        >
          <div className="mb-6 flex items-center justify-between border-b border-border pb-4">
             <span className="text-[10px] font-mono text-text-muted tracking-widest uppercase">Active Curriculum</span>
          </div>

          <div className="space-y-4">
            {path && path.items.length > 0 ? (
              path.items.slice(0, 5).map((item, i) => {
                const mastery = item.mastery_score || 0;
                const statusLabel = mastery > 0.8 ? 'Mastered' : mastery > 0.4 ? 'In Progress' : 'Needs Review';
                const statusColor = mastery > 0.8 ? 'text-sage' : mastery > 0.4 ? 'text-accent' : 'text-terracotta';
                
                return (
                  <motion.div
                    key={item.order}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.6 + i * 0.05 }}
                    className="flex flex-col sm:flex-row sm:items-center justify-between p-4 rounded-xl border border-border bg-surface-2 hover:bg-surface-3 transition-colors gap-4"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-1">
                        <span className="text-xs font-mono text-text-muted">{String(i+1).padStart(2, '0')}</span>
                        <h3 className="font-heading font-medium text-text-primary">{item.title}</h3>
                      </div>
                      <p className="text-sm text-text-secondary line-clamp-1 ml-7">{item.description}</p>
                    </div>
                    
                    <div className="flex items-center gap-6 sm:pl-4 sm:border-l border-border ml-7 sm:ml-0">
                      <div className="flex flex-col items-end">
                         <span className={`text-[10px] uppercase font-mono mb-1 ${statusColor}`}>{statusLabel}</span>
                         <span className="font-mono font-medium text-text-primary">{Math.round(mastery * 100)}%</span>
                      </div>
                    </div>
                  </motion.div>
                )
              })
            ) : (
               <div className="text-center py-20 px-6 border border-border border-dashed rounded-xl bg-surface-2/50 text-text-muted">
                 <p className="text-base font-medium text-text-primary mb-1">No active curriculum.</p>
                 <p className="text-sm">Upload study materials in the Library to generate a learning path.</p>
               </div>
            )}
          </div>
        </motion.div>

      </div>
    </div>
  )
}
