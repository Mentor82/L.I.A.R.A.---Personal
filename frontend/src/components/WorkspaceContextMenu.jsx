import { useEffect, useRef } from 'react';

/**
 * Context menu displayed on right-click of a file or folder in the Workspace file tree.
 */
export default function WorkspaceContextMenu({ menu, onClose, handlers }) {
  const menuRef = useRef(null);

  // Close on any click outside the menu, or on Escape - the two standard
  // ways every native/OS context menu dismisses itself.
  useEffect(() => {
    const handleClick = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) onClose();
    };
    const handleKey = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('mousedown', handleClick);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handleClick);
      document.removeEventListener('keydown', handleKey);
    };
  }, [onClose]);

  const { node, x, y } = menu;
  const isFolder = node.type === 'folder';

  // Rough clamp against an assumed max menu footprint - exact size isn't
  // known until after render, but this keeps it on-screen in the common
  // case (right-clicking near the sidebar's own right/bottom edge).
  const left = Math.min(x, window.innerWidth - 200);
  const top = Math.min(y, window.innerHeight - 260);

  const copyPath = async () => {
    try {
      await navigator.clipboard.writeText(node.path);
    } catch {
      // Clipboard API can be unavailable (insecure context, permissions) -
      // silently no-op rather than surfacing an error for a convenience action.
    }
    onClose();
  };

  const run = (fn) => { fn(); onClose(); };

  return (
    <div className="workspace-context-menu" style={{ left, top }} ref={menuRef}>
      {!isFolder && (
        <button onClick={() => run(() => handlers.onOpenFile(node.path))}>📄 Öffnen</button>
      )}
      {isFolder && (
        <>
          <button onClick={() => run(() => handlers.onNewFileHere(node.path))}>➕ Neue Datei hier</button>
          <button onClick={() => run(() => handlers.onNewFolderHere(node.path))}>📁 Neuer Ordner hier</button>
          <button onClick={() => run(() => handlers.onUploadHere(node.path))}>⬆️ Hierher hochladen</button>
        </>
      )}
      {!isFolder && (
        <button onClick={() => run(() => handlers.onToggleContext(node.path))}>
          💬 {node.selected_for_context ? 'Aus Chat-Kontext entfernen' : 'Zu Chat-Kontext hinzufügen'}
        </button>
      )}
      {!isFolder && (
        <button onClick={() => run(() => handlers.onDownload(node.path))}>⬇️ Herunterladen</button>
      )}
      <button onClick={() => run(() => handlers.onRename(node.path, node.name))}>✏️ Umbenennen</button>
      <button onClick={copyPath}>📋 Pfad kopieren</button>
      <div className="workspace-context-menu-divider" />
      <button
        className="danger"
        onClick={() => run(() => handlers.onDelete(node.path, isFolder ? 'folder' : 'file'))}
      >🗑️ Löschen</button>
    </div>
  );
}
