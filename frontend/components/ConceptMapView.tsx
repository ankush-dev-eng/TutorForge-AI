'use client';

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { conceptsApi, ConceptGraph, ConceptGraphNode } from '@/lib/api';
import { Network, RefreshCw, X, Info, Target, AlertTriangle, Loader2 } from 'lucide-react';
import {
  ReactFlow,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  Panel,
  useReactFlow,
  ReactFlowProvider,
  Node,
  Edge,
  BackgroundVariant
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
// dagre removed — using deterministic explicit layout

function getMasteryColor(status: string): string {
  switch (status) {
    case 'mastered': return 'var(--color-mastered)';
    case 'developing': return 'var(--color-developing)';
    case 'weak': return 'var(--color-needs-review)';
    default: return 'var(--color-not-started)';
  }
}

function getMasteryBg(status: string): string {
  switch (status) {
    case 'mastered': return 'bg-[var(--color-mastered-soft)] border-[var(--color-mastered-border)] text-[var(--color-mastered-text)]';
    case 'developing': return 'bg-[var(--color-developing-soft)] border-[var(--color-developing-border)] text-[var(--color-developing-text)]';
    case 'weak': return 'bg-[var(--color-needs-review-soft)] border-[var(--color-needs-review-border)] text-[var(--color-needs-review-text)]';
    default: return 'bg-[var(--color-not-started-soft)] border-[var(--color-not-started-border)] text-[var(--color-not-started-text)]';
  }
}

function getMasteryText(status: string): string {
  switch (status) {
    case 'mastered': return 'text-[var(--color-mastered-text)]';
    case 'developing': return 'text-[var(--color-developing-text)]';
    case 'weak': return 'text-[var(--color-needs-review-text)]';
    default: return 'text-[var(--color-not-started-text)]';
  }
}

interface ConceptNodeData {
  node: ConceptGraphNode;
  isMajor: boolean;
  isMinor: boolean;
  dimmed: boolean;
}

// Custom Node Component
const ConceptNodeComponent = ({ data, selected }: { data: ConceptNodeData, selected: boolean }) => {
  const { node, isMajor, isMinor } = data;
  const r = isMajor ? 68 : isMinor ? 52 : 60; 
  
  return (
    <div 
      className={`relative flex flex-col items-center justify-center transition-all duration-200 ${selected ? 'scale-[1.04]' : 'scale-100'}`}
      style={{ opacity: data.dimmed ? 0.6 : 1 }}
    >
       {/* Subtle shadow using a generic absolute div */}
       <div 
         className="absolute rounded-full" 
         style={{ 
           width: r, height: r, 
           backgroundColor: getMasteryColor(node.status), 
           opacity: 0.1, 
           transform: selected ? 'translate(2px, 4px)' : 'translate(1px, 2px)',
           top: 0
         }} 
       />
       
       <div 
         className={`relative flex items-center justify-center bg-card rounded-full ${getMasteryBg(node.status)} shadow-sm`}
         style={{ width: r, height: r, borderWidth: selected ? '2px' : '1.5px', borderColor: getMasteryColor(node.status), zIndex: 10 }}
       >
         <span 
           className={`font-semibold text-center leading-none ${getMasteryText(node.status)}`} 
           style={{ 
             fontSize: isMajor ? '15px' : isMinor ? '12px' : '14px',
             fontFamily: "var(--font-heading)" 
           }}
         >
           {node.mastery_pct !== null ? `${node.mastery_pct}%` : '--%'}
         </span>
       </div>
       <div 
         className={`mt-2.5 font-medium leading-[1.2] text-center line-clamp-2 ${selected ? getMasteryText(node.status) : 'text-foreground/80'}`}
         style={{ maxWidth: '120px', fontSize: isMajor ? '14px' : isMinor ? '12px' : '13px' }}
       >
         {node.label}
       </div>
       
       <Handle type="target" position={Position.Top} className="opacity-0" />
       <Handle type="source" position={Position.Bottom} className="opacity-0" />
    </div>
  );
};

const nodeTypes = {
  concept: ConceptNodeComponent,
};

// ---------------------------------------------------------------------------
// DETERMINISTIC LAYOUT
// Explicit positions keyed by actual backend node IDs.
// Canvas logical coordinate space: 1100 × 700.
// All positions refer to the TOP-LEFT corner of the node's bounding box (60×60).
// ---------------------------------------------------------------------------

// Preferred positions for the known 12-concept Computer Networks dataset.
// Keys are stringified backend node IDs.
const PREFERRED_POSITIONS: Record<string, { x: number; y: number }> = {
  '1':  { x: 490, y: 20  },  // Computer Networks  — root
  '9':  { x: 200, y: 150 },  // Network Layer
  '2':  { x: 620, y: 150 },  // Transport Layer
  '12': { x: 920, y: 150 },  // Data Link Layer
  '10': { x: 80,  y: 290 },  // IP Protocol
  '11': { x: 310, y: 290 },  // Routing Algorithms
  '3':  { x: 560, y: 290 },  // TCP
  '4':  { x: 780, y: 290 },  // UDP
  '5':  { x: 400, y: 420 },  // Flow Control
  '6':  { x: 600, y: 420 },  // Congestion Control
  '8':  { x: 780, y: 420 },  // Retransmission
  '7':  { x: 490, y: 555 },  // Sliding Window
};

// Grid fallback for any nodes not in the preferred map.
// Columns of 4, spaced 240px apart, starting below the known graph.
const GRID_FALLBACK_START_Y = 750;
const GRID_COLS = 4;
const GRID_COL_GAP = 240;
const GRID_ROW_GAP = 150;

function getNodePosition(id: string, unknownIndex: number): { x: number; y: number } {
  if (PREFERRED_POSITIONS[id]) return PREFERRED_POSITIONS[id];
  const col = unknownIndex % GRID_COLS;
  const row = Math.floor(unknownIndex / GRID_COLS);
  return {
    x: Math.min(80 + col * GRID_COL_GAP, 980),
    y: GRID_FALLBACK_START_Y + row * GRID_ROW_GAP,
  };
}

function FlowMap({ graph, onNodeSelect, selectedNodeId }: { graph: ConceptGraph, onNodeSelect: (node: ConceptGraphNode | null) => void, selectedNodeId: number | null }) {
  const { fitView } = useReactFlow();
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const didFitRef = useRef(false);

  // Derive which node IDs are directly connected to the selected node.
  const connectedIds = useMemo(() => {
    if (!selectedNodeId) return new Set<string>();
    const s = new Set<string>();
    graph.edges.forEach(e => {
      if (e.source.toString() === selectedNodeId.toString()) s.add(e.target.toString());
      if (e.target.toString() === selectedNodeId.toString()) s.add(e.source.toString());
    });
    return s;
  }, [selectedNodeId, graph.edges]);

  const initLayout = useCallback(() => {
    if (!graph || graph.nodes.length === 0) return;
    didFitRef.current = false;

    // Degree counts to identify major (root) / minor (leaf) nodes.
    const inDegree: Record<string, number> = {};
    const outDegree: Record<string, number> = {};
    graph.nodes.forEach(n => {
      inDegree[n.id.toString()] = 0;
      outDegree[n.id.toString()] = 0;
    });
    graph.edges.forEach(e => {
      outDegree[e.source.toString()] = (outDegree[e.source.toString()] || 0) + 1;
      inDegree[e.target.toString()]  = (inDegree[e.target.toString()]  || 0) + 1;
    });

    // Assign deterministic positions — NO random, NO dagre, NO animation delays.
    let unknownIdx = 0;
    const newNodes: Node[] = graph.nodes.map(node => {
      const id = node.id.toString();
      const isMajor = inDegree[id] === 0 && outDegree[id] > 0;
      const isMinor = outDegree[id] === 0 && inDegree[id] > 0;
      const pos = getNodePosition(id, !PREFERRED_POSITIONS[id] ? unknownIdx++ : 0);

      if (process.env.NODE_ENV === 'development') {
        console.log(`[ConceptMap] node id=${id} label="${node.label}" pos=(${pos.x},${pos.y}) finiteX=${Number.isFinite(pos.x)} finiteY=${Number.isFinite(pos.y)}`);
      }

      return {
        id,
        type: 'concept',
        position: pos,          // stable, finite, pixel coordinates
        data: { node, isMajor, isMinor, dimmed: false },
        style: { opacity: 1 }, // ALWAYS visible — no animation dependency
      };
    });

    // Validate and deduplicate edges — skip any that reference missing nodes.
    const nodeIdSet = new Set(newNodes.map(n => n.id));
    const edgeKeySet = new Set<string>();
    const newEdges: Edge[] = [];
    graph.edges.forEach((edge, i) => {
      const src = edge.source.toString();
      const tgt = edge.target.toString();
      const key = `${src}->${tgt}`;
      if (!nodeIdSet.has(src) || !nodeIdSet.has(tgt)) {
        console.warn(`[ConceptMap] skipping edge ${src}->${tgt}: node not found`);
        return;
      }
      if (edgeKeySet.has(key)) return; // deduplicate
      edgeKeySet.add(key);
      newEdges.push({
        id: `e${src}-${tgt}-${i}`,
        source: src,
        target: tgt,
        type: 'smoothstep',
        animated: false,
        style: { strokeWidth: 1.2, stroke: 'currentColor', opacity: 0.45 },
      });
    });

    if (process.env.NODE_ENV === 'development') {
      console.log(`[ConceptMap] layout complete: ${newNodes.length} nodes, ${newEdges.length} unique edges`);
    }

    setNodes(newNodes);
    setEdges(newEdges);

    // fitView exactly once after React has committed the new nodes.
    window.requestAnimationFrame(() => {
      fitView({ padding: 0.15, minZoom: 0.55, maxZoom: 1.15, duration: 400 });
      didFitRef.current = true;
    });
  }, [graph, setNodes, setEdges, fitView]);

  useEffect(() => {
    initLayout();
  }, [initLayout]);

  // Apply selection-based dim/highlight to nodes and edges.
  // Skipped when nodes aren't laid out yet or when nothing changed.
  useEffect(() => {
    if (nodes.length === 0) return;
    setNodes(nds => nds.map(n => {
      const isSelected = selectedNodeId?.toString() === n.id;
      const shouldDim = selectedNodeId ? (!isSelected && !connectedIds.has(n.id)) : false;
      if ((n.data as unknown as ConceptNodeData).dimmed === shouldDim) return n; // skip unchanged
      return { ...n, data: { ...n.data, dimmed: shouldDim } };
    }));
    setEdges(eds => eds.map(e => {
      const linked = selectedNodeId
        ? (e.source === selectedNodeId.toString() || e.target === selectedNodeId.toString())
        : false;
      return {
        ...e,
        style: {
          ...e.style,
          strokeWidth: linked ? 1.8 : 1.2,
          stroke: linked ? 'var(--color-accent)' : 'currentColor',
          opacity: selectedNodeId ? (linked ? 1 : 0.15) : 0.5,
        },
      };
    }));
  }, [selectedNodeId, connectedIds, setNodes, setEdges, nodes.length]);

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={(_, node) => onNodeSelect(node.data.node as ConceptGraphNode)}
        onPaneClick={() => onNodeSelect(null)}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.18, minZoom: 0.65, maxZoom: 1.15 }}
        minZoom={0.55}
        maxZoom={1.35}
        nodesConnectable={false}
        nodesDraggable={true}
        elementsSelectable={true}
        className="bg-card"
      >
        <Background color="var(--color-border)" variant={BackgroundVariant.Cross} gap={40} size={1} style={{ opacity: 0.1 }} />
        <Controls showInteractive={false} className="shadow-sm border border-border bg-card fill-foreground text-foreground" />
        <Panel position="top-right" className="flex gap-2">
          <button
            onClick={initLayout}
            className="bg-card border border-border text-xs px-3 py-1.5 shadow-sm text-foreground font-medium hover:bg-muted transition-colors rounded-sm"
          >
            Reset Layout
          </button>
        </Panel>
      </ReactFlow>
    </div>
  );
}


