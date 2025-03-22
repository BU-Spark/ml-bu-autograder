/**
 * Theme context for managing light/dark mode throughout the application
 * Provides a theme toggle and persists user preference
 */

import React, { createContext, useState, useContext, useEffect } from 'react';
import { ThemeProvider as MUIThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { createAppTheme } from '../theme/theme';
import { APP_CONFIG } from '../config/config';

// Create the context
const ThemeContext = createContext({
  mode: 'light',
  toggleTheme: () => {},
});

// Custom hook to use the theme context
export const useTheme = () => useContext(ThemeContext);

// Theme provider component
export const ThemeProvider = ({ children }) => {
  // Try to get the saved theme from localStorage, fall back to default
  const [mode, setMode] = useState(() => {
    // Check if we're in the browser environment
    if (typeof window !== 'undefined') {
      const savedMode = localStorage.getItem('themeMode');
      return savedMode || APP_CONFIG.defaultTheme;
    }
    return APP_CONFIG.defaultTheme;
  });

  // Create the MUI theme based on current mode
  const theme = createAppTheme(mode);

  // Function to toggle between light and dark mode
  const toggleTheme = () => {
    const newMode = mode === 'light' ? 'dark' : 'light';
    setMode(newMode);
    // Save to localStorage for persistence
    if (typeof window !== 'undefined') {
      localStorage.setItem('themeMode', newMode);
    }
  };

  // Effect to handle system preference changes
  useEffect(() => {
    // Skip on server-side rendering
    if (typeof window === 'undefined') return;

    // Check if user has a saved preference
    const savedMode = localStorage.getItem('themeMode');
    if (savedMode) return; // User has explicit preference, no need to sync with system

    // If no saved preference, listen to system preference
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    // Set initial theme based on system preference
    if (!savedMode) {
      setMode(mediaQuery.matches ? 'dark' : 'light');
    }

    // Update theme when system preference changes
    const handleChange = (e) => {
      if (!localStorage.getItem('themeMode')) { // Only if user hasn't set explicit preference
        setMode(e.matches ? 'dark' : 'light');
      }
    };

    // Add listener for preference changes
    mediaQuery.addEventListener('change', handleChange);

    // Clean up
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  // Context value to be provided
  const contextValue = {
    mode,
    toggleTheme,
  };

  return (
    <ThemeContext.Provider value={contextValue}>
      <MUIThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </MUIThemeProvider>
    </ThemeContext.Provider>
  );
};

export default ThemeProvider;