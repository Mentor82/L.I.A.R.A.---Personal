import { createContext } from 'react';

// Kept in its own file (no Provider/hook here) - react-refresh requires a
// file exporting a component to only export components, and the context
// object itself doesn't qualify as one.
export const ViewModeContext = createContext(null);
