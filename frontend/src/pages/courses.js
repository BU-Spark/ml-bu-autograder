/**
 * Course List Page for BU MET Autograder
 * Displays courses and handles course creation/deletion.
 */

import React, { useState, useCallback } from 'react'; // Removed useEffect unless needed for other purposes
import { useRouter } from 'next/router';
import {
  Alert as MuiAlert, // Renamed
  Box,
  Button,
  Card,
  CardActionArea,
  CardContent,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Divider,
  FormControl,
  Grid,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Snackbar,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  School as SchoolIcon,
  Person as PersonIcon,
} from '@mui/icons-material';
// Assuming api.js is in the parent directory's 'api' folder
import { useCourses, courseService } from '../api'; // Removed authService import
import { ERROR_MESSAGES } from '../config'; // Kept config import for messages
import CardSkeleton from '../components/CardSkeleton'; // Adjust path if needed
import ConfirmationDialog from '../components/ConfirmationDialog'; // Adjust path if needed

// --- Styled components (Keep as is) ---
const CourseCard = styled(Card)(({ theme }) => ({
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    transition: 'transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out',
    '&:hover': {
        transform: 'translateY(-4px)',
        boxShadow: theme.shadows[6],
    },
}));
const CourseCardContent = styled(CardContent)({
    flexGrow: 1,
    display: 'flex',
    flexDirection: 'column',
});
const CourseCardHeader = styled(Box)(({ theme }) => ({
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: theme.spacing(1),
}));
const InstructorsList = styled(Box)(({ theme }) => ({
    display: 'flex',
    alignItems: 'center',
    marginTop: 'auto', // Push to bottom
    paddingTop: theme.spacing(1),
    '& .MuiSvgIcon-root': {
        fontSize: '1rem',
        marginRight: theme.spacing(0.5),
        color: theme.palette.text.secondary,
    },
}));
const NoCoursesBox = styled(Box)(({ theme }) => ({
    textAlign: 'center',
    padding: theme.spacing(4),
    backgroundColor: theme.palette.background.default, // Use default bg
    borderRadius: theme.shape.borderRadius,
    marginTop: theme.spacing(4),
    border: `1px dashed ${theme.palette.divider}`,
}));

// --- Alert component for Snackbar ---
const Alert = React.forwardRef(function Alert(props, ref) {
    return <MuiAlert elevation={6} ref={ref} variant="filled" {...props} />;
});

