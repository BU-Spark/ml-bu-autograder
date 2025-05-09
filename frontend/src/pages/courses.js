/**
 * Course List Page for BU MET Autograder
 * Displays all courses with creation and deletion options
 */

import React, { useState } from 'react';
import { useRouter } from 'next/router';
import {
  Alert,
  Box,
  Button,
  Card,
  CardActionArea,
  CardContent,
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
  Typography,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  School as SchoolIcon,
  Person as PersonIcon,
} from '@mui/icons-material';
// Assuming api.js is in src/api/index.js or similar and exports courseService and useCourses
import { useCourses, courseService } from '../api'; // Adjust path if necessary
import CardSkeleton from '../components/CardSkeleton';
import ConfirmationDialog from '../components/ConfirmationDialog';

// Styled components
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
  marginTop: 'auto',
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
  backgroundColor: theme.palette.background.paper,
  borderRadius: theme.shape.borderRadius,
  marginTop: theme.spacing(4),
}));

// Course list page component
export default function Courses() {
  const router = useRouter();
  // useCourses hook now might take an optional semester argument if you want to filter initially
  // For listing all courses, no argument is needed if your useCourses hook defaults to that.
  const { courses, isLoading, isError, mutate } = useCourses();

  // State for create course dialog
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newCourseData, setNewCourseData] = useState({ // Renamed for clarity
    course_id: '',
    semester: '',
    // instructors: [], // Instructors are usually added by the backend or in a separate step
  });

  // State for delete course dialog
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [courseToDelete, setCourseToDelete] = useState(null);

  // State for alerts
  const [alertOpen, setAlertOpen] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [alertSeverity, setAlertSeverity] = useState('success');

  // Generate semester options
  const getSemesterOptions = () => {
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth();

    let semesters = [];
    let currentYear = year;
    const seasons = ['Spring', 'Summer', 'Fall'];

    let currentSeasonIndex;
    if (month >= 0 && month <= 4) currentSeasonIndex = 0; // Spring (Jan-May)
    else if (month >= 5 && month <= 7) currentSeasonIndex = 1; // Summer (Jun-Aug)
    else currentSeasonIndex = 2; // Fall (Sep-Dec)


    for (let i = 0; i < 5; i++) { // Current + next 4 semesters
      const seasonIndex = (currentSeasonIndex + i) % 3;
      const yearOffset = Math.floor((currentSeasonIndex + i) / 3);
      semesters.push(`${seasons[seasonIndex]} ${currentYear + yearOffset}`);
    }
    return semesters;
  };

  const semesterOptions = getSemesterOptions();

  // Handle creating a new course
  const handleCreateCourse = async () => {
    // The `courseService.createCourse` now expects a single object argument
    // matching the `Course` type defined in your OpenAPI spec and JSDoc.
    const coursePayload = {
      course_id: newCourseData.course_id,
      semester: newCourseData.semester,
      // instructors: [], // OpenAPI spec for Course allows instructors.
                         // Backend usually adds the currently authenticated user as an instructor.
                         // If you need to explicitly pass it, ensure your user object is available.
                         // For simplicity, if the backend handles it, this can be omitted or empty.
    };

    try {
      await courseService.createCourse(coursePayload);

      mutate(); // Refresh course list

      setNewCourseData({ course_id: '', semester: '' });
      setCreateDialogOpen(false);

      setAlertMessage('Course created successfully');
      setAlertSeverity('success');
      setAlertOpen(true);
    } catch (error) {
      console.error('Error creating course:', error);
      setAlertMessage(error.message || 'Failed to create course');
      setAlertSeverity('error');
      setAlertOpen(true);
    }
  };

  // Handle deleting a course
  const handleDeleteCourse = async () => {
    if (!courseToDelete) return;

    // `courseService.deleteCourse` now expects a single object with course_id and semester
    const deleteParams = {
      course_id: courseToDelete.course_id,
      semester: courseToDelete.semester,
    };

    try {
      await courseService.deleteCourse(deleteParams);

      mutate(); // Refresh course list

      setDeleteDialogOpen(false);
      setCourseToDelete(null);

      setAlertMessage('Course deleted successfully');
      setAlertSeverity('success');
      setAlertOpen(true);
    } catch (error) {
      console.error('Error deleting course:', error);
      setAlertMessage(error.message || 'Failed to delete course');
      setAlertSeverity('error');
      setAlertOpen(true);
    }
  };

  // Open delete confirmation dialog
  const openDeleteDialog = (course, event) => {
    event.stopPropagation(); // Prevent card click
    setCourseToDelete(course);
    setDeleteDialogOpen(true);
  };

  // Navigate to course detail page
  const navigateToCourse = (course) => {
    // Ensure course object has course_id and semester
    if (course && course.course_id && course.semester) {
      router.push(`/course/${course.course_id}?semester=${course.semester}`);
    } else {
      console.error("Invalid course data for navigation:", course);
      setAlertMessage("Cannot navigate: Invalid course data.");
      setAlertSeverity("error");
      setAlertOpen(true);
    }
  };

  // Handle form input changes for the create course dialog
  const handleInputChange = (event) => {
    const { name, value } = event.target;
    setNewCourseData({
      ...newCourseData,
      [name]: value,
    });
  };

  return (
    <Box sx={{ py: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Courses
        </Typography>

        <Button
          variant="contained"
          color="primary"
          startIcon={<AddIcon />}
          onClick={() => setCreateDialogOpen(true)}
        >
          Create Course
        </Button>
      </Box>

      {isError && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {isError.message || 'Failed to load courses. Please try again.'}
        </Alert>
      )}

      {isLoading ? (
        <Grid container spacing={3}>
          {[1, 2, 3, 4].map((item) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={item}>
              <CardSkeleton height={180} />
            </Grid>
          ))}
        </Grid>
      ) : courses && courses.length > 0 ? (
        <Grid container spacing={3}>
          {courses.map((course) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={`${course.course_id}-${course.semester}`}>
              <CourseCard>
                <CardActionArea onClick={() => navigateToCourse(course)}>
                  <CourseCardContent>
                    <CourseCardHeader>
                      <Typography variant="h6" component="h2" noWrap sx={{ flexGrow: 1, mr: 1 }}>
                        {course.course_id}
                      </Typography>
                      <IconButton
                        size="small"
                        color="error"
                        aria-label="delete course"
                        onClick={(e) => openDeleteDialog(course, e)} // Pass event to stop propagation
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </CourseCardHeader>

                    <Typography variant="subtitle2" color="text.secondary">
                      {course.semester}
                    </Typography>

                    <Divider sx={{ my: 1.5 }} />
                    {/* Ensure course.instructors is an array before accessing length */}
                    {Array.isArray(course.instructors) && (
                        <InstructorsList>
                        <PersonIcon />
                        <Typography variant="body2" color="text.secondary">
                            {course.instructors.length} {course.instructors.length === 1 ? 'Instructor' : 'Instructors'}
                        </Typography>
                        </InstructorsList>
                    )}
                  </CourseCardContent>
                </CardActionArea>
              </CourseCard>
            </Grid>
          ))}
        </Grid>
      ) : (
        <NoCoursesBox>
          <SchoolIcon sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            No Courses Found
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            You don't have any courses yet. Create your first course to get started.
          </Typography>
          <Button
            variant="contained"
            color="primary"
            startIcon={<AddIcon />}
            onClick={() => setCreateDialogOpen(true)}
          >
            Create Course
          </Button>
        </NoCoursesBox>
      )}

      {/* Create Course Dialog */}
      <Dialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Create New Course</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            Enter the course ID and select a semester to create a new course.
          </DialogContentText>

          <Grid container spacing={2}>
            <Grid item xs={12}>
              <TextField
                autoFocus
                name="course_id" // This should match the key in newCourseData state
                label="Course ID"
                placeholder="e.g., CS601"
                fullWidth
                value={newCourseData.course_id}
                onChange={handleInputChange}
                margin="dense" // Changed from normal for tighter spacing in dialog
                required
                helperText="Unique identifier for the course (e.g., CS101, Intro to Programming)"
              />
            </Grid>

            <Grid item xs={12}>
              <FormControl fullWidth margin="dense" required> {/* Changed from normal */}
                <InputLabel id="semester-select-label">Semester</InputLabel>
                <Select
                  labelId="semester-select-label"
                  name="semester" // This should match the key in newCourseData state
                  value={newCourseData.semester}
                  onChange={handleInputChange}
                  label="Semester"
                >
                  {semesterOptions.map((semester) => (
                    <MenuItem key={semester} value={semester}>
                      {semester}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </DialogContent>

        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleCreateCourse}
            variant="contained"
            color="primary"
            disabled={!newCourseData.course_id || !newCourseData.semester}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Course Confirmation Dialog */}
      <ConfirmationDialog
        open={deleteDialogOpen}
        title="Delete Course"
        message={`Are you sure you want to delete the course "${courseToDelete?.course_id}" for ${courseToDelete?.semester}? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        confirmButtonProps={{ color: 'error' }}
        onConfirm={handleDeleteCourse}
        onCancel={() => {
          setDeleteDialogOpen(false);
          setCourseToDelete(null);
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