/**
 * Instructor Management Page for BU MET Autograder
 * Allows adding and removing instructors from courses
 */

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import {
  Alert,
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  IconButton,
  List,
  ListItem,
  ListItemAvatar,
  ListItemSecondaryAction,
  ListItemText,
  Paper,
  Snackbar,
  TextField,
  Typography,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  ArrowBack as ArrowBackIcon,
  Delete as DeleteIcon,
  Email as EmailIcon,
  PersonAdd as PersonAddIcon,
} from '@mui/icons-material';
import { courseService, useUser } from '../../../api';
import ConfirmationDialog from '../../../components/ConfirmationDialog';
import CardSkeleton from '../../../components/CardSkeleton';

// Styled components
const InstructorCard = styled(Card)(({ theme }) => ({
  marginBottom: theme.spacing(3),
}));

const AddInstructorForm = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  gap: theme.spacing(1),
  marginBottom: theme.spacing(3),
  [theme.breakpoints.down('sm')]: {
    flexDirection: 'column',
    alignItems: 'stretch',
  },
}));

// Instructor management page component
export default function InstructorManagement() {
  const router = useRouter();
  const { id: courseId, semester } = router.query;
  const { user } = useUser();

  // State for course data
  const [course, setCourse] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // State for instructor management
  const [newInstructorEmail, setNewInstructorEmail] = useState('');
  const [instructorToRemove, setInstructorToRemove] = useState(null);
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);

  // State for alerts
  const [alertOpen, setAlertOpen] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [alertSeverity, setAlertSeverity] = useState('success');

  // Fetch course data
  useEffect(() => {
    const fetchCourse = async () => {
      if (!courseId || !semester) return;

      setLoading(true);
      try {
        const courseData = await courseService.getCourse(courseId, semester);
        setCourse(courseData);
        setError(null);
      } catch (err) {
        console.error('Error fetching course:', err);
        setError(err.message || 'Failed to load course data');
      } finally {
        setLoading(false);
      }
    };

    fetchCourse();
  }, [courseId, semester]);

  // Check if current user is in the instructors list
  const isCurrentUserInstructor = () => {
    if (!user || !course) return false;
    return course.instructors.includes(user.user_email);
  };

  // Handle adding a new instructor
  const handleAddInstructor = async (e) => {
    e.preventDefault();

    if (!newInstructorEmail) return;

    try {
      await courseService.addInstructor(courseId, semester, newInstructorEmail);

      // Refresh course data
      const courseData = await courseService.getCourse(courseId, semester);
      setCourse(courseData);

      // Reset form
      setNewInstructorEmail('');

      // Show success alert
      setAlertMessage('Instructor added successfully');
      setAlertSeverity('success');
      setAlertOpen(true);
    } catch (error) {
      console.error('Error adding instructor:', error);
      setAlertMessage(error.message || 'Failed to add instructor');
      setAlertSeverity('error');
      setAlertOpen(true);
    }
  };

  // Open confirmation dialog for removing instructor
  const openRemoveDialog = (instructor) => {
    setInstructorToRemove(instructor);
    setConfirmDialogOpen(true);
  };

  // Handle removing an instructor
  const handleRemoveInstructor = async () => {
    if (!instructorToRemove) return;

    // Prevent removing yourself
    if (user && instructorToRemove === user.user_email) {
      setAlertMessage('You cannot remove yourself as an instructor');
      setAlertSeverity('error');
      setAlertOpen(true);
      setConfirmDialogOpen(false);
      setInstructorToRemove(null);
      return;
    }

    try {
      await courseService.removeInstructor(courseId, semester, instructorToRemove);

      // Refresh course data
      const courseData = await courseService.getCourse(courseId, semester);
      setCourse(courseData);

      // Close dialog
      setConfirmDialogOpen(false);
      setInstructorToRemove(null);

      // Show success alert
      setAlertMessage('Instructor removed successfully');
      setAlertSeverity('success');
      setAlertOpen(true);
    } catch (error) {
      console.error('Error removing instructor:', error);
      setAlertMessage(error.message || 'Failed to remove instructor');
      setAlertSeverity('error');
      setAlertOpen(true);
    }
  };

  // Email validation
  const isValidEmail = (email) => {
    // Basic email validation
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  };

  // Generate initials from email
  const getInitials = (email) => {
    if (!email) return '';

    // Try to extract name from email (e.g., john.doe@example.com -> JD)
    const parts = email.split('@')[0].split('.');
    if (parts.length >= 2) {
      return (parts[0].charAt(0) + parts[1].charAt(0)).toUpperCase();
    }

    // Fallback to first letter of email
    return email.charAt(0).toUpperCase();
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <IconButton
          edge="start"
          aria-label="back to course"
          onClick={() => router.push(`/course/${courseId}?semester=${semester}`)}
          sx={{ mr: 1 }}
        >
          <ArrowBackIcon />
        </IconButton>

        <Typography variant="h4" component="h1">
          Manage Instructors
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {loading ? (
        <CardSkeleton height={400} />
      ) : (
        <>
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Course Information
            </Typography>

            <Divider sx={{ mb: 2 }} />

            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
              <Box sx={{ flexGrow: 1, minWidth: '200px' }}>
                <Typography variant="subtitle2" color="text.secondary">
                  Course ID
                </Typography>
                <Typography variant="body1" sx={{ mb: 1 }}>
                  {course?.course_id}
                </Typography>
              </Box>

              <Box sx={{ flexGrow: 1, minWidth: '200px' }}>
                <Typography variant="subtitle2" color="text.secondary">
                  Semester
                </Typography>
                <Typography variant="body1" sx={{ mb: 1 }}>
                  {course?.semester}
                </Typography>
              </Box>

              <Box sx={{ flexGrow: 1, minWidth: '200px' }}>
                <Typography variant="subtitle2" color="text.secondary">
                  Number of Instructors
                </Typography>
                <Typography variant="body1" sx={{ mb: 1 }}>
                  {course?.instructors.length}
                </Typography>
              </Box>
            </Box>
          </Paper>

          <InstructorCard>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Add Instructor
              </Typography>

              <Divider sx={{ mb: 2 }} />

              <Typography variant="body2" paragraph>
                Enter the email address of the instructor you want to add to this course.
                They will have full access to manage assignments, rubrics, and grade submissions.
              </Typography>

              <AddInstructorForm component="form" onSubmit={handleAddInstructor}>
                <TextField
                  label="Instructor Email"
                  variant="outlined"
                  fullWidth
                  value={newInstructorEmail}
                  onChange={(e) => setNewInstructorEmail(e.target.value)}
                  placeholder="instructor@example.com"
                  error={newInstructorEmail !== '' && !isValidEmail(newInstructorEmail)}
                  helperText={
                    newInstructorEmail !== '' && !isValidEmail(newInstructorEmail)
                      ? 'Please enter a valid email address'
                      : ''
                  }
                  InputProps={{
                    startAdornment: <EmailIcon color="action" sx={{ mr: 1 }} />,
                  }}
                />

                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<PersonAddIcon />}
                  type="submit"
                  disabled={!newInstructorEmail || !isValidEmail(newInstructorEmail)}
                  sx={{ minWidth: '120px' }}
                >
                  Add
                </Button>
              </AddInstructorForm>
            </CardContent>
          </InstructorCard>

          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Current Instructors
              </Typography>

              <Divider sx={{ mb: 2 }} />

              {course?.instructors.length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 3 }}>
                  <Typography variant="body1" color="text.secondary">
                    No instructors assigned to this course yet.
                  </Typography>
                </Box>
              ) : (
                <List>
                  {course?.instructors.map((instructor) => {
                    const isCurrentUser = user && instructor === user.user_email;

                    return (
                      <ListItem
                        key={instructor}
                        sx={{
                          bgcolor: isCurrentUser ? 'action.selected' : 'transparent',
                          borderRadius: 1,
                        }}
                      >
                        <ListItemAvatar>
                          <Avatar sx={{ bgcolor: isCurrentUser ? 'primary.main' : 'secondary.main' }}>
                            {getInitials(instructor)}
                          </Avatar>
                        </ListItemAvatar>

                        <ListItemText
                          primary={instructor}
                          secondary={
                            isCurrentUser && (
                              <Chip
                                label="You"
                                size="small"
                                color="primary"
                                variant="outlined"
                              />
                            )
                          }
                        />

                        <ListItemSecondaryAction>
                          <IconButton
                            edge="end"
                            aria-label="delete"
                            onClick={() => openRemoveDialog(instructor)}
                            disabled={course?.instructors.length <= 1}
                            title={
                              course?.instructors.length <= 1
                                ? 'Cannot remove the last instructor'
                                : 'Remove instructor'
                            }
                          >
                            <DeleteIcon color={course?.instructors.length <= 1 ? 'disabled' : 'error'} />
                          </IconButton>
                        </ListItemSecondaryAction>
                      </ListItem>
                    );
                  })}
                </List>
              )}

              {course?.instructors.length <= 1 && (
                <Alert severity="info" sx={{ mt: 2 }}>
                  A course must have at least one instructor. You cannot remove the last instructor.
                </Alert>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {/* Confirmation Dialog for Removing Instructor */}
      <ConfirmationDialog
        open={confirmDialogOpen}
        title="Remove Instructor"
        message={`Are you sure you want to remove ${instructorToRemove} from this course? They will no longer have access to manage assignments, rubrics, or grade submissions.`}
        confirmText="Remove"
        cancelText="Cancel"
        confirmButtonProps={{ color: 'error' }}
        onConfirm={handleRemoveInstructor}
        onCancel={() => {
          setConfirmDialogOpen(false);
          setInstructorToRemove(null);
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
    </Box>
  );
}