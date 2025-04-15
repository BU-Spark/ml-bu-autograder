/**
 * Course List Page for BU MET Autograder
 * Displays courses and handles course creation/deletion.
 */

import React, { useState, useCallback, useEffect } from 'react'; // Added useCallback, useEffect
import { useRouter } from 'next/router';
import {
  Alert as MuiAlert, // Renamed
  Box,
  Button,
  Card,
  CardActionArea,
  CardContent,
  CircularProgress, // Added
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
  Tooltip, // Added
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
import { useCourses, courseService, authService } from '../api'; // Added authService if needed for callback
import { ERROR_MESSAGES } from '../config'; // Added config import
import CardSkeleton from '../components/CardSkeleton'; // Adjust path if needed
import ConfirmationDialog from '../components/ConfirmationDialog'; // Adjust path if needed

// --- Styled components (Keep as is) ---
const CourseCard = styled(Card)(({ theme }) => ({ /* ... */ }));
const CourseCardContent = styled(CardContent)({ /* ... */ });
const CourseCardHeader = styled(Box)(({ theme }) => ({ /* ... */ }));
const InstructorsList = styled(Box)(({ theme }) => ({ /* ... */ }));
const NoCoursesBox = styled(Box)(({ theme }) => ({ /* ... */ }));

// --- Alert component for Snackbar ---
const Alert = React.forwardRef(function Alert(props, ref) {
    return <MuiAlert elevation={6} ref={ref} variant="filled" {...props} />;
});

// --- Course list page component ---
export default function Courses() {
  const router = useRouter();
  // useCourses fetches based on token, might fail initially if token isn't set yet during callback
  const { courses, isLoading: isLoadingCoursesHook, isError: isCoursesErrorHook, mutate } = useCourses();

  // State for create course dialog
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [courseData, setCourseData] = useState({ course_id: '', semester: '' });
  const [createLoading, setCreateLoading] = useState(false); // Loading state for create action
  const [createFormError, setCreateFormError] = useState(''); // Error specific to create form validation

  // State for delete course dialog
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [courseToDelete, setCourseToDelete] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(false); // Loading state for delete action


  // State for alerts
  const [alertOpen, setAlertOpen] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [alertSeverity, setAlertSeverity] = useState('success');

  // State for Callback Processing (Moved from Login.js)
  const [callbackLoading, setCallbackLoading] = useState(false);
  const [callbackError, setCallbackError] = useState(null); // Specific error state for callback

  // --- Helper Functions ---
  const showAlert = useCallback((message, severity = 'success') => {
    setAlertMessage(message);
    setAlertSeverity(severity);
    setAlertOpen(true);
  }, []);

  // Show error message specifically related to callback failure
  const showCallbackError = useCallback((message) => {
      const msg = message || ERROR_MESSAGES.auth.loginFailed;
      setCallbackError(msg);
      console.error("OAuth Callback Error:", msg);
  }, []);



  // --- Course Management Functions ---

  // Generate semester options in 'seasonYYYY' format
  const getSemesterOptions = useCallback(() => {
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth();
    let semesters = [];
    let currentYear = year;
    const seasons = ['spring', 'summer', 'fall']; // Use lowercase
    let currentSeasonIndex;
    if (month < 4) currentSeasonIndex = 0; // Jan-Apr -> Spring
    else if (month < 8) currentSeasonIndex = 1; // May-Aug -> Summer
    else currentSeasonIndex = 2; // Sep-Dec -> Fall

    for (let i = 0; i < 5; i++) { // Generate 5 semesters (current + next 4)
      const seasonIndex = (currentSeasonIndex + i) % 3;
      const yearOffset = Math.floor((currentSeasonIndex + i) / 3);
      // <<< --- FORMAT CHANGED --- >>>
      semesters.push(`${seasons[seasonIndex]}${currentYear + yearOffset}`);
    }
    return semesters;
  }, []); // No dependencies needed

  const semesterOptions = getSemesterOptions();

  // Handle input changes for create dialog
  const handleInputChange = useCallback((event) => {
    const { name, value } = event.target;
    setCourseData(prev => ({ ...prev, [name]: value }));
    setCreateFormError(''); // Clear validation error on input change
  }, []);

  // Validate and handle creating a new course
  const handleCreateCourse = async () => {
    setCreateFormError(''); // Clear previous errors
    const courseIdInput = courseData.course_id.trim();
    const semesterInput = courseData.semester;

    // Frontend Validation (matching backend rules)
    const courseIdPattern = /^[a-z0-9_]+$/; // lowercase letters, numbers, underscore
    const semesterPattern = /^[a-z]{1,12}[0-9]{4}$/; // seasonYYYY

    let validationPassed = true;
    let formattedCourseId = '';
    let formattedSemester = '';

    if (!courseIdInput) {
        setCreateFormError('Course ID is required.');
        validationPassed = false;
    } else {
        formattedCourseId = courseIdInput.toLowerCase(); // Convert to lowercase first
        if (!courseIdPattern.test(formattedCourseId)) {
            setCreateFormError('Course ID can only contain lowercase letters, numbers, and underscores.');
            validationPassed = false;
        }
    }

    if (!semesterInput) {
        // Should not happen if dropdown is required, but check anyway
        setCreateFormError('Semester is required.');
        validationPassed = false;
    } else {
        // Semester format is handled by the dropdown generation, just ensure it's selected
        formattedSemester = semesterInput; // Already in correct format from getSemesterOptions
        if (!semesterPattern.test(formattedSemester)) {
            // This indicates an issue with getSemesterOptions if it happens
             setCreateFormError('Selected semester format is invalid.');
             validationPassed = false;
        }
    }


    if (!validationPassed) {
      return; // Stop if validation fails
    }

    setCreateLoading(true);
    try {
      // <<< --- Send FORMATTED Data --- >>>
      await courseService.createCourse({
        course_id: formattedCourseId,
        semester: formattedSemester,
        // instructors: [] // Backend handles adding creator
      });

      mutate(); // Re-fetch courses list
      setCourseData({ course_id: '', semester: '' }); // Reset form
      setCreateDialogOpen(false);
      showAlert('Course created successfully', 'success');
    } catch (error) {
      console.error('Error creating course:', error);
       // Display specific backend error if available (like 'Course already exists')
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
    // Ensure course_id and semester are valid before navigating
    if (course?.course_id && course?.semester) {
        router.push(`/course/${course.course_id}?semester=${course.semester}`);
    } else {
        console.error("Attempted to navigate with invalid course data:", course);
        showAlert("Cannot navigate to course: missing data.", "warning");
    }
  };


  // --- Component Render ---
  return (
    <Box sx={{ py: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">Courses</Typography>
      </Box>

      {/* Display Callback Processing / Errors */}
      {callbackLoading && <Alert severity="info" sx={{ mb: 3 }}>Processing login...</Alert>}
      {callbackError && <Alert severity="error" sx={{ mb: 3 }}>Login Error: {callbackError}</Alert>}
      {isCoursesErrorHook && !callbackLoading && !callbackError && <Alert severity="error" sx={{ mb: 3 }}>Failed to load courses. Please try again.</Alert>}


      {/* Course List */}
      {(isLoadingCoursesHook && !courses) || callbackLoading ? (
        <Grid container spacing={3}>{[1, 2, 3, 4].map((item) => (<Grid item xs={12} sm={6} md={4} lg={3} key={item}><CardSkeleton height={180} /></Grid>))} </Grid>
      ) : courses && courses.length > 0 ? (
        <Grid container spacing={3}>
          {courses.map((course) => (
             <Grid item xs={12} sm={6} md={4} lg={3} key={`${course.course_id}-${course.semester}`}>
               <CourseCard>
                 <CardActionArea onClick={() => navigateToCourse(course)} sx={{ flexGrow: 1}}>
                   <CourseCardContent>
                     <CourseCardHeader>
                       <Typography variant="h6" component="h2" noWrap title={course.course_id}>{course.course_id}</Typography>
                       <Tooltip title="Delete Course"><IconButton size="small" color="error" aria-label="delete course" onClick={(e) => openDeleteDialog(course, e)}><DeleteIcon fontSize="small" /></IconButton></Tooltip>
                     </CourseCardHeader>
                     <Typography variant="subtitle2" color="text.secondary">{course.semester}</Typography>
                     <Divider sx={{ my: 1.5 }} />
                     <InstructorsList>
                       <PersonIcon /><Typography variant="body2" color="text.secondary">{course.instructors?.length ?? 0} Instructor(s)</Typography>
                     </InstructorsList>
                   </CourseCardContent>
                 </CardActionArea>
               </CourseCard>
             </Grid>
          ))}
        </Grid>
      ) : !isLoadingCoursesHook && !callbackLoading ? (
        <NoCoursesBox>
          <SchoolIcon sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" gutterBottom>No Courses Found</Typography>
          <Typography variant="body2" color="text.secondary" paragraph>Create your first course.</Typography>
          <Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={() => setCreateDialogOpen(true)}>Create Course</Button>
        </NoCoursesBox>
      ) : null}

      {/* --- Dialogs --- */}
      {/* Create Course Dialog */}
      <Dialog open={createDialogOpen} onClose={() => !createLoading && setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Course</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>Enter course identifier and select semester.</DialogContentText>
           {/* Display form validation error */}
          {createFormError && <Alert severity="warning" sx={{ mb: 2 }}>{createFormError}</Alert>}
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
        onClose={() => !deleteLoading && setDeleteDialogOpen(false)} // Prevent closing while deleting
        title="Delete Course Confirmation"
        description={`Delete "${courseToDelete?.course_id} (${courseToDelete?.semester})"? This permanently deletes the course and ALL associated data. This cannot be undone.`}
        confirmText="Delete Course"
        cancelText="Cancel"
        confirmColor="error"
        onConfirm={handleDeleteCourse}
        loading={deleteLoading} // Show loading state on confirm button
      />

      {/* Alert Snackbar */}
      <Snackbar open={alertOpen} autoHideDuration={6000} onClose={() => setAlertOpen(false)} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert onClose={() => setAlertOpen(false)} severity={alertSeverity}>
          {alertMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
}