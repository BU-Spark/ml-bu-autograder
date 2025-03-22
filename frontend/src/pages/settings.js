/**
 * Settings Page for BU MET Autograder
 * Manages user profile settings and API tokens
 */

import React, { useState, useEffect } from 'react';
import {
  Alert,
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Divider,
  FormControlLabel,
  Grid,
  IconButton,
  List,
  ListItem,
  ListItemAvatar,
  ListItemSecondaryAction,
  ListItemText,
  Paper,
  Snackbar,
  Switch,
  Tab,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  AccountCircle as AccountIcon,
  Add as AddIcon,
  ContentCopy as CopyIcon,
  Delete as DeleteIcon,
  Key as KeyIcon,
  Person as PersonIcon,
  Refresh as RefreshIcon,
  Save as SaveIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
} from '@mui/icons-material';
import { useTheme } from '../context/ThemeContext';
import { authService, userService } from '../services/api';
import CardSkeleton from '../components/CardSkeleton';
import ConfirmationDialog from '../components/ConfirmationDialog';

// Styled components
const SettingsContainer = styled(Box)(({ theme }) => ({
  maxWidth: 1200,
  margin: '0 auto',
  padding: theme.spacing(3),
}));

const SettingsCard = styled(Card)(({ theme }) => ({
  marginBottom: theme.spacing(3),
}));

const TokenCard = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(2),
  marginBottom: theme.spacing(2),
  borderRadius: theme.shape.borderRadius,
  backgroundColor: theme.palette.background.default,
}));

