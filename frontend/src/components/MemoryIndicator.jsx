import React from 'react';
import { Brain, Sparkles } from 'lucide-react';
import './MemoryIndicator.css';

/**
 * Memory Context Indicator
 * Zeigt an wenn Liara sich an frühere Gespräche erinnert (Neo4j Context Injection)
 */

export const MemoryIndicator = ({ memoryContext }) => {
  if (!memoryContext || memoryContext.length === 0) {
    return null;
  }

  const conceptCount = memoryContext.length;
  const totalMentions = memoryContext.reduce((sum, item) => sum + (item.mentions || 0), 0);
  const avgSimilarity = memoryContext.reduce((sum, item) => sum + (item.similarity || 0), 0) / conceptCount;

  return (
    <div className="memory-indicator">
      <div className="memory-badge">
        <Brain className="memory-icon" size={16} />
        <span className="memory-text">
          Liara erinnert sich
        </span>
        <Sparkles className="sparkle-icon" size={14} />
      </div>
      
      <div className="memory-details">
        <div className="memory-stat">
          <span className="stat-label">Konzepte:</span>
          <span className="stat-value">{conceptCount}</span>
        </div>
        <div className="memory-stat">
          <span className="stat-label">Erwähnungen:</span>
          <span className="stat-value">{totalMentions}x</span>
        </div>
        <div className="memory-stat">
          <span className="stat-label">Relevanz:</span>
          <span className="stat-value">{(avgSimilarity * 100).toFixed(0)}%</span>
        </div>
      </div>

      <div className="memory-concepts">
        {memoryContext.slice(0, 3).map((item, idx) => (
          <div key={idx} className="memory-concept">
            <div className="concept-header">
              <span className="concept-text">{item.concept}</span>
              <span className="concept-similarity">{(item.similarity * 100).toFixed(0)}%</span>
            </div>
            {item.related_messages && item.related_messages.length > 0 && (
              <div className="concept-preview">
                "{item.related_messages[0].content.substring(0, 80)}..."
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

/**
 * Compact Memory Badge (für Input-Area)
 */
export const MemoryBadge = ({ memoryContext }) => {
  if (!memoryContext || memoryContext.length === 0) {
    return null;
  }

  const conceptCount = memoryContext.length;

  return (
    <div className="memory-badge-compact">
      <Brain size={14} className="badge-icon" />
      <span className="badge-text">{conceptCount} Erinnerung{conceptCount > 1 ? 'en' : ''}</span>
    </div>
  );
};
