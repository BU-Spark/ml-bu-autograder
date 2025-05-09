/**
 * Grading Dashboard for BU MET Autograder
 * Displays student submissions for grading and review
 * Located at: pages/course/[id]/grading.js
 */

import React, { useState, useEffect, useCallback } from 'react'; // Added useCallback
import { useRouter } from 'next/router';
import {
  Alert, Badge, Box, Button, Card, CardContent, Chip, CircularProgress, Divider,
  FormControl, Grid, IconButton, InputLabel, MenuItem, Paper, Select, Snackbar,
  Tab, Tabs, TextField, Tooltip, Typography, useTheme, InputAdornment// Added useTheme and missing imports
} from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  ArrowBack as ArrowBackIcon, Assignment as AssignmentIcon, AssignmentTurnedIn as GradedIcon,
  Assessment as GradeIcon, Refresh as RefreshIcon, Search as SearchIcon, FilterList as FilterIcon,
  PersonSearch as StudentSearchIcon, QuestionAnswer as QuestionIcon,
} from '@mui/icons-material';
// Import Checkbox for SelectableList
import Checkbox from '@mui/material/Checkbox';
import { assignmentService, responseService } from '../../../api'; // Ensure correct path
import CardSkeleton from '../../../components/CardSkeleton'; // Assuming path
import GradingModeSelect from '../../../components/GradingModeSelect'; // Assuming path
import SelectableList from '../../../components/SelectableList'; // Assuming path
import ConfirmationDialog from '../../../components/ConfirmationDialog'; // Assuming path

// Styled components
const StyledCard = styled(Card)(({ theme }) => ({ height: '100%', display: 'flex', flexDirection: 'column', }));
const GradingActionCard = styled(Paper)(({ theme }) => ({ padding: theme.spacing(3), marginBottom: theme.spacing(3), }));
const ResponseDetailCard = styled(Paper)(({ theme }) => ({ padding: theme.spacing(3), marginBottom: theme.spacing(3) })); // Renamed for clarity
const GradeCard = styled(Paper)(({ theme, gradePercent = 0 }) => ({
    padding: theme.spacing(2), marginBottom: theme.spacing(2), borderLeftWidth: '4px', borderLeftStyle: 'solid',
    // Using theme palette directly for colors
    borderLeftColor: gradePercent >= 90 ? theme.palette.success.main :
                     gradePercent >= 80 ? theme.palette.info.main :
                     gradePercent >= 70 ? theme.palette.warning.main :
                     gradePercent >= 60 ? theme.palette.error.dark : // Adjusted D grade color slightly
                     theme.palette.error.main, // F grade color
    backgroundColor: theme.palette.background.default,
}));

const TabPanel = (props) => { const { children, value, index, ...other } = props; return ( <div role="tabpanel" hidden={value !== index} id={`grading-tabpanel-${index}`} aria-labelledby={`grading-tab-${index}`} {...other}> {value === index && <Box sx={{ pt: 3 }}>{children}</Box>} </div> ); };

