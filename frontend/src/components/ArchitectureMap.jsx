import { useMemo, useState } from 'react';
import {
  architectureEdges,
  architectureNodes,
  architectureViews,
  boundaryLabels,
  flowStyles,
  kindFlow,
  statusLabels,
} from '../data/architectureData';
import './ArchitectureMap.css';

const NODE_WIDTH = 160;
const NODE_HEIGHT = 64;
const BOUNDARY_PADDING = 55;
const FEEDBACK_BOW = 55;

const statusColors = {
  implemented: '#3ddc84',
  'in-progress': '#f2bd58',
  planned: '#8b93a7',
};

// Outgoing edges of these kinds represent this node causing a decision or
// state change elsewhere (vs. just passing data through) - shown in the
// detail panel's "Influences" bucket.
const INFLUENCE_KINDS = ['tool-call', 'memory-write', 'auth-consent', 'optional-cloud'];
// Incoming edges of these kinds are inputs this node actually needs to do
// its job (vs. e.g. a plain stream relay) - shown under "Depends on".
const DEPENDENCY_KINDS = ['request', 'context', 'memory-read', 'tool-result', 'evidence', 'model-inference', 'auth-consent'];

function edgeKey(edge) {
  return `${edge.from}->${edge.to}:${edge.label}`;
}

