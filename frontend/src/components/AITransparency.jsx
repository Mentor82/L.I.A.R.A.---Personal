import { useState } from 'react';
import './AITransparency.css';

function AITransparency() {
  const [expandedSection, setExpandedSection] = useState(null);

  const toggleSection = (section) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  return (
    <div className="ai-transparency-container">
      {/* Main Disclosure */}
      <div className="ai-disclosure-banner">
        <div className="ai-disclosure-icon">⚠️</div>
        <div className="ai-disclosure-content">
          <h3>This is an AI System / Dies ist ein KI-System</h3>
          <p>
            <strong>LIARA is an Artificial Intelligence System.</strong> All responses are generated 
            by machine learning algorithms. Please read our AI Transparency Statement for details.
          </p>
          <p>
            <strong>LIARA ist ein künstliches Intelligenzsystem.</strong> Alle Antworten werden 
            durch maschinelle Lernalgorithmen erzeugt. Bitte lesen Sie unsere KI-Transparenzerklärung.
          </p>
        </div>
      </div>

      {/* EU AI Act Classification */}
      <div className="ai-risk-classification">
        <div className="risk-badge minimal-risk">
          <span className="risk-icon">✓</span>
          <span className="risk-label">EU AI Act: Minimal Risk</span>
        </div>
        <p>
          LIARA is classified as a <strong>minimal risk AI system</strong> under the EU AI Act 
          because it does not make high-risk decisions and operates with full transparency.
        </p>
      </div>

      {/* How AI Works */}
      <div className="ai-explainability-section">
        <h3>🧠 How LIARA's AI Works</h3>
        
        <div className="ai-component-accordion">
          {/* LLM Section */}
          <div className={`ai-component ${expandedSection === 'llm' ? 'expanded' : ''}`}>
            <button className="ai-component-header" onClick={() => toggleSection('llm')}>
              <span className="component-icon">🤖</span>
              <span className="component-title">Large Language Models (LLMs)</span>
              <span className="expand-icon">{expandedSection === 'llm' ? '▼' : '▶'}</span>
            </button>
            {expandedSection === 'llm' && (
              <div className="ai-component-content">
                <div className="component-detail">
                  <strong>Technology:</strong> Ollama (local inference)
                </div>
                <div className="component-detail">
                  <strong>Models:</strong> Mistral, Llama, Qwen, Phi (user-selectable)
                </div>
                <div className="component-detail">
                  <strong>Purpose:</strong> Text generation, conversation, reasoning
                </div>
                <div className="component-detail">
                  <strong>How it works:</strong> Transformer-based neural networks predict the most 
                  likely next words based on training data and conversation context.
                </div>
                <div className="component-limitations">
                  <strong>Limitations:</strong>
                  <ul>
                    <li>May produce factually incorrect information ("hallucinations")</li>
                    <li>Limited by training data cutoff (typically 2023 or earlier)</li>
                    <li>May reflect biases present in training data</li>
                  </ul>
                </div>
              </div>
            )}
          </div>

          {/* Embeddings Section */}
          <div className={`ai-component ${expandedSection === 'embeddings' ? 'expanded' : ''}`}>
            <button className="ai-component-header" onClick={() => toggleSection('embeddings')}>
              <span className="component-icon">🧬</span>
              <span className="component-title">Semantic Memory (Embeddings)</span>
              <span className="expand-icon">{expandedSection === 'embeddings' ? '▼' : '▶'}</span>
            </button>
            {expandedSection === 'embeddings' && (
              <div className="ai-component-content">
                <div className="component-detail">
                  <strong>Technology:</strong> sentence-transformers (all-MiniLM-L6-v2)
                </div>
                <div className="component-detail">
                  <strong>Purpose:</strong> Long-term memory, similarity search
                </div>
                <div className="component-detail">
                  <strong>How it works:</strong> Converts text to 768-dimensional vectors that capture 
                  semantic meaning, stored in Neo4j graph database.
                </div>
                <div className="component-detail">
                  <strong>Consent Required:</strong> ✅ Must be explicitly enabled
                </div>
                <div className="component-limitations">
                  <strong>Limitations:</strong>
                  <ul>
                    <li>Associative memory, not perfect recall</li>
                    <li>May retrieve irrelevant memories if embeddings are similar</li>
                  </ul>
                </div>
              </div>
            )}
          </div>

          {/* Sentiment Section */}
          <div className={`ai-component ${expandedSection === 'sentiment' ? 'expanded' : ''}`}>
            <button className="ai-component-header" onClick={() => toggleSection('sentiment')}>
              <span className="component-icon">😊</span>
              <span className="component-title">Sentiment Analysis</span>
              <span className="expand-icon">{expandedSection === 'sentiment' ? '▼' : '▶'}</span>
            </button>
            {expandedSection === 'sentiment' && (
              <div className="ai-component-content">
                <div className="component-detail">
                  <strong>Technology:</strong> transformers (DistilBERT)
                </div>
                <div className="component-detail">
                  <strong>Purpose:</strong> Detect emotional tone in conversations
                </div>
                <div className="component-detail">
                  <strong>How it works:</strong> Classifies messages into Positive, Negative, Neutral 
                  with confidence scores.
                </div>
                <div className="component-detail">
                  <strong>Consent Required:</strong> ✅ Must be explicitly enabled
                </div>
                <div className="component-limitations">
                  <strong>Limitations:</strong>
                  <ul>
                    <li>May misclassify sarcasm or complex emotions</li>
                    <li>Based on text only, cannot see facial expressions</li>
                  </ul>
                </div>
              </div>
            )}
          </div>

          {/* Image Generation Section */}
          <div className={`ai-component ${expandedSection === 'images' ? 'expanded' : ''}`}>
            <button className="ai-component-header" onClick={() => toggleSection('images')}>
              <span className="component-icon">🎨</span>
              <span className="component-title">Image Generation (Optional)</span>
              <span className="expand-icon">{expandedSection === 'images' ? '▼' : '▶'}</span>
            </button>
            {expandedSection === 'images' && (
              <div className="ai-component-content">
                <div className="component-detail">
                  <strong>Technology:</strong> Stable Diffusion (local model)
                </div>
                <div className="component-detail">
                  <strong>Purpose:</strong> Generate images from text prompts
                </div>
                <div className="component-detail">
                  <strong>How it works:</strong> Diffusion model iteratively denoises random noise 
                  into images matching text prompts.
                </div>
                <div className="component-detail">
                  <strong>Optional Feature:</strong> Must be enabled in configuration
                </div>
                <div className="component-limitations">
                  <strong>Limitations:</strong>
                  <ul>
                    <li>May produce unexpected or distorted results</li>
                    <li>Cannot guarantee specific details</li>
                    <li>Requires significant GPU resources</li>
                  </ul>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* No Manipulation */}
      <div className="ai-ethics-section">
        <h3>🛡️ Ethical Safeguards</h3>
        <div className="ethics-grid">
          <div className="ethics-item">
            <span className="ethics-icon">✓</span>
            <div>
              <strong>No Dark Patterns</strong>
              <p>No manipulative UI design to trick users</p>
            </div>
          </div>
          <div className="ethics-item">
            <span className="ethics-icon">✓</span>
            <div>
              <strong>No Emotional Manipulation</strong>
              <p>No exploitation of vulnerabilities</p>
            </div>
          </div>
          <div className="ethics-item">
            <span className="ethics-icon">✓</span>
            <div>
              <strong>Clear AI Disclosure</strong>
              <p>Always identified as AI, never impersonates humans</p>
            </div>
          </div>
          <div className="ethics-item">
            <span className="ethics-icon">✓</span>
            <div>
              <strong>User Control</strong>
              <p>Full control over all AI features, can disable anytime</p>
            </div>
          </div>
        </div>
      </div>

      {/* AI-Generated Content Label */}
      <div className="ai-content-label-example">
        <h4>AI-Generated Content Labeling</h4>
        <p>All LIARA responses include a clear indicator:</p>
        <div className="content-label-demo">
          <div className="demo-message">
            This is an example AI-generated response from LIARA.
          </div>
          <div className="demo-footer">
            💬 AI-Generated Response
          </div>
        </div>
      </div>

      {/* Learn More */}
      <div className="ai-transparency-footer">
        <p>
          For detailed information about how LIARA works, please read our{' '}
          <a href="/docs/AI_TRANSPARENCY_STATEMENT.md" target="_blank" rel="noopener noreferrer">
            AI Transparency Statement
          </a>
        </p>
      </div>
    </div>
  );
}

export default AITransparency;