// Main component
export default function GradingDashboardPage() { // Renamed component
  const router = useRouter();
  const theme = useTheme();
  const { id: courseIdParam, semester: semesterParam } = router.query;
  const courseId = typeof courseIdParam === 'string' ? courseIdParam : null;
  const semester = typeof semesterParam === 'string' ? semesterParam : null;

  // State
  const [assignments, setAssignments] = useState([]);
  const [selectedAssignment, setSelectedAssignment] = useState(null);
  const [responses, setResponses] = useState([]);
  const [filteredResponses, setFilteredResponses] = useState([]);
  const [selectedResponse, setSelectedResponse] = useState(null);

  // Loading/Error States
  const [loadingAssignments, setLoadingAssignments] = useState(true);
  const [loadingResponses, setLoadingResponses] = useState(false);
  const [isGrading, setIsGrading] = useState(false);
  const [error, setError] = useState(null);

  // Filters/Search State
  const [questionFilter, setQuestionFilter] = useState('all');
  const [gradingStatusFilter, setGradingStatusFilter] = useState('all');
  const [studentSearch, setStudentSearch] = useState('');

  // Grading Action State
  const [gradingMode, setGradingMode] = useState('ungraded');
  const [selectedStudents, setSelectedStudents] = useState([]);
  const [confirmGradingOpen, setConfirmGradingOpen] = useState(false);

  // UI State
  const [tabValue, setTabValue] = useState(0);

  // Alert State
  const [alertOpen, setAlertOpen] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [alertSeverity, setAlertSeverity] = useState('success');

  // --- UTILITY FUNCTIONS ---
  const showAlert = useCallback((message, severity = 'success') => { setAlertMessage(message); setAlertSeverity(severity); setAlertOpen(true); }, []);
  const formatApiError = useCallback((err, defaultMessage) => { let displayError = defaultMessage; if(err.response){const detail = err.response.data?.detail; if(detail){if(Array.isArray(detail)){displayError = detail.map(d => `${d.loc?.join('.') || 'error'}: ${d.msg}`).join('; ');} else if(typeof detail === 'string'){displayError = detail;}}else if(err.response.statusText){displayError = `Error: ${err.response.status} ${err.response.statusText}`;}} else if(err.request){displayError="Network Error";} else if(err.message){displayError = err.message;} return displayError||defaultMessage; }, []);
  const calculateGradePercentage = (points, maxPoints) => (maxPoints ? (points / maxPoints) * 100 : 0);
  const getLetterGrade = (percentage) => { if (percentage >= 90) return 'A'; if (percentage >= 80) return 'B'; if (percentage >= 70) return 'C'; if (percentage >= 60) return 'D'; return 'F'; };
  const countUngradedResponses = useCallback(() => responses.filter(r => !r.grade).length, [responses]);
  const countUngradedResponsesForQuestion = useCallback((qIndex) => responses.filter(r => r.question_index === qIndex && !r.grade).length, [responses]);


  // --- DATA FETCHING ---

  // Fetch responses for selected assignment
  const fetchResponses = useCallback(async (assignmentId, questionIndex = null) => {
    if (!courseId || !semester || !assignmentId) { console.warn("Cannot fetch responses: Missing context."); setResponses([]); setFilteredResponses([]); return; }
    setLoadingResponses(true); setError(null); // Use general error state for simplicity here too, or add dedicated responseError state
    try {
      console.log(`FETCHING responses for ${courseId}/${semester}/${assignmentId}, Q-Index: ${questionIndex ?? 'all'}`);
      // *** CORRECTED API CALL: Pass params object ***
      const responseData = await responseService.getResponses({
          semester: semester,
          course_id: courseId,
          assignment_id: assignmentId,
          question_index: questionIndex === 'all' ? null : questionIndex, // Pass null if 'all'
          student_id: null
      });

      if (Array.isArray(responseData)) {
           console.log("RECEIVED responses:", responseData);
           // Ensure each response has necessary fields
           const validResponses = responseData.filter(r => r && r.student_id && typeof r.question_index === 'number');
           setResponses(validResponses);
           setFilteredResponses(validResponses); // Apply filters in separate effect
           setSelectedResponse(null); setSelectedStudents([]); // Reset selections
      } else { throw new Error("Invalid data format received for responses."); }
    } catch (err) {
      console.error('Error fetching responses:', err);
      const errorMsg = formatApiError(err, 'Failed to load responses.');
      setError(errorMsg); // Set general error state
      showAlert(errorMsg, 'error');
      setResponses([]); setFilteredResponses([]);
    } finally { setLoadingResponses(false); }
  }, [courseId, semester, formatApiError, showAlert]); // Dependencies

  // Fetch assignments initially
  useEffect(() => {
    if (!router.isReady || !courseId || !semester) return;
    let isMounted = true;
    const fetchAssignmentsList = async () => {
      setLoadingAssignments(true); setError(null); setAssignments([]); setSelectedAssignment(null); setResponses([]); setFilteredResponses([]);
      try {
        console.log(`FETCHING assignments list for ${courseId}/${semester}`);
        // Fetch assignments WITH questions
        const assignmentsData = await assignmentService.getAssignments({ course_id: courseId, semester: semester, include_questions: true });

        if (isMounted) {
            if (Array.isArray(assignmentsData)) {
               const validAssignments = (assignmentsData || []).filter(a => a && typeof a.assignment_id !== 'undefined').map(a => ({...a, questions: Array.isArray(a?.questions) ? a.questions.sort((qa,qb) => qa.question_index - qb.question_index) : [] }));
               validAssignments.sort((a,b) => String(a.assignment_id).localeCompare(String(b.assignment_id)));
               setAssignments(validAssignments);
               if (validAssignments.length > 0) {
                    const firstAssignment = validAssignments[0];
                    setSelectedAssignment(firstAssignment); // Select first by default
                    await fetchResponses(firstAssignment.assignment_id); // Fetch its responses
               } else { setLoadingResponses(false); } // No assignments, no responses to load
            } else { throw new Error("Invalid assignment data format."); }
        }
      } catch (err) { console.error("Error fetching assignments list:", err); if (isMounted) { setError(formatApiError(err, 'Failed to load assignments list.')); setAssignments([]); setLoadingResponses(false); } }
      finally { if (isMounted) { setLoadingAssignments(false); } }
    };
    fetchAssignmentsList();
    return () => { isMounted = false; };
  }, [router.isReady, courseId, semester, fetchResponses, formatApiError]); // Added fetchResponses


  // --- UI HANDLERS ---

  const handleSelectAssignment = useCallback(async (assignment) => {
    if (!assignment || assignment.assignment_id === selectedAssignment?.assignment_id) return;
    setSelectedAssignment(assignment);
    setQuestionFilter('all'); setGradingStatusFilter('all'); setStudentSearch('');
    setSelectedResponse(null); setSelectedStudents([]);
    await fetchResponses(assignment.assignment_id); // Fetch responses for the newly selected assignment
  }, [fetchResponses, selectedAssignment?.assignment_id]);

  const handleSelectResponse = useCallback((response) => {
    setSelectedResponse(response);
    setTabValue(0); // Switch to response tab
  }, []);

  // Apply filters client-side
  useEffect(() => {
    if (!Array.isArray(responses)) return;
    let filtered = [...responses];
    if (questionFilter !== 'all') { filtered = filtered.filter(r => r.question_index === parseInt(questionFilter)); }
    if (gradingStatusFilter === 'graded') { filtered = filtered.filter(r => !!r.grade); }
    else if (gradingStatusFilter === 'ungraded') { filtered = filtered.filter(r => !r.grade); }
    if (studentSearch) { const searchLower = studentSearch.toLowerCase(); filtered = filtered.filter(r => r.student_id?.toLowerCase().includes(searchLower)); }
    setFilteredResponses(filtered);
    if (selectedResponse && !filtered.some(r => r.student_id === selectedResponse.student_id && r.question_index === selectedResponse.question_index)) {
        setSelectedResponse(null);
    }
  }, [responses, questionFilter, gradingStatusFilter, studentSearch, selectedResponse]);


  // --- GRADING ACTIONS ---

  const handleStartGrading = () => { setConfirmGradingOpen(true); };

  const handleGradeSubmissions = async () => {
    setConfirmGradingOpen(false);
    if (!selectedAssignment || !courseId || !semester) return showAlert("Cannot grade: Course/Assignment context missing.", "error");

    setIsGrading(true); setError(null);

    const assignmentId = selectedAssignment.assignment_id;
    const questionIndexToGrade = questionFilter === 'all' ? null : parseInt(questionFilter);
    let gradeActionPromise;
    let resultCount = 0; // Track how many were processed

    try {
      // *** CORRECTED API CALLS: Pass params object including semester & courseId ***
      const baseParams = { semester, course_id: courseId, assignment_id: assignmentId, question_index: questionIndexToGrade };

      switch (gradingMode) {
        case 'specific':
          if (selectedStudents.length === 0) throw new Error('No students selected.');
          console.log(`GRADING specific students (${selectedStudents.length}) for A:${assignmentId} Q:${questionIndexToGrade ?? 'all'}`);
          // gradeSpecific expects { ...baseParams, student_ids: string[] }
          gradeActionPromise = responseService.gradeSpecific({ ...baseParams, student_ids: selectedStudents });
          resultCount = selectedStudents.length; // Assume API processes all requested
          break;
        case 'ungraded':
          console.log(`GRADING ungraded for A:${assignmentId} Q:${questionIndexToGrade ?? 'all'}`);
          // gradeUngraded expects baseParams
          gradeActionPromise = responseService.gradeUngraded(baseParams);
           // Count ungraded responses matching the filter
          resultCount = filteredResponses.filter(r => !r.grade).length;
          break;
        case 'all':
           console.log(`GRADING/REGRADING ALL for A:${assignmentId} Q:${questionIndexToGrade ?? 'all'}`);
          // gradeAll expects baseParams
          gradeActionPromise = responseService.gradeAll(baseParams);
           // Count all responses matching the filter
          resultCount = filteredResponses.length;
          break;
        default: throw new Error('Invalid grading mode selected.');
      }

      const result = await gradeActionPromise; // Await the API call
      console.log("Grading API response:", result);

      // Refresh responses after grading completes successfully
      showAlert(`Grading initiated for ${resultCount} response(s). Refreshing list...`, 'success');
      await fetchResponses(assignmentId, questionIndexToGrade === null ? 'all' : questionIndexToGrade); // Pass 'all' or specific index

    } catch (err) {
      console.error('Error during grading submissions:', err);
      showAlert(formatApiError(err, 'Grading failed.'), 'error');
    } finally { setIsGrading(false); }
  };

  // Handle refreshing responses list
  const handleRefreshResponses = useCallback(async () => {
    if (!selectedAssignment) return;
    const questionIndexToFetch = questionFilter === 'all' ? null : parseInt(questionFilter);
    showAlert('Refreshing responses...', 'info');
    await fetchResponses(selectedAssignment.assignment_id, questionIndexToFetch);
  }, [selectedAssignment, questionFilter, fetchResponses, showAlert]);

  // Handle tab change
  const handleTabChange = (event, newValue) => { setTabValue(newValue); };

  // Get question text helper
  const getQuestionText = useCallback((qIndex) => { if (!selectedAssignment || !Array.isArray(selectedAssignment.questions) || typeof qIndex !== 'number') return 'N/A'; const question = selectedAssignment.questions.find(q => q.question_index === qIndex); return question ? question.question_text : `Question text (Index ${qIndex}) not found`; }, [selectedAssignment]);


  // --- RENDER FUNCTIONS ---

  const renderAssignmentSelection = () => {
    if (loadingAssignments) return <CardSkeleton height={80} sx={{mb: 3}} />; // Use skeleton for loading
    if (error && assignments.length === 0) return <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>; // Show error if list failed AND is empty
    if (!loadingAssignments && assignments.length === 0) return <Alert severity="info" sx={{ mb: 3 }}>No assignments found for this course.</Alert>;

    return (
      <FormControl fullWidth variant="outlined" sx={{ mb: 3 }}>
        <InputLabel id="assignment-select-label">Select Assignment</InputLabel>
        <Select labelId="assignment-select-label" value={selectedAssignment?.assignment_id ?? ''} onChange={(e) => { const assignment = assignments.find((a) => a.assignment_id === e.target.value); if (assignment) handleSelectAssignment(assignment); }} label="Select Assignment" disabled={isGrading || loadingResponses}>
          {assignments.map((assignment) => ( <MenuItem key={assignment.assignment_id} value={assignment.assignment_id}> {assignment.assignment_id} ({assignment.questions?.length ?? 0} Qs) </MenuItem> ))}
        </Select>
      </FormControl>
    );
  };

  const renderGradingActions = () => {
    if (!selectedAssignment || !Array.isArray(selectedAssignment.questions)) return null; // Ensure assignment and questions exist

    const ungradedTotal = countUngradedResponses();
    const questionsExist = selectedAssignment.questions.length > 0;

    return (
      <GradingActionCard variant="outlined">
        <Typography variant="h6" gutterBottom>Grading Actions</Typography>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={6} md={4}> <GradingModeSelect value={gradingMode} onChange={setGradingMode} disabled={isGrading}/> </Grid>
          <Grid item xs={12} sm={6} md={4}>
             <FormControl fullWidth variant="outlined" size="small" disabled={isGrading || !questionsExist}>
               <InputLabel id="question-filter-label">Filter/Grade Question</InputLabel>
               <Select labelId="question-filter-label" value={questionFilter} onChange={(e) => setQuestionFilter(e.target.value)} label="Filter/Grade Question">
                 <MenuItem value="all">All Questions</MenuItem>
                 {selectedAssignment.questions.map((question) => (
                    <MenuItem key={question.question_index} value={question.question_index}>
                       <Box component="span" sx={{ display: 'flex', alignItems: 'center', width: '100%', justifyContent: 'space-between' }}>
                           {`Q ${question.question_index + 1}`}
                           <Tooltip title="Ungraded responses for this question">
                              <Badge badgeContent={countUngradedResponsesForQuestion(question.question_index)} color="warning" sx={{ ml: 1 }} />
                           </Tooltip>
                       </Box>
                   </MenuItem>
                 ))}
               </Select>
             </FormControl>
          </Grid>
          <Grid item xs={12} sm={12} md={4}>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button variant="contained" color="primary" fullWidth onClick={handleStartGrading} disabled={ isGrading || loadingResponses || !responses.length || (gradingMode === 'ungraded' && ungradedTotal === 0) || (gradingMode === 'specific' && selectedStudents.length === 0) } startIcon={isGrading ? <CircularProgress size={20} color="inherit" /> : <GradeIcon />}> {isGrading ? 'Grading...' : 'Start Grading'} </Button>
              <Tooltip title="Refresh Responses List"><IconButton color="primary" onClick={handleRefreshResponses} disabled={isGrading || loadingResponses}><RefreshIcon /></IconButton></Tooltip>
            </Box>
          </Grid>
          <Grid item xs={12}><Divider sx={{ my: 1 }} /></Grid>
          <Grid item xs={12} sm={6} md={4}>
             <FormControl variant="outlined" size="small" fullWidth disabled={isGrading || loadingResponses}>
               <InputLabel id="status-filter-label">Filter Status</InputLabel>
               <Select labelId="status-filter-label" value={gradingStatusFilter} onChange={(e) => setGradingStatusFilter(e.target.value)} label="Filter Status"> <MenuItem value="all">All Responses</MenuItem> <MenuItem value="graded">Graded Only</MenuItem> <MenuItem value="ungraded">Ungraded Only</MenuItem> </Select>
             </FormControl>
          </Grid>
          <Grid item xs={12} sm={6} md={5}>
             <TextField label="Search Student ID" variant="outlined" size="small" fullWidth value={studentSearch} onChange={(e) => setStudentSearch(e.target.value)} disabled={isGrading || loadingResponses} InputProps={{ startAdornment: (<InputAdornment position="start"><StudentSearchIcon color="action"/></InputAdornment>), endAdornment: studentSearch ? (<IconButton size="small" onClick={() => setStudentSearch('')} edge="end"><DeleteIcon fontSize='small'/></IconButton>) : null }} />
          </Grid>
          <Grid item xs={12} md={3} sx={{ textAlign: { xs: 'left', md: 'right' }, alignSelf: 'center' }}>
            <Typography variant="body2" color="text.secondary"> {filteredResponses.length} shown ({ungradedTotal} ungraded total) </Typography>
          </Grid>
        </Grid>
      </GradingActionCard>
    );
  };

  const renderResponsesContent = () => {
    if (loadingResponses) return <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}><CircularProgress /></Box>;
    // Let main error Alert handle list loading errors
    // if (error && responses.length === 0) return null;
    if (!loadingAssignments && !loadingResponses && !error && filteredResponses.length === 0) {
      return <Alert severity="info" sx={{ mt: 3 }}>No responses found matching the current filters for assignment '{selectedAssignment?.assignment_id}'.</Alert>;
    }
    // Don't render if list is loading or empty
    if (loadingAssignments || loadingResponses || !Array.isArray(filteredResponses)) return null;

    return (
      <Grid container spacing={3}>
        {/* Response List */}
        <Grid item xs={12} md={5} lg={4}>
          <Typography variant="h6" gutterBottom> Student Responses </Typography>
          <SelectableList
            items={filteredResponses} // Use filtered list
            keyField="student_id"
            secondaryKeyField="question_index" // Needed for unique key within list
            selectedItems={selectedStudents} // Array of student_ids
            onSelectionChange={setSelectedStudents}
            onItemClick={handleSelectResponse}
            highlightedItem={selectedResponse}
            selectionMode={gradingMode === 'specific' ? 'multiple' : 'single'} // Allow single selection even if not grading specific
            renderItem={(response) => (
              <Box sx={{ width: '100%' }}>
                <Typography variant="body1" component="div" noWrap sx={{ fontWeight: 500 }}>{response.student_id}</Typography>
                <Typography variant="body2" color="text.secondary" component="div" sx={{ mb: 0.5 }}>Q {response.question_index + 1}</Typography>
                <Box> {response.grade ? ( <Chip icon={<GradedIcon fontSize="small"/>} label={`${response.grade.points}/${response.grade.max_points}`} size="small" color="success" variant="outlined" /> ) : ( <Chip label="Ungraded" size="small" color="warning" variant="outlined"/> )} </Box>
              </Box>
            )}
            sx={{ maxHeight: '70vh', overflowY: 'auto' }} // Make list scrollable
          />
           {gradingMode === 'specific' && ( <Typography variant="caption" display="block" sx={{mt:1}}> Selected: {selectedStudents.length} student(s) </Typography> )}
        </Grid>

        {/* Response Details / Grade */}
        <Grid item xs={12} md={7} lg={8}>
          <Typography variant="h6" gutterBottom> Response Details </Typography>
          {!selectedResponse ? (
              <Paper variant="outlined" sx={{ p: 3, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: 300, borderStyle: 'dashed' }}> <AssignmentIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} /> <Typography variant="h6" gutterBottom>No Response Selected</Typography> <Typography variant="body2" color="text.secondary" align="center">Select a student response from the list.</Typography> </Paper>
          ) : (
            <>
              <ResponseDetailCard variant="outlined">
                 <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}> <Typography variant="h6">{selectedResponse.student_id}</Typography> <Chip label={selectedResponse.grade ? 'Graded' : 'Ungraded'} color={selectedResponse.grade ? 'success' : 'warning'} variant="outlined" /> </Box>
                 <Typography variant="subtitle1" gutterBottom>Question {selectedResponse.question_index + 1}:</Typography>
                 <Paper variant="outlined" sx={{ p: 1.5, mb: 2, bgcolor: 'action.hover', maxHeight: '150px', overflowY: 'auto' }}><Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{getQuestionText(selectedResponse.question_index)}</Typography></Paper>
                 <Divider sx={{ my: 2 }} />
                 <Typography variant="subtitle1" gutterBottom>Student Response:</Typography>
                 {/* Basic rendering - enhance based on actual data_type */}
                 <Paper variant="outlined" sx={{ p: 2, bgcolor: 'background.default', maxHeight: '300px', overflowY: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}> {selectedResponse.data?.content || <Typography component="em" sx={{color: 'text.disabled'}}>(No response content available)</Typography>} </Paper>
              </ResponseDetailCard>

              {selectedResponse.grade ? (
                  <GradeCard variant="outlined" gradePercent={calculateGradePercentage(selectedResponse.grade.points, selectedResponse.grade.max_points)}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}> <Typography variant="h6">Grade</Typography> <Box sx={{ textAlign: 'right' }}> <Typography variant="h4" color="primary">{selectedResponse.grade.points}/{selectedResponse.grade.max_points}</Typography> <Typography variant="subtitle1" color="text.secondary"> {calculateGradePercentage(selectedResponse.grade.points, selectedResponse.grade.max_points).toFixed(1)}% ({getLetterGrade(calculateGradePercentage(selectedResponse.grade.points, selectedResponse.grade.max_points))}) </Typography> </Box> </Box>
                      <Divider sx={{ mb: 2 }} />
                      <Typography variant="subtitle1" gutterBottom>Explanation:</Typography>
                      <Paper elevation={0} sx={{ p: 1.5, bgcolor: 'background.paper', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{selectedResponse.grade.explanation || <Typography component="em" sx={{color: 'text.disabled'}}>(No explanation provided)</Typography>}</Paper>
                  </GradeCard>
              ) : ( <Alert severity="info">This response is currently ungraded.</Alert> )}
            </>
          )}
        </Grid>
      </Grid>
    );
  };


  // --- MAIN RETURN JSX ---
  return (
    <Box sx={{ p: { xs: 1, sm: 2, md: 3 } }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 1 }}>
        <IconButton title="Back to Course Overview" aria-label="back" onClick={() => (courseId && semester) && router.push(`/course/${courseId}?semester=${semester}`)} disabled={!courseId || !semester || isGrading} sx={{ mr: 1 }}> <ArrowBackIcon /> </IconButton>
        <Typography variant="h4" component="h1" sx={{ flexGrow: 1, mr: 1 }}>Grading Dashboard</Typography>
      </Box>
      {error && !loadingAssignments && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}
      {renderAssignmentSelection()}
      {selectedAssignment && renderGradingActions()}
      <Divider sx={{ my: 4 }} />
      {selectedAssignment && renderResponsesContent()}

      <ConfirmationDialog open={confirmGradingOpen} onClose={() => !isGrading && setConfirmGradingOpen(false)} onConfirm={handleGradeSubmissions} title="Confirm Grading Action" description={ gradingMode === 'specific' ? `Grade ${selectedStudents.length} selected response(s)?` : gradingMode === 'ungraded' ? `Grade all ungraded responses${questionFilter !== 'all' ? ` for Q${parseInt(questionFilter) + 1}` : ''}?` : `Grade/Regrade ALL responses${questionFilter !== 'all' ? ` for Q${parseInt(questionFilter) + 1}` : ''}? This may overwrite existing grades.` } confirmText={isGrading ? "Grading..." : "Start Grading"} cancelText="Cancel" loading={isGrading}/>
      <Snackbar open={alertOpen} autoHideDuration={6000} onClose={() => setAlertOpen(false)} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}><Alert onClose={() => setAlertOpen(false)} severity={alertSeverity} variant="filled" sx={{ width: '100%' }}> {alertMessage} </Alert></Snackbar>
    </Box>
  );
}