// Tab panel component
const TabPanel = (props) => {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`settings-tabpanel-${index}`}
      aria-labelledby={`settings-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
};

// Main component
export default function Settings() {
  // Theme context
  const { mode, toggleTheme } = useTheme();

  // Tab state
  const [tabValue, setTabValue] = useState(0);

  // User data state
  const [userData, setUserData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    dark_mode: false,
  });

  // Token state
  const [tokens, setTokens] = useState([]);
  const [loadingTokens, setLoadingTokens] = useState(false);
  const [newTokenName, setNewTokenName] = useState('');
  const [newToken, setNewToken] = useState(null);
  const [showToken, setShowToken] = useState(false);

  // Dialog state
  const [createTokenDialogOpen, setCreateTokenDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [tokenToDelete, setTokenToDelete] = useState(null);

  // Alert state
  const [alertOpen, setAlertOpen] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [alertSeverity, setAlertSeverity] = useState('success');

  // Fetch user data on component mount
  useEffect(() => {
    const fetchUserData = async () => {
      try {
        const data = await userService.getUserData();
        setUserData(data);
        setFormData({
          first_name: data.first_name || '',
          last_name: data.last_name || '',
          dark_mode: data.dark_mode || false,
        });
      } catch (error) {
        console.error('Error fetching user data:', error);
        setAlertMessage('Failed to load user data: ' + error.message);
        setAlertSeverity('error');
        setAlertOpen(true);
      } finally {
        setLoading(false);
      }
    };

    fetchUserData();
  }, []);

  // Fetch tokens
  const fetchTokens = async () => {
    setLoadingTokens(true);
    try {
      const data = await authService.listTokens();
      setTokens(data || []);
    } catch (error) {
      console.error('Error fetching tokens:', error);
      setAlertMessage('Failed to load tokens: ' + error.message);
      setAlertSeverity('error');
      setAlertOpen(true);
    } finally {
      setLoadingTokens(false);
    }
  };

  // Fetch tokens when API tab is selected
  useEffect(() => {
    if (tabValue === 1) {
      fetchTokens();
    }
  }, [tabValue]);

  // Handle tab change
  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  // Handle form input change
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value,
    });
  };

  // Handle dark mode toggle
  const handleDarkModeToggle = () => {
    setFormData({
      ...formData,
      dark_mode: !formData.dark_mode,
    });

    // Also toggle the theme in the context (for immediate visual feedback)
    toggleTheme();
  };

  // Handle form submission
  const handleSaveProfile = async () => {
    setSaving(true);
    try {
      const updatedUser = await userService.updateUserPreferences(formData);
      setUserData(updatedUser);

      setAlertMessage('Profile updated successfully');
      setAlertSeverity('success');
      setAlertOpen(true);
    } catch (error) {
      console.error('Error updating profile:', error);
      setAlertMessage('Failed to update profile: ' + error.message);
      setAlertSeverity('error');
      setAlertOpen(true);
    } finally {
      setSaving(false);
    }
  };

  // Handle token creation
  const handleCreateToken = async () => {
    try {
      const token = await authService.createToken(newTokenName);
      setNewToken(token);
      setNewTokenName('');
      setCreateTokenDialogOpen(false);

      // Refresh tokens list
      await fetchTokens();

      setAlertMessage('Token created successfully');
      setAlertSeverity('success');
      setAlertOpen(true);
    } catch (error) {
      console.error('Error creating token:', error);
      setAlertMessage('Failed to create token: ' + error.message);
      setAlertSeverity('error');
      setAlertOpen(true);
    }
  };

  // Handle token deletion
  const handleDeleteToken = async () => {
    if (!tokenToDelete) return;

    try {
      await authService.deleteToken(tokenToDelete.token_id);

      // Remove token from list
      setTokens(tokens.filter((t) => t.token_id !== tokenToDelete.token_id));

      setAlertMessage('Token deleted successfully');
      setAlertSeverity('success');
      setAlertOpen(true);
    } catch (error) {
      console.error('Error deleting token:', error);
      setAlertMessage('Failed to delete token: ' + error.message);
      setAlertSeverity('error');
      setAlertOpen(true);
    } finally {
      setTokenToDelete(null);
      setDeleteDialogOpen(false);
    }
  };

  // Handle copying token to clipboard
  const handleCopyToken = (token) => {
    navigator.clipboard.writeText(token);
    setAlertMessage('Token copied to clipboard');
    setAlertSeverity('success');
    setAlertOpen(true);
  };

  // Render profile settings tab
  const renderProfileSettings = () => {
    if (loading) {
      return <CardSkeleton height={300} />;
    }

    return (
      <SettingsCard>
        <CardHeader
          avatar={
            <Avatar
              sx={{
                bgcolor: 'primary.main',
                width: 56,
                height: 56,
              }}
            >
              <PersonIcon fontSize="large" />
            </Avatar>
          }
          title={
            <Typography variant="h5">
              {userData?.first_name && userData?.last_name
                ? `${userData.first_name} ${userData.last_name}`
                : 'Profile Settings'}
            </Typography>
          }
          subheader={userData?.user_email}
        />

        <Divider />

        <CardContent>
          <Grid container spacing={3}>
            <Grid item xs={12} sm={6}>
              <TextField
                label="First Name"
                name="first_name"
                value={formData.first_name}
                onChange={handleInputChange}
                fullWidth
                margin="normal"
                variant="outlined"
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                label="Last Name"
                name="last_name"
                value={formData.last_name}
                onChange={handleInputChange}
                fullWidth
                margin="normal"
                variant="outlined"
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                label="Email"
                value={userData?.user_email || ''}
                fullWidth
                margin="normal"
                variant="outlined"
                disabled
                helperText="Email cannot be changed"
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <Paper
                sx={{
                  p: 2,
                  mt: 2,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <Typography variant="body1">Dark Mode</Typography>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.dark_mode}
                      onChange={handleDarkModeToggle}
                      color="primary"
                    />
                  }
                  label={formData.dark_mode ? 'On' : 'Off'}
                  labelPlacement="start"
                />
              </Paper>
            </Grid>

            <Grid item xs={12}>
              <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={saving ? <CircularProgress size={20} /> : <SaveIcon />}
                  onClick={handleSaveProfile}
                  disabled={saving}
                >
                  {saving ? 'Saving...' : 'Save Changes'}
                </Button>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </SettingsCard>
    );
  };

  // Render API tokens tab
  const renderAPITokens = () => {
    return (
      <>
        <SettingsCard>
          <CardHeader
            avatar={
              <Avatar sx={{ bgcolor: 'secondary.main' }}>
                <KeyIcon />
              </Avatar>
            }
            title={<Typography variant="h5">API Tokens</Typography>}
            subheader="Manage access tokens for programmatic API access"
            action={
              <Button
                variant="contained"
                color="primary"
                startIcon={<AddIcon />}
                onClick={() => setCreateTokenDialogOpen(true)}
                sx={{ mt: 1, mr: 1 }}
              >
                Create Token
              </Button>
            }
          />

          <Divider />

          <CardContent>
            {loadingTokens ? (
              <CardSkeleton height={100} />
            ) : tokens.length === 0 ? (
              <Alert severity="info">
                You don't have any API tokens yet. Create one to access the API programmatically.
              </Alert>
            ) : (
              <List>
                {tokens.map((token) => (
                  <TokenCard key={token.token_id}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <ListItemAvatar>
                          <Avatar sx={{ bgcolor: 'primary.main' }}>
                            <KeyIcon />
                          </Avatar>
                        </ListItemAvatar>

                        <Box>
                          <Typography variant="subtitle1" fontWeight="bold">
                            {token.token_name}
                          </Typography>

                          <Typography variant="body2" color="text.secondary">
                            ID: {token.token_id}
                          </Typography>

                          {token.token_expiry && (
                            <Typography variant="body2" color="text.secondary">
                              Expires: {new Date(token.token_expiry).toLocaleDateString()}
                            </Typography>
                          )}
                        </Box>
                      </Box>

                      <Box>
                        <Tooltip title="Delete Token">
                          <IconButton
                            edge="end"
                            color="error"
                            onClick={() => {
                              setTokenToDelete(token);
                              setDeleteDialogOpen(true);
                            }}
                          >
                            <DeleteIcon />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </Box>
                  </TokenCard>
                ))}
              </List>
            )}

            <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
              <Button
                startIcon={<RefreshIcon />}
                onClick={fetchTokens}
                disabled={loadingTokens}
              >
                Refresh
              </Button>
            </Box>
          </CardContent>
        </SettingsCard>

        {/* Display new token after creation */}
        {newToken && (
          <SettingsCard>
            <CardHeader
              title={<Typography variant="h6">New Token Created</Typography>}
              subheader="This token will only be shown once. Please copy it now."
            />

            <CardContent>
              <Alert severity="warning" sx={{ mb: 2 }}>
                Make sure to copy this token now. For security reasons, it won't be displayed again.
              </Alert>

              <Paper
                sx={{
                  p: 2,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  bgcolor: 'background.default',
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', flexGrow: 1, overflow: 'hidden' }}>
                  <Typography
                    variant="body2"
                    fontFamily="monospace"
                    sx={{
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {showToken ? newToken.token_id : '••••••••••••••••••••••••••••••••••••••••'}
                  </Typography>
                </Box>

                <Box sx={{ display: 'flex', ml: 2 }}>
                  <Tooltip title={showToken ? 'Hide Token' : 'Show Token'}>
                    <IconButton onClick={() => setShowToken(!showToken)} size="small">
                      {showToken ? <VisibilityOffIcon /> : <VisibilityIcon />}
                    </IconButton>
                  </Tooltip>

                  <Tooltip title="Copy to Clipboard">
                    <IconButton
                      onClick={() => handleCopyToken(newToken.token_id)}
                      color="primary"
                      size="small"
                    >
                      <CopyIcon />
                    </IconButton>
                  </Tooltip>
                </Box>
              </Paper>

              <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
                <Button
                  variant="contained"
                  onClick={() => setNewToken(null)}
                >
                  I've Copied My Token
                </Button>
              </Box>
            </CardContent>
          </SettingsCard>
        )}
      </>
    );
  };

  return (
    <SettingsContainer>
      <Typography variant="h4" component="h1" gutterBottom>
        Settings
      </Typography>

      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          variant="fullWidth"
          aria-label="settings tabs"
        >
          <Tab
            label="Profile"
            icon={<AccountIcon />}
            iconPosition="start"
          />
          <Tab
            label="API Tokens"
            icon={<KeyIcon />}
            iconPosition="start"
          />
        </Tabs>
      </Paper>

      <TabPanel value={tabValue} index={0}>
        {renderProfileSettings()}
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        {renderAPITokens()}
      </TabPanel>

      {/* Create Token Dialog */}
      <Dialog
        open={createTokenDialogOpen}
        onClose={() => setCreateTokenDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Create New API Token</DialogTitle>
        <DialogContent>
          <DialogContentText>
            API tokens allow programmatic access to the BU MET Autograder API. Tokens should be kept
            secure and not shared with others.
          </DialogContentText>

          <TextField
            autoFocus
            margin="dense"
            label="Token Name"
            fullWidth
            variant="outlined"
            value={newTokenName}
            onChange={(e) => setNewTokenName(e.target.value)}
            placeholder="e.g., Development, Testing, etc."
            sx={{ mt: 2 }}
          />
        </DialogContent>

        <DialogActions>
          <Button onClick={() => setCreateTokenDialogOpen(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleCreateToken}
            variant="contained"
            color="primary"
            disabled={!newTokenName.trim()}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Token Confirmation Dialog */}
      <ConfirmationDialog
        open={deleteDialogOpen}
        title="Delete API Token"
        message={`Are you sure you want to delete the token "${tokenToDelete?.token_name}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        confirmButtonProps={{ color: 'error' }}
        onConfirm={handleDeleteToken}
        onCancel={() => {
          setDeleteDialogOpen(false);
          setTokenToDelete(null);
        }}
      />

      {/* Alert Snackbar */}
      <Snackbar
        open={alertOpen}
        autoHideDuration={6000}
        onClose={() => setAlertOpen(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setAlertOpen(false)}
          severity={alertSeverity}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {alertMessage}
        </Alert>
      </Snackbar>
    </SettingsContainer>
  );
}