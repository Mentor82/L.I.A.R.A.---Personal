import './ComplianceBadges.css';

function ComplianceBadges() {
  const badges = [
    {
      icon: '🛡️',
      title: '100% Local Processing',
      description: 'No cloud dependencies',
      status: 'verified'
    },
    {
      icon: '🤖',
      title: 'AI Transparency Ready',
      description: 'EU AI Act compliant',
      status: 'verified'
    },
    {
      icon: '🌍',
      title: 'GDPR / UK GDPR / CCPA',
      description: 'Multi-jurisdictional compliance',
      status: 'verified'
    },
    {
      icon: '🔓',
      title: 'Open Source Verified',
      description: 'Auditable codebase',
      status: 'verified'
    },
    {
      icon: '🔒',
      title: 'Privacy by Design',
      description: 'Built-in privacy features',
      status: 'verified'
    },
    {
      icon: '🚫',
      title: 'No Third-Party Tracking',
      description: 'Zero surveillance',
      status: 'verified'
    }
  ];

  return (
    <div className="compliance-badges-container">
      <div className="compliance-badges-header">
        <h3>🏅 Compliance & Privacy Certifications</h3>
        <p>LIARA meets international standards for privacy, AI transparency, and data protection</p>
      </div>
      <div className="compliance-badges-grid">
        {badges.map((badge, index) => (
          <div key={index} className="compliance-badge">
            <div className="compliance-badge-icon">{badge.icon}</div>
            <div className="compliance-badge-content">
              <h4>{badge.title}</h4>
              <p>{badge.description}</p>
              <span className={`compliance-badge-status ${badge.status}`}>
                {badge.status === 'verified' && '✓ Verified'}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ComplianceBadges;
