/**
 * Course Detail Page for BU MET Autograder
 * Shows course information, instructors, assignments, and course transfer options
 */

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import {
  Alert,
  Avatar,
  AvatarGroup,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
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
  Paper,
  Select,
  Snackbar,
  Tab,
  Tabs,
  Typography,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  ArrowBack as ArrowBackIcon,
  Assignment as AssignmentIcon,
  Description as MaterialsIcon,
  RuleFolder as RubricsIcon,
  People as PeopleIcon,
  Assessment as GradingIcon,
  SwapHoriz as TransferIcon,
} from '@mui/icons-material';
import { courseService, assignmentService, useUser } from '../../../api';
import CardSkeleton from '../../../components/CardSkeleton';

// Styled components
const CourseHeader = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  marginBottom: theme.spacing(3),
  [theme.breakpoints.down('sm')]: {
    flexDirection: 'column',
    alignItems: 'flex-start',
  },
}));

const HeaderTitle = styled(Box)(({ theme }) => ({
  flex: 1,
  [theme.breakpoints.down('sm')]: {
    width: '100%',
    marginBottom: theme.spacing(2),
  },
}));

const HeaderActions = styled(Box)(({ theme }) => ({
  display: 'flex',
  gap: theme.spacing(1),
  [theme.breakpoints.down('sm')]: {
    width: '100%',
    justifyContent: 'flex-start',
  },
}));

const StyledCard = styled(Card)(({ theme }) => ({
  height: '100%',
}));

