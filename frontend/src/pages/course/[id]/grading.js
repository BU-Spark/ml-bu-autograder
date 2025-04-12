import React, { useState, useEffect, useCallback } from 'react'; // Added useCallback
import { useRouter } from 'next/router';
import {
  Alert,
  Badge,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  FormControl,
  Grid,
  IconButton,
  InputAdornment, // Added for search icon
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Snackbar,
  Tab,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  ArrowBack as ArrowBackIcon,
  Assignment as AssignmentIcon,
  AssignmentTurnedIn as GradedIcon,
  Assessment as GradeIcon, // Use this for the button
  Refresh as RefreshIcon,
  Search as SearchIcon,
  FilterList as FilterIcon,
  // PersonSearch as StudentSearchIcon, // Using SearchIcon now
  QuestionAnswer as QuestionIcon,
  CheckCircleOutline as CheckCircleOutlineIcon, // For graded status
  HourglassEmpty as HourglassEmptyIcon, // For ungraded status
} from '@mui/icons-material';
// Assuming these exist and are correctly implemented
import { assignmentService, responseService } from '../../../api';
import CardSkeleton from '../../../components/CardSkeleton'; // Assuming this exists
import GradingModeSelect from '../../../components/GradingModeSelect'; // Assuming this exists
import SelectableList from '../../../components/SelectableList'; // Assuming this exists
import ConfirmationDialog from '../../../components/ConfirmationDialog'; // Assuming this exists

// Styled components
const StyledCard = styled(Card)(({ theme }) => ({
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
}));

const GradingActionCard = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  marginBottom: theme.spacing(3),
}));

const ResponseCard = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  marginBottom: theme.spacing(3),
  borderLeft: `4px solid ${theme.palette.primary.main}`,
}));

// Define custom colors if not in theme
const defaultTheme = {
  palette: {
    custom: {
      gradeA: '#4caf50', // Green
      gradeB: '#8bc34a', // Light Green
      gradeC: '#ffeb3b', // Yellow
      gradeD: '#ff9800', // Orange
      gradeF: '#f44336', // Red
    },
  },
};

const GradeCard = styled(Paper)(({ theme, gradePercent = 0 }) => {
  const effectiveTheme = { ...defaultTheme, ...theme }; // Merge default theme
  const { gradeA, gradeB, gradeC, gradeD, gradeF } = effectiveTheme.palette.custom;
  let borderColor = theme.palette?.divider || '#e0e0e0'; // Default border

  if (gradePercent >= 90) borderColor = gradeA;
  else if (gradePercent >= 80) borderColor = gradeB;
  else if (gradePercent >= 70) borderColor = gradeC;
  else if (gradePercent >= 60) borderColor = gradeD;
  else if (gradePercent > 0) borderColor = gradeF; // Only color if grade > 0

  return {
      padding: theme.spacing(3),
      marginBottom: theme.spacing(3),
      borderLeft: `4px solid ${borderColor}`,
  };
});

