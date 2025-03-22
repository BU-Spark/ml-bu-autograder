/**
 * Header component for BU MET Autograder
 * Contains app bar, menu toggle, and user actions
 */

import React, { useState } from 'react';
import { useRouter } from 'next/router';
import {
  AppBar,
  Avatar,
  Badge,
  Box,
  Button,
  IconButton,
  Menu,
  MenuItem,
  Toolbar,
  Tooltip,
  Typography,
  Divider,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  Menu as MenuIcon,
  Notifications as NotificationsIcon,
  Settings as SettingsIcon,
  Logout as LogoutIcon,
  Person as PersonIcon,
} from '@mui/icons-material';
import { useUser } from '../api';
import ThemeToggle from './ThemeToggle';
import { APP_CONFIG } from '../config';

// Styled components
const StyledAppBar = styled(AppBar)(({ theme }) => ({
  height: 'var(--header-height)',
  backgroundColor: theme.palette.background.paper,
  color: theme.palette.text.primary,
  boxShadow: theme.shadows[2],
  zIndex: theme.zIndex.drawer + 1,
}));

const StyledToolbar = styled(Toolbar)({
  display: 'flex',
  justifyContent: 'space-between',
  height: 'var(--header-height)',
  padding: '0 16px',
});

const LogoContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  '& img': {
    height: 40,
  },
  [theme.breakpoints.down('sm')]: {
    '& .app-name': {
      display: 'none',
    },
  },
}));

const ActionContainer = styled(Box)({
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
});

// Header component
export default function Header({ sidebarOpen, onSidebarToggle }) {
  const router = useRouter();
  const { user, isLoading } = useUser();
  const [anchorEl, setAnchorEl] = useState(null);

  const handleMenuOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = async () => {
    handleMenuClose();
    // In a real implementation, this would call the logout API
    router.push('/login');
  };

  const handleSettings = () => {
    handleMenuClose();
    router.push('/settings');
  };

  const handleProfile = () => {
    handleMenuClose();
    router.push('/profile');
  };

  const handleNotifications = () => {
    // Handle notifications click
    console.log('Notifications clicked');
  };

  return (
    <StyledAppBar position="fixed">
      <StyledToolbar>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            onClick={onSidebarToggle}
            edge="start"
            sx={{ mr: 2 }}
          >
            <MenuIcon />
          </IconButton>

          <LogoContainer>
            <img
              src="/images/bu-logo.png"
              alt="Boston University Logo"
              height={40}
            />
            <Typography
              variant="h6"
              component="div"
              sx={{ ml: 2 }}
              className="app-name"
            >
              {APP_CONFIG.appName}
            </Typography>
          </LogoContainer>
        </Box>

        <ActionContainer>
          <ThemeToggle />

          <Tooltip title="Notifications">
            <IconButton color="inherit" onClick={handleNotifications}>
              <Badge badgeContent={3} color="error">
                <NotificationsIcon />
              </Badge>
            </IconButton>
          </Tooltip>

          <Box sx={{ ml: 2 }}>
            {isLoading ? (
              <Button
                variant="outlined"
                color="inherit"
                onClick={() => router.push('/login')}
              >
                Sign In
              </Button>
            ) : (
              <>
                <Tooltip title="Account">
                  <IconButton
                    onClick={handleMenuOpen}
                    size="small"
                    aria-controls={Boolean(anchorEl) ? 'account-menu' : undefined}
                    aria-haspopup="true"
                    aria-expanded={Boolean(anchorEl) ? 'true' : undefined}
                  >
                    {user?.first_name ? (
                      <Avatar
                        alt={`${user.first_name} ${user.last_name || ''}`}
                        src="/images/avatar-placeholder.png"
                        sx={{ width: 32, height: 32 }}
                      />
                    ) : (
                      <Avatar sx={{ width: 32, height: 32 }}>
                        <PersonIcon />
                      </Avatar>
                    )}
                  </IconButton>
                </Tooltip>

                <Menu
                  id="account-menu"
                  anchorEl={anchorEl}
                  open={Boolean(anchorEl)}
                  onClose={handleMenuClose}
                  transformOrigin={{ horizontal: 'right', vertical: 'top' }}
                  anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
                  PaperProps={{
                    elevation: 2,
                    sx: {
                      minWidth: 200,
                      mt: 1.5,
                      '& .MuiMenuItem-root': {
                        px: 2,
                        py: 1,
                      },
                    },
                  }}
                >
                  {user && (
                    <Box sx={{ px: 2, py: 1.5 }}>
                      <Typography variant="subtitle1" fontWeight="bold">
                        {user.first_name ? `${user.first_name} ${user.last_name || ''}` : user.user_email}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {user.user_email}
                      </Typography>
                    </Box>
                  )}

                  <Divider />

                  <MenuItem onClick={handleProfile}>
                    <PersonIcon fontSize="small" sx={{ mr: 2 }} />
                    Profile
                  </MenuItem>

                  <MenuItem onClick={handleSettings}>
                    <SettingsIcon fontSize="small" sx={{ mr: 2 }} />
                    Settings
                  </MenuItem>

                  <Divider />

                  <MenuItem onClick={handleLogout}>
                    <LogoutIcon fontSize="small" sx={{ mr: 2 }} />
                    Logout
                  </MenuItem>
                </Menu>
              </>
            )}
          </Box>
        </ActionContainer>
      </StyledToolbar>
    </StyledAppBar>
  );
}