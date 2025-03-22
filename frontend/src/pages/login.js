/**
 * Login page for BU MET Autograder
 * Handles OAuth authentication with Google and Microsoft
 */

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Image from 'next/image';
import {
  Box,
  Button,
  Card,
  CardContent,
  Container,
  Divider,
  Typography,
  Alert,
  Link as MuiLink,
  CircularProgress,
} from '@mui/material';
import { Google as GoogleIcon, Microsoft as MicrosoftIcon } from '@mui/icons-material';
import { styled } from '@mui/material/styles';
import { authService } from '../api';
import { ERROR_MESSAGES, APP_CONFIG } from '../config';
import Link from 'next/link';

// Styled components
const LoginContainer = styled(Container)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  minHeight: '100vh',
  padding: theme.spacing(3),
}));

const LoginCard = styled(Card)(({ theme }) => ({
  width: '100%',
  maxWidth: 450,
  borderRadius: theme.shape.borderRadius * 2,
  boxShadow: theme.shadows[3],
}));

const LogoContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  justifyContent: 'center',
  marginBottom: theme.spacing(3),
}));

const ProviderButton = styled(Button)(({ theme }) => ({
  width: '100%',
  padding: theme.spacing(1.5),
  marginBottom: theme.spacing(2),
  borderRadius: theme.shape.borderRadius,
  textTransform: 'none',
  fontWeight: 500,
}));

// Login page component
export default function Login() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Check if redirected with error parameter
  useEffect(() => {
    if (router.query.error) {
      setError(
        router.query.error === 'unauthorized'
          ? ERROR_MESSAGES.auth.unauthorized
          : ERROR_MESSAGES.auth.loginFailed
      );
    }
  }, [router.query]);

  // Handle Google OAuth login
  const handleGoogleLogin = async () => {
    setLoading(true);
    setError(null);

    try {
      // In a real implementation, this would redirect to Google OAuth flow
      // For now, we'll simulate by redirecting to callback URL
      window.location.href = '/api/auth/signin/google';
    } catch (err) {
      console.error('Google login error:', err);
      setError(ERROR_MESSAGES.auth.loginFailed);
      setLoading(false);
    }
  };

  // Handle Microsoft OAuth login
  const handleMicrosoftLogin = async () => {
    setLoading(true);
    setError(null);

    try {
      // In a real implementation, this would redirect to Microsoft OAuth flow
      window.location.href = '/api/auth/signin/microsoft';
    } catch (err) {
      console.error('Microsoft login error:', err);
      setError(ERROR_MESSAGES.auth.loginFailed);
      setLoading(false);
    }
  };

  return (
    <LoginContainer maxWidth="sm">
      <LogoContainer>
        <Image
          src="/images/bu-logo.png"
          alt="Boston University Logo"
          width={200}
          height={60}
          priority
        />
      </LogoContainer>

      <LoginCard>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h4" component="h1" align="center" gutterBottom>
            {APP_CONFIG.appName}
          </Typography>

          <Typography variant="body1" align="center" color="textSecondary" sx={{ mb: 4 }}>
            Sign in with your Boston University credentials to access the autograding platform.
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          )}

          <ProviderButton
            variant="outlined"
            startIcon={<GoogleIcon />}
            onClick={handleGoogleLogin}
            disabled={loading}
          >
            {loading ? <CircularProgress size={24} /> : 'Sign in with Google'}
          </ProviderButton>

          <ProviderButton
            variant="outlined"
            startIcon={<MicrosoftIcon />}
            onClick={handleMicrosoftLogin}
            disabled={loading}
          >
            {loading ? <CircularProgress size={24} /> : 'Sign in with Microsoft'}
          </ProviderButton>

          <Divider sx={{ my: 3 }} />

          <Typography variant="body2" align="center" color="textSecondary">
            By signing in, you agree to the{' '}
            <MuiLink component={Link} href="/terms" underline="hover">
              Terms of Service
            </MuiLink>{' '}
            and{' '}
            <MuiLink component={Link} href="/privacy" underline="hover">
              Privacy Policy
            </MuiLink>
          </Typography>
        </CardContent>
      </LoginCard>

      <Box mt={4} textAlign="center">
        <Typography variant="body2" color="textSecondary">
          Need help?{' '}
          <MuiLink
            href={`mailto:${APP_CONFIG.supportEmail}`}
            underline="hover"
          >
            Contact Support
          </MuiLink>
        </Typography>
      </Box>
    </LoginContainer>
  );
}