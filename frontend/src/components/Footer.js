/**
 * Footer component for BU MET Autograder
 * Displays copyright information and useful links
 */

import React from 'react';
import { Box, Container, Divider, Grid, Link, Typography } from '@mui/material';
import { styled } from '@mui/material/styles';
import { APP_CONFIG } from '../config/config';

// Styled components
const FooterRoot = styled(Box)(({ theme }) => ({
  backgroundColor: theme.palette.background.paper,
  borderTop: `1px solid ${theme.palette.divider}`,
  padding: theme.spacing(3, 0),
  [theme.breakpoints.down('sm')]: {
    padding: theme.spacing(2, 0),
  },
}));

const FooterLink = styled(Link)(({ theme }) => ({
  color: theme.palette.text.secondary,
  '&:hover': {
    color: theme.palette.primary.main,
  },
}));

// Footer component
export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <FooterRoot component="footer">
      <Container maxWidth="lg">
        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <Typography variant="h6" color="text.primary" gutterBottom>
              {APP_CONFIG.appName}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              An AI-based autograding tool for BU MET courses.
            </Typography>
          </Grid>

          <Grid item xs={12} md={4}>
            <Typography variant="h6" color="text.primary" gutterBottom>
              Resources
            </Typography>
            <Box>
              <FooterLink href="/help" variant="body2">
                Help Center
              </FooterLink>
            </Box>
            <Box>
              <FooterLink href="/documentation" variant="body2">
                Documentation
              </FooterLink>
            </Box>
            <Box>
              <FooterLink href="/faq" variant="body2">
                FAQ
              </FooterLink>
            </Box>
          </Grid>

          <Grid item xs={12} md={4}>
            <Typography variant="h6" color="text.primary" gutterBottom>
              Legal
            </Typography>
            <Box>
              <FooterLink href="/terms" variant="body2">
                Terms of Service
              </FooterLink>
            </Box>
            <Box>
              <FooterLink href="/privacy" variant="body2">
                Privacy Policy
              </FooterLink>
            </Box>
          </Grid>
        </Grid>

        <Divider sx={{ my: 2 }} />

        <Box sx={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap' }}>
          <Typography variant="body2" color="text.secondary">
            © {currentYear} Boston University Metropolitan College. All rights reserved.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            <FooterLink href={`mailto:${APP_CONFIG.supportEmail}`}>
              Contact Support
            </FooterLink>
          </Typography>
        </Box>
      </Container>
    </FooterRoot>
  );
}