const TabPanel = (props) => {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`course-tabpanel-${index}`}
      aria-labelledby={`course-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
};

// Course detail page component
export default function CourseDetail() {
  const router = useRouter();
  const { id: courseId, semester } = router.query;
  const { user } = useUser();

  // State for course data
  const [course, setCourse] = useState(null);
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // State for tabs
  const [tabValue, setTabValue] = useState(0);

  // State for course transfer dialog
  const [transferDialogOpen, setTransferDialogOpen] = useState(false);
  const [transferData, setTransferData] = useState({
    copyFromCourseId: '',
    copyFromCourseSemester: '',
  });
  const [availableCourses, setAvailableCourses] = useState([]);

  // State for alerts
  const [alertOpen, setAlertOpen] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [alertSeverity, setAlertSeverity] = useState('success');

  // Fetch course data and assignments
  useEffect(() => {
    const fetchData = async () => {
      // --- Ensure courseId and semester are available ---
      if (!courseId || !semester) {
        console.log("Course ID or Semester missing from query.");
        // Optionally set an error state or return early
        // setError("Course ID or Semester not found.");
        setLoading(false); // Stop loading if we can't proceed
        return; // Stop execution if parameters are missing
      }
      // --- End Check ---

      setLoading(true);
      setError(null);
      setCourse(null);
      setAssignments([]);
      setAvailableCourses([]); // Reset available courses

      try {
        // Fetch course details
        const courseData = await courseService.getCourse(courseId, semester);
        // Basic check if courseData is valid before setting
        if (courseData && typeof courseData === 'object') {
             setCourse(courseData);
        } else {
            console.warn("Received invalid course data:", courseData);
            // Handle error case - maybe set an error message
            setError(`Failed to load course details for ${courseId} - ${semester}.`);
        }


        // Fetch assignments for this course
        const assignmentsData = await assignmentService.getAssignments(courseId, semester);
        if (Array.isArray(assignmentsData)) {
          setAssignments(assignmentsData);
        } else {
          console.warn("assignmentService.getAssignments did not return an array. Received:", assignmentsData);
          setAssignments([]); // Default to empty array
        }

        // Fetch available courses for transfer
        const coursesData = await courseService.getCourses();
        console.log('Raw coursesData received:', coursesData); // Keep this for debugging

        // --- Logic to handle different coursesData structures ---
        let coursesArray = []; // Initialize as empty array

        if (Array.isArray(coursesData)) {
          // Case 1: coursesData is already the array we need
          coursesArray = coursesData;
          console.log('coursesData is an array.');
        } else if (coursesData && typeof coursesData === 'object') {
          // Case 2: coursesData is an object, check for nested array
          // Adjust the key ('data', 'courses', etc.) based on your actual API response structure
          if (Array.isArray(coursesData.data)) { // Example: check for 'data' key
             coursesArray = coursesData.data;
             console.log('Found courses array under coursesData.data');
          } else if (Array.isArray(coursesData.courses)) { // Example: check for 'courses' key
             coursesArray = coursesData.courses;
             console.log('Found courses array under coursesData.courses');
          }
           // Add more 'else if' checks here if your API uses other keys like 'items', 'results', etc.
          else {
             console.warn("coursesData is an object, but no standard array key ('data', 'courses', etc.) was found. Received:", coursesData);
             // coursesArray remains empty
          }
        } else {
          // Case 3: coursesData is neither an array nor a recognized object containing one
          console.warn("courseService.getCourses returned unexpected data type or structure. Received:", coursesData);
          // coursesArray remains empty
        }
        // --- End structure handling logic ---

        // Now filter the extracted (or empty) coursesArray
        // Added check for valid course object 'c' inside filter
        const filteredCourses = coursesArray.filter(
          (c) => c && typeof c === 'object' && c.course_id && c.semester && !(c.course_id === courseId && c.semester === semester)
        );
        setAvailableCourses(filteredCourses);
        console.log('Filtered available courses:', filteredCourses);


      } catch (err) {
        console.error('Error fetching data in CourseDetail:', err);
        setError(err.message || 'Failed to load course data');
        // Ensure states are reset on error
        setCourse(null);
        setAssignments([]);
        setAvailableCourses([]);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [courseId, semester]); // Dependency array includes courseId and semester

  // Handle tab change
  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  // Navigate to other course tabs
  const navigateToTab = (tab) => {
    router.push(`/course/${courseId}/${tab}?semester=${semester}`);
  };

  // Handle course transfer
  const handleCourseTransfer = async () => {
    if (!transferData.copyFromCourseId || !transferData.copyFromCourseSemester) {
        setAlertMessage('Please select a source course to transfer from.');
        setAlertSeverity('warning');
        setAlertOpen(true);
        return;
    }

    try {
      await courseService.transferCourse(
        courseId,
        semester,
        transferData.copyFromCourseId,
        transferData.copyFromCourseSemester
      );

      // Close dialog
      setTransferDialogOpen(false);

      // Show success alert
      setAlertMessage('Course materials and rubrics transferred successfully. Refreshing data...');
      setAlertSeverity('success');
      setAlertOpen(true);

      // --- Refresh data after successful transfer ---
      setLoading(true); // Show loading indicator while refreshing
      setError(null);
      try {
        const updatedCourseData = await courseService.getCourse(courseId, semester);
         if (updatedCourseData && typeof updatedCourseData === 'object') {
             setCourse(updatedCourseData);
        } else {
             console.warn("Received invalid course data after transfer:", updatedCourseData);
             // Keep old data or set an error? Decide based on desired UX
        }

        const updatedAssignmentsData = await assignmentService.getAssignments(courseId, semester);
        if (Array.isArray(updatedAssignmentsData)) {
          setAssignments(updatedAssignmentsData);
        } else {
          console.warn("Assignments data invalid after transfer:", updatedAssignmentsData);
          setAssignments([]); // Reset if invalid
        }
      } catch(refreshError) {
          console.error("Error refreshing data after transfer:", refreshError);
          setAlertMessage('Transfer succeeded, but failed to refresh data automatically.');
          setAlertSeverity('warning');
          setAlertOpen(true); // Show warning about refresh failure
      } finally {
          setLoading(false); // Hide loading indicator
      }
      // --- End data refresh ---

    } catch (error) {
      console.error('Error transferring course:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to transfer course materials';
      setAlertMessage(errorMessage);
      setAlertSeverity('error');
      setAlertOpen(true);
    }
  };

  // Handle form input changes for transfer
  const handleTransferInputChange = (event) => {
    const { name, value } = event.target;

    if (name === 'sourceCourse') {
        if (value) { // Ensure a value is selected
            // Parse the combined value (courseId|semester)
            const [copyFromCourseId, copyFromCourseSemester] = value.split('|');
            setTransferData({
              copyFromCourseId,
              copyFromCourseSemester,
            });
        } else {
             // Handle case where user deselects or selects placeholder
             setTransferData({
                copyFromCourseId: '',
                copyFromCourseSemester: '',
             });
        }
    }
    // Removed the 'else' block - this component only manages 'sourceCourse' selection
    // If you add more form fields, you might need it back.
  };

  // Calculate total questions (safely)
  const totalQuestions = Array.isArray(assignments)
    ? assignments.reduce((total, assignment) => {
        const questions = assignment?.questions; // Safely access questions
        return total + (Array.isArray(questions) ? questions.length : 0); // Add length only if it's an array
      }, 0)
    : 0; // Default to 0 if assignments is not an array

  return (
    <Box>
      <CourseHeader>
        <HeaderTitle>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <IconButton
              edge="start"
              aria-label="back to courses"
              onClick={() => router.push('/courses')}
              sx={{ mr: 1 }}
            >
              <ArrowBackIcon />
            </IconButton>

            <Box>
              <Typography variant="h4" component="h1">
                {loading && !course ? 'Loading...' : course?.course_id || 'Course Detail'}
              </Typography>

              <Typography variant="subtitle1" color="text.secondary">
                {loading && !course ? 'Loading...' : course?.semester}
              </Typography>
            </Box>
          </Box>
        </HeaderTitle>

        <HeaderActions>
          {/* Only show transfer button if there are available courses to transfer from */}
          {Array.isArray(availableCourses) && availableCourses.length > 0 && (
            <Button
                variant="outlined"
                startIcon={<TransferIcon />}
                onClick={() => setTransferDialogOpen(true)}
                disabled={loading} // Disable while loading initial data
            >
                Transfer Course
            </Button>
           )}
        </HeaderActions>
      </CourseHeader>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          variant="scrollable"
          scrollButtons="auto"
          aria-label="course tabs"
        >
          <Tab label="Overview" icon={<AssignmentIcon />} iconPosition="start" />
          <Tab
            label="Assignments"
            icon={<AssignmentIcon />}
            iconPosition="start"
            onClick={() => navigateToTab('assignments')}
          />
          <Tab
            label="Materials"
            icon={<MaterialsIcon />}
            iconPosition="start"
            onClick={() => navigateToTab('materials')}
          />
          <Tab
            label="Rubrics"
            icon={<RubricsIcon />}
            iconPosition="start"
            onClick={() => navigateToTab('rubrics')}
          />
          <Tab
            label="Grading"
            icon={<GradingIcon />}
            iconPosition="start"
            onClick={() => navigateToTab('grading')}
          />
          <Tab
            label="Instructors"
            icon={<PeopleIcon />}
            iconPosition="start"
            onClick={() => navigateToTab('instructors')}
          />
        </Tabs>
      </Paper>

      <TabPanel value={tabValue} index={0}>
        {loading ? (
          <Grid container spacing={3}>
            <Grid item xs={12} md={8}>
              <CardSkeleton height={300} />
            </Grid>
            <Grid item xs={12} md={4}>
              <CardSkeleton height={300} />
            </Grid>
          </Grid>
        ) : !course ? ( // Handle case where loading finished but course is still null (e.g., fetch failed)
           <Alert severity="warning">Could not load course details.</Alert>
        ) : (
          <Grid container spacing={3}>
            {/* Course Overview */}
            <Grid item xs={12} md={8}>
              <StyledCard>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Course Overview
                  </Typography>

                  <Divider sx={{ mb: 2 }} />

                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={6}>
                      <Typography variant="subtitle2" color="text.secondary">
                        Course ID {courseId}
                      </Typography>
                      <Typography variant="body1" sx={{ mb: 2 }}>
                        {course?.course_id}
                        {console.log(course?.course_id)}
                      </Typography>
                    </Grid>

                    <Grid item xs={12} sm={6}>
                      <Typography variant="subtitle2" color="text.secondary">
                        Semester {semester}
                      </Typography>
                      <Typography variant="body1" sx={{ mb: 2 }}>
                        {course?.semester}
                        {console.log(course?.semester)}
                      </Typography>
                    </Grid>

                    <Grid item xs={12}>
                      <Typography variant="subtitle2" color="text.secondary">
                        Instructors
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
                       {/* Ensure instructors is an array before mapping */}
                      {Array.isArray(course?.instructors) && course.instructors.map((instructor) => (
                          <Chip
                            key={instructor} // Assuming instructor names are unique within a course
                            label={instructor}
                            size="small"
                            avatar={
                              <Avatar sx={{ width: 24, height: 24, fontSize: '0.8rem' }}>
                                {/* Add check for instructor being a non-empty string */}
                                {instructor && typeof instructor === 'string' ? instructor.charAt(0).toUpperCase() : '?'}
                              </Avatar>
                            }
                          />
                        ))}
                        {(!Array.isArray(course?.instructors) || course.instructors.length === 0) && (
                             <Typography variant="body2" color="text.secondary">No instructors assigned.</Typography>
                        )}
                      </Box>
                    </Grid>
                  </Grid>

                  <Divider sx={{ my: 2 }} />

                  <Typography variant="subtitle1" gutterBottom>
                    Assignment Statistics
                  </Typography>

                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={4}>
                      <Paper
                        elevation={0}
                        sx={{
                          p: 2,
                          textAlign: 'center',
                          bgcolor: 'background.default',
                        }}
                      >
                        <Typography variant="h5" color="primary">
                          {/* Ensure assignments is an array before getting length */}
                          {Array.isArray(assignments) ? assignments.length : 0}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Total Assignments
                        </Typography>
                      </Paper>
                    </Grid>

                    <Grid item xs={12} sm={4}>
                      <Paper
                        elevation={0}
                        sx={{
                          p: 2,
                          textAlign: 'center',
                          bgcolor: 'background.default',
                        }}
                      >
                        <Typography variant="h5" color="primary">
                          {totalQuestions}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Total Questions
                        </Typography>
                      </Paper>
                    </Grid>

                    <Grid item xs={12} sm={4}>
                      <Paper
                        elevation={0}
                        sx={{
                          p: 2,
                          textAlign: 'center',
                          bgcolor: 'background.default',
                        }}
                      >
                        <Typography variant="h5" color="primary">
                          {Array.isArray(course?.instructors) ? course.instructors.length : 0}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Instructors
                        </Typography>
                      </Paper>
                    </Grid>
                  </Grid>
                </CardContent>
              </StyledCard>
            </Grid>

            {/* Quick Links */}
            <Grid item xs={12} md={4}>
              <StyledCard>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Quick Links
                  </Typography>

                  <Divider sx={{ mb: 2 }} />

                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                    <Button
                      variant="outlined"
                      fullWidth
                      startIcon={<AssignmentIcon />}
                      component={Link}
                      href={`/course/${courseId}/assignments?semester=${semester}`}
                      disabled={!courseId || !semester} // Disable if IDs are missing
                    >
                      Manage Assignments
                    </Button>

                    <Button
                      variant="outlined"
                      fullWidth
                      startIcon={<MaterialsIcon />}
                      component={Link}
                      href={`/course/${courseId}/materials?semester=${semester}`}
                      disabled={!courseId || !semester}
                    >
                      Course Materials
                    </Button>

                    <Button
                      variant="outlined"
                      fullWidth
                      startIcon={<RubricsIcon />}
                      component={Link}
                      href={`/course/${courseId}/rubrics?semester=${semester}`}
                      disabled={!courseId || !semester}
                    >
                      Manage Rubrics
                    </Button>

                    <Button
                      variant="outlined"
                      fullWidth
                      startIcon={<GradingIcon />}
                      component={Link}
                      href={`/course/${courseId}/grading?semester=${semester}`}
                      disabled={!courseId || !semester}
                    >
                      Grade Submissions
                    </Button>

                    <Button
                      variant="outlined"
                      fullWidth
                      startIcon={<PeopleIcon />}
                      component={Link}
                      href={`/course/${courseId}/instructors?semester=${semester}`}
                      disabled={!courseId || !semester}
                    >
                      Manage Instructors
                    </Button>
                  </Box>
                </CardContent>
              </StyledCard>
            </Grid>

            {/* Recent Assignments */}
            <Grid item xs={12}>
              <StyledCard>
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Typography variant="h6">
                      Recent Assignments
                    </Typography>

                    {/* Only show View All if there are assignments */}
                    {Array.isArray(assignments) && assignments.length > 0 && (
                         <Button
                            component={Link}
                            href={`/course/${courseId}/assignments?semester=${semester}`}
                            size="small"
                            disabled={!courseId || !semester}
                         >
                            View All
                         </Button>
                    )}
                  </Box>

                  <Divider sx={{ mb: 2 }} />

                  {/* Check if assignments is an array AND has items */}
                  {Array.isArray(assignments) && assignments.length > 0 ? (
                    <Grid container spacing={2}>
                      {assignments.slice(0, 3).map((assignment) => (
                        // Add a check that assignment is a valid object before rendering
                        assignment && typeof assignment === 'object' && assignment.assignment_id ? (
                          <Grid item xs={12} sm={4} key={assignment.assignment_id}>
                            <Paper
                              elevation={0}
                              sx={{
                                p: 2,
                                bgcolor: 'background.default',
                                borderRadius: 2,
                                height: '100%', // Ensure papers have consistent height
                                display: 'flex',
                                flexDirection: 'column',
                                justifyContent: 'space-between',
                              }}
                            >
                              <Box>
                                <Typography variant="subtitle1" noWrap sx={{ mb: 0.5 }}>
                                  {assignment.assignment_title || 'Untitled Assignment'}
                                </Typography>
                                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                                  {/* Check questions is array before accessing length */}
                                  {Array.isArray(assignment.questions) ? assignment.questions.length : 0} questions
                                </Typography>
                              </Box>
                              <Button
                                size="small"
                                component={Link}
                                href={`/course/${courseId}/assignments/${assignment.assignment_id}?semester=${semester}`} // Link directly to assignment detail
                                disabled={!courseId || !semester}
                              >
                                View Details
                              </Button>
                            </Paper>
                          </Grid>
                        ) : null // Render nothing if assignment object is invalid or missing id
                      ))}
                    </Grid>
                  ) : (
                    // This is the case where assignments array is empty or not an array
                    <Box sx={{ textAlign: 'center', py: 3 }}>
                      <Typography variant="body1" color="text.secondary">
                        No assignments created yet for this course.
                      </Typography>
                      <Button
                        variant="contained"
                        component={Link}
                        href={`/course/${courseId}/assignments/?semester=${semester}&assignment=`} // Link to create new assignment

                        sx={{ mt: 2 }}
                        disabled={!courseId || !semester}
                      >
                        Create Assignment
                      </Button>
                    </Box>
                  )}
                </CardContent>
              </StyledCard>
            </Grid>
          </Grid>
        )}
      </TabPanel>

      {/* Course Transfer Dialog */}
      <Dialog
        open={transferDialogOpen}
        onClose={() => setTransferDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Transfer Course Materials</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            Select a source course to copy materials and rubrics from. Existing assignments in
             <Typography component="span" fontWeight="bold">{` ${course?.course_id} (${course?.semester}) `}</Typography>
             will not be affected. This action cannot be undone.
          </DialogContentText>

          <FormControl fullWidth margin="normal" required>
            <InputLabel id="source-course-select-label">Source Course</InputLabel>
            <Select
              labelId="source-course-select-label"
              id="source-course-select" // Added id for accessibility
              name="sourceCourse"
              // Use empty string if IDs are not set, otherwise combine them
              value={transferData.copyFromCourseId && transferData.copyFromCourseSemester
                     ? `${transferData.copyFromCourseId}|${transferData.copyFromCourseSemester}`
                     : ''}
              onChange={handleTransferInputChange}
              label="Source Course"
            >
              {/* Optional: Add a placeholder/default option */}
               <MenuItem value="" disabled>
                    <em>Select a course...</em>
               </MenuItem>
              {/* Ensure availableCourses is an array before mapping */}
              {Array.isArray(availableCourses) && availableCourses.map((c) => (
                // Add check for valid course object and properties
                c && typeof c === 'object' && c.course_id && c.semester ? (
                  <MenuItem
                    key={`${c.course_id}-${c.semester}`}
                    value={`${c.course_id}|${c.semester}`}
                  >
                    {c.course_id} - {c.semester}
                  </MenuItem>
                ) : null // Render nothing for invalid course entries
              ))}
            </Select>
          </FormControl>
        </DialogContent>

        <DialogActions>
          <Button onClick={() => setTransferDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleCourseTransfer}
            variant="contained"
            color="primary"
            disabled={!transferData.copyFromCourseId || !transferData.copyFromCourseSemester || loading} // Disable if no selection or during loading
          >
            Transfer
          </Button>
        </DialogActions>
      </Dialog>

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