function ArchitectureMap() {
  const [view, setView] = useState('system');
  const [selectedId, setSelectedId] = useState('backend');
  const [query, setQuery] = useState('');
  const [detailOpen, setDetailOpen] = useState(true);

  const nodesById = useMemo(
    () => Object.fromEntries(architectureNodes.map((node) => [node.id, node])),
    []
  );

  const visibleNodes = useMemo(
    () => architectureNodes.filter((node) => node.views.includes(view)),
    [view]
  );

  const visibleEdges = useMemo(
    () => architectureEdges.filter((edge) => edge.views.includes(view)),
    [view]
  );

  // The local/self-hosted perimeter is drawn from the LOCAL-boundary nodes
  // actually visible in the current view (not every local node across all
  // tabs) - each tab gets a canvas sized to what it actually shows, instead
  // of the System tab (8 nodes) carrying dead space reserved for Chat &
  // Agent's much larger node set.
  const boundaryRect = useMemo(() => {
    const localNodes = visibleNodes.filter((node) => node.boundary === 'local');
    const minX = Math.min(...localNodes.map((n) => n.x)) - NODE_WIDTH / 2 - BOUNDARY_PADDING;
    const maxX = Math.max(...localNodes.map((n) => n.x)) + NODE_WIDTH / 2 + BOUNDARY_PADDING;
    const minY = Math.min(...localNodes.map((n) => n.y)) - NODE_HEIGHT / 2 - BOUNDARY_PADDING;
    const maxY = Math.max(...localNodes.map((n) => n.y)) + NODE_HEIGHT / 2 + BOUNDARY_PADDING;
    return { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
  }, [visibleNodes]);

  // Canvas viewBox likewise fits the current view's own nodes (local, client
  // and cloud alike) instead of a single fixed size shared by all tabs.
  const viewBox = useMemo(() => {
    const CANVAS_PADDING = 70;
    const minX = Math.min(...visibleNodes.map((n) => n.x)) - NODE_WIDTH / 2 - CANVAS_PADDING;
    const maxX = Math.max(...visibleNodes.map((n) => n.x)) + NODE_WIDTH / 2 + CANVAS_PADDING;
    const minY = Math.min(...visibleNodes.map((n) => n.y)) - NODE_HEIGHT / 2 - CANVAS_PADDING - 20;
    const maxY = Math.max(...visibleNodes.map((n) => n.y)) + NODE_HEIGHT / 2 + CANVAS_PADDING;
    return `${minX} ${minY} ${maxX - minX} ${maxY - minY}`;
  }, [visibleNodes]);

  const searchMatches = useMemo(() => {
    if (!query.trim()) return [];
    const q = query.trim().toLowerCase();
    return architectureNodes.filter((node) =>
      `${node.title} ${node.subtitle} ${node.layer}`.toLowerCase().includes(q)
    );
  }, [query]);

  const selected = nodesById[selectedId];
  const selectedVisible = selected && selected.views.includes(view);

  // Flow-shaped relations instead of one flat list: who feeds this node,
  // what it hands onward, which decisions/state it drives, and what it
  // structurally needs to function.
  const incoming = useMemo(
    () => (selected ? architectureEdges.filter((e) => e.to === selected.id) : []),
    [selected]
  );
  const outgoing = useMemo(
    () => (selected ? architectureEdges.filter((e) => e.from === selected.id) : []),
    [selected]
  );
  const dependsOn = useMemo(
    () => incoming.filter((e) => DEPENDENCY_KINDS.includes(e.kind)),
    [incoming]
  );
  const influences = useMemo(
    () => outgoing.filter((e) => INFLUENCE_KINDS.includes(e.kind)),
    [outgoing]
  );

  const chooseNode = (id) => {
    setSelectedId(id);
    setDetailOpen(true);
    const node = nodesById[id];
    if (node && !node.views.includes(view)) {
      setView(node.views[0]);
    }
  };

  const renderRelationGroup = (title, edges, direction) => {
    if (edges.length === 0) return null;
    return (
      <>
        <h4>{title}</h4>
        <div className="arch-relations">
          {edges.map((edge) => {
            const otherId = direction === 'in' ? edge.from : edge.to;
            const otherNode = nodesById[otherId];
            const arrow = direction === 'in' ? '←' : '→';
            return (
              <button key={`${title}-${edgeKey(edge)}`} type="button" onClick={() => chooseNode(otherId)}>
                {arrow} {otherNode?.title} <small>{edge.label}</small>
              </button>
            );
          })}
        </div>
      </>
    );
  };

  return (
    <div className="arch-root">
      <section className="arch-toolbar" aria-label="Architekturansicht auswählen">
        <div className="arch-tabs" role="tablist">
          {architectureViews.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={view === item.id}
              className={`arch-tab${view === item.id ? ' arch-tab-active' : ''}`}
              onClick={() => setView(item.id)}
              title={item.description}
            >
              {item.label}
            </button>
          ))}
        </div>

        <div className="arch-search">
          <label className="arch-search-label" htmlFor="arch-search-input">Komponente finden</label>
          <input
            id="arch-search-input"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="z. B. Tool Calling"
            aria-label="Komponente suchen"
          />
          {searchMatches.length > 0 && (
            <div className="arch-search-results">
              {searchMatches.map((node) => (
                <button
                  key={node.id}
                  type="button"
                  onClick={() => {
                    chooseNode(node.id);
                    setQuery('');
                  }}
                >
                  <strong>{node.title}</strong> <span>{node.layer}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </section>

      <div className="arch-legend" aria-label="Legende">
        {Object.entries(statusLabels).map(([key, label]) => (
          <span key={key} className="arch-legend-item">
            <span className="arch-legend-dot" style={{ background: statusColors[key] }} />
            {label}
          </span>
        ))}
        <span className="arch-legend-divider" aria-hidden="true" />
        {Object.entries(flowStyles).map(([key, style]) => (
          <span key={key} className="arch-legend-item">
            <span
              className="arch-legend-line"
              style={{ borderTopColor: style.color, borderTopStyle: style.dash ? 'dashed' : 'solid' }}
            />
            {style.label}
          </span>
        ))}
      </div>

      <div className="arch-workspace">
        <div className="arch-diagram" aria-label={`${architectureViews.find((v) => v.id === view)?.label} Diagramm`}>
          <svg viewBox={viewBox} role="img" aria-labelledby="architecture-title">
            <title id="architecture-title">Architektur-Diagramm: {view}</title>

            <defs>
              {Object.entries(flowStyles).map(([role, style]) => (
                <marker
                  key={role}
                  id={`arch-arrow-${role}`}
                  viewBox="0 0 10 10"
                  refX="8"
                  refY="5"
                  markerWidth="7"
                  markerHeight="7"
                  orient="auto-start-reverse"
                >
                  <path d="M0,0 L10,5 L0,10 z" fill={style.color} />
                </marker>
              ))}
              <marker
                id="arch-arrow-planned"
                viewBox="0 0 10 10"
                refX="8"
                refY="5"
                markerWidth="7"
                markerHeight="7"
                orient="auto-start-reverse"
              >
                <path d="M0,0 L10,5 L0,10 z" fill={statusColors.planned} />
              </marker>
            </defs>

            {/* Trust boundary: everything inside is Liara's self-hosted perimeter */}
            <rect
              x={boundaryRect.x}
              y={boundaryRect.y}
              width={boundaryRect.width}
              height={boundaryRect.height}
              className="arch-boundary-rect"
            />
            <text x={boundaryRect.x + 16} y={boundaryRect.y + 24} className="arch-boundary-label">
              Self-hosted / Local-first Perimeter
            </text>

            {/* Edges - forward flow uses a horizontal-tangent curve pulled
                back to each node's border; feedback edges (a result/response
                going back against the main direction) bow out to the side
                instead, so a forward and its matching return edge between
                the same two nodes never sit on top of each other. */}
            {visibleEdges.map((edge) => {
              const from = nodesById[edge.from];
              const to = nodesById[edge.to];
              if (!from || !to) return null;
              const key = edgeKey(edge);

              const flowRole = kindFlow[edge.kind] || 'main';
              const style = flowStyles[flowRole];
              // A connection into/out of a not-yet-built ("planned") node
              // shouldn't read as a solid, already-working main-flow line.
              const isPlannedEdge = from.status === 'planned' || to.status === 'planned';

              const dx = to.x - from.x;
              const dy = to.y - from.y;
              const dist = Math.hypot(dx, dy) || 1;
              const inset = NODE_WIDTH / 2 + 6;
              const ux = dx / dist;
              const uy = dy / dist;
              const sx = from.x + ux * inset;
              const sy = from.y + uy * inset;
              const ex = to.x - ux * inset;
              const ey = to.y - uy * inset;

              // Most edges just use the flow-role's default bow behaviour,
              // but a specific edge can override it (direction/amount) when
              // its default path happens to graze an unrelated node's box -
              // e.g. the long Model->Ollama Cloud hop crossing right through
              // the Chat & Agent tool-branch column.
              const useBow = edge.bow !== undefined ? edge.bow : style.bow;
              const bowDir = edge.bowDir || 1;
              const bowAmount = edge.bowAmount || FEEDBACK_BOW;

              let d;
              let labelX;
              let labelY;
              if (useBow) {
                // Perpendicular offset from the straight line, bowing the
                // return path out and around the forward one.
                const px = -uy * bowDir;
                const py = ux * bowDir;
                const midX = (sx + ex) / 2 + px * bowAmount;
                const midY = (sy + ey) / 2 + py * bowAmount;
                d = `M ${sx},${sy} Q ${midX},${midY} ${ex},${ey}`;
                labelX = midX;
                labelY = midY;
              } else {
                const midX = (sx + ex) / 2;
                d = `M ${sx},${sy} C ${midX},${sy} ${midX},${ey} ${ex},${ey}`;
                labelX = midX;
                labelY = (sy + ey) / 2 - 6;
              }

              return (
                <g key={key} className="arch-edge-group">
                  <path
                    d={d}
                    fill="none"
                    stroke={isPlannedEdge ? statusColors.planned : style.color}
                    strokeWidth={2}
                    strokeDasharray={isPlannedEdge ? '3 5' : (style.dash || undefined)}
                    opacity={isPlannedEdge ? 0.6 : 0.85}
                    markerEnd={`url(#arch-arrow-${isPlannedEdge ? 'planned' : flowRole})`}
                  />
                  <text
                    x={labelX}
                    y={labelY}
                    textAnchor="middle"
                    className="arch-edge-label"
                    paintOrder="stroke"
                  >
                    {edge.label}
                  </text>
                </g>
              );
            })}

            {/* Nodes */}
            {visibleNodes.map((node) => (
              <g
                key={node.id}
                className={`arch-node${selectedId === node.id ? ' arch-node-selected' : ''}`}
                transform={`translate(${node.x - NODE_WIDTH / 2}, ${node.y - NODE_HEIGHT / 2})`}
                onClick={() => chooseNode(node.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') chooseNode(node.id); }}
              >
                <rect
                  width={NODE_WIDTH}
                  height={NODE_HEIGHT}
                  rx={10}
                  className={`arch-node-rect arch-node-${node.boundary}`}
                  stroke={statusColors[node.status]}
                />
                <text x={NODE_WIDTH / 2} y={26} textAnchor="middle" className="arch-node-title">
                  {node.title}
                </text>
                <text x={NODE_WIDTH / 2} y={44} textAnchor="middle" className="arch-node-subtitle">
                  {node.subtitle}
                </text>
              </g>
            ))}
          </svg>
        </div>

        {/* Mobile fallback - plain button list instead of the SVG canvas */}
        <div className="arch-mobile-list">
          {visibleNodes.map((node) => (
            <button
              key={node.id}
              type="button"
              className={selectedId === node.id ? 'arch-mobile-selected' : ''}
              onClick={() => chooseNode(node.id)}
            >
              <span className="arch-legend-dot" style={{ background: statusColors[node.status] }} />
              {node.title}
            </button>
          ))}
        </div>

        {/* Detail panel - floats over the diagram so the canvas keeps full width */}
        {detailOpen && selected && (
          <aside className="arch-detail-panel" aria-live="polite">
            <button
              type="button"
              className="arch-detail-close"
              onClick={() => setDetailOpen(false)}
              aria-label="Detailansicht schließen"
            >
              ✕
            </button>
            <>
              <div className="arch-detail-header">
                <h3>{selected.title}</h3>
                <span>{selected.subtitle}</span>
              </div>
              <div className="arch-detail-meta">
                <span className="arch-badge" style={{ borderColor: statusColors[selected.status] }}>
                  {statusLabels[selected.status]}
                </span>
                <span className="arch-badge arch-badge-boundary">
                  {boundaryLabels[selected.boundary]}
                </span>
                <span className="arch-badge arch-badge-layer">{selected.layer}</span>
              </div>
              {!selectedVisible && (
                <p className="arch-detail-hint">
                  Nicht Teil der Ansicht „{architectureViews.find((v) => v.id === view)?.label}“ - andere Ansicht wählen, um die Position zu sehen.
                </p>
              )}
              <p className="arch-detail-description">{selected.description}</p>
              {selected.responsibilities.length > 0 && (
                <>
                  <h4>Zuständigkeiten</h4>
                  <ul>
                    {selected.responsibilities.map((r) => <li key={r}>{r}</li>)}
                  </ul>
                </>
              )}
              {selected.paths.length > 0 && (
                <div className="arch-detail-paths">
                  {selected.paths.map((path) => <code key={path}>{path}</code>)}
                </div>
              )}
              {renderRelationGroup('Incoming', incoming, 'in')}
              {renderRelationGroup('Outgoing', outgoing, 'out')}
              {renderRelationGroup('Influences', influences, 'out')}
              {renderRelationGroup('Depends on', dependsOn, 'in')}
            </>
          </aside>
        )}

        {!detailOpen && selected && (
          <button
            type="button"
            className="arch-detail-reopen"
            onClick={() => setDetailOpen(true)}
          >
            ℹ️ {selected.title}
          </button>
        )}
      </div>

      <div className="arch-stats-bar">
        <span>Quelle: implementierter Code und diese Session verifizierte Fakten</span>
        <span>
          {architectureNodes.length} Komponenten · {architectureEdges.length} Beziehungen · datengetrieben erweiterbar
        </span>
      </div>
    </div>
  );
}

export default ArchitectureMap;
