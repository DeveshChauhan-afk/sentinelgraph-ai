import React, { useEffect, useRef, useState, useCallback } from 'react';
import cytoscape, { Core, EventObject } from 'cytoscape';
import { graphApi } from '../../api';
import { GraphResponse, VisualNode } from '../../types';
import { LoadingState } from '../common/LoadingState';
import { ErrorState } from '../common/ErrorState';
import { EmptyState } from '../common/EmptyState';
import { Badge } from '../common/Badge';
import {
  Network,
  Maximize2,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Tag,
  ArrowRight,
  ShieldAlert,
} from 'lucide-react';

interface GraphVisualizationProps {
  targetValue: string;
  onSelectNewTarget?: (newTarget: string) => void;
  className?: string;
}

export const GraphVisualization: React.FC<GraphVisualizationProps> = ({
  targetValue,
  onSelectNewTarget,
  className = '',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [graphData, setGraphData] = useState<GraphResponse | null>(null);
  const [resolvedTargetId, setResolvedTargetId] = useState<string | null>(null);
  const [activeNode, setActiveNode] = useState<VisualNode | null>(null);

  // Fetch graph data whenever targetValue changes
  const fetchGraph = useCallback(async () => {
    if (!targetValue) return;

    setLoading(true);
    setError(null);
    setActiveNode(null);

    // Destroy existing cytoscape instance before fetching new target
    if (cyRef.current) {
      cyRef.current.destroy();
      cyRef.current = null;
    }

    try {
      // 1. Resolve entity to get its canonical graph node ID
      let nodeId = targetValue.trim();

      try {
        const entity = await graphApi.getEntity(nodeId);
        if (entity && entity.id) {
          nodeId = entity.id;
        }
      } catch {
        // If entity resolution fails (e.g. raw ID or direct complaint prefix),
        // fallback to trying the raw target value directly
      }

      setResolvedTargetId(nodeId);

      // 2. Fetch multi-hop visualization graph (depth=2)
      const data = await graphApi.getVisualization(nodeId, 2);
      setGraphData(data);
    } catch (err: any) {
      setError(
        err.message ||
          `Failed to load fraud network visualization for target "${targetValue}".`
      );
    } finally {
      setLoading(false);
    }
  }, [targetValue]);

  useEffect(() => {
    fetchGraph();

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, [fetchGraph]);

  // Initialize Cytoscape when data arrives and DOM is ready
  useEffect(() => {
    if (loading || error || !graphData || !containerRef.current) {
      return;
    }

    if (graphData.nodes.length === 0) {
      return;
    }

    // Safety destroy previous instance
    if (cyRef.current) {
      cyRef.current.destroy();
      cyRef.current = null;
    }

    const elements: cytoscape.ElementDefinition[] = [];

    // Format nodes
    graphData.nodes.forEach((node) => {
      const isTarget =
        node.id === resolvedTargetId ||
        node.properties?.lookup_value === targetValue ||
        node.label === targetValue;

      let displayLabel = node.label || node.id;
      // Abbreviate lengthy complaint UUIDs for readability
      if (displayLabel.startsWith('complaint:')) {
        const parts = displayLabel.split(':');
        const uuidPart = parts[1] || '';
        displayLabel = `CASE-${uuidPart.slice(0, 6).toUpperCase()}`;
      }

      elements.push({
        group: 'nodes',
        data: {
          id: node.id,
          label: displayLabel,
          fullLabel: node.label,
          type: node.type || 'Entity',
          isTarget: isTarget ? 'true' : 'false',
          rawNode: node,
        },
      });
    });

    // Format edges
    graphData.edges.forEach((edge) => {
      elements.push({
        group: 'edges',
        data: {
          id: edge.id || `${edge.source}-${edge.target}-${edge.label}`,
          source: edge.source,
          target: edge.target,
          label: edge.label || 'MENTIONS',
        },
      });
    });

    // Initialize Cytoscape
    const cy = cytoscape({
      container: containerRef.current,
      elements,
      boxSelectionEnabled: false,
      autounselectify: false,
      minZoom: 0.3,
      maxZoom: 2.5,
      style: [
        // Base Node Style
        {
          selector: 'node',
          style: {
            label: 'data(label)',
            color: '#cbd5e1',
            'font-size': 9,
            'font-family': 'JetBrains Mono, monospace',
            'text-valign': 'bottom',
            'text-margin-y': 5,
            'text-max-width': '100px',
            'text-wrap': 'ellipsis',
            width: 38,
            height: 38,
            'background-color': '#1e293b',
            'border-width': 2,
            'border-color': '#475569',
            'transition-property':
              'background-color, border-color, border-width, width, height, opacity',
            'transition-duration': 150,
          },
        },
        // Entity Type: Phone
        {
          selector: 'node[type = "Phone"]',
          style: {
            'background-color': '#1e3a8a',
            'border-color': '#3b82f6',
            shape: 'ellipse',
          },
        },
        // Entity Type: UPI
        {
          selector: 'node[type = "UPI"]',
          style: {
            'background-color': '#064e3b',
            'border-color': '#10b981',
            shape: 'ellipse',
          },
        },
        // Entity Type: Email
        {
          selector: 'node[type = "Email"]',
          style: {
            'background-color': '#78350f',
            'border-color': '#f59e0b',
            shape: 'ellipse',
          },
        },
        // Entity Type: Complaint
        {
          selector: 'node[type = "Complaint"]',
          style: {
            'background-color': '#7f1d1d',
            'border-color': '#ef4444',
            shape: 'round-rectangle',
            width: 44,
            height: 34,
          },
        },
        // Entity Type: Organization
        {
          selector: 'node[type = "Organization"]',
          style: {
            'background-color': '#312e81',
            'border-color': '#6366f1',
            shape: 'round-diamond',
            width: 42,
            height: 42,
          },
        },
        // Entity Type: Person
        {
          selector: 'node[type = "Person"]',
          style: {
            'background-color': '#581c87',
            'border-color': '#a855f7',
            shape: 'ellipse',
          },
        },
        // Entity Type: BankAccount
        {
          selector: 'node[type = "BankAccount"]',
          style: {
            'background-color': '#164e63',
            'border-color': '#06b6d4',
            shape: 'ellipse',
          },
        },
        // Highlight Target Entity
        {
          selector: 'node[isTarget = "true"]',
          style: {
            width: 52,
            height: 52,
            'border-width': 4,
            'border-color': '#38bdf8',
            'border-opacity': 1,
            color: '#38bdf8',
            'font-size': 11,
            'font-weight': 'bold',
            'underlay-color': '#0284c7',
            'underlay-padding': 6,
            'underlay-opacity': 0.4,
          },
        },
        // Clicked Node State
        {
          selector: 'node:selected',
          style: {
            'border-color': '#ffffff',
            'border-width': 3,
            color: '#ffffff',
            'font-weight': 'bold',
          },
        },
        // Dimmed State during hover/inspection
        {
          selector: '.dimmed',
          style: {
            opacity: 0.25,
          },
        },
        // Highlighted Neighborhood State
        {
          selector: '.highlighted',
          style: {
            opacity: 1,
            'border-width': 3,
          },
        },
        // Base Edge Style
        {
          selector: 'edge',
          style: {
            width: 1.5,
            'line-color': '#334155',
            'curve-style': 'bezier',
            'target-arrow-shape': 'triangle',
            'target-arrow-color': '#475569',
            'arrow-scale': 0.8,
            label: 'data(label)',
            color: '#64748b',
            'font-size': 8,
            'font-family': 'monospace',
            'text-rotation': 'autorotate',
            'text-background-color': '#0a0d14',
            'text-background-opacity': 0.85,
            'text-background-padding': '2px',
          },
        },
        {
          selector: 'edge.highlighted',
          style: {
            width: 2.5,
            'line-color': '#60a5fa',
            'target-arrow-color': '#60a5fa',
            color: '#93c5fd',
            opacity: 1,
          },
        },
      ],
      layout: {
        name: 'cose',
        animate: false,
        nodeDimensionsIncludeLabels: true,
        idealEdgeLength: 70,
        nodeOverlap: 25,
        fit: true,
        padding: 40,
        randomize: false,
        componentSpacing: 80,
        nodeRepulsion: 300000,
        edgeElasticity: 100,
        gravity: 80,
        numIter: 800,
      } as any,
    });

    // Tap node listener
    cy.on('tap', 'node', (evt: EventObject) => {
      const node = evt.target;
      const rawNode = node.data('rawNode') as VisualNode;
      setActiveNode(rawNode);

      // Neighborhood focus
      cy.elements().removeClass('highlighted dimmed');
      const neighborhood = node.neighborhood().add(node);
      cy.elements().not(neighborhood).addClass('dimmed');
      neighborhood.addClass('highlighted');
    });

    // Tap background listener
    cy.on('tap', (evt: EventObject) => {
      if (evt.target === cy) {
        setActiveNode(null);
        cy.elements().removeClass('highlighted dimmed');
      }
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [graphData, loading, error, resolvedTargetId, targetValue]);

  // Graph Viewport Controls
  const handleFit = () => {
    if (cyRef.current) {
      cyRef.current.fit(undefined, 35);
    }
  };

  const handleZoomIn = () => {
    if (cyRef.current) {
      cyRef.current.zoom({
        level: cyRef.current.zoom() * 1.3,
        renderedPosition: {
          x: cyRef.current.width() / 2,
          y: cyRef.current.height() / 2,
        },
      });
    }
  };

  const handleZoomOut = () => {
    if (cyRef.current) {
      cyRef.current.zoom({
        level: cyRef.current.zoom() * 0.75,
        renderedPosition: {
          x: cyRef.current.width() / 2,
          y: cyRef.current.height() / 2,
        },
      });
    }
  };

  const handleResetLayout = () => {
    if (cyRef.current) {
      cyRef.current.elements().removeClass('highlighted dimmed');
      setActiveNode(null);
      cyRef.current
        .layout({
          name: 'cose',
          animate: true,
          animationDuration: 500,
          fit: true,
          padding: 40,
          idealEdgeLength: 70,
        } as any)
        .run();
    }
  };

  return (
    <div
      className={`rounded-lg bg-sentinel-surface border border-sentinel-border overflow-hidden flex flex-col ${className}`}
    >
      {/* 1. Compact Graph Header */}
      <div className="p-3.5 border-b border-sentinel-border flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 bg-sentinel-surface select-none">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded bg-blue-950/60 border border-blue-800/80 text-blue-400">
            <Network className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-bold font-mono uppercase text-sentinel-text tracking-wider">
                Fraud Network
              </h3>
              {graphData && !loading && (
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-sentinel-bg border border-sentinel-border text-sentinel-dim">
                  2-HOP DEPTH
                </span>
              )}
            </div>

            {graphData && !loading && (
              <p className="text-[11px] font-mono text-sentinel-muted mt-0.5">
                {graphData.nodes.length} nodes • {graphData.edges.length} relationships
              </p>
            )}
          </div>
        </div>

        {/* Viewport Actions */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={handleFit}
            disabled={loading || !!error}
            title="Fit to Viewport"
            className="p-1.5 rounded bg-sentinel-bg hover:bg-sentinel-surfaceHover border border-sentinel-border text-sentinel-muted hover:text-sentinel-text transition-colors disabled:opacity-40"
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleZoomIn}
            disabled={loading || !!error}
            title="Zoom In"
            className="p-1.5 rounded bg-sentinel-bg hover:bg-sentinel-surfaceHover border border-sentinel-border text-sentinel-muted hover:text-sentinel-text transition-colors disabled:opacity-40"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleZoomOut}
            disabled={loading || !!error}
            title="Zoom Out"
            className="p-1.5 rounded bg-sentinel-bg hover:bg-sentinel-surfaceHover border border-sentinel-border text-sentinel-muted hover:text-sentinel-text transition-colors disabled:opacity-40"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleResetLayout}
            disabled={loading || !!error}
            title="Reset Layout Positions"
            className="p-1.5 rounded bg-sentinel-bg hover:bg-sentinel-surfaceHover border border-sentinel-border text-sentinel-muted hover:text-sentinel-text transition-colors disabled:opacity-40"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* 2. Graph Workspace Canvas */}
      <div className="relative w-full h-[480px] bg-[#0a0d14] overflow-hidden">
        {loading && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-sentinel-bg/85 backdrop-blur-sm">
            <LoadingState
              message="Traversing knowledge graph..."
              description={`Expanding 2-hop neighborhood for target: ${targetValue}`}
            />
          </div>
        )}

        {error && !loading && (
          <div className="absolute inset-0 z-10 flex items-center justify-center p-6 bg-sentinel-bg/90">
            <ErrorState
              title="Graph Traversal Failed"
              message={error}
              onRetry={fetchGraph}
            />
          </div>
        )}

        {!loading && !error && graphData && graphData.nodes.length === 0 && (
          <div className="absolute inset-0 z-10 flex items-center justify-center p-6">
            <EmptyState
              title="No graph connections found"
              message={`The entity "${targetValue}" exists in records but has no active multi-hop relationships in the graph.`}
            />
          </div>
        )}

        {/* The Cytoscape mount target */}
        <div ref={containerRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

        {/* 3. Node Details Overlay (When node is clicked) */}
        {activeNode && (
          <div className="absolute bottom-3 left-3 right-3 sm:right-auto sm:max-w-md z-20 p-3 rounded-lg bg-sentinel-surface/95 border border-sentinel-border shadow-xl backdrop-blur-md">
            <div className="flex items-start justify-between gap-2 mb-1.5">
              <div className="flex items-center gap-2 min-w-0">
                <Tag className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                <span className="font-mono text-xs font-bold text-sentinel-text truncate">
                  {activeNode.label || activeNode.id}
                </span>
              </div>
              <Badge variant="info">{activeNode.type}</Badge>
            </div>

            <div className="text-[11px] font-mono text-sentinel-muted truncate mb-2">
              ID: {activeNode.id}
            </div>

            {onSelectNewTarget && (
              <div className="pt-2 border-t border-sentinel-border flex items-center justify-between">
                <span className="text-[10px] text-sentinel-dim">Pivot investigation:</span>
                <button
                  onClick={() =>
                    onSelectNewTarget(
                      activeNode.properties?.lookup_value ||
                        activeNode.properties?.value ||
                        activeNode.label ||
                        activeNode.id
                    )
                  }
                  className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium text-white bg-blue-600 hover:bg-blue-500 rounded transition-colors"
                >
                  <span>Set as Target</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 4. Major Entity Types Legend */}
      <div className="p-2.5 border-t border-sentinel-border bg-sentinel-surface flex flex-wrap items-center justify-between gap-2 text-[11px] select-none font-mono">
        <div className="flex items-center gap-1.5 text-sentinel-dim uppercase text-[10px] tracking-wider">
          <ShieldAlert className="w-3 h-3 text-sentinel-dim" />
          <span>Legend:</span>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-500 ring-2 ring-blue-400/40" />
            <span className="text-sentinel-muted">Phone</span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 ring-2 ring-emerald-400/40" />
            <span className="text-sentinel-muted">UPI</span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500 ring-2 ring-amber-400/40" />
            <span className="text-sentinel-muted">Email</span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded bg-rose-500 ring-2 ring-rose-400/40" />
            <span className="text-sentinel-muted">Complaint</span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 ring-2 ring-indigo-400/40" />
            <span className="text-sentinel-muted">Org</span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-500 ring-2 ring-purple-400/40" />
            <span className="text-sentinel-muted">Person</span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-500 ring-2 ring-cyan-400/40" />
            <span className="text-sentinel-muted">Bank</span>
          </div>

          <div className="flex items-center gap-1.5 pl-2 border-l border-sentinel-border">
            <span className="w-2.5 h-2.5 rounded-full bg-sky-400 ring-4 ring-sky-400/30" />
            <span className="text-sky-300 font-semibold">Target</span>
          </div>
        </div>
      </div>
    </div>
  );
};
