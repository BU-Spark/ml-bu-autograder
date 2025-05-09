/**
 * Course Detail Page for BU MET Autograder
 * Shows course information, instructors, assignments, and course transfer options
 * Located at: pages/course/[id]/index.js
 */

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
// Link component isn't used for navigation, onClick + router.push is used instead. Can remove if not needed elsewhere.
// import Link from 'next/link';
import {
  Alert,
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
// Assuming api.js is in src/api/index.js or similar
import { courseService, assignmentService } from '../../../api';
import CardSkeleton from '../../../components/CardSkeleton';
// ConfirmationDialog isn't used on this page, can be removed
// import ConfirmationDialog from '../../../components/ConfirmationDialog';

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
    <div role="tabpanel" hidden={value !== index} id={`course-tabpanel-${index}`} aria-labelledby={`course-tab-${index}`} {...other}>
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
};

// Course detail page component
export default function CourseDetail() {
  const router = useRouter();
  const { id: courseIdFromRoute, semester: semesterFromQuery } = router.query;

  const [course, setCourse] = useState(null);
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tabValue, setTabValue] = useState(0);
  const [transferDialogOpen, setTransferDialogOpen] = useState(false);
  const [transferData, setTransferData] = useState({ copyFromCourseId: '', copyFromCourseSemester: '' });
  const [availableCourses, setAvailableCourses] = useState([]);
  const [alertOpen, setAlertOpen] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [alertSeverity, setAlertSeverity] = useState('success');

  useEffect(() => {
    if (!router.isReady) return;
    if (!courseIdFromRoute || !semesterFromQuery) {
      setError("Course ID or Semester is missing from the URL.");
      setLoading(false);
      return;
    }

    let isMounted = true;
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        // Fetch course details
        const courseDataResultPromise = courseService.getCourse({ course_id: courseIdFromRoute, semester: semesterFromQuery });
        // Fetch assignments
        const assignmentsDataResultPromise = assignmentService.getAssignments({ course_id: courseIdFromRoute, semester: semesterFromQuery, include_questions: true });
        // Fetch all courses for transfer dropdown
        const allCoursesDataPromise = courseService.getCourses();

        const [courseDataResult, assignmentsDataResult, coursesResponse] = await Promise.all([
            courseDataResultPromise,
            assignmentsDataResultPromise,
            allCoursesDataPromise
        ]);

        if(isMounted) {
            setCourse(courseDataResult);
            setAssignments(Array.isArray(assignmentsDataResult) ? assignmentsDataResult : []);

            let allCoursesData = [];
            if (Array.isArray(coursesResponse)) { allCoursesData = coursesResponse; }
            else if (coursesResponse && typeof coursesResponse === 'object' && Array.isArray(coursesResponse.data)) { allCoursesData = coursesResponse.data; }
            else if (coursesResponse && typeof coursesResponse === 'object' && Array.isArray(coursesResponse.items)) { allCoursesData = coursesResponse.items; }
            else { console.warn('courseService.getCourses() format issue:', coursesResponse); }

            const filteredCourses = allCoursesData.filter(
                (c) => c && typeof c === 'object' && c.course_id && c.semester && !(c.course_id === courseIdFromRoute && c.semester === semesterFromQuery)
            );
            setAvailableCourses(filteredCourses);
        }

      } catch (err) {
        console.error('Error fetching course data:', err);
        if (isMounted) {
            let detailedMessage = err.message || 'Failed to load course data. Please try again.';
            if (err.response) {
                if (err.response.status === 404) { detailedMessage = `Course ${courseIdFromRoute} for semester ${semesterFromQuery} not found.`; }
                else if (err.response.data && err.response.data.detail) { detailedMessage = typeof err.response.data.detail === 'string' ? err.response.data.detail : JSON.stringify(err.response.data.detail); }
            }
            setError(detailedMessage);
        }
      } finally {
        if (isMounted) { setLoading(false); }
      }
    };
    fetchData();
    return () => { isMounted = false };
  }, [router.isReady, courseIdFromRoute, semesterFromQuery]);

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  // --- CORRECTED NAVIGATION ---
  const navigateToSubPage = (subPage) => {
    if (courseIdFromRoute && semesterFromQuery) {
        // Use singular "course" to match the folder structure
        router.push(`/course/${courseIdFromRoute}/${subPage}?semester=${semesterFromQuery}`);
    } else {
        console.error("Cannot navigate: Course ID or semester is missing.");
        setAlertMessage("Cannot navigate: Course information is missing.");
        setAlertSeverity("error");
        setAlertOpen(true);
    }
  };

  const handleCourseTransfer = async () => {
    if (!courseIdFromRoute || !semesterFromQuery || !transferData.copyFromCourseId || !transferData.copyFromCourseSemester) {
        setAlertMessage('Missing required information for course transfer.');
        setAlertSeverity('error');
        setAlertOpen(true);
        return;
    }
    try {
      await courseService.transferCourse({ current_course_id: courseIdFromRoute, current_semester: semesterFromQuery, copy_from_course_id: transferData.copyFromCourseId, copy_from_course_semester: transferData.copyFromCourseSemester });
      setTransferDialogOpen(false);
      setAlertMessage('Course materials and rubrics transfer initiated. Note: Backend may not have this feature implemented yet.');
      setAlertSeverity('success');
      setAlertOpen(true);
    } catch (error) {
      console.error('Error transferring course:', error);
      setAlertMessage(error.message || 'Failed to transfer course materials.');
      setAlertSeverity('error');
      setAlertOpen(true);
    }
  };

  const handleTransferInputChange = (event) => {
    const { name, value } = event.target;
    if (name === 'sourceCourse') {
      if (value) { const [copyFromCourseId, copyFromCourseSemester] = value.split('|'); setTransferData({ copyFromCourseId, copyFromCourseSemester }); }
      else { setTransferData({ copyFromCourseId: '', copyFromCourseSemester: '' }); }
    }
  };

  // --- Loading and Error States ---
  if (!router.isReady || loading) {
    return ( /* ... Loading Skeleton remains the same ... */
      <Box>
          <CourseHeader>
            <HeaderTitle><Box sx={{ display: 'flex', alignItems: 'center' }}><IconButton edge="start" sx={{ mr: 1 }}><ArrowBackIcon /></IconButton><Box><Typography variant="h4" component="h1"><CardSkeleton width={150} height={40} inline /></Typography><Typography variant="subtitle1" color="text.secondary"><CardSkeleton width={100} height={20} inline /></Typography></Box></Box></HeaderTitle>
            <HeaderActions><Button variant="outlined" startIcon={<TransferIcon />} disabled>Transfer Course</Button></HeaderActions>
          </CourseHeader>
          <Paper sx={{ mb: 3 }}><Tabs value={0}><Tab label="Overview" /></Tabs></Paper>
          <Grid container spacing={3}><Grid item xs={12} md={8}><CardSkeleton height={300} /></Grid><Grid item xs={12} md={4}><CardSkeleton height={300} /></Grid><Grid item xs={12}><CardSkeleton height={200} /></Grid></Grid>
      </Box>
    );
  }
  if (error) {
    return ( /* ... Error display remains the same ... */
      <Box sx={{ py: 3, textAlign: 'center' }}>
        <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>
        <Button variant="outlined" startIcon={<ArrowBackIcon />} onClick={() => router.push('/courses')}>Back to Courses</Button>
      </Box>
    );
  }
  if (!course) {
    return ( /* ... No course found display remains the same ... */
        <Box sx={{ py: 3, textAlign: 'center' }}>
            <Typography>Course not found or failed to load.</Typography>
            <Button variant="outlined" startIcon={<ArrowBackIcon />} onClick={() => router.push('/courses')} sx={{mt: 2}}>Back to Courses</Button>
        </Box>
    );
  }

  // --- Main Return JSX ---
  return (
    <Box>
      <CourseHeader>
        <HeaderTitle>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            {/* Corrected Back Button Path (assuming /courses is the list page) */}
            <IconButton edge="start" aria-label="back to courses" onClick={() => router.push('/courses')} sx={{ mr: 1 }}>
              <ArrowBackIcon />
            </IconButton>
            <Box>
              <Typography variant="h4" component="h1">{course.course_id}</Typography>
              <Typography variant="subtitle1" color="text.secondary">{course.semester}</Typography>
            </Box>
          </Box>
        </HeaderTitle>
        <HeaderActions>
          <Button variant="outlined" startIcon={<TransferIcon />} onClick={() => setTransferDialogOpen(true)} disabled={availableCourses.length === 0}>Transfer Course</Button>
        </HeaderActions>
      </CourseHeader>

      <Paper sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange} variant="scrollable" scrollButtons="auto" aria-label="course tabs">
          <Tab label="Overview" icon={<AssignmentIcon />} iconPosition="start" id="course-tab-0" aria-controls="course-tabpanel-0" />
          {/* Corrected onClick handlers to use navigateToSubPage */}
          <Tab label="Assignments" icon={<AssignmentIcon />} iconPosition="start" onClick={() => navigateToSubPage('assignments')} id="course-tab-1" aria-controls="course-tabpanel-1"/>
          <Tab label="Materials" icon={<MaterialsIcon />} iconPosition="start" onClick={() => navigateToSubPage('materials')} id="course-tab-2" aria-controls="course-tabpanel-2"/>
          <Tab label="Rubrics" icon={<RubricsIcon />} iconPosition="start" onClick={() => navigateToSubPage('rubrics')} id="course-tab-3" aria-controls="course-tabpanel-3"/>
          <Tab label="Grading" icon={<GradingIcon />} iconPosition="start" onClick={() => navigateToSubPage('grading')} id="course-tab-4" aria-controls="course-tabpanel-4"/>
          <Tab label="Instructors" icon={<PeopleIcon />} iconPosition="start" onClick={() => navigateToSubPage('instructors')} id="course-tab-5" aria-controls="course-tabpanel-5"/>
        </Tabs>
      </Paper>

      <TabPanel value={tabValue} index={0}>
        <Grid container spacing={3}>
            {/* Course Overview Card */}
            <Grid item xs={12} md={8}>
              <StyledCard>
                <CardContent>
                  <Typography variant="h6" gutterBottom>Course Overview</Typography>
                  <Divider sx={{ mb: 2 }} />
                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={6}><Typography variant="subtitle2" color="text.secondary">Course ID</Typography><Typography variant="body1" sx={{ mb: 2 }}>{course.course_id}</Typography></Grid>
                    <Grid item xs={12} sm={6}><Typography variant="subtitle2" color="text.secondary">Semester</Typography><Typography variant="body1" sx={{ mb: 2 }}>{course.semester}</Typography></Grid>
                    <Grid item xs={12}>
                      <Typography variant="subtitle2" color="text.secondary">Instructors</Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
                        {Array.isArray(course.instructors) && course.instructors.length > 0 ? ( course.instructors.map((instructorEmail) => (<Chip key={instructorEmail} label={instructorEmail} size="small" />)) ) : (<Typography variant="body2" color="text.secondary">No instructors listed.</Typography>)}
                      </Box>
                    </Grid>
                  </Grid>
                  <Divider sx={{ my: 2 }} /><Typography variant="subtitle1" gutterBottom>Assignment Statistics</Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={4}><Paper elevation={0} sx={{ p: 2, textAlign: 'center', bgcolor: 'background.default' }}><Typography variant="h5" color="primary">{assignments.length}</Typography><Typography variant="body2" color="text.secondary">Total Assignments</Typography></Paper></Grid>
                    <Grid item xs={12} sm={4}><Paper elevation={0} sx={{ p: 2, textAlign: 'center', bgcolor: 'background.default' }}><Typography variant="h5" color="primary">{assignments.reduce((sum, assignment) => sum + (assignment && Array.isArray(assignment.questions) ? assignment.questions.length : 0), 0)}</Typography><Typography variant="body2" color="text.secondary">Total Questions</Typography></Paper></Grid>
                    <Grid item xs={12} sm={4}><Paper elevation={0} sx={{ p: 2, textAlign: 'center', bgcolor: 'background.default' }}><Typography variant="h5" color="primary">{Array.isArray(course.instructors) ? course.instructors.length : 0}</Typography><Typography variant="body2" color="text.secondary">Instructors</Typography></Paper></Grid>
                  </Grid>
                </CardContent>
              </StyledCard>
            </Grid>
            {/* Quick Links Card */}
            <Grid item xs={12} md={4}>
              <StyledCard>
                <CardContent>
                  <Typography variant="h6" gutterBottom>Quick Links</Typography>
                  <Divider sx={{ mb: 2 }} />
                   {/* Corrected onClick handlers */}
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                    <Button variant="outlined" fullWidth startIcon={<AssignmentIcon />} onClick={() => navigateToSubPage('assignments')}>Manage Assignments</Button>
                    <Button variant="outlined" fullWidth startIcon={<MaterialsIcon />} onClick={() => navigateToSubPage('materials')}>Course Materials</Button>
                    <Button variant="outlined" fullWidth startIcon={<RubricsIcon />} onClick={() => navigateToSubPage('rubrics')}>Manage Rubrics</Button>
                    <Button variant="outlined" fullWidth startIcon={<GradingIcon />} onClick={() => navigateToSubPage('grading')}>Grade Submissions</Button>
                    <Button variant="outlined" fullWidth startIcon={<PeopleIcon />} onClick={() => navigateToSubPage('instructors')}>Manage Instructors</Button>
                  </Box>
                </CardContent>
              </StyledCard>
            </Grid>
            {/* Recent Assignments Card */}
            <Grid item xs={12}>
              <StyledCard>
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Typography variant="h6">Recent Assignments</Typography>
                    {assignments.length > 0 && (<Button onClick={() => navigateToSubPage('assignments')} size="small">View All</Button>)}
                  </Box>
                  <Divider sx={{ mb: 2 }} />
                  {assignments.length === 0 ? (
                    <Box sx={{ textAlign: 'center', py: 3 }}><Typography variant="body1" color="text.secondary">No assignments created yet.</Typography><Button variant="contained" onClick={() => navigateToSubPage('assignments')} sx={{ mt: 2 }}>Create Assignment</Button></Box>
                  ) : (
                    <Grid container spacing={2}>
                      {assignments.slice(0, 3).map((assignment) => (
                        assignment && assignment.assignment_id ? (
                            <Grid item xs={12} sm={4} key={assignment.assignment_id}>
                            <Paper elevation={0} sx={{ p: 2, bgcolor: 'background.default', borderRadius: 2 }}>
                                <Typography variant="subtitle1" noWrap>{assignment.assignment_id}</Typography>
                                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>{(assignment.questions?.length || 0)} questions</Typography>
                                {/* Corrected path for View Details button */}
                                <Button size="small" onClick={() => router.push(`/course/${courseIdFromRoute}/assignments?semester=${semesterFromQuery}&assignmentId=${assignment.assignment_id}`)}>
                                  View Details
                                </Button>
                            </Paper>
                            </Grid>
                        ) : null
                      ))}
                    </Grid>
                  )}
                </CardContent>
              </StyledCard>
            </Grid>
          </Grid>
      </TabPanel>

       {/* Transfer Dialog (remains the same) */}
      <Dialog open={transferDialogOpen} onClose={() => setTransferDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Transfer Course Materials</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>Select a source course to copy materials and rubrics from. This action will not affect the source course. Current assignments will not be overwritten. (Note: Backend implementation status should be confirmed.)</DialogContentText>
          <FormControl fullWidth margin="normal" required disabled={availableCourses.length === 0}>
            <InputLabel id="source-course-select-label">Source Course</InputLabel>
            <Select labelId="source-course-select-label" name="sourceCourse" value={(transferData.copyFromCourseId && transferData.copyFromCourseSemester) ? `${transferData.copyFromCourseId}|${transferData.copyFromCourseSemester}` : ''} onChange={handleTransferInputChange} label="Source Course">
              <MenuItem value=""><em>None</em></MenuItem>
              {availableCourses.map((c) => ( c && c.course_id && c.semester ? ( <MenuItem key={`${c.course_id}-${c.semester}`} value={`${c.course_id}|${c.semester}`}>{c.course_id} - {c.semester}</MenuItem>) : null ))}
            </Select>
          </FormControl>
          {availableCourses.length === 0 && (<Typography color="text.secondary" variant="caption">No other courses available to transfer from.</Typography>)}
        </DialogContent>
        <DialogActions><Button onClick={() => setTransferDialogOpen(false)}>Cancel</Button><Button onClick={handleCourseTransfer} variant="contained" color="primary" disabled={!transferData.copyFromCourseId || !transferData.copyFromCourseSemester}>Transfer</Button></DialogActions>
      </Dialog>

      {/* Alert Snackbar (remains the same) */}
      <Snackbar open={alertOpen} autoHideDuration={6000} onClose={() => setAlertOpen(false)} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert onClose={() => setAlertOpen(false)} severity={alertSeverity} variant="filled" sx={{ width: '100%' }}>{alertMessage}</Alert>
      </Snackbar>
    </Box>
  );
}