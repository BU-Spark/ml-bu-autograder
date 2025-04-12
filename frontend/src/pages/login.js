/**
 * Login page OR OAuth Callback Handler for BU MET Autograder
 * Handles initiating OAuth flows and processing the callback after user authenticates with provider.
 */

// >>> IMPORT React and necessary hooks <<<
import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/router';
import Image from 'next/image'; // Use next/image for optimized images
// >>> IMPORT All required MUI components <<<
import {
  Alert, // <<< IMPORTED
  Box,
  Button,
  Card,
  CardContent,
  Container,
  Divider,
  Typography,
  Link as MuiLink,
  CircularProgress,
  Snackbar, // <<< IMPORTED
} from '@mui/material';
// >>> IMPORT All required MUI Icons <<<
import { Google as GoogleIcon, Microsoft as MicrosoftIcon } from '@mui/icons-material';
import { styled } from '@mui/material/styles';
// Assuming api.js and config.js are correctly placed relative to pages/login.js
// >>> IMPORT your API service and Config <<<
import { authService } from '../api'; // Adjust path if needed
import { ERROR_MESSAGES, APP_CONFIG } from '../config'; // Adjust path if needed
import Link from 'next/link'; // Use Next.js Link for internal navigation

// Styled components (Keep as they are)
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