// --- Course list page component ---
export default function Courses() {
  const router = useRouter();
  // useCourses hook fetches course data based on stored auth token
  const { courses, isLoading: isLoadingCoursesHook, isError: isCoursesErrorHook, mutate } = useCourses();

  // State for create course dialog
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [courseData, setCourseData] = useState({ course_id: '', semester: '' });
  const [createLoading, setCreateLoading] = useState(false);
  const [createFormError, setCreateFormError] = useState('');

  // State for delete course dialog
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [courseToDelete, setCourseToDelete] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  // State for alerts
  const [alertOpen, setAlertOpen] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [alertSeverity, setAlertSeverity] = useState('success');


  // --- Helper Functions ---
  const showAlert = useCallback((message, severity = 'success') => {
    setAlertMessage(message);
    setAlertSeverity(severity);
    setAlertOpen(true);
  }, []);

  // --- Course Management Functions ---

  // Generate semester options (lowercase seasonYYYY format)
  const getSemesterOptions = useCallback(() => {
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth();
    let semesters = [];
    let currentYear = year;
    const seasons = ['spring', 'summer', 'fall'];
    let currentSeasonIndex;
    if (month < 4) currentSeasonIndex = 0;
    else if (month < 8) currentSeasonIndex = 1;
    else currentSeasonIndex = 2;
    for (let i = 0; i < 5; i++) {
      const seasonIndex = (currentSeasonIndex + i) % 3;
      const yearOffset = Math.floor((currentSeasonIndex + i) / 3);
      semesters.push(`${seasons[seasonIndex]}${currentYear + yearOffset}`);
    }
    return semesters;
  }, []);

  const semesterOptions = getSemesterOptions();

  // Handle input changes for create dialog
  const handleInputChange = useCallback((event) => {
    const { name, value } = event.target;
    setCourseData(prev => ({ ...prev, [name]: value }));
    setCreateFormError('');
  }, []);

  // Validate and handle creating a new course
  const handleCreateCourse = async () => {
    setCreateFormError('');
    const courseIdInput = courseData.course_id.trim();
    const semesterInput = courseData.semester;
    const courseIdPattern = /^[a-z0-9_]+$/;
    let validationPassed = true;
    let formattedCourseId = '';

    if (!courseIdInput) {
        setCreateFormError('Course ID is required.'); validationPassed = false;
    } else {
        formattedCourseId = courseIdInput.toLowerCase();
        if (!courseIdPattern.test(formattedCourseId)) {
            setCreateFormError('Course ID can only contain lowercase letters, numbers, and underscores.'); validationPassed = false;
        }
    }
    if (!semesterInput) {
        setCreateFormError('Semester is required.'); validationPassed = false;
    }
    if (!validationPassed) return;

    setCreateLoading(true);
    try {
      await courseService.createCourse({
        course_id: formattedCourseId,
        semester: semesterInput, // Already in correct format
      });
      mutate(); // Re-fetch courses list
      setCourseData({ course_id: '', semester: '' });
      setCreateDialogOpen(false);
      showAlert('Course created successfully', 'success');
    } catch (error) {
      console.error('Error creating course:', error);
      showAlert(error.message || 'Failed to create course', 'error');
    } finally {
        setCreateLoading(false);
    }
  };

  // Open delete confirmation dialog
  const openDeleteDialog = useCallback((course, event) => {
    event.stopPropagation();
    setCourseToDelete(course);
    setDeleteDialogOpen(true);
  }, []);

  // Handle deleting a course
  const handleDeleteCourse = async () => {
    if (!courseToDelete) return;
    setDeleteLoading(true);
    try {
      await courseService.deleteCourse(courseToDelete.course_id, courseToDelete.semester);
      mutate(); // Re-fetch courses list
      setDeleteDialogOpen(false);
      setCourseToDelete(null);
      showAlert('Course deleted successfully', 'success');
    } catch (error) {
      console.error('Error deleting course:', error);
      showAlert(error.message || 'Failed to delete course', 'error');
    } finally {
        setDeleteLoading(false);
    }
  };

  // Navigate to course detail page
  const navigateToCourse = (course) => {
    if (course?.course_id && course?.semester) {
        router.push(`/course/${course.course_id}?semester=${course.semester}`);
    } else {
        console.error("Attempted navigation with invalid course data:", course);
        showAlert("Cannot navigate: missing course data.", "warning");
    }
  };


  // --- Component Render ---
  return (
    <Box sx={{ py: 3, px: { xs: 1, sm: 2, md: 3 } }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 2 }}>
         <Typography variant="h4" component="h1">Courses</Typography>
         <Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={() => setCreateDialogOpen(true)} disabled={createLoading || deleteLoading}>Create Course</Button>
      </Box>

      {/* Display SWR loading error */}
      {isCoursesErrorHook && (
          <MuiAlert severity="error" sx={{ mb: 3 }}>
              {isCoursesErrorHook.message || 'Failed to load courses. Please try again.'}
          </MuiAlert>
      )}

      {/* Course List Section */}
      {isLoadingCoursesHook ? (
        // Loading State
        <Grid container spacing={3}>
          {[1, 2, 3, 4].map((item) => (<Grid item xs={12} sm={6} md={4} lg={3} key={item}><CardSkeleton height={180} /></Grid>))}
        </Grid>
      ) : courses && courses.length > 0 ? (
        // **** Display Courses ****
        <Grid container spacing={3}>
          {courses.map((course) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={`${course.course_id}-${course.semester}`}>
              <CourseCard variant="outlined">
                <CardActionArea onClick={() => navigateToCourse(course)} sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                  <CourseCardContent>
                    <CourseCardHeader>
                      <Tooltip title={`${course.course_id} (${course.semester})`}>
                        <Typography variant="h6" component="h2" noWrap>
                          {course.course_id}
                        </Typography>
                      </Tooltip>
                      <Tooltip title="Delete Course">
                        {/* Disable delete button while another delete is in progress */}
                        <IconButton size="small" color="error" aria-label="delete course" onClick={(e) => openDeleteDialog(course, e)} disabled={deleteLoading}>
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </CourseCardHeader>
                    <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1.5 }}>
                      {course.semester}
                    </Typography>
                    <Box sx={{ flexGrow: 1 }} /> {/* Pushes content below down */}
                    <Divider sx={{ my: 1 }} />
                    <InstructorsList>
                      <PersonIcon />
                      <Typography variant="body2" color="text.secondary">
                        {course.instructors?.length ?? 0} Instructor(s)
                      </Typography>
                    </InstructorsList>
                  </CourseCardContent>
                </CardActionArea>
              </CourseCard>
            </Grid>
          ))}
        </Grid>
      ) : (
        // No Courses State
        <NoCoursesBox>
          <SchoolIcon sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" gutterBottom>No Courses Found</Typography>
          <Typography variant="body2" color="text.secondary" paragraph>Create your first course to get started.</Typography>
          <Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={() => setCreateDialogOpen(true)} disabled={createLoading}>Create Course</Button>
        </NoCoursesBox>
      )}

      {/* --- Dialogs --- */}
      {/* Create Course Dialog */}
      <Dialog open={createDialogOpen} onClose={() => !createLoading && setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Course</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>Enter course identifier and select semester.</DialogContentText>
          {createFormError && <MuiAlert severity="warning" sx={{ mb: 2 }}>{createFormError}</MuiAlert>}
          <TextField autoFocus name="course_id" label="Course ID" placeholder="e.g., cs505 or metcs505_oa1" fullWidth value={courseData.course_id} onChange={handleInputChange} margin="dense" required error={!!createFormError && !courseData.course_id?.trim()} helperText="Lowercase letters, numbers, underscores only (e.g., cs505)." />
          <FormControl fullWidth margin="dense" required error={!!createFormError && !courseData.semester}>
             <InputLabel id="semester-select-label">Semester</InputLabel>
             <Select labelId="semester-select-label" name="semester" value={courseData.semester} onChange={handleInputChange} label="Semester" >
               <MenuItem value="" disabled><em>Select a semester...</em></MenuItem>
               {semesterOptions.map((sem) => (<MenuItem key={sem} value={sem}>{sem}</MenuItem>))}
             </Select>
             {!courseData.semester && createFormError.includes('Semester') && <Typography variant="caption" color="error" sx={{ pl: 2, pt: 0.5 }}>Semester is required</Typography>}
           </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)} disabled={createLoading}>Cancel</Button>
          <Button onClick={handleCreateCourse} variant="contained" color="primary" disabled={createLoading || !courseData.course_id?.trim() || !courseData.semester}>
            {createLoading ? <CircularProgress size={24} /> : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Course Confirmation Dialog */}
      <ConfirmationDialog
        open={deleteDialogOpen}
        onClose={() => !deleteLoading && setDeleteDialogOpen(false)}
        title="Delete Course Confirmation"
        description={`Delete "${courseToDelete?.course_id} (${courseToDelete?.semester})"? This permanently deletes the course and ALL associated data. This cannot be undone.`}
        confirmText="Delete Course"
        cancelText="Cancel"
        confirmColor="error"
        onConfirm={handleDeleteCourse}
        loading={deleteLoading}
      />

      {/* Alert Snackbar */}
      <Snackbar open={alertOpen} autoHideDuration={6000} onClose={() => setAlertOpen(false)} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert onClose={() => setAlertOpen(false)} severity={alertSeverity}>{alertMessage}</Alert>
      </Snackbar>
    </Box>
  );
}