/**
 * Main layout component for BU MET Autograder
 * Provides consistent page structure with header, navigation, and footer
 */

import React, { useState } from 'react';
import { Box, Container, useMediaQuery } from '@mui/material';
import { styled, useTheme } from '@mui/material/styles';
import Header from './Header';
import Footer from './Footer';
import Navigation from './Navigation';

// Styled components
const LayoutRoot = styled(Box)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  minHeight: '100vh',
  backgroundColor: theme.palette.background.default,
}));

const LayoutContent = styled(Box)(({ theme, open, isMobile }) => ({
  display: 'flex',
  flex: '1 1 auto',
  paddingTop: 'var(--header-height)',
  [theme.breakpoints.up('md')]: {
    marginLeft: open ? 'var(--sidebar-width)' : 'var(--sidebar-collapsed-width)',
    width: open
      ? `calc(100% - var(--sidebar-width))`
      : `calc(100% - var(--sidebar-collapsed-width))`,
    transition: theme.transitions.create(['margin', 'width'], {
      easing: theme.transitions.easing.sharp,
      duration: theme.transitions.duration.leavingScreen,
    }),
  },
}));

const MainContainer = styled(Container)(({ theme }) => ({
  flexGrow: 1,
  padding: theme.spacing(3),
  [theme.breakpoints.down('sm')]: {
    padding: theme.spacing(2),
  },
}));

// Main layout component
export default function Layout({ children }) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [sidebarOpen, setSidebarOpen] = useState(!isMobile);

  // Toggle sidebar open/closed
  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  // Close sidebar on mobile when clicking outside
  const handleCloseSidebar = () => {
    if (isMobile) {
      setSidebarOpen(false);
    }
  };

  return (
    <LayoutRoot>
      <Header
        sidebarOpen={sidebarOpen}
        onSidebarToggle={toggleSidebar}
      />

      <Navigation
        open={sidebarOpen}
        onClose={handleCloseSidebar}
        variant={isMobile ? 'temporary' : 'permanent'}
      />

      <LayoutContent open={sidebarOpen} isMobile={isMobile}>
        <MainContainer maxWidth="xl">
          {children}
        </MainContainer>
      </LayoutContent>

      <Footer />
    </LayoutRoot>
  );
}