export default function Login() {
  const router = useRouter();
  const [loading, setLoading] = useState(false); // General loading for button clicks
  const [callbackLoading, setCallbackLoading] = useState(false); // Specific loading for callback processing
  const [error, setError] = useState(null); // For displaying primary error message

  // >>> DEFINE State for Snackbar Alerts <<<
  const [alertOpen, setAlertOpen] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [alertSeverity, setAlertSeverity] = useState('success'); // 'success' | 'error' | 'warning' | 'info'

  // Helper to show snackbar alerts
  const showAlert = useCallback((message, severity = 'success') => {
    setAlertMessage(message);
    setAlertSeverity(severity);
    setAlertOpen(true);
  }, []); // Empty dependency array

  // Helper to show primary page errors (distinct from snackbar alerts)
  const showError = useCallback((message) => {
    setError(message || ERROR_MESSAGES.auth.loginFailed);
    console.error("Login/Callback Error:", message);
    // Optionally call showAlert here too if you want both
    // showAlert(message || ERROR_MESSAGES.auth.loginFailed, 'error');
  }, []); // Empty dependency array


  // --- Handle OAuth Callback ---
  useEffect(() => {
    const processCallback = async (code) => {
      setCallbackLoading(true);
      setError(null); // Clear primary error when processing code
      console.log("Processing OAuth callback with code:", code.substring(0, 10) + "...");

      try {
        const response = await authService.googleOAuth(code);

        if (response && response.data && response.data.authentication_token) {
          const token = response.data.authentication_token;
          console.log("Received auth token from backend:", token.substring(0, 10) + "...");
          sessionStorage.setItem('authToken', token);
          console.log("Auth token saved to sessionStorage.");
          const redirectTo = router.query.state || '/dashboard';
          console.log("Redirecting to:", redirectTo);
          router.push(redirectTo);
          // Successful redirect, loading state managed by page transition
        } else {
          console.error("Backend response missing authentication_token:", response);
          showError("Login failed: Could not retrieve authentication token from server.");
          router.push('/login?error=token_missing');
        }
      } catch (err) {
        console.error("Error during OAuth callback API call:", err);
        // Use the error processed by the axios interceptor if available
        showError(err.message || "An error occurred during login processing.");
         router.push('/login?error=callback_api_failed');
      } finally {
         // Only set loading false if we *failed* to get token and redirect
         if (!sessionStorage.getItem('authToken')) {
             setCallbackLoading(false);
         }
      }
    };

    if (router.isReady) {
       const { code, error: oauthError, error_description } = router.query;
       if (code && typeof code === 'string' && !callbackLoading) {
           processCallback(code);
       }
       else if (oauthError) {
           showError(error_description || `OAuth Error: ${oauthError}`);
           // Optionally remove error from URL: router.replace('/login', undefined, { shallow: true });
       }
       // Handle errors passed from previous redirect attempts
       else if (router.query.error && !error && !code) { // Only if not processing code and no OAuth error
            const knownError = ERROR_MESSAGES.auth[router.query.error] || ERROR_MESSAGES.auth.loginFailed;
            showError(knownError);
            // Optionally remove error from URL: router.replace('/login', undefined, { shallow: true });
       }
    }
  }, [router.isReady, router.query, callbackLoading, showError, router]);


  // --- Login Button Handlers ---
  const handleGoogleLogin = async () => {
    setLoading(true); setError(null);
    try {
        const response = await authService.getGoogleOAuthUrl();
        if (response?.data?.oauth_url) {
             window.location.href = response.data.oauth_url;
        } else { throw new Error("Could not get Google OAuth URL from server."); }
    } catch (err) {
      console.error('Google login initiation error:', err);
      showError(err.message || ERROR_MESSAGES.auth.loginFailed);
      setLoading(false);
    }
  };

  const handleMicrosoftLogin = async () => {
    setLoading(true); setError(null);
    // Use showAlert for temporary info message
    showAlert("Microsoft login is not implemented yet.", "info");
    setLoading(false);
    // Implement similar logic as handleGoogleLogin when ready
  };

  // --- Component Render ---
  return (
    <LoginContainer maxWidth="sm">
      <LogoContainer>
         {/* Placeholder Logo */}
         <Typography variant="h5" color="primary">BU MET Autograder Logo</Typography>
      </LogoContainer>

      <LoginCard>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h4" component="h1" align="center" gutterBottom>
            {APP_CONFIG.appName}
          </Typography>
          <Typography variant="body1" align="center" color="textSecondary" sx={{ mb: 4 }}>
            Sign in with your Boston University credentials.
          </Typography>

          {/* Show callback loading OR general error */}
          {callbackLoading && (
              <Box textAlign="center" my={2}>
                  <CircularProgress />
                  <Typography>Processing login...</Typography>
              </Box>
          )}
          {error && !callbackLoading && (
            <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>
          )}

          {/* Login Buttons */}
          {!callbackLoading && ( // Hide buttons while processing callback
            <>
              <ProviderButton variant="outlined" startIcon={<GoogleIcon />} onClick={handleGoogleLogin} disabled={loading}>
                {loading ? <CircularProgress size={24} sx={{mr: 1}} /> : null}
                Sign in with Google
              </ProviderButton>
              {/* Add Microsoft button if/when implemented */}
              {/* <ProviderButton variant="outlined" startIcon={<MicrosoftIcon />} onClick={handleMicrosoftLogin} disabled={loading}>
                 {loading ? <CircularProgress size={24} sx={{mr: 1}} /> : null}
                 Sign in with Microsoft
              </ProviderButton> */}
            </>
          )}

          <Divider sx={{ my: 3 }}><Typography variant="caption">BU Login</Typography></Divider>

          <Typography variant="body2" align="center" color="textSecondary">
            By signing in, you agree to the{' '}
            <MuiLink component={Link} href="/terms" underline="hover">Terms</MuiLink> & <MuiLink component={Link} href="/privacy" underline="hover">Privacy Policy</MuiLink>.
          </Typography>
        </CardContent>
      </LoginCard>

      <Box mt={4} textAlign="center">
        <Typography variant="body2" color="textSecondary">
          Need help?{' '}
          <MuiLink href={`mailto:${APP_CONFIG.supportEmail}`} underline="hover">Contact Support</MuiLink>
        </Typography>
      </Box>

      {/* Snackbar for Alerts (distinct from the main error display) */}
       <Snackbar
        open={alertOpen}
        autoHideDuration={6000}
        onClose={() => setAlertOpen(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        {/* Need to wrap Alert in forwardRef for Snackbar */}
        <Alert ref={React.forwardRef((props, ref) => <MuiAlert elevation={6} ref={ref} variant="filled" {...props} />)}
               onClose={() => setAlertOpen(false)}
               severity={alertSeverity}
               sx={{ width: '100%' }}
        >
          {alertMessage}
        </Alert>
      </Snackbar>
    </LoginContainer>
  );
}

// If this page should NOT use the default Layout (defined in _app.js)
// uncomment the line below. Most login pages don't use the main layout.
// Login.getLayout = function getLayout(page) {
//   return <>{page}</>;
// };