export function ConceptMapView({ onNavigate }: { onNavigate?: (tab: string) => void } = {}) {
  const [graph, setGraph] = useState<ConceptGraph | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<ConceptGraphNode | null>(null);

  const loadGraph = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await conceptsApi.graph();
      setGraph(data);
      // Re-sync selected against the refreshed node list so the detail panel
      // always shows current mastery data; clear it if the node was removed.
      setSelected(prev => {
        if (!prev) return null;
        return data.nodes.find(n => n.id === prev.id) ?? null;
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load concept graph');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // loadGraph is async — setState only runs after the fetch resolves, not synchronously.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadGraph();
  }, [loadGraph]);


  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
        <p className="text-muted-foreground text-sm uppercase tracking-widest font-medium">Loading Concept Map</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 max-w-sm mx-auto text-center">
        <AlertTriangle className="w-10 h-10 text-amber-500" />
        <div>
          <h3 className="text-lg font-semibold mb-2">Failed to Load Graph</h3>
          <p className="text-muted-foreground text-sm">{error}</p>
        </div>
        <button onClick={loadGraph} className="border border-border/40 hover:bg-muted px-6 py-2.5 text-sm font-medium transition-colors flex items-center gap-2 mt-2">
          <RefreshCw className="w-4 h-4" />Retry
        </button>
      </div>
    );
  }

  if (!graph || graph.nodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full max-w-2xl mx-auto space-y-8 animate-in fade-in duration-700">
        <div className="w-16 h-16 bg-muted/30 flex items-center justify-center rounded-lg border border-border/40">
          <Network className="w-8 h-8 text-primary/80" />
        </div>
        <div className="text-center">
          <h2 className="text-3xl font-semibold mb-4 tracking-tight">Concept Map</h2>
          <p className="text-muted-foreground text-base leading-relaxed max-w-lg mx-auto">
            Upload materials and complete assessments to populate your interactive concept map.
          </p>
        </div>
      </div>
    );
  }

  // Count by status
  const statusCounts = { mastered: 0, developing: 0, weak: 0, unseen: 0 };
  graph.nodes.forEach(n => { statusCounts[n.status as keyof typeof statusCounts]++; });

  return (
    <div className="flex flex-col animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-7xl mx-auto w-full py-8 px-4 md:px-0">
      <header className="flex flex-col md:flex-row md:justify-between md:items-end gap-6 mb-8">
        <div>
          <h1 className="text-3xl md:text-4xl font-semibold mb-3 tracking-tight">
            Concept Map
          </h1>
          <p className="text-muted-foreground text-sm uppercase tracking-widest font-medium">
            {graph.nodes.length} concepts · {graph.edges.length} relationships
          </p>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={loadGraph}
            className="flex items-center gap-2 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors border border-border/40 px-3 py-1.5 bg-card hover:bg-muted"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </button>
        </div>
      </header>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Mastered', count: statusCounts.mastered, color: 'text-[var(--color-mastered)]', borderColor: 'border-border/40' },
          { label: 'Developing', count: statusCounts.developing, color: 'text-[var(--color-developing)]', borderColor: 'border-border/40' },
          { label: 'Needs Review', count: statusCounts.weak, color: 'text-[var(--color-needs-review)]', borderColor: 'border-border/40' },
          { label: 'Not Started', count: statusCounts.unseen, color: 'text-[var(--color-not-started)]', borderColor: 'border-border/40' },
        ].map(s => (
          <div key={s.label} className={`bg-card p-4 border shadow-sm flex flex-col justify-between ${s.borderColor}`}>
            <div className={`text-3xl font-semibold mb-1 ${s.color}`}>{s.count}</div>
            <div className="flex items-center gap-2">
               <div className="w-2 h-2 rounded-full" style={{ backgroundColor: s.color.replace('text-[', '').replace(']', '') }} />
              <div className="text-xs font-medium uppercase tracking-widest text-muted-foreground">{s.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Graph + panel row. Explicit min-height so React Flow always has pixels to fill. */}
      <div className="flex flex-col md:flex-row gap-6 relative" style={{ minHeight: '560px' }}>
        {/* React Flow Graph — MUST have explicit height; React Flow collapses to 0 on h-auto */}
        <div
          className="flex-1 bg-card border border-border/40 overflow-hidden relative shadow-sm rounded-lg"
          style={{ height: 'clamp(560px, 68vh, 760px)' }}
        >
          <div className="absolute top-4 left-4 z-10 hidden md:block">
            <div className="flex flex-col gap-2 p-3 bg-card border border-border shadow-sm text-xs rounded-md">
              {[
                { color: 'var(--color-mastered)', label: 'Mastered' },
                { color: 'var(--color-developing)', label: 'Developing' },
                { color: 'var(--color-needs-review)', label: 'Needs Review' },
                { color: 'var(--color-not-started)', label: 'Not Started' },
              ].map(item => (
                <div key={item.label} className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color }} />
                  <span className="text-muted-foreground font-medium">{item.label}</span>
                </div>
              ))}
            </div>
          </div>
          
          <ReactFlowProvider>
            <FlowMap 
              graph={graph} 
              onNodeSelect={setSelected} 
              selectedNodeId={selected ? selected.id : null} 
            />
          </ReactFlowProvider>
        </div>

        {/* Detail Panel Desktop (Right Panel) */}
        {selected && (
          <div className="hidden md:flex w-80 bg-card border border-border/40 p-6 flex-col gap-6 animate-in slide-in-from-right-4 duration-300 shadow-sm shrink-0 overflow-y-auto rounded-lg">
             <DetailPanelContent selected={selected} setSelected={setSelected} onNavigate={onNavigate} />
          </div>
        )}

        {/* Detail Panel Mobile (Bottom Sheet Style) */}
        {selected && (
          <div className="md:hidden absolute bottom-0 left-0 right-0 bg-card border-t border-border/40 p-6 flex flex-col gap-6 animate-in slide-in-from-bottom-4 duration-300 shadow-[0_-4px_20px_rgba(0,0,0,0.1)] z-50 rounded-t-xl max-h-[80vh] overflow-y-auto">
             <DetailPanelContent selected={selected} setSelected={setSelected} onNavigate={onNavigate} />
          </div>
        )}
      </div>
    </div>
  );
}

