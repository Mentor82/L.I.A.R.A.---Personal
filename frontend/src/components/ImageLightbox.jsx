import { useEffect } from 'react';
import { createPortal } from 'react-dom';

// Full-size overlay for images shown small inline (chat plots, generated
// images) - click-to-enlarge without navigating away via window.open.
//
// Rendered via a portal straight into document.body: chat bubbles use
// backdrop-filter (the glass-blur effect), which - like transform/filter -
// creates a new containing block for `position: fixed` descendants. Without
// the portal, this overlay would be scoped to the bubble's box instead of
// the viewport, showing up mispositioned/invisible instead of as a proper
// full-screen overlay.
const ImageLightbox = ({ src, alt, onClose }) => {
  useEffect(() => {
    const handleKey = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [onClose]);

  return createPortal(
    <div className="image-lightbox-backdrop" onClick={onClose}>
      <button className="image-lightbox-close" onClick={onClose} title="Schließen">✕</button>
      <img
        src={src}
        alt={alt || 'Bild'}
        className="image-lightbox-img"
        onClick={(e) => e.stopPropagation()}
      />
    </div>,
    document.body
  );
};

export default ImageLightbox;
