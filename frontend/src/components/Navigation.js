// src/components/Navigation.js
import React, { useState } from 'react';
import { useRouter } from 'next/router';
import {
  Box,
  Collapse,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  Tooltip,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  Dashboard as DashboardIcon,
  School as SchoolIcon,
  Assignment as AssignmentIcon,
  RuleFolder as RubricIcon,
  Assessment as GradingIcon,
  Description as MaterialsIcon,
  People as InstructorsIcon,
  Upload as UploadIcon,
  Settings as SettingsIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
} from '@mui/icons-material';

// Styled components
const DrawerContent = styled(Box)(({ theme }) => ({
  width: 'var(--sidebar-width)',
  marginTop: 'var(--header-height)',
  overflowX: 'hidden',
  [theme.breakpoints.down('md')]: {
    width: 'var(--sidebar-width)', // Keep width on mobile
  },
}));

const StyledListItemButton = styled(ListItemButton, {
  shouldForwardProp: (prop) => prop !== '$active'
})(({ theme, $active }) => ({
  borderRadius: theme.shape.borderRadius,
  margin: theme.spacing(0.5, 1),
  color: $active ? theme.palette.primary.main : theme.palette.text.primary,
  backgroundColor: $active ? `${theme.palette.primary.main}10` : 'transparent',
  '&:hover': {
    backgroundColor: $active
      ? `${theme.palette.primary.main}20`
      : theme.palette.action.hover,
  },
}));

const StyledListItemIcon = styled(ListItemIcon, {
    shouldForwardProp: (prop) => prop !== '$active'
})(({ theme, $active }) => ({
  color: $active ? theme.palette.primary.main : theme.palette.text.primary,
  minWidth: 40,
}));

// Navigation component
export default function Navigation({ open, onClose, variant = 'permanent' }) {
  const router = useRouter();
  const [expandedItems, setExpandedItems] = useState({
    course: true,
  });

    const isActivePath = (path) => {
        return router.pathname === path || router.pathname.startsWith(path + "/");
    };

  const toggleExpand = (section) => {
    setExpandedItems((prevExpandedItems) => ({
      ...prevExpandedItems,
      [section]: !prevExpandedItems[section],
    }));
  };

    const navigateTo = (path) => {
      if (router.pathname !== path) {
        router.push(path);
      }
      if (variant === 'temporary') {
        onClose();
      }
    };

  const navigationItems = [
    {
      text: 'Dashboard',
      icon: <DashboardIcon />,
      path: '/courses',
    },
    {
      text: 'Courses',
      icon: <SchoolIcon />,
      path: '/courses',
      expandable: true,
      section: 'course',
      subItems: [
        {
          text: 'Assignments',
          icon: <AssignmentIcon />,
          path: '/assignments',
        },
        {
          text: 'Rubrics',
          icon: <RubricIcon />,
          path: '/rubrics',
        },
        {
          text: 'Materials',
          icon: <MaterialsIcon />,
          path: '/materials',
        },
        {
          text: 'Grading',
          icon: <GradingIcon />,
          path: '/grading',
        },
        {
          text: 'Instructors',
          icon: <InstructorsIcon />,
          path: '/instructors',
        },
      ],
    },
    {
      text: 'Manual Submission',
      icon: <UploadIcon />,
      path: '/manual_submission',
    },
    {
      text: 'Settings',
      icon: <SettingsIcon />,
      path: '/settings',
    },
  ];

  const drawerContent = (
    <DrawerContent>
      <List component="nav">
        {navigationItems.map((item) => (
          <React.Fragment key={item.text}>
            <ListItem disablePadding>
              {item.expandable ? (
                <StyledListItemButton
                  $active={isActivePath(item.path)}
                  onClick={() => toggleExpand(item.section)}
                >
                  <StyledListItemIcon $active={isActivePath(item.path)}>
                    {item.icon}
                  </StyledListItemIcon>
                  <ListItemText primary={item.text} />
                  {expandedItems[item.section] ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                </StyledListItemButton>
              ) : (
                <StyledListItemButton
                  $active={isActivePath(item.path)}
                  onClick={() => navigateTo(item.path)}
                >
                  <StyledListItemIcon $active={isActivePath(item.path)}>
                    {item.icon}
                  </StyledListItemIcon>
                  <ListItemText primary={item.text} />
                </StyledListItemButton>
              )}
            </ListItem>

            {item.expandable && item.subItems && (
              <Collapse
                in={expandedItems[item.section]}
                timeout="auto"
                unmountOnExit
              >
                <List component="div" disablePadding>
                  {item.subItems.map((subItem) => (
                    <ListItem key={subItem.text} disablePadding>
                      <StyledListItemButton
                        $active={isActivePath(subItem.path)}
                        onClick={() => navigateTo(subItem.path)}
                        sx={{ pl: 4 }}
                      >
                        <StyledListItemIcon $active={isActivePath(subItem.path)}>
                          {subItem.icon}
                        </StyledListItemIcon>
                        <ListItemText primary={subItem.text} />
                      </StyledListItemButton>
                    </ListItem>
                  ))}
                </List>
              </Collapse>
            )}
          </React.Fragment>
        ))}
      </List>

      <Divider sx={{ my: 2 }} />

      <Box sx={{ p: 2, textAlign: 'center' }}>
        <img
          src="/images/bu-met-logo.png"
          alt="BU MET Logo"
          width={120}
          style={{ opacity: 0.7 }}
        />
      </Box>
    </DrawerContent>
  );

  return variant === 'temporary' ? (
     <Drawer
      variant="temporary"
      open={open}
      onClose={onClose}
      ModalProps={{
        keepMounted: true,
      }}
      sx={{
        display: { xs: 'block', md: 'none' },
        '& .MuiDrawer-paper': {
          width: 'var(--sidebar-width)',
        },
      }}
    >
      {drawerContent}
    </Drawer>
  ) : (
    <Drawer
      variant="permanent"
      open={open}
      sx={{
        display: { xs: 'none', md: 'block' },
        '& .MuiDrawer-paper': {
          width: open ? 'var(--sidebar-width)' : 0, // Set width to 0 when closed
          transition: (theme) =>
            theme.transitions.create('width', { // Animate only the width
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.enteringScreen,
            }),
          overflowX: 'hidden',
          transitionProperty: 'width', // Specify transition property
        },
      }}
    >
      {drawerContent}
    </Drawer>
  );
}