function DetailPanelContent({
  selected,
  setSelected,
  onNavigate,
}: {
  selected: ConceptGraphNode;
  setSelected: (n: ConceptGraphNode | null) => void;
  onNavigate?: (tab: string) => void;
}) {
  return (
    <>
      <div className="flex justify-between items-start gap-4">
        <h3 className="font-semibold text-lg leading-tight">{selected.label}</h3>
        <button onClick={() => setSelected(null)} className="text-muted-foreground hover:text-foreground shrink-0 border border-transparent hover:border-border/40 p-1 bg-muted/20">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className={`flex items-center gap-2 px-3 py-2 border text-sm font-medium uppercase tracking-wider ${getMasteryBg(selected.status)}`}>
        <Target className="w-4 h-4" />
        {selected.status === 'mastered' ? 'Mastered' :
         selected.status === 'developing' ? 'Developing' :
         selected.status === 'weak' ? 'Needs Review' : 'Not Started'}
        {selected.mastery_pct !== null && ` · ${selected.mastery_pct}%`}
      </div>

      {selected.description && (
        <div>
          <div className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-2 flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5" />Description
          </div>
          <p className="text-sm text-foreground/80 leading-relaxed">{selected.description}</p>
        </div>
      )}

      <div>
        <div className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-2">Subject</div>
        <div className="text-xs font-medium uppercase tracking-wider bg-muted text-foreground px-2 py-1 inline-block border border-border/30">
          {selected.subject}
        </div>
      </div>

      <div className="mt-auto flex flex-col gap-3">
        {selected.status === 'not_started' && (
          // Navigate to AI Tutor to introduce this topic.
          <button
            onClick={() => onNavigate?.('tutor')}
            className="w-full py-2.5 bg-primary text-primary-foreground font-medium text-sm hover:bg-primary/90 transition-colors"
          >
            Start with AI Tutor
          </button>
        )}
        {selected.status === 'weak' && (
          <>
            {/* Navigate to Assessment for a focused review session. */}
            <button
              onClick={() => onNavigate?.('assessment')}
              className="w-full py-2.5 bg-primary text-primary-foreground font-medium text-sm hover:bg-primary/90 transition-colors"
            >
              Focus Review
            </button>
            {/* Navigate to Tutor to ask questions about weak areas. */}
            <button
              onClick={() => onNavigate?.('tutor')}
              className="w-full py-2.5 bg-transparent border border-primary text-primary font-medium text-sm hover:bg-primary/5 transition-colors"
            >
              Ask Tutor
            </button>
          </>
        )}
        {selected.status === 'developing' && (
          <>
            {/* Navigate to AI Tutor to continue learning. */}
            <button
              onClick={() => onNavigate?.('tutor')}
              className="w-full py-2.5 bg-primary text-primary-foreground font-medium text-sm hover:bg-primary/90 transition-colors"
            >
              Continue
            </button>
            {/* Navigate to Assessment to review fundamentals. */}
            <button
              onClick={() => onNavigate?.('assessment')}
              className="w-full py-2.5 bg-transparent border border-primary text-primary font-medium text-sm hover:bg-primary/5 transition-colors"
            >
              Review Fundamentals
            </button>
          </>
        )}
        {selected.status === 'mastered' && (
          // Navigate to Assessment for a periodic review.
          <button
            onClick={() => onNavigate?.('assessment')}
            className="w-full py-2.5 bg-transparent border border-primary text-primary font-medium text-sm hover:bg-primary/5 transition-colors"
          >
            Review
          </button>
        )}
      </div>
    </>
  );
}
