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
import { useCourses, courseService } from '../api';
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
  const { courses, isLoading, isError, mutate } = useCourses();

  // State for create course dialog
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [courseData, setCourseData] = useState({
    course_id: '',
    semester: '',
  });

  // State for delete course dialog
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [courseToDelete, setCourseToDelete] = useState(null);

  // State for alerts
  const [alertOpen, setAlertOpen] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [alertSeverity, setAlertSeverity] = useState('success');

  // Generate semester options (current semester + 2 future semesters)
  const getSemesterOptions = () => {
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth();

    let semesters = [];
    let currentYear = year;
    let seasons = ['Spring', 'Summer', 'Fall'];

    // Determine current season
    let currentSeasonIndex;
    if (month < 4) currentSeasonIndex = 0; // Spring
    else if (month < 8) currentSeasonIndex = 1; // Summer
    else currentSeasonIndex = 2; // Fall

    // Add current semester and next 4 semesters
    for (let i = 0; i < 5; i++) {
      const seasonIndex = (currentSeasonIndex + i) % 3;
      const yearOffset = Math.floor((currentSeasonIndex + i) / 3);
      semesters.push(`${seasons[seasonIndex]} ${currentYear + yearOffset}`);
    }

    return semesters;
  };

  const semesterOptions = getSemesterOptions();

  // Handle creating a new course
  const handleCreateCourse = async () => {
    try {
      await courseService.createCourse(courseData.semester, {
        course_id: courseData.course_id,
        semester: courseData.semester,
        instructors: [], // Will be populated with current user
      });

      // Refresh course list
      mutate();

      // Reset form and close dialog
      setCourseData({
        course_id: '',
        semester: '',
      });
      setCreateDialogOpen(false);

      // Show success alert
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

    try {
      await courseService.deleteCourse(courseToDelete.course_id, courseToDelete.semester);

      // Refresh course list
      mutate();

      // Close dialog
      setDeleteDialogOpen(false);
      setCourseToDelete(null);

      // Show success alert
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
    event.stopPropagation();
    setCourseToDelete(course);
    setDeleteDialogOpen(true);
  };

  // Navigate to course detail page
  const navigateToCourse = (course) => {
    router.push(`/course/${course.course_id}?semester=${course.semester}`);
  };

  // Handle form input changes
  const handleInputChange = (event) => {
    const { name, value } = event.target;
    setCourseData({
      ...courseData,
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
          Failed to load courses. Please try again.
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
                      <Typography variant="h6" component="h2" noWrap>
                        {course.course_id}
                      </Typography>
                      <IconButton
                        size="small"
                        color="error"
                        aria-label="delete course"
                        onClick={(e) => openDeleteDialog(course, e)}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </CourseCardHeader>

                    <Typography variant="subtitle2" color="text.secondary">
                      {course.semester}
                    </Typography>

                    <Divider sx={{ my: 1.5 }} />

                    <InstructorsList>
                      <PersonIcon />
                      <Typography variant="body2" color="text.secondary">
                        {course.instructors.length} {course.instructors.length === 1 ? 'Instructor' : 'Instructors'}
                      </Typography>
                    </InstructorsList>
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
                name="course_id"
                label="Course ID"
                placeholder="e.g., CS601"
                fullWidth
                value={courseData.course_id}
                onChange={handleInputChange}
                margin="normal"
                required
                helperText="Enter the course ID or name"
              />
            </Grid>

            <Grid item xs={12}>
              <FormControl fullWidth margin="normal" required>
                <InputLabel id="semester-select-label">Semester</InputLabel>
                <Select
                  labelId="semester-select-label"
                  name="semester"
                  value={courseData.semester}
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
            disabled={!courseData.course_id || !courseData.semester}
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