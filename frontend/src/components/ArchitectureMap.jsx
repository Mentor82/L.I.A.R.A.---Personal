import { useMemo, useState } from 'react';
import {
  architectureEdges,
  architectureNodes,
  architectureViews,
  boundaryLabels,
  statusLabels,
} from '../data/architectureData';
import './ArchitectureMap.css';

const NODE_WIDTH = 160;
const NODE_HEIGHT = 64;
const BOUNDARY_PADDING = 55;

const statusColors = {
  implemented: '#3ddc84',
  'in-progress': '#f2bd58',
  planned: '#8b93a7',
};

const kindColors = {
  data: '#62dff5',
  decision: '#f2bd58',
  mutation: '#ff7a9c',
  validation: '#77e6ae',
};

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

  // The local/self-hosted perimeter is drawn from ALL local-boundary nodes'
  // positions (not just the ones visible in the current view), so it reads
  // as a stable backdrop across tabs instead of jumping around.
  const boundaryRect = useMemo(() => {
    const localNodes = architectureNodes.filter((node) => node.boundary === 'local');
    const minX = Math.min(...localNodes.map((n) => n.x)) - NODE_WIDTH / 2 - BOUNDARY_PADDING;
    const maxX = Math.max(...localNodes.map((n) => n.x)) + NODE_WIDTH / 2 + BOUNDARY_PADDING;
    const minY = Math.min(...localNodes.map((n) => n.y)) - NODE_HEIGHT / 2 - BOUNDARY_PADDING;
    const maxY = Math.max(...localNodes.map((n) => n.y)) + NODE_HEIGHT / 2 + BOUNDARY_PADDING;
    return { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
  }, []);

  const searchMatches = useMemo(() => {
    if (!query.trim()) return [];
    const q = query.trim().toLowerCase();
    return architectureNodes.filter((node) =>
      `${node.title} ${node.subtitle} ${node.layer}`.toLowerCase().includes(q)
    );
  }, [query]);

  const selected = nodesById[selectedId];
  const selectedVisible = selected && selected.views.includes(view);

  const relatedEdges = useMemo(() => {
    if (!selected) return [];
    return architectureEdges.filter((e) => e.from === selected.id || e.to === selected.id);
  }, [selected]);

  const chooseNode = (id) => {
    setSelectedId(id);
    setDetailOpen(true);
    const node = nodesById[id];
    if (node && !node.views.includes(view)) {
      setView(node.views[0]);
    }
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
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Komponente suchen…"
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
        <span className="arch-legend-title">Status:</span>
        {Object.entries(statusLabels).map(([key, label]) => (
          <span key={key} className="arch-legend-item">
            <span className="arch-legend-dot" style={{ background: statusColors[key] }} />
            {label}
          </span>
        ))}
      </div>

      <div className="arch-workspace">
        <div className="arch-diagram" aria-label={`${architectureViews.find((v) => v.id === view)?.label} Diagramm`}>
          <svg viewBox="0 0 1560 620" role="img" aria-labelledby="architecture-title">
            <title id="architecture-title">Architektur-Diagramm: {view}</title>

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

            {/* Edges */}
            {visibleEdges.map((edge) => {
              const from = nodesById[edge.from];
              const to = nodesById[edge.to];
              if (!from || !to) return null;
              const key = edgeKey(edge);
              const midX = (from.x + to.x) / 2;
              const midY = (from.y + to.y) / 2;
              return (
                <g key={key} className="arch-edge-group">
                  <line
                    x1={from.x}
                    y1={from.y}
                    x2={to.x}
                    y2={to.y}
                    stroke={kindColors[edge.kind] || '#8b93a7'}
                    strokeWidth={2}
                    strokeDasharray={edge.crossesBoundary ? '6 5' : undefined}
                    opacity={0.85}
                  />
                  <rect
                    x={midX - edge.label.length * 3.4 - 6}
                    y={midY - 10}
                    width={edge.label.length * 6.8 + 12}
                    height={18}
                    className="arch-edge-label-bg"
                  />
                  <text x={midX} y={midY + 4} textAnchor="middle" className="arch-edge-label">
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
              {relatedEdges.length > 0 && (
                <>
                  <h4>Beziehungen</h4>
                  <div className="arch-relations">
                    {relatedEdges.map((edge) => {
                      const other = edge.from === selected.id ? edge.to : edge.from;
                      const otherNode = nodesById[other];
                      const direction = edge.from === selected.id ? '→' : '←';
                      return (
                        <button key={edgeKey(edge)} type="button" onClick={() => chooseNode(other)}>
                          {direction} {otherNode?.title} <small>{edge.label}</small>
                        </button>
                      );
                    })}
                  </div>
                </>
              )}
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
    </div>
  );
}

export default ArchitectureMap;
