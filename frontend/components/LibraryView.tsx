import { useState, useRef, useCallback, useEffect } from 'react';
import { Source, sourcesApi, UploadResponse } from '@/lib/api';
import { FileText, Video, Upload, FileType2, Plus, X, CheckCircle2, AlertCircle, Loader2, Eye, Trash2, Clock, BookMarked } from 'lucide-react';
import { motion } from 'framer-motion';

interface UploadState {
  file: File;
  progress: number;
  status: 'uploading' | 'processing' | 'done' | 'error';
  error?: string;
  sourceId?: number;
}

interface LibraryViewProps {
  sources: Source[];
  onSourcesChange: () => void;
}

export function LibraryView({ sources, onSourcesChange }: LibraryViewProps) {
  const [uploads, setUploads] = useState<UploadState[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState<number | null>(null);
  const selectedSource = sources.find(s => s.id === selectedSourceId) || null;
  const [deleting, setDeleting] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollingRefs = useRef<{ [sourceId: number]: NodeJS.Timeout }>({});
  const unmountedRef = useRef(false);

  const getIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'pdf': return <FileText className="w-5 h-5" />;
      case 'video': return <Video className="w-5 h-5" />;
      case 'pptx': return <FileType2 className="w-5 h-5" />;
      default: return <FileText className="w-5 h-5" />;
    }
  };

  const pollProcessingStatus = useCallback((sourceId: number) => {
    const poll = async () => {
      if (unmountedRef.current) return;
      try {
        const status = await sourcesApi.getStatus(sourceId);
        if (unmountedRef.current) return;
        if (status.status === 'processed' || status.status === 'completed') {
          setUploads(prev => prev.map(u =>
            u.sourceId === sourceId ? { ...u, status: 'done' } : u
          ));
          onSourcesChange();
          delete pollingRefs.current[sourceId];
        } else if (status.status === 'error') {
          setUploads(prev => prev.map(u =>
            u.sourceId === sourceId
              ? { ...u, status: 'error', error: status.error_message || 'Processing failed' }
              : u
          ));
          onSourcesChange();
          delete pollingRefs.current[sourceId];
        } else {
          pollingRefs.current[sourceId] = setTimeout(poll, 2000);
        }
      } catch {
        if (unmountedRef.current) return;
        setUploads(prev => prev.map(u =>
          u.sourceId === sourceId ? { ...u, status: 'error', error: 'Status check failed' } : u
        ));
        delete pollingRefs.current[sourceId];
      }
    };
    pollingRefs.current[sourceId] = setTimeout(poll, 2000);
  }, [onSourcesChange]);

  useEffect(() => {
    const currentPollingRefs = pollingRefs.current;
    return () => { 
      unmountedRef.current = true;
      Object.values(currentPollingRefs).forEach(clearTimeout); 
    };
  }, []);

  const handleFiles = useCallback(async (files: FileList) => {
    const allowedTypes = ['pdf', 'pptx', 'ppt', 'docx', 'doc', 'txt', 'md', 'mp4', 'mov', 'avi', 'mp3', 'wav', 'm4a'];

    for (const file of Array.from(files)) {
      const ext = file.name.split('.').pop()?.toLowerCase() || '';
      if (!allowedTypes.includes(ext)) {
        setUploads(prev => [...prev, {
          file, progress: 0, status: 'error',
          error: `File type .${ext} not supported`
        }]);
        continue;
      }

      const uploadState: UploadState = { file, progress: 0, status: 'uploading' };
      setUploads(prev => [...prev, uploadState]);

      try {
        const result: UploadResponse = await sourcesApi.upload(file, (pct) => {
          setUploads(prev => prev.map(u =>
            u.file === file ? { ...u, progress: pct } : u
          ));
        });

        setUploads(prev => prev.map(u =>
          u.file === file
            ? { ...u, progress: 100, status: 'processing', sourceId: result.id }
            : u
        ));

        pollProcessingStatus(result.id);
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Upload failed';
        setUploads(prev => prev.map(u =>
          u.file === file ? { ...u, status: 'error', error: msg } : u
        ));
      }
    }
  }, [pollProcessingStatus]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files.length > 0) handleFiles(e.dataTransfer.files);
  }, [handleFiles]);

  const handleDelete = async (source: Source) => {
    if (!confirm(`Delete "${source.name}"? This cannot be undone.`)) return;
    setDeleting(source.id);
    try {
      await sourcesApi.delete(source.id);
      onSourcesChange();
      if (selectedSourceId === source.id) setSelectedSourceId(null);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Delete failed');
    } finally {
      setDeleting(null);
    }
  };

  const statusBadge = (status: string) => {
    switch (status) {
      case 'processed':
      case 'completed':
        return <span className="flex items-center gap-1.5 text-success text-[10px] font-mono uppercase tracking-widest"><CheckCircle2 className="w-3 h-3" />Processed</span>;
      case 'processing':
        return <span className="flex items-center gap-1.5 text-warning text-[10px] font-mono uppercase tracking-widest"><Loader2 className="w-3 h-3 animate-spin" />Processing</span>;
      case 'pending':
        return <span className="flex items-center gap-1.5 text-accent text-[10px] font-mono uppercase tracking-widest"><Clock className="w-3 h-3" />Pending</span>;
      case 'error':
        return <span className="flex items-center gap-1.5 text-error text-[10px] font-mono uppercase tracking-widest"><AlertCircle className="w-3 h-3" />Error</span>;
      default:
        return <span className="text-[10px] font-mono uppercase tracking-widest text-text-muted">{status}</span>;
    }
  };

  return (
    <div className="space-y-12 animate-in fade-in duration-700 max-w-6xl mx-auto pb-24">
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-6 border-b border-border pb-6 pt-4">
        <div className="space-y-4">
          <motion.div 
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="font-mono text-[10px] tracking-widest text-text-muted uppercase"
          >
            Knowledge Vault
          </motion.div>
          <motion.h2 
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
            className="text-4xl md:text-5xl font-heading font-medium tracking-tight text-text-primary"
          >
            Library
          </motion.h2>
          <motion.p 
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
            className="text-lg text-text-secondary font-light max-w-xl"
          >
            Add source documents and reference materials to inform the curriculum.
          </motion.p>
        </div>
        
        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.4 }}>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="bg-accent hover:bg-accent-hover text-surface px-6 py-3 rounded transition-colors font-mono text-[10px] uppercase tracking-widest flex items-center gap-3"
          >
            <Upload className="w-4 h-4" />
            Upload File
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            accept=".pdf,.pptx,.ppt,.docx,.doc,.txt,.md,.mp4,.mov,.avi,.mp3,.wav,.m4a"
            onChange={(e) => { if (e.target.files) handleFiles(e.target.files); e.target.value = ''; }}
          />
        </motion.div>
      </header>

      {/* Active uploads */}
      {uploads.length > 0 && (
        <motion.div 
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          className="space-y-4 mb-12"
        >
          <h3 className="text-[10px] font-mono text-text-muted uppercase tracking-widest">Active Uploads</h3>
          <div className="grid gap-4">
            {uploads.map((u, i) => (
              <div key={i} className="bg-surface-2 border border-border p-4 flex items-center gap-4 rounded">
                <div className="p-2 bg-surface border border-border text-text-secondary rounded">
                   {getIcon(u.file.name.split('.').pop() || 'txt')}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-medium truncate text-text-primary font-mono">{u.file.name}</span>
                    {u.status === 'uploading' && <span className="text-[10px] font-mono text-accent">{u.progress}%</span>}
                    {u.status === 'processing' && <span className="text-[10px] text-warning font-mono flex items-center gap-2"><Loader2 className="w-3 h-3 animate-spin" />PROCESSING</span>}
                    {u.status === 'done' && <span className="text-[10px] text-success font-mono flex items-center gap-2"><CheckCircle2 className="w-3 h-3" />COMPLETE</span>}
                    {u.status === 'error' && <span className="text-[10px] text-error font-mono flex items-center gap-2"><AlertCircle className="w-3 h-3" />{u.error}</span>}
                  </div>
                  {(u.status === 'uploading') && (
                    <div className="h-0.5 bg-border w-full overflow-hidden">
                      <div className="h-full bg-accent transition-all duration-300" style={{ width: `${u.progress}%` }} />
                    </div>
                  )}
                  {u.status === 'processing' && (
                    <div className="h-0.5 bg-border w-full overflow-hidden">
                      <div className="h-full bg-warning animate-pulse w-2/3" />
                    </div>
                  )}
                </div>
                <button onClick={() => setUploads(prev => prev.filter((_, idx) => idx !== i))} className="text-text-muted hover:text-text-primary p-2">
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Main Grid */}
      <motion.div 
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5, duration: 0.8 }}
        className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
      >
        {/* Upload Drop Zone */}
        <button
          onClick={() => fileInputRef.current?.click()}
          className="flex flex-col items-center justify-center p-8 border border-dashed border-border hover:border-border-strong bg-surface-2/50 hover:bg-surface-2 transition-colors group min-h-60 rounded"
        >
          <div className="w-12 h-12 bg-surface border border-border flex items-center justify-center text-text-muted group-hover:text-text-primary transition-colors mb-6 rounded">
            <Plus className="w-5 h-5" />
          </div>
          <span className="font-mono text-[10px] uppercase tracking-widest text-text-muted group-hover:text-text-primary">Drop Files Here</span>
          <span className="text-[10px] text-text-muted/70 mt-3 font-mono text-center leading-relaxed">PDF · PPTX · DOCX · TXT<br/>MP4 · MP3</span>
        </button>

        {sources.map(source => (
          <div
            key={source.id}
            className="bg-surface border border-border hover:border-border-strong transition-colors group flex flex-col cursor-pointer overflow-hidden relative rounded"
            onClick={() => setSelectedSourceId(selectedSourceId === source.id ? null : source.id)}
          >
            {selectedSourceId === source.id && (
              <div className="absolute inset-0 border-2 border-accent pointer-events-none rounded" />
            )}
            <div className="p-6 flex-1 flex flex-col">
              <div className="flex justify-between items-start mb-6">
                <div className="p-3 bg-surface-2 border border-border text-text-secondary rounded">
                  {getIcon(source.source_type)}
                </div>
                <span className="text-[10px] font-mono uppercase bg-surface-3 border border-border px-2 py-1 text-text-muted tracking-widest rounded">
                  {source.source_type}
                </span>
              </div>
              <h4 className="font-heading font-medium text-lg leading-tight line-clamp-3 text-text-primary mb-4 flex-1" title={source.name}>
                {source.name}
              </h4>
              <div className="font-mono text-[10px] text-text-muted tracking-widest uppercase">
                {source.chunk_count} nodes
              </div>
            </div>
            
            <div className="px-6 py-4 bg-surface-2 border-t border-border flex justify-between items-center">
              {statusBadge(source.status)}
              <div className="flex items-center gap-3">
                <button
                  onClick={(e) => { e.stopPropagation(); setSelectedSourceId(source.id); }}
                  className="text-text-muted hover:text-text-primary transition-colors"
                  title="View details"
                >
                  <Eye className="w-4.5 h-4.5" />
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDelete(source); }}
                  disabled={deleting === source.id}
                  className="text-text-muted hover:text-error transition-colors disabled:opacity-50"
                  title="Delete source"
                >
                  {deleting === source.id ? <Loader2 className="w-4.5 h-4.5 animate-spin" /> : <Trash2 className="w-4.5 h-4.5" />}
                </button>
              </div>
            </div>
          </div>
        ))}
      </motion.div>

      {/* Source Detail Panel */}
      {selectedSource && (
        <motion.div 
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          className="mt-12 bg-surface-2 border border-border p-8 relative overflow-hidden rounded"
        >
          <div className="absolute top-0 left-0 w-1 h-full bg-accent" />
          
          <div className="flex justify-between items-start mb-8 relative z-10 pl-2">
            <div className="flex items-start gap-6">
              <div className="p-4 bg-surface border border-border text-text-secondary rounded">
                {getIcon(selectedSource.source_type)}
              </div>
              <div>
                <h3 className="text-2xl font-heading font-medium text-text-primary mb-2">{selectedSource.name}</h3>
                <p className="text-sm font-mono text-text-secondary">{selectedSource.original_filename}</p>
              </div>
            </div>
            <button onClick={() => setSelectedSourceId(null)} className="text-text-muted hover:text-text-primary p-2 border border-transparent hover:border-border transition-colors bg-transparent hover:bg-surface rounded">
              <X className="w-5 h-5" />
            </button>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 relative z-10 pl-2">
            <div className="bg-surface border border-border p-4 rounded">
              <div className="font-mono text-[10px] tracking-widest text-text-muted uppercase mb-2">Type</div>
              <div className="font-mono text-sm text-text-primary uppercase">{selectedSource.source_type}</div>
            </div>
            <div className="bg-surface border border-border p-4 rounded">
              <div className="font-mono text-[10px] tracking-widest text-text-muted uppercase mb-2">Status</div>
              <div className="font-medium text-sm">{statusBadge(selectedSource.status)}</div>
            </div>
            <div className="bg-surface border border-border p-4 rounded">
              <div className="font-mono text-[10px] tracking-widest text-text-muted uppercase mb-2">Nodes</div>
              <div className="font-mono text-lg text-text-primary">{selectedSource.chunk_count}</div>
            </div>
            <div className="bg-surface border border-border p-4 rounded">
              <div className="font-mono text-[10px] tracking-widest text-text-muted uppercase mb-2">Size</div>
              <div className="font-mono text-sm text-text-primary">
                {selectedSource.file_size ? `${(selectedSource.file_size / 1024).toFixed(1)} KB` : '—'}
              </div>
            </div>
          </div>
          
          {selectedSource.error_message && (
            <div className="mt-6 ml-2 p-4 bg-error-bg border border-error/20 text-sm font-mono text-error flex items-start gap-3 relative z-10 rounded">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <div>
                <div className="uppercase tracking-widest text-[10px] mb-1 font-semibold">Processing Error</div>
                {selectedSource.error_message}
              </div>
            </div>
          )}
          
          <div className="mt-8 ml-2 text-[10px] font-mono tracking-widest uppercase text-text-muted relative z-10 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-text-muted" />
            Added: {new Date(selectedSource.created_at).toLocaleString()}
          </div>
        </motion.div>
      )}

      {sources.length === 0 && uploads.length === 0 && (
        <motion.div 
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6 }}
          className="flex flex-col items-center justify-center py-32 text-center"
        >
          <div className="w-16 h-16 border border-border bg-surface flex items-center justify-center mb-6 rounded-lg text-text-muted">
            <BookMarked className="w-6 h-6" />
          </div>
          <h3 className="text-xl font-heading font-medium mb-3 text-text-primary">Library is Empty</h3>
          <p className="text-text-secondary max-w-sm font-light text-base">
            Upload course materials, documents, or media to establish your knowledge baseline.
          </p>
        </motion.div>
      )}
    </div>
  );
}
