'use client';

import { useState, useEffect, useCallback } from 'react';
import { analyticsApi, AnalyticsDashboard, ConceptMastery } from '@/lib/api';
import { BarChart3, Target, TrendingUp, BookOpen, Clock, Flame, RefreshCw, Loader2, AlertTriangle, CheckCircle2, AlertCircle, Sparkles } from 'lucide-react';

export function AnalyticsView() {
  const [data, setData] = useState<AnalyticsDashboard | null>(null);
  const [insights, setInsights] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [dashboard, insightsResult] = await Promise.all([
        analyticsApi.dashboard(),
        analyticsApi.insights(),
      ]);
      setData(dashboard);
      setInsights(insightsResult.insights);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load analytics');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const t = setTimeout(() => { load(); }, 0);
    return () => clearTimeout(t);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
        <p className="text-muted-foreground text-sm uppercase tracking-widest font-medium">Loading Analytics</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 max-w-sm mx-auto text-center">
        <AlertTriangle className="w-10 h-10 text-amber-500" />
        <div>
          <h3 className="text-lg font-semibold mb-2">Failed to Load Analytics</h3>
          <p className="text-muted-foreground text-sm">{error}</p>
        </div>
        <button onClick={load} className="border border-border/40 hover:bg-muted px-6 py-2.5 text-sm font-medium transition-colors flex items-center gap-2 mt-2">
          <RefreshCw className="w-4 h-4" />Retry
        </button>
      </div>
    );
  }

  if (!data) return null;

  const statCards = [
    {
      label: 'Overall Mastery',
      value: `${data.overall_mastery_pct}%`,
      sub: `${data.mastered_concepts} concepts mastered`,
      icon: <Target className="w-4 h-4" />,
      color: 'text-accent',
      bar: data.overall_mastery,
      barColor: 'bg-accent',
    },
    {
      label: 'Accuracy',
      value: `${data.accuracy_pct}%`,
      sub: `${data.correct_count}/${data.total_questions_answered} correct`,
      icon: <TrendingUp className="w-4 h-4" />,
      color: 'text-sage',
      bar: data.accuracy,
      barColor: 'bg-sage',
    },
    {
      label: 'Questions Answered',
      value: data.total_questions_answered.toString(),
      sub: `Across ${data.total_concepts_attempted} concepts`,
      icon: <BookOpen className="w-4 h-4" />,
      color: 'text-text-primary',
      bar: null,
      barColor: '',
    },
    {
      label: 'Study Streak',
      value: `${data.streak_days} Days`,
      sub: data.streak_days > 0 ? 'Consistent progress' : 'Start studying today',
      icon: <Flame className="w-4 h-4" />,
      color: 'text-terracotta',
      bar: null,
      barColor: '',
    },
    {
      label: 'Study Time',
      value: `${Math.round(data.study_time_minutes)}m`,
      sub: 'Tracked session time',
      icon: <Clock className="w-4 h-4" />,
      color: 'text-brass',
      bar: null,
      barColor: '',
    },
  ];

  // Sort concept masteries: strong at top, weak at bottom
  const sorted = [...data.concept_masteries].sort((a, b) => b.score - a.score);
  const strong = sorted.filter(c => c.score >= 0.8);
  const developing = sorted.filter(c => c.score >= 0.55 && c.score < 0.8);
  const weak = sorted.filter(c => c.score < 0.55);

  return (
    <div className="flex flex-col h-full w-full max-w-7xl mx-auto py-8 px-2 md:px-0 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      <header className="flex flex-col md:flex-row justify-between md:items-end gap-6 mb-10">
        <div>
          <h1 className="text-3xl md:text-4xl font-semibold mb-3 tracking-tight">
            Performance Analytics
          </h1>
          <p className="text-muted-foreground text-sm uppercase tracking-widest font-medium">
            Real-time telemetry and actionable insights.
          </p>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-2 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors border border-border/40 px-3 py-1.5 bg-card hover:bg-muted"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh Data
        </button>
      </header>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
        {statCards.map((card) => (
          <div key={card.label} className="bg-card p-5 border border-border/40 flex flex-col shadow-sm">
            <div className={`flex items-center gap-2 mb-4 text-xs font-medium uppercase tracking-widest ${card.color}`}>
              {card.icon}
              <span>{card.label}</span>
            </div>
            <div className={`text-3xl font-semibold mb-1 ${card.color}`}>{card.value}</div>
            <div className="text-xs text-muted-foreground font-medium">{card.sub}</div>
            {card.bar !== null && (
              <div className="mt-3 h-1 w-full bg-muted overflow-hidden">
                <div
                  className={`h-full ${card.barColor} transition-all duration-1000`}
                  style={{ width: `${card.bar * 100}%` }}
                />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* AI Insights */}
      {insights.length > 0 && (
        <div className="bg-card border border-border/40 p-6 md:p-8 mb-8 shadow-sm">
          <h3 className="text-sm font-semibold uppercase tracking-widest text-muted-foreground mb-6 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-accent" />
            Synthesized Insights
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {insights.map((insight, i) => (
              <div key={i} className="p-4 border border-border/30 bg-muted/20 text-sm leading-relaxed text-foreground/80 font-medium">
                {insight}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Concept Mastery Breakdown */}
      {data.concept_masteries.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* Breakdown Table */}
          <div className="lg:col-span-7 bg-card border border-border/40 p-6 md:p-8 shadow-sm flex flex-col">
            <h3 className="text-sm font-semibold uppercase tracking-widest text-muted-foreground mb-6">
              Concept Telemetry
            </h3>
            
            <div className="space-y-6 flex-1 pr-2 overflow-y-auto max-h-125">
              {sorted.map((concept: ConceptMastery) => (
                <div key={concept.concept_id} className="pb-4 border-b border-border/20 last:border-0 last:pb-0">
                  <div className="flex justify-between items-baseline mb-2">
                    <span className="font-medium text-sm md:text-base leading-tight pr-4">{concept.concept_name}</span>
                    <span className="font-semibold text-sm shrink-0">{concept.percentage}%</span>
                  </div>
                  <div className="h-1.5 w-full bg-muted overflow-hidden mb-2">
                    <div
                      className={`h-full transition-all duration-1000 ${
                        concept.score >= 0.8 ? 'bg-sage' :
                        concept.score >= 0.55 ? 'bg-accent' : 'bg-terracotta'
                      }`}
                      style={{ width: `${concept.percentage}%` }}
                    />
                  </div>
                  <div className="text-xs font-medium text-muted-foreground flex justify-between">
                    <span>{concept.questions_seen} questions · {concept.correct_answers} correct</span>
                    <span className="uppercase tracking-wider">{concept.label}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Categorized Lists */}
          <div className="lg:col-span-5 space-y-4">
            
            {/* Mastered */}
            <div className="bg-card p-6 border border-sage/30 shadow-sm">
              <h3 className="text-sm font-semibold uppercase tracking-widest text-sage mb-4 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" /> Mastered ({strong.length})
              </h3>
              <div className="flex flex-wrap gap-2">
                {strong.length > 0
                  ? strong.map(c => (
                    <span key={c.concept_id} className="text-xs font-medium bg-sage-soft text-sage px-2 py-1 border border-sage/20">
                      {c.concept_name} ({c.percentage}%)
                    </span>
                  ))
                  : <span className="text-xs font-medium text-muted-foreground">Complete more assessments to master concepts.</span>
                }
              </div>
            </div>

            {/* Developing */}
            <div className="bg-card p-6 border border-accent/30 shadow-sm">
              <h3 className="text-sm font-semibold uppercase tracking-widest text-accent mb-4 flex items-center gap-2">
                <TrendingUp className="w-4 h-4" /> Developing ({developing.length})
              </h3>
              <div className="flex flex-wrap gap-2">
                {developing.length > 0
                  ? developing.map(c => (
                    <span key={c.concept_id} className="text-xs font-medium bg-accent-soft text-accent px-2 py-1 border border-accent/20">
                      {c.concept_name} ({c.percentage}%)
                    </span>
                  ))
                  : <span className="text-xs font-medium text-muted-foreground">No concepts in developing phase.</span>
                }
              </div>
            </div>

            {/* Weak */}
            <div className="bg-card p-6 border border-terracotta/30 shadow-sm">
              <h3 className="text-sm font-semibold uppercase tracking-widest text-terracotta mb-4 flex items-center gap-2">
                <AlertCircle className="w-4 h-4" /> Priority Focus ({weak.length})
              </h3>
              <div className="flex flex-wrap gap-2">
                {weak.length > 0
                  ? weak.map(c => (
                    <span key={c.concept_id} className="text-xs font-medium bg-terracotta-soft text-terracotta px-2 py-1 border border-terracotta/20">
                      {c.concept_name} ({c.percentage}%)
                    </span>
                  ))
                  : <span className="text-xs font-medium text-muted-foreground">No critical weaknesses identified.</span>
                }
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-card border border-border/40 p-12 text-center shadow-sm">
          <div className="w-16 h-16 bg-muted/30 flex items-center justify-center border border-border/40 mx-auto mb-6">
            <BarChart3 className="w-8 h-8 text-muted-foreground" />
          </div>
          <h3 className="text-xl font-semibold mb-2">Insufficient Telemetry Data</h3>
          <p className="text-muted-foreground max-w-md mx-auto text-sm">
            Complete assessments and interact with the AI Tutor to generate concept mastery analytics.
          </p>
        </div>
      )}
    </div>
  );
}
