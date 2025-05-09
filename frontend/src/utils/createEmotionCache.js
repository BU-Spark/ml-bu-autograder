/**
 * Utility to create an Emotion cache for Material UI styling
 * This helps avoid CSS injection order conflicts, especially with SSR
 */

import createCache from '@emotion/cache';

const isBrowser = typeof document !== 'undefined';

// Function to create a custom Emotion cache
export default function createEmotionCache() {
  // On the client side, Create a new cache with a 'prepend' key insertion to ensure MUI styles are injected first
  // This helps prevent CSS specificity issues and ensures MUI styles take precedence
  return createCache({
    key: 'mui',
    prepend: true,
    // Prevents style duplication in SSR scenarios
    container: isBrowser ? document.head : undefined,
  });
}