// Tab Panel Helper
const TabPanel = (props) => {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`grading-tabpanel-${index}`}
      aria-labelledby={`grading-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
};

// Main component
export default function GradingDashboard() {
  const router = useRouter();
  const { id: courseId, semester } = router.query; // These are strings

  // State for assignments and submissions
  const [assignments, setAssignments] = useState([]);
  const [selectedAssignment, setSelectedAssignment] = useState(null); // Holds full Assignment object
  const [responses, setResponses] = useState([]); // Holds raw GradedStudentResponse[] from API
  const [filteredResponses, setFilteredResponses] = useState([]); // Holds responses after filtering
  const [selectedResponse, setSelectedResponse] = useState(null); // Holds single GradedStudentResponse

  // State for loading and error
  const [loadingAssignments, setLoadingAssignments] = useState(true);
  const [loadingResponses, setLoadingResponses] = useState(false);
  const [grading, setGrading] = useState(false); // True when grading API call is in progress
  const [error, setError] = useState(null); // General page/fetch error

  // State for filters and search
  const [questionFilter, setQuestionFilter] = useState('all'); // 'all' or question_index (string)
  const [gradingStatusFilter, setGradingStatusFilter] = useState('all'); // 'all', 'graded', 'ungraded'
  const [studentSearch, setStudentSearch] = useState('');

  // State for grading action panel
  const [gradingMode, setGradingMode] = useState('ungraded'); // 'ungraded', 'all', 'specific'
  const [selectedStudents, setSelectedStudents] = useState([]); // List of student_id strings for 'specific' mode
  const [confirmGradingOpen, setConfirmGradingOpen] = useState(false);

  // State for response/grade tabs
  const [tabValue, setTabValue] = useState(0);

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

  // --- Data Fetching ---

  // Fetch responses for selected assignment (now includes semester, courseId)
  const fetchResponses = useCallback(async (assignmentId, questionIndex = null) => {
      if (!semester || !courseId || !assignmentId) {
          console.warn("Missing semester, courseId, or assignmentId for fetching responses.");
          setResponses([]);
          // setFilteredResponses([]); // Filter useEffect will handle this
          return [];
      }
      setLoadingResponses(true);
      setError(null);
      try {
          // <<< Pass semester and courseId >>>
          const responsesData = await responseService.getResponses(
              semester,
              courseId,
              assignmentId,
              questionIndex,
              null // studentId filter applied locally
          );
          setResponses(responsesData || []);
          setSelectedResponse(null);
          setSelectedStudents([]);
          return responsesData || [];
      } catch (err) {
          console.error('Error fetching responses:', err);
          const errorMsg = err.message || 'Failed to load responses';
          setError(errorMsg);
          showAlert(errorMsg, 'error');
          setResponses([]);
          return [];
      } finally {
          setLoadingResponses(false);
      }
  }, [semester, courseId, showAlert]); // Dependencies

  // Fetch assignments list
  useEffect(() => {
    const fetchAssignments = async () => {
      if (!courseId || !semester) {
        setLoadingAssignments(false);
        return;
      }
      setLoadingAssignments(true);
      setError(null);
      try {
        const assignmentsData = await assignmentService.getAssignments(courseId, semester);
        setAssignments(assignmentsData || []);
        // Automatically select and fetch responses for the first assignment if list is not empty
        if (assignmentsData && assignmentsData.length > 0 && !selectedAssignment) {
          setSelectedAssignment(assignmentsData[0]);
          await fetchResponses(assignmentsData[0].assignment_id); // Fetch responses for default selection
        } else if (!assignmentsData || assignmentsData.length === 0) {
            setSelectedAssignment(null); // Ensure no selection if no assignments
            setResponses([]); // Clear responses
        }
      } catch (err) {
        console.error('Error fetching assignments:', err);
        const errorMsg = err.message || 'Failed to load assignments';
        setError(errorMsg);
        showAlert(errorMsg, 'error');
      } finally {
        setLoadingAssignments(false);
      }
    };
    fetchAssignments();
    // Run only when courseId or semester changes
  }, [courseId, semester, showAlert, fetchResponses]); // Added fetchResponses


  // --- Filtering Logic ---
  useEffect(() => {
    let filtered = responses ? [...responses] : [];

    // Filter by question index
    if (questionFilter !== 'all') {
        const index = parseInt(questionFilter, 10);
        if (!isNaN(index)) {
            filtered = filtered.filter((response) => response.question_index === index);
        }
    }

    // Filter by grading status
    if (gradingStatusFilter === 'graded') {
      filtered = filtered.filter((response) => !!response.grade); // Check if grade object exists
    } else if (gradingStatusFilter === 'ungraded') {
      filtered = filtered.filter((response) => !response.grade);
    }

    // Filter by student search term (case-insensitive)
    if (studentSearch) {
      const searchTerm = studentSearch.toLowerCase();
      filtered = filtered.filter((response) =>
        response.student_id.toLowerCase().includes(searchTerm)
      );
    }

    setFilteredResponses(filtered);
  }, [responses, questionFilter, gradingStatusFilter, studentSearch]);


  // --- Event Handlers ---

  // Handle selecting an assignment from dropdown
  const handleSelectAssignment = useCallback(async (assignment) => {
    setSelectedAssignment(assignment); // Update selected assignment state
    // Reset filters and selections when changing assignment
    setQuestionFilter('all');
    setGradingStatusFilter('all');
    setStudentSearch('');
    setTabValue(0); // Reset tabs
    setSelectedResponse(null);
    // Fetch responses for the newly selected assignment
    if (assignment) {
      await fetchResponses(assignment.assignment_id);
    } else {
      setResponses([]); // Clear responses if assignment is deselected
    }
  }, [fetchResponses]); // Dependency on fetchResponses

  // Handle selecting a response from the list
  const handleSelectResponse = useCallback((response) => {
    setSelectedResponse(response);
    setTabValue(0); // Switch to the response tab
  }, []);

  // Handle starting the grading process (opens confirmation)
  const handleStartGrading = () => {
    setConfirmGradingOpen(true);
  };

  // Handle the actual grading API call (now includes semester, courseId)
  const handleGradeSubmissions = useCallback(async () => {
    setConfirmGradingOpen(false);
    if (!semester || !courseId || !selectedAssignment?.assignment_id) {
        showAlert("Cannot start grading: Missing course or assignment information.", "error");
        return;
    }
    setGrading(true);
    setError(null);
    try {
        let gradedApiResult; // Renamed to avoid conflict with state
        const questionIndexToGrade = questionFilter === 'all' ? null : parseInt(questionFilter, 10);

        switch (gradingMode) {
            case 'specific':
                if (!selectedStudents || selectedStudents.length === 0) {
                    showAlert('No students selected for specific grading', 'warning');
                    setGrading(false);
                    return;
                }
                // <<< Pass semester and courseId >>>
                gradedApiResult = await responseService.gradeSpecific(
                    semester, courseId, selectedAssignment.assignment_id,
                    selectedStudents, questionIndexToGrade
                );
                break;
            case 'ungraded':
                // <<< Pass semester and courseId >>>
                gradedApiResult = await responseService.gradeUngraded(
                    semester, courseId, selectedAssignment.assignment_id,
                    questionIndexToGrade
                );
                break;
            case 'all':
                 // <<< Pass semester and courseId >>>
                gradedApiResult = await responseService.gradeAll(
                    semester, courseId, selectedAssignment.assignment_id,
                    questionIndexToGrade
                );
                break;
            default:
                throw new Error('Invalid grading mode selected.');
        }
        showAlert(
            `Successfully submitted ${gradedApiResult?.length ?? 0} ${
              gradedApiResult?.length === 1 ? 'response' : 'responses'
            } for grading. Refreshing list...`,
            'success'
        );
        // Refresh responses
        await fetchResponses(selectedAssignment.assignment_id, questionIndexToGrade);
    } catch (err) {
        console.error('Error grading submissions:', err);
        const errorMsg = err.message || 'Failed to grade submissions';
        setError(errorMsg);
        showAlert(errorMsg, 'error');
    } finally {
        setGrading(false);
    }
  }, [
    semester, courseId, selectedAssignment, gradingMode,
    questionFilter, selectedStudents, fetchResponses, showAlert
  ]); // Dependencies for grading submission

  // Handle refreshing responses list
  const handleRefreshResponses = useCallback(async () => {
    if (!selectedAssignment) return;
    const questionIndexToFetch = questionFilter === 'all' ? null : parseInt(questionFilter, 10);
    showAlert('Refreshing responses...', 'info');
    await fetchResponses(selectedAssignment.assignment_id, questionIndexToFetch);
    // showAlert('Responses refreshed', 'success'); // fetchResponses handles errors
  }, [selectedAssignment, questionFilter, fetchResponses, showAlert]); // Dependencies


  // Handle tab change in the details pane
  const handleTabChange = useCallback((event, newValue) => {
    setTabValue(newValue);
  }, []);


  // --- Calculation Helpers ---
  const calculateGradePercentage = (points, maxPoints) => {
    if (points === null || points === undefined || maxPoints === null || maxPoints === undefined || maxPoints === 0) return 0;
    return Math.max(0, Math.min(100, (points / maxPoints) * 100)); // Ensure percentage is between 0 and 100
  };

  const getLetterGrade = (percentage) => {
    if (percentage >= 90) return 'A';
    if (percentage >= 80) return 'B';
    if (percentage >= 70) return 'C';
    if (percentage >= 60) return 'D';
    return 'F';
  };

  // Memoize counts? For large datasets, maybe. For now, direct calculation is fine.
  const countUngradedResponses = () => {
    return responses?.filter((r) => !r.grade).length ?? 0;
  };
  const countResponsesForQuestion = (idx) => {
      return responses?.filter(r => r.question_index === idx).length ?? 0;
  };
  const countUngradedResponsesForQuestion = (idx) => {
    return responses?.filter(r => r.question_index === idx && !r.grade).length ?? 0;
  };


  // --- Render Functions ---

  // Render assignment selection dropdown
  const renderAssignmentSelection = () => {
    if (loadingAssignments) {
      return <Typography sx={{ mb: 3, fontStyle: 'italic' }}>Loading assignments...</Typography>;
    }
    if (!assignments || assignments.length === 0) {
      return (
        <Alert severity="warning" sx={{ mb: 3 }}>
          No assignments found for this course. Please create an assignment first.
        </Alert>
      );
    }
    return (
      <FormControl fullWidth variant="outlined" sx={{ mb: 3 }}>
        <InputLabel id="assignment-select-label">Select Assignment</InputLabel>
        <Select
          labelId="assignment-select-label"
          value={selectedAssignment?.assignment_id || ''}
          onChange={(e) => {
            const assignment = assignments.find((a) => a.assignment_id === e.target.value);
            if (assignment) handleSelectAssignment(assignment);
          }}
          label="Select Assignment"
          disabled={loadingAssignments || grading}
        >
          {assignments.map((assignment) => (
            <MenuItem key={assignment.assignment_id} value={assignment.assignment_id}>
              {assignment.assignment_title || `Assignment ID: ${assignment.assignment_id}`}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    );
  };

  // Render grading actions section
  const renderGradingActions = () => {
    if (!selectedAssignment) return null;

    const numUngraded = countUngradedResponses();
    const isGradeButtonDisabled = grading || loadingResponses || responses.length === 0 ||
                                  (gradingMode === 'ungraded' && numUngraded === 0) ||
                                  (gradingMode === 'specific' && selectedStudents.length === 0);

    return (
      <GradingActionCard>
        <Typography variant="h6" gutterBottom>
          Grading Actions for "{selectedAssignment.assignment_title || 'Selected Assignment'}"
        </Typography>
        <Grid container spacing={2} alignItems="center">
          {/* Row 1: Grading Mode, Question Filter, Action Buttons */}
          <Grid item xs={12} sm={4} md={3}>
            <GradingModeSelect
              value={gradingMode}
              onChange={(mode) => { setGradingMode(mode); setSelectedStudents([]); }} // Reset selection on mode change
              disabled={grading || loadingResponses}
            />
          </Grid>
          <Grid item xs={12} sm={4} md={4}>
            <FormControl fullWidth variant="outlined" size="small">
              <InputLabel id="question-filter-label">Filter by Question</InputLabel>
              <Select
                labelId="question-filter-label"
                value={questionFilter}
                onChange={(e) => setQuestionFilter(e.target.value)}
                label="Filter by Question"
                disabled={grading || loadingResponses || !selectedAssignment.questions?.length}
              >
                <MenuItem value="all">
                    All Questions
                    <Badge badgeContent={numUngraded} color="warning" sx={{ ml: 2 }} />
                </MenuItem>
                {(selectedAssignment.questions || []).map((question) => (
                  <MenuItem key={question.question_index} value={question.question_index}>
                    Q{question.question_index + 1}: {question.question_text.substring(0, 30)}...
                    <Badge badgeContent={countUngradedResponsesForQuestion(question.question_index)} color="warning" sx={{ ml: 2 }} />
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={4} md={5} sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
            <Button
              variant="contained"
              color="primary"
              onClick={handleStartGrading}
              disabled={isGradeButtonDisabled}
              startIcon={grading ? <CircularProgress size={20} color="inherit" /> : <GradeIcon />}
              sx={{ flexGrow: { xs: 1, sm: 0 } }} // Full width on small screens
            >
              {grading ? 'Grading...' : `Grade ${gradingMode.charAt(0).toUpperCase() + gradingMode.slice(1)}`}
            </Button>
            <Tooltip title="Refresh Responses List">
              <span> {/* Span needed for disabled tooltip */}
                <IconButton
                  color="primary"
                  onClick={handleRefreshResponses}
                  disabled={grading || loadingResponses}
                >
                  <RefreshIcon />
                </IconButton>
              </span>
            </Tooltip>
          </Grid>

          {/* Row 2: Status Filter, Student Search, Counts */}
          <Grid item xs={12}><Divider sx={{ my: 1 }} /></Grid>
          <Grid item xs={12} sm={4} md={3}>
            <FormControl variant="outlined" size="small" fullWidth>
              <InputLabel id="status-filter-label">Filter by Status</InputLabel>
              <Select
                labelId="status-filter-label"
                value={gradingStatusFilter}
                onChange={(e) => setGradingStatusFilter(e.target.value)}
                label="Filter by Status"
                disabled={grading || loadingResponses}
              >
                <MenuItem value="all">All Statuses</MenuItem>
                <MenuItem value="graded">Graded</MenuItem>
                <MenuItem value="ungraded">Ungraded</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} sm={8} md={6}>
            <TextField
              label="Search Student ID"
              variant="outlined"
              size="small"
              fullWidth
              value={studentSearch}
              onChange={(e) => setStudentSearch(e.target.value)}
              disabled={grading || loadingResponses}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon color="action" />
                  </InputAdornment>
                ),
              }}
            />
          </Grid>
          <Grid item xs={12} md={3} sx={{ textAlign: { xs: 'left', md: 'right' }, alignSelf: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              Showing {filteredResponses.length} / {responses.length} Responses
            </Typography>
          </Grid>
        </Grid>
      </GradingActionCard>
    );
  };

  // Render responses list and details pane
  const renderResponsesContent = () => {
    if (loadingResponses) {
      return (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <CircularProgress /> <Typography sx={{ ml: 2 }}>Loading responses...</Typography>
        </Box>
      );
    }
    if (!responses || responses.length === 0) {
        return (
            <Alert severity="info" sx={{ mt: 3 }}>
                No student responses have been submitted for this assignment yet.
            </Alert>
        );
    }
    if (filteredResponses.length === 0) {
      return (
        <Alert severity="info" sx={{ mt: 3 }}>
          No responses found matching the current filters (Status: {gradingStatusFilter}, Question: {questionFilter === 'all' ? 'All' : `Q${parseInt(questionFilter)+1}`}, Search: "{studentSearch || 'None'}").
        </Alert>
      );
    }

    return (
      <Grid container spacing={3}>
        {/* Response List */}
        <Grid item xs={12} md={4}>
          <Typography variant="h6" gutterBottom>
            Responses List
          </Typography>
          <SelectableList
            items={filteredResponses}
            // Use a composite key if student+question isn't unique, but likely is
            keyField="student_id"
            secondaryKeyField="question_index" // Helps ensure uniqueness if student has multiple responses shown
            selectedItems={selectedStudents}
            onSelectionChange={setSelectedStudents}
            onItemClick={handleSelectResponse}
            highlightedItem={selectedResponse}
            selectionMode={gradingMode === 'specific' ? 'multiple' : 'none'}
            renderItem={(response) => (
              <Box sx={{ display: 'flex', alignItems: 'center', width: '100%', justifyContent: 'space-between' }}>
                <Box>
                  <Typography variant="body1" component="div" noWrap sx={{ fontWeight: 500 }}>
                    {response.student_id}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Question {response.question_index + 1}
                  </Typography>
                </Box>
                {response.grade ? (
                    <Tooltip title={`Graded: ${response.grade.points}/${response.grade.max_points}`}>
                        <CheckCircleOutlineIcon color="success" fontSize="small" />
                    </Tooltip>
                ) : (
                     <Tooltip title="Ungraded">
                        <HourglassEmptyIcon color="warning" fontSize="small" />
                     </Tooltip>
                )}
              </Box>
            )}
          />
        </Grid>

        {/* Response Details / Grade View */}
        <Grid item xs={12} md={8}>
          {!selectedResponse ? (
             <Paper
              sx={{
                p: 3, display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center',
                height: { xs: 200, md: 400 }, // Adjust height
                border: `1px dashed grey`
              }}
              variant="outlined"
            >
              <AssignmentIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 2 }} />
              <Typography variant="h6" color="text.secondary">
                Select a response
              </Typography>
              <Typography variant="body2" color="text.secondary" align="center">
                Click on a student response from the list to view its details and grade.
              </Typography>
            </Paper>
          ) : (
            <>
              <Paper sx={{ mb: 3 }}>
                <Tabs
                  value={tabValue}
                  onChange={handleTabChange}
                  variant="fullWidth"
                  indicatorColor="primary"
                  textColor="primary"
                  aria-label="response tabs"
                >
                  <Tab label="View Response" icon={<QuestionIcon />} iconPosition="start" />
                  <Tab
                    label="View Grade"
                    icon={selectedResponse.grade ? <CheckCircleOutlineIcon /> : <HourglassEmptyIcon />}
                    iconPosition="start"
                    disabled={!selectedResponse.grade} // Only enable if graded
                  />
                </Tabs>
              </Paper>

              {/* Tab Panel for Response */}
              <TabPanel value={tabValue} index={0}>
                <ResponseCard>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                    <Typography variant="h6">
                      Response from: {selectedResponse.student_id}
                    </Typography>
                    <Chip
                      label={selectedResponse.grade ? 'Graded' : 'Ungraded'}
                      color={selectedResponse.grade ? 'success' : 'warning'}
                      variant="outlined"
                      size="small"
                      icon={selectedResponse.grade ? <CheckCircleOutlineIcon /> : <HourglassEmptyIcon />}
                    />
                  </Box>
                  <Typography variant="body1" fontWeight="medium" gutterBottom>
                     Question {selectedResponse.question_index + 1}: {getQuestionText(selectedResponse.question_index)}
                  </Typography>
                  <Divider sx={{ my: 2 }} />
                  <Typography variant="body1" fontWeight="medium" gutterBottom>
                    Student's Answer:
                  </Typography>
                  <Paper variant="outlined" sx={{ p: 2, bgcolor: 'action.hover', whiteSpace: 'pre-wrap', maxHeight: '400px', overflowY: 'auto' }}>
                    {/* TODO: Handle different response data types (e.g., images) */}
                    {selectedResponse.data?.content || <Typography color="text.secondary" fontStyle="italic">No content submitted.</Typography>}
                  </Paper>
                </ResponseCard>
              </TabPanel>

              {/* Tab Panel for Grade */}
              <TabPanel value={tabValue} index={1}>
                {selectedResponse.grade ? (
                  <GradeCard
                    gradePercent={calculateGradePercentage(
                      selectedResponse.grade.points,
                      selectedResponse.grade.max_points
                    )}
                  >
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                      <Typography variant="h6">Grade Details</Typography>
                      <Box sx={{ textAlign: 'right' }}>
                        <Typography variant="h4" color="primary" component="span" sx={{ fontWeight: 'bold' }}>
                          {selectedResponse.grade.points}
                        </Typography>
                        <Typography variant="h6" component="span" color="text.secondary">
                          {' '} / {selectedResponse.grade.max_points}
                        </Typography>
                         <Typography variant="subtitle1" color="text.secondary">
                          {calculateGradePercentage(selectedResponse.grade.points, selectedResponse.grade.max_points).toFixed(1)}%
                          {' ('}{getLetterGrade(calculateGradePercentage(selectedResponse.grade.points, selectedResponse.grade.max_points))}{')'}
                        </Typography>
                      </Box>
                    </Box>
                    <Divider sx={{ mb: 3 }} />
                    <Typography variant="body1" fontWeight="medium" gutterBottom>
                      Explanation / Feedback:
                    </Typography>
                    <Paper variant="outlined" sx={{ p: 2, bgcolor: 'action.hover', whiteSpace: 'pre-wrap', maxHeight: '400px', overflowY: 'auto' }}>
                      {selectedResponse.grade.explanation || <Typography color="text.secondary" fontStyle="italic">No explanation provided.</Typography>}
                    </Paper>
                  </GradeCard>
                ) : (
                  <Alert severity="info">This response has not been graded yet.</Alert>
                )}
              </TabPanel>
            </>
          )}
        </Grid>
      </Grid>
    );
  };

  // Helper to get question text for display
  const getQuestionText = useCallback((questionIndex) => {
      if (!selectedAssignment?.questions) return 'Question text not available.';
      const question = selectedAssignment.questions.find(q => q.question_index === questionIndex);
      return question ? question.question_text : `Question index ${questionIndex+1} not found in assignment data.`;
  }, [selectedAssignment]);


  // --- Main Component Return ---
  return (
    <Box sx={{ p: { xs: 1, sm: 2, md: 3 } }}>
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
          Grading Dashboard
        </Typography>
      </Box>

      {error && !loadingAssignments && ( // Show general fetch errors if not loading
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {renderAssignmentSelection()}

      {selectedAssignment && renderGradingActions()}

      {selectedAssignment && renderResponsesContent()}

      {!selectedAssignment && !loadingAssignments && !error && assignments?.length > 0 && (
           <Alert severity="info" sx={{ mt: 3 }}>
                Select an assignment above to view responses and start grading.
            </Alert>
      )}

      {/* Grading Confirmation Dialog */}
      <ConfirmationDialog
        open={confirmGradingOpen}
        title="Confirm Grading Action"
        description={ // Updated message generation
             gradingMode === 'specific'
             ? `Grade ${selectedStudents.length} selected response(s)${questionFilter !== 'all' ? ` for Q${parseInt(questionFilter)+1}` : ''}?`
             : gradingMode === 'ungraded'
             ? `Grade all ${countUngradedResponses()} ungraded response(s)${questionFilter !== 'all' ? ` for Q${parseInt(questionFilter)+1}` : ''}?`
             : `Grade/Regrade ALL ${filteredResponses.length} response(s)${questionFilter !== 'all' ? ` for Q${parseInt(questionFilter)+1}` : ''}? This may overwrite existing grades.`
        }
        confirmText={grading ? "Grading..." : "Start Grading"}
        cancelText="Cancel"
        onConfirm={handleGradeSubmissions}
        onCancel={() => setConfirmGradingOpen(false)} // Changed from onCancel to onClose
        loading={grading} // Pass loading state
        confirmColor="primary"
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
          variant="filled" // Use filled for better visibility
          sx={{ width: '100%' }}
        >
          {alertMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
}