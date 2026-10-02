'use client';

import { useState, useRef, useEffect } from 'react';
import { chatApi, ChatMessage, Citation, ChatSession } from '@/lib/api';
import { Send, Trash2, BookOpen, FileText, Sparkles, ClipboardList, HelpCircle, ChevronDown, ExternalLink, AlertTriangle, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

type TutorMode = 'default' | 'explain_simple' | 'exam_answer' | 'give_example' | 'summarize' | 'quiz_me';

const MODES: { id: TutorMode; label: string; prompt: string; icon: React.ReactNode }[] = [
  { id: 'explain_simple', label: 'Explain Simply', icon: <Sparkles className="w-4.5 h-4.5" />, prompt: 'Explain this in simple terms a beginner would understand: ' },
  { id: 'exam_answer', label: 'Exam Answer', icon: <ClipboardList className="w-4.5 h-4.5" />, prompt: 'Write a model exam answer for: ' },
  { id: 'give_example', label: 'Give Example', icon: <BookOpen className="w-4.5 h-4.5" />, prompt: 'Give a concrete real-world example for: ' },
  { id: 'summarize', label: 'Summarize', icon: <FileText className="w-4.5 h-4.5" />, prompt: 'Summarize the key points about: ' },
  { id: 'quiz_me', label: 'Quiz Me', icon: <HelpCircle className="w-4.5 h-4.5" />, prompt: 'Quiz me with 3 questions about: ' },
];

function CitationCard({ cit }: { cit: Citation }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div
      className="bg-surface p-3 rounded text-xs border border-border hover:border-accent hover:shadow-sm transition-all cursor-pointer"
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <FileText className="w-3.5 h-3.5 text-accent shrink-0" />
          <span className="font-medium text-text-primary truncate">{cit.source_name}</span>
          {cit.location && (
            <span className="text-text-muted shrink-0 font-mono text-[10px] uppercase">• {cit.location}</span>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0 bg-surface-2 px-2 py-0.5 rounded">
          <span className="text-text-secondary font-mono text-[10px]">{Math.round(cit.relevance * 100)}%</span>
          <ChevronDown className={`w-3 h-3 text-text-muted transition-transform ${expanded ? 'rotate-180' : ''}`} />
        </div>
      </div>
      <AnimatePresence>
        {expanded && cit.excerpt && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <p className="text-text-secondary mt-3 text-[13px] leading-relaxed border-t border-border pt-3">
              &quot;{cit.excerpt}&quot;
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function AiTutor() {
  const [session, setSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<TutorMode>('default');
  const [initError, setInitError] = useState<string | null>(null);
  const [resetting, setResetting] = useState(false);
  const [initialized, setInitialized] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const retryingRef = useRef(false);
  const requestCounterRef = useRef(0);

  const msgCounterRef = useRef(0);

  useEffect(() => {
    let mounted = true;
    
    const init = async () => {
      try {
        setInitError(null);
        const sessions = await chatApi.listSessions();
        if (!mounted) return;

        if (sessions.length > 0) {
          const latest = sessions[0];
          setSession(latest);
          const msgs = await chatApi.getMessages(latest.id);
          if (mounted) setMessages(msgs);
        } else {
          const newSession = await chatApi.createSession('Main Session');
          if (mounted) {
            setSession(newSession);
            setMessages([]);
          }
        }
        if (mounted) {
          setInitialized(true);
        }
      } catch (e) {
        if (mounted) {
          console.error('Failed to initialize chat session:', e);
          setInitError('Cannot connect to backend. Ensure the server is running on port 8000.');
        }
      }
    };

    init();
    
    return () => { mounted = false; };
  }, []);

  const retryConnection = async () => {
    if (retryingRef.current) return;
    retryingRef.current = true;
    try {
      setInitialized(false);
      setInitError(null);
      const sessions = await chatApi.listSessions();
      if (sessions.length > 0) {
        const latest = sessions[0];
        setSession(latest);
        const msgs = await chatApi.getMessages(latest.id);
        setMessages(msgs);
      } else {
        const newSession = await chatApi.createSession('Main Session');
        setSession(newSession);
        setMessages([]);
      }
      setInitialized(true);
    } catch (e) {
      console.error('Failed to initialize chat session:', e);
      setInitError('Cannot connect to backend. Ensure the server is running on port 8000.');
    } finally {
      retryingRef.current = false;
    }
  };


  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent, overrideInput?: string, overrideMode?: TutorMode) => {
    e.preventDefault();
    const rawInput = overrideInput ?? input.trim();
    if (!rawInput || loading || resetting || !initialized) return;

    // Apply mode prefix
    const currentModeId = overrideMode ?? mode;
    const modeConfig = MODES.find(m => m.id === currentModeId);
    const finalContent = modeConfig ? modeConfig.prompt + rawInput : rawInput;

    setInput('');
    setLoading(true);
    requestCounterRef.current += 1;
    const currentReqId = requestCounterRef.current;

    msgCounterRef.current -= 1;
    const userMsgId = msgCounterRef.current;
    msgCounterRef.current -= 1;
    const asstMsgId = msgCounterRef.current;

    setMessages(prev => [
      ...prev,
      {
        id: userMsgId,
        role: 'user',
        content: rawInput + (modeConfig ? ` [${modeConfig.label}]` : ''),
        citations: [],
        created_at: new Date().toISOString()
      },
      {
        id: asstMsgId,
        role: 'assistant',
        content: '',
        citations: [],
        created_at: new Date().toISOString()
      }
    ]);

    try {
      let currentSession = session;
      if (!currentSession) {
        currentSession = await chatApi.createSession(rawInput.slice(0, 60));
        setSession(currentSession);
      }

      const result = await chatApi.sendMessage(finalContent, currentSession.id);

      setMessages(prev => {
        const exists = prev.find(m => m.id === asstMsgId);
        if (!exists) return prev; // session was cleared!
        return prev.map(m =>
          m.id === asstMsgId
            ? { ...m, id: result.message_id, content: result.response, citations: result.citations }
            : m
        );
      });
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : 'An error occurred';
      setMessages(prev => {
        const exists = prev.find(m => m.id === asstMsgId);
        if (!exists) return prev; // session was cleared!
        return prev.map(m =>
          m.id === asstMsgId
            ? { ...m, content: errMsg, citations: [], isError: true }
            : m
        );
      });
    } finally {
      if (requestCounterRef.current === currentReqId) {
        setLoading(false);
      }
    }
  };

  const handleClearSession = async () => {
    if (!session || resetting || !initialized) return;
    if (!confirm('Clear this conversation? This cannot be undone.')) return;
    
    // Immediate UI clear
    setMessages([]);
    setInput('');
    setLoading(false);
    setMode('default');
    requestCounterRef.current += 1; // invalidate pending requests
    setTimeout(() => inputRef.current?.focus(), 0);

    try {
      setResetting(true);
      await chatApi.deleteSession(session.id);
      const newSession = await chatApi.createSession('New Chat');
      setSession(newSession);
    } catch (e) {
      console.error(e);
    } finally {
      setResetting(false);
    }
  };

  const handleModeQuickSend = (modeId: TutorMode) => {
    if (!input.trim()) {
      setMode(modeId);
      return;
    }
    const modeConfig = MODES.find(m => m.id === modeId);
    if (modeConfig) {
      const syntheticEvent = { preventDefault: () => {} } as React.FormEvent;
      setMode(modeId);
      handleSubmit(syntheticEvent, input.trim(), modeId).catch(console.error);
    }
  };

  if (initError) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <AlertTriangle className="w-12 h-12 text-warning" />
        <div className="text-center">
          <h3 className="text-lg font-heading font-medium mb-2 text-text-primary">Backend Unavailable</h3>
          <p className="text-text-secondary text-sm max-w-md">{initError}</p>
        </div>
        <button
          onClick={retryConnection}
          className="bg-accent text-surface px-6 py-3 rounded font-mono text-[10px] uppercase tracking-widest mt-4"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 h-full w-full animate-in fade-in duration-500 max-w-[1600px] mx-auto pb-4">
      {/* Left Column: Mode Selection + Context */}
      <div className="hidden lg:flex lg:col-span-3 flex-col gap-6">
        <div className="bg-surface-2 rounded border border-border p-6 flex flex-col h-full">
          <h3 className="font-heading font-medium mb-6 text-text-primary flex items-center gap-2 text-lg">
            <Sparkles className="w-4 h-4 text-accent" />
            Tutor Mode
          </h3>
          <div className="space-y-2 mb-6">
            <button
              onClick={() => setMode('default')}
              className={`w-full text-left px-4 py-3 rounded text-sm transition-colors flex items-center gap-3 font-medium ${
                mode === 'default'
                  ? 'bg-surface-3 text-text-primary border border-border-strong'
                  : 'hover:bg-surface-3/50 text-text-secondary border border-transparent hover:text-text-primary'
              }`}
            >
              <div className="w-4.5 h-4.5 shrink-0" />
              Default
            </button>
            {MODES.map(m => (
              <button
                key={m.id}
                onClick={() => setMode(m.id)}
                className={`w-full text-left px-4 py-3 rounded text-sm transition-colors flex items-center gap-3 font-medium ${
                  mode === m.id
                    ? 'bg-surface-3 text-text-primary border border-border-strong'
                    : 'hover:bg-surface-3/50 text-text-secondary border border-transparent hover:text-text-primary'
                }`}
              >
                <span className={mode === m.id ? "text-accent" : "text-text-muted"}>{m.icon}</span>
                {m.label}
              </button>
            ))}
          </div>

          {mode !== 'default' && (
            <div className="mt-auto p-4 bg-surface-3 border border-border rounded text-xs text-text-secondary leading-relaxed">
              <strong className="text-text-primary font-medium">{MODES.find(m => m.id === mode)?.label}:</strong> Your question will be prefixed with the mode prompt.
            </div>
          )}
        </div>
      </div>

      {/* Center Column: Chat Interface */}
      <div className="col-span-1 lg:col-span-6 flex flex-col bg-surface border border-border rounded overflow-hidden relative">
        <div className="px-6 py-4 border-b border-border flex justify-between items-center bg-surface-2">
          <h3 className="font-heading font-medium flex items-center gap-3 text-text-primary">
            <span className="h-2 w-2 rounded-full bg-accent"></span>
            TutorForge Assistant
          </h3>
          <button
            onClick={handleClearSession}
            disabled={!initialized || resetting}
            className="text-[10px] font-mono tracking-widest uppercase text-text-muted hover:text-danger transition-colors flex items-center gap-1.5 px-3 py-1.5 border border-transparent hover:border-danger/30 rounded hover:bg-danger/5 disabled:opacity-50 disabled:pointer-events-none"
          >
            <Trash2 className="w-3 h-3" />
            Clear
          </button>
        </div>

        {/* Quick mode buttons - mobile visible */}
        <div className="flex lg:hidden gap-2 px-4 py-3 border-b border-border bg-surface-2 overflow-x-auto">
          {MODES.map(m => (
            <button
              key={m.id}
              onClick={() => handleModeQuickSend(m.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs whitespace-nowrap transition-colors font-medium border ${
                mode === m.id ? 'bg-surface-3 text-text-primary border-border-strong' : 'bg-surface border-border text-text-secondary hover:bg-surface-3/50'
              }`}
            >
              <span className={mode === m.id ? "text-accent" : "text-text-muted"}>{m.icon}</span>
              {m.label}
            </button>
          ))}
        </div>

        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto p-6 space-y-8 custom-scrollbar"
        >
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-text-secondary space-y-6">
              <div className="w-16 h-16 rounded border border-border bg-surface-2 flex items-center justify-center mb-2">
                <BookOpen className="w-8 h-8 text-text-muted" />
              </div>
              <p className="text-xl font-heading font-medium text-text-primary">How can I help you learn today?</p>
              <p className="text-sm max-w-md text-center leading-relaxed">
                Ask questions about your uploaded materials. Use the mode buttons to change how I respond.
              </p>
              <div className="flex flex-wrap gap-3 justify-center mt-6">
                {['Summarize the key topics', 'What are the main concepts?', 'Give me a quiz question'].map(q => (
                  <button
                    key={q}
                    onClick={(e) => handleSubmit(e as unknown as React.FormEvent, q)}
                    className="text-xs bg-surface hover:bg-surface-3 border border-border px-4 py-2 rounded transition-colors text-text-primary"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg, i) => (
              <div key={msg.id || i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] px-6 py-4 rounded ${
                  msg.role === 'user'
                    ? 'bg-accent text-surface shadow-sm'
                    : msg.isError
                      ? 'bg-danger/10 border border-danger/30 text-text-primary shadow-sm'
                      : 'bg-surface text-text-primary border border-border shadow-sm'
                }`}>
                  {msg.role === 'assistant' && msg.content === '' && loading ? (
                    <div className="flex items-center gap-3 text-text-muted font-mono text-xs uppercase tracking-widest">
                      <div className="flex gap-1">
                        <span className="w-1.5 h-1.5 bg-accent rounded-full animate-pulse" style={{ animationDelay: '0ms' }} />
                        <span className="w-1.5 h-1.5 bg-accent rounded-full animate-pulse" style={{ animationDelay: '150ms' }} />
                        <span className="w-1.5 h-1.5 bg-accent rounded-full animate-pulse" style={{ animationDelay: '300ms' }} />
                      </div>
                      Trying an available AI model…
                    </div>
                  ) : msg.isError ? (
                    <div className="flex flex-col gap-3">
                      <div className="flex items-center gap-2 text-danger font-medium text-sm">
                        <AlertTriangle className="w-4 h-4" />
                        Status: Error
                      </div>
                      <div className="whitespace-pre-wrap leading-relaxed text-[15px]">{msg.content}</div>
                      <button
                        onClick={() => {
                          const userMsg = messages[i - 1];
                          if (userMsg && userMsg.role === 'user') {
                            const syntheticEvent = { preventDefault: () => {} } as React.FormEvent;
                            // Clean up the error prefix/suffix from original input if needed, or just use the userMsg content.
                            // But mode was already prefixed. So we just pass it as is.
                            // Wait, handleSubmit expects raw input. Let's just remove the last two messages and resubmit
                            setMessages(prev => prev.slice(0, i - 1));
                            handleSubmit(syntheticEvent, userMsg.content.replace(/ \[.*?\]$/, ''));
                          }
                        }}
                        className="self-start mt-2 bg-surface text-text-primary border border-border hover:bg-surface-2 px-4 py-2 rounded text-xs font-medium transition-colors"
                      >
                        Retry
                      </button>
                    </div>
                  ) : (
                    <div className="whitespace-pre-wrap leading-relaxed text-[15px]">{msg.content}</div>
                  )}

                  {msg.citations && msg.citations.length > 0 && (
                    <div className="mt-6 pt-4 border-t border-border">
                      <p className="text-[10px] font-mono uppercase tracking-widest text-text-muted mb-3 flex items-center gap-1.5">
                        <ExternalLink className="w-3 h-3" />
                        Sources Cited ({msg.citations.length})
                      </p>
                      <div className="flex flex-col gap-2">
                        {msg.citations.map((cit, idx) => (
                          <CitationCard key={idx} cit={cit} />
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>

        <div className="p-4 md:p-6 bg-surface-2 border-t border-border">
          {mode !== 'default' && (
            <div className="flex items-center gap-2 mb-3 text-xs text-text-primary">
              <span className="bg-surface border border-border px-3 py-1 rounded flex items-center gap-2 font-medium">
                <span className="text-accent">{MODES.find(m => m.id === mode)?.icon}</span>
                {MODES.find(m => m.id === mode)?.label}
              </span>
              <button onClick={() => setMode('default')} className="text-text-muted hover:text-text-primary bg-surface border border-border rounded w-6 h-6 flex items-center justify-center">
                <X className="w-3 h-3" />
              </button>
            </div>
          )}
          <form onSubmit={handleSubmit} className="flex gap-3 relative">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={mode !== 'default' ? `${MODES.find(m => m.id === mode)?.label}: type your topic…` : 'Ask a question about your materials…'}
              disabled={loading}
              className="flex-1 bg-surface px-5 py-4 rounded text-sm focus:outline-none focus:ring-1 focus:ring-accent transition-all border border-border text-text-primary placeholder:text-text-muted"
            />
            <button
              type="submit"
              disabled={loading || !input.trim() || !initialized}
              className="bg-accent text-surface h-14 w-14 rounded flex items-center justify-center hover:bg-accent-hover transition-colors disabled:opacity-50 disabled:pointer-events-none"
            >
              {loading ? (
                <span className="w-5 h-5 border-2 border-surface/30 border-t-surface rounded-full animate-spin" />
              ) : (
                <Send className="w-4.5 h-4.5" />
              )}
            </button>
          </form>
        </div>
      </div>

      {/* Right Column: Source Viewer / Citation Details */}
      <div className="hidden lg:flex lg:col-span-3 flex-col gap-6">
        <div className="bg-surface-2 rounded border border-border p-6 flex flex-col h-full">
          <h3 className="font-heading font-medium mb-6 text-text-primary flex items-center gap-2 text-lg">
            <FileText className="w-4 h-4 text-text-muted" />
            Reference Material
          </h3>

          {/* Show latest citations from last assistant message */}
          {(() => {
            const lastAsstMsg = [...messages].reverse().find(m => m.role === 'assistant' && m.citations.length > 0);
            if (!lastAsstMsg || !lastAsstMsg.citations.length) {
              return (
                <div className="flex-1 flex flex-col items-center justify-center text-text-muted border border-dashed border-border rounded p-6 text-center bg-surface/50">
                  <FileText className="w-6 h-6 mb-3 text-text-muted/50" />
                  <p className="text-sm leading-relaxed">Citations from the last AI response will appear here.</p>
                </div>
              );
            }
            return (
              <div className="flex-1 space-y-4 overflow-y-auto custom-scrollbar pr-2">
                <p className="text-[10px] font-mono text-text-muted uppercase tracking-widest">From last response:</p>
                {lastAsstMsg.citations.map((cit, i) => (
                  <div key={i} className="bg-surface border border-border rounded p-4">
                    <div className="flex items-center gap-3 mb-3">
                      <FileText className="w-4 h-4 text-accent shrink-0" />
                      <span className="text-sm font-medium text-text-primary leading-tight">{cit.source_name}</span>
                    </div>
                    {cit.location && (
                      <div className="text-[10px] font-mono text-text-secondary uppercase tracking-widest mb-3">📍 {cit.location}</div>
                    )}
                    {cit.excerpt && (
                      <p className="text-sm text-text-secondary leading-relaxed border-l-2 border-accent/50 pl-3 my-3 bg-surface-2/50 p-2 rounded-r">
                        &quot;{cit.excerpt}&quot;
                      </p>
                    )}
                    <div className="mt-3 text-[10px] font-mono text-text-muted uppercase tracking-widest pt-3 border-t border-border">
                      Relevance: {Math.round(cit.relevance * 100)}%
                    </div>
                  </div>
                ))}
              </div>
            );
          })()}
        </div>
      </div>
    </div>
  );
}
