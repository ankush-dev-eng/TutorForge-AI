'use client';

import { useState, useEffect, useCallback } from 'react';
import { learningPathApi, LearningPath, sourcesApi, Source } from '@/lib/api';
import AiTutor from '@/components/AiTutor';
import AssessmentView from '@/components/AssessmentView';
import { AppLayout } from '@/components/AppLayout';
import { DashboardView } from '@/components/DashboardView';
import { LibraryView } from '@/components/LibraryView';
import { LearningPathView } from '@/components/LearningPathView';
import { ConceptMapView } from '@/components/ConceptMapView';
import { AnalyticsView } from '@/components/AnalyticsView';
import { SettingsView } from '@/components/SettingsView';

export default function Dashboard() {
  const [path, setPath] = useState<LearningPath | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');

  const refreshSources = useCallback(async () => {
    try {
      const sourcesData = await sourcesApi.list();
      setSources(sourcesData);
    } catch (e) {
      console.error('Failed to refresh sources:', e);
    }
  }, []);

  const refreshPath = useCallback(async () => {
    try {
      const pathData = await learningPathApi.get();
      setPath(pathData);
    } catch (e) {
      console.error('Failed to refresh learning path:', e);
    }
  }, []);

  useEffect(() => {
    Promise.allSettled([
      learningPathApi.get(),
      sourcesApi.list()
    ]).then(([pathResult, sourcesResult]) => {
      if (pathResult.status === 'fulfilled') {
        setPath(pathResult.value);
      } else {
        console.error('Failed to load learning path:', pathResult.reason);
      }

      if (sourcesResult.status === 'fulfilled') {
        setSources(sourcesResult.value);
      } else {
        console.error('Failed to load sources:', sourcesResult.reason);
      }

      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-background">
        <div className="w-16 h-16 border-4 border-primary/20 border-t-primary rounded-full animate-spin mb-6 shadow-[0_0_15px_rgba(0,200,255,0.5)]"></div>
        <h2 className="text-2xl font-semibold bg-linear-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent animate-pulse">Initializing TutorForge AI</h2>
      </div>
    );
  }

  return (
    <AppLayout activeTab={activeTab} setActiveTab={setActiveTab}>
      {activeTab === 'overview' && <DashboardView path={path} />}
      {activeTab === 'sources' && (
        <LibraryView
          sources={sources}
          onSourcesChange={() => {
            refreshSources();
            refreshPath();
          }}
        />
      )}
      {activeTab === 'tutor' && (
        <div className="h-[calc(100vh-8rem)] min-h-150 animate-in fade-in slide-in-from-bottom-4 duration-500">
          <AiTutor />
        </div>
      )}
      {activeTab === 'assessment' && (
        <div className="h-[calc(100vh-8rem)] min-h-150 animate-in fade-in slide-in-from-bottom-4 duration-500">
          <AssessmentView />
        </div>
      )}
      {activeTab === 'path' && <LearningPathView path={path} setActiveTab={setActiveTab} />}
      {activeTab === 'concept-map' && <ConceptMapView />}
      {activeTab === 'analytics' && <AnalyticsView />}
      {activeTab === 'settings' && <SettingsView />}
    </AppLayout>
  );
}
