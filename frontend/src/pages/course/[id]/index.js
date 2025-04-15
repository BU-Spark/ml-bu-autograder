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
      if (!courseId || !semester) return;

      setLoading(true);
      try {
        // Fetch course details
        const courseData = await courseService.getCourse(courseId, semester);
        setCourse(courseData);

        // Fetch assignments for this course
        const assignmentsData = await assignmentService.getAssignments(courseId, semester);
        setAssignments(assignmentsData || []);

        // Fetch available courses for transfer
        const coursesData = await courseService.getCourses();
        // Filter out current course and only include courses with different semesters
        const filteredCourses = coursesData.filter(
          (c) => !(c.course_id === courseId && c.semester === semester)
        );
        setAvailableCourses(filteredCourses);

        setError(null);
      } catch (err) {
        console.error('Error fetching course data:', err);
        setError(err.message || 'Failed to load course data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [courseId, semester]);

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
      setAlertMessage('Course materials and rubrics transferred successfully');
      setAlertSeverity('success');
      setAlertOpen(true);

      // Refresh data
      const courseData = await courseService.getCourse(courseId, semester);
      setCourse(courseData);

      const assignmentsData = await assignmentService.getAssignments(courseId, semester);
      setAssignments(assignmentsData || []);
    } catch (error) {
      console.error('Error transferring course:', error);
      setAlertMessage(error.message || 'Failed to transfer course materials');
      setAlertSeverity('error');
      setAlertOpen(true);
    }
  };

  // Handle form input changes for transfer
  const handleTransferInputChange = (event) => {
    const { name, value } = event.target;

    if (name === 'sourceCourse') {
      // Parse the combined value (courseId|semester)
      const [copyFromCourseId, copyFromCourseSemester] = value.split('|');
      setTransferData({
        copyFromCourseId,
        copyFromCourseSemester,
      });
    } else {
      setTransferData({
        ...transferData,
        [name]: value,
      });
    }
  };

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
                {loading ? 'Loading...' : course?.course_id}
              </Typography>

              <Typography variant="subtitle1" color="text.secondary">
                {loading ? 'Loading...' : course?.semester}
              </Typography>
            </Box>
          </Box>
        </HeaderTitle>

        <HeaderActions>
          <Button
            variant="outlined"
            startIcon={<TransferIcon />}
            onClick={() => setTransferDialogOpen(true)}
          >
            Transfer Course
          </Button>
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
                        Course ID
                      </Typography>
                      <Typography variant="body1" sx={{ mb: 2 }}>
                        {course?.course_id}
                      </Typography>
                    </Grid>

                    <Grid item xs={12} sm={6}>
                      <Typography variant="subtitle2" color="text.secondary">
                        Semester
                      </Typography>
                      <Typography variant="body1" sx={{ mb: 2 }}>
                        {course?.semester}
                      </Typography>
                    </Grid>

                    <Grid item xs={12}>
                      <Typography variant="subtitle2" color="text.secondary">
                        Instructors
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
                      {(course?.instructors || []).map((instructor) => (
                          <Chip
                            key={instructor}
                            label={instructor}
                            size="small"
                            avatar={
                              <Avatar>
                                {instructor.charAt(0).toUpperCase()}
                              </Avatar>
                            }
                          />
                        ))}
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
                          {assignments.length}
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
                          {/* Add || [] before .reduce */}
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
                          {/* This would come from a real API call */}
                          {course?.instructors?.length || 0}
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
                    >
                      Manage Assignments
                    </Button>

                    <Button
                      variant="outlined"
                      fullWidth
                      startIcon={<MaterialsIcon />}
                      component={Link}
                      href={`/course/${courseId}/materials?semester=${semester}`}
                    >
                      Course Materials
                    </Button>

                    <Button
                      variant="outlined"
                      fullWidth
                      startIcon={<RubricsIcon />}
                      component={Link}
                      href={`/course/${courseId}/rubrics?semester=${semester}`}
                    >
                      Manage Rubrics
                    </Button>

                    <Button
                      variant="outlined"
                      fullWidth
                      startIcon={<GradingIcon />}
                      component={Link}
                      href={`/course/${courseId}/grading?semester=${semester}`}
                    >
                      Grade Submissions
                    </Button>

                    <Button
                      variant="outlined"
                      fullWidth
                      startIcon={<PeopleIcon />}
                      component={Link}
                      href={`/course/${courseId}/instructors?semester=${semester}`}
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

                    <Button
                      component={Link}
                      href={`/course/${courseId}/assignments?semester=${semester}`}
                      size="small"
                    >
                      View All
                    </Button>
                  </Box>

                  <Divider sx={{ mb: 2 }} />

                  {assignments.length === 0 ? (
                    <Box sx={{ textAlign: 'center', py: 3 }}>
                      <Typography variant="body1" color="text.secondary">
                        No assignments created yet.
                      </Typography>
                      <Button
                        variant="contained"
                        component={Link}
                        href={`/course/${courseId}/assignments?semester=${semester}`}
                        sx={{ mt: 2 }}
                      >
                        Create Assignment
                      </Button>
                    </Box>
                  ) : (
                    <Grid container spacing={2}>
                      {assignment.length == 0 || assignments.slice(0, 3).map((assignment) => (
                        <Grid item xs={12} sm={4} key={assignment.assignment_id}>
                          <Paper
                            elevation={0}
                            sx={{
                              p: 2,
                              bgcolor: 'background.default',
                              borderRadius: 2,
                            }}
                          >
                            <Typography variant="subtitle1" noWrap>
                              {assignment.assignment_title || 'Untitled Assignment'}
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                              {assignment.questions?.length || 0} questions
                            </Typography>
                            <Button
                              size="small"
                              component={Link}
                              href={`/course/${courseId}/assignments?semester=${semester}&assignmentId=${assignment.assignment_id}`}
                            >
                              View Details
                            </Button>
                          </Paper>
                        </Grid>
                      ))}
                    </Grid>
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
            Select a source course to copy materials, assignments, and rubrics from.
            This will not affect the source course.
          </DialogContentText>

          <FormControl fullWidth margin="normal" required>
            <InputLabel id="source-course-select-label">Source Course</InputLabel>
            <Select
              labelId="source-course-select-label"
              name="sourceCourse"
              value={`${transferData.copyFromCourseId}|${transferData.copyFromCourseSemester}`}
              onChange={handleTransferInputChange}
              label="Source Course"
            >
              {availableCourses.map((course) => (
                <MenuItem
                  key={`${course.course_id}-${course.semester}`}
                  value={`${course.course_id}|${course.semester}`}
                >
                  {course.course_id} - {course.semester}
                </MenuItem>
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
            disabled={!transferData.copyFromCourseId || !transferData.copyFromCourseSemester}
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