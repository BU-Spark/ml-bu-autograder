/**
 * Grading Dashboard for BU MET Autograder
 * Displays student submissions for grading and review
 */

import React, { useState, useEffect } from 'react';
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
  Assessment as GradeIcon,
  Refresh as RefreshIcon,
  Search as SearchIcon,
  FilterList as FilterIcon,
  PersonSearch as StudentSearchIcon,
  QuestionAnswer as QuestionIcon,
} from '@mui/icons-material';
import { assignmentService, responseService } from '../../../api';
import CardSkeleton from '../../../components/CardSkeleton';
import GradingModeSelect from '../../../components/GradingModeSelect';
import SelectableList from '../../../components/SelectableList';
import ConfirmationDialog from '../../../components/ConfirmationDialog';

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

const GradeCard = styled(Paper)(({ theme, gradePercent }) => ({
  padding: theme.spacing(3),
  marginBottom: theme.spacing(3),
  borderLeft: `4px solid ${
    gradePercent >= 90
      ? theme.palette.custom.gradeA
      : gradePercent >= 80
      ? theme.palette.custom.gradeB
      : gradePercent >= 70
      ? theme.palette.custom.gradeC
      : gradePercent >= 60
      ? theme.palette.custom.gradeD
      : theme.palette.custom.gradeF
  }`,
}));

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
  const { id: courseId, semester } = router.query;

  // State for assignments and submissions
  const [assignments, setAssignments] = useState([]);
  const [selectedAssignment, setSelectedAssignment] = useState(null);
  const [responses, setResponses] = useState([]);
  const [filteredResponses, setFilteredResponses] = useState([]);
  const [selectedResponse, setSelectedResponse] = useState(null);

  // State for loading and error
  const [loading, setLoading] = useState(true);
  const [loadingResponses, setLoadingResponses] = useState(false);
  const [grading, setGrading] = useState(false);
  const [error, setError] = useState(null);

  // State for filters and search
  const [questionFilter, setQuestionFilter] = useState('all');
  const [gradingStatusFilter, setGradingStatusFilter] = useState('all');
  const [studentSearch, setStudentSearch] = useState('');

  // State for grading
  const [gradingMode, setGradingMode] = useState('ungraded');
  const [selectedStudents, setSelectedStudents] = useState([]);
  const [confirmGradingOpen, setConfirmGradingOpen] = useState(false);

  // State for tabs
  const [tabValue, setTabValue] = useState(0);

  // State for alerts
  const [alertOpen, setAlertOpen] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [alertSeverity, setAlertSeverity] = useState('success');

  // Fetch assignments
  useEffect(() => {
    const fetchAssignments = async () => {
      if (!courseId || !semester) return;

      setLoading(true);
      try {
        const assignmentsData = await assignmentService.getAssignments(courseId, semester);
        setAssignments(assignmentsData || []);

        // If there are assignments, select the first one by default
        if (assignmentsData && assignmentsData.length > 0) {
          setSelectedAssignment(assignmentsData[0]);
          await fetchResponses(assignmentsData[0].assignment_id);
        }

        setError(null);
      } catch (err) {
        console.error('Error fetching assignments:', err);
        setError(err.message || 'Failed to load assignments');
      } finally {
        setLoading(false);
      }
    };

    fetchAssignments();
  }, [courseId, semester]);

  // Fetch responses for selected assignment
  const fetchResponses = async (assignmentId, questionIndex = null) => {
    setLoadingResponses(true);
    try {
      const responsesData = await responseService.getResponses(assignmentId, questionIndex);
      setResponses(responsesData || []);
      setFilteredResponses(responsesData || []);
      setSelectedResponse(null);
      setSelectedStudents([]);
      return responsesData;
    } catch (err) {
      console.error('Error fetching responses:', err);
      setAlertMessage(err.message || 'Failed to load responses');
      setAlertSeverity('error');
      setAlertOpen(true);
      return [];
    } finally {
      setLoadingResponses(false);
    }
  };

  // Handle selecting an assignment
  const handleSelectAssignment = async (assignment) => {
    setSelectedAssignment(assignment);
    setQuestionFilter('all');
    setGradingStatusFilter('all');
    setStudentSearch('');
    await fetchResponses(assignment.assignment_id);
  };

  // Handle selecting a response
  const handleSelectResponse = (response) => {
    setSelectedResponse(response);
    setTabValue(0); // Switch to the response tab
  };

  // Apply filters to responses
  useEffect(() => {
    if (!responses) return;

    let filtered = [...responses];

    // Filter by question
    if (questionFilter !== 'all') {
      filtered = filtered.filter(
        (response) => response.question_index === parseInt(questionFilter)
      );
    }

    // Filter by grading status
    if (gradingStatusFilter === 'graded') {
      filtered = filtered.filter((response) => response.grade);
    } else if (gradingStatusFilter === 'ungraded') {
      filtered = filtered.filter((response) => !response.grade);
    }

    // Filter by student search
    if (studentSearch) {
      filtered = filtered.filter((response) =>
        response.student_identifier.toLowerCase().includes(studentSearch.toLowerCase())
      );
    }

    setFilteredResponses(filtered);
  }, [responses, questionFilter, gradingStatusFilter, studentSearch]);

  // Handle starting the grading process
  const handleStartGrading = () => {
    setConfirmGradingOpen(true);
  };

  // Handle the actual grading process
  const handleGradeSubmissions = async () => {
    setConfirmGradingOpen(false);
    setGrading(true);

    try {
      let gradedResponses;
      const questionIndexToGrade = questionFilter === 'all' ? null : parseInt(questionFilter);

      switch (gradingMode) {
        case 'specific':
          // Grade specific students
          if (selectedStudents.length === 0) {
            throw new Error('No students selected for grading');
          }

          gradedResponses = await responseService.gradeSpecific(
            selectedStudents,
            selectedAssignment.assignment_id,
            questionIndexToGrade
          );
          break;

        case 'ungraded':
          // Grade all ungraded responses
          gradedResponses = await responseService.gradeUngraded(
            selectedAssignment.assignment_id,
            questionIndexToGrade
          );
          break;

        case 'all':
          // Grade/regrade all responses
          gradedResponses = await responseService.gradeAll(
            selectedAssignment.assignment_id,
            questionIndexToGrade
          );
          break;

        default:
          throw new Error('Invalid grading mode');
      }

      // Refresh responses after grading
      await fetchResponses(selectedAssignment.assignment_id, questionIndexToGrade);

      // Show success message
      setAlertMessage(
        `Successfully graded ${gradedResponses.length} ${
          gradedResponses.length === 1 ? 'response' : 'responses'
        }`
      );
      setAlertSeverity('success');
      setAlertOpen(true);
    } catch (err) {
      console.error('Error grading submissions:', err);
      setAlertMessage(err.message || 'Failed to grade submissions');
      setAlertSeverity('error');
      setAlertOpen(true);
    } finally {
      setGrading(false);
    }
  };

  // Handle refreshing responses
  const handleRefreshResponses = async () => {
    if (!selectedAssignment) return;

    const questionIndexToFetch = questionFilter === 'all' ? null : parseInt(questionFilter);
    await fetchResponses(selectedAssignment.assignment_id, questionIndexToFetch);

    setAlertMessage('Responses refreshed');
    setAlertSeverity('success');
    setAlertOpen(true);
  };

  // Handle tab change
  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  // Calculate grade percentage
  const calculateGradePercentage = (points, maxPoints) => {
    if (!points || !maxPoints) return 0;
    return (points / maxPoints) * 100;
  };

  // Get letter grade based on percentage
  const getLetterGrade = (percentage) => {
    if (percentage >= 90) return 'A';
    if (percentage >= 80) return 'B';
    if (percentage >= 70) return 'C';
    if (percentage >= 60) return 'D';
    return 'F';
  };

  // Count ungraded responses
  const countUngradedResponses = () => {
    return responses.filter((response) => !response.grade).length;
  };

  // Count responses for a specific question
  const countResponsesForQuestion = (questionIndex) => {
    return responses.filter((response) => response.question_index === questionIndex).length;
  };

  // Count ungraded responses for a specific question
  const countUngradedResponsesForQuestion = (questionIndex) => {
    return responses.filter(
      (response) => response.question_index === questionIndex && !response.grade
    ).length;
  };

  // Render assignment selection section
  const renderAssignmentSelection = () => {
    if (loading) {
      return <CardSkeleton height={100} />;
    }

    if (assignments.length === 0) {
      return (
        <Alert severity="info" sx={{ mb: 3 }}>
          No assignments found. Create an assignment first to grade submissions.
        </Alert>
      );
    }

    return (
      <FormControl fullWidth variant="outlined" sx={{ mb: 3 }}>
        <InputLabel id="assignment-select-label">Assignment</InputLabel>
        <Select
          labelId="assignment-select-label"
          value={selectedAssignment?.assignment_id || ''}
          onChange={(e) => {
            const assignment = assignments.find((a) => a.assignment_id === e.target.value);
            if (assignment) {
              handleSelectAssignment(assignment);
            }
          }}
          label="Assignment"
        >
          {assignments.map((assignment) => (
            <MenuItem key={assignment.assignment_id} value={assignment.assignment_id}>
              {assignment.assignment_title || 'Untitled Assignment'}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    );
  };

  // Render grading actions section
  const renderGradingActions = () => {
    if (!selectedAssignment) return null;

    return (
      <GradingActionCard>
        <Typography variant="h6" gutterBottom>
          Grading Actions
        </Typography>

        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <GradingModeSelect
              value={gradingMode}
              onChange={setGradingMode}
              disabled={grading}
            />
          </Grid>

          <Grid item xs={12} md={4}>
            <FormControl fullWidth variant="outlined">
              <InputLabel id="question-filter-label">Question</InputLabel>
              <Select
                labelId="question-filter-label"
                value={questionFilter}
                onChange={(e) => setQuestionFilter(e.target.value)}
                label="Question"
                disabled={grading}
              >
                <MenuItem value="all">All Questions</MenuItem>
                {selectedAssignment.questions.map((question) => (
                  <MenuItem key={question.question_index} value={question.question_index}>
                    Question {question.question_index + 1}{' '}
                    <Badge
                      badgeContent={countUngradedResponsesForQuestion(question.question_index)}
                      color="error"
                      sx={{ ml: 1 }}
                    />
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} md={4}>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button
                variant="contained"
                color="primary"
                fullWidth
                onClick={handleStartGrading}
                disabled={
                  grading ||
                  responses.length === 0 ||
                  (gradingMode === 'ungraded' && countUngradedResponses() === 0) ||
                  (gradingMode === 'specific' && selectedStudents.length === 0)
                }
                startIcon={<GradeIcon />}
              >
                {grading ? 'Grading...' : 'Start Grading'}
              </Button>

              <Tooltip title="Refresh Responses">
                <IconButton
                  color="primary"
                  onClick={handleRefreshResponses}
                  disabled={grading || loadingResponses}
                >
                  <RefreshIcon />
                </IconButton>
              </Tooltip>
            </Box>
          </Grid>

          <Grid item xs={12}>
            <Divider sx={{ my: 1 }} />

            <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <FilterIcon sx={{ mr: 1, color: 'action.active' }} />
                <FormControl variant="outlined" size="small" sx={{ minWidth: 150 }}>
                  <InputLabel id="status-filter-label">Status</InputLabel>
                  <Select
                    labelId="status-filter-label"
                    value={gradingStatusFilter}
                    onChange={(e) => setGradingStatusFilter(e.target.value)}
                    label="Status"
                    disabled={grading}
                  >
                    <MenuItem value="all">All Responses</MenuItem>
                    <MenuItem value="graded">Graded Only</MenuItem>
                    <MenuItem value="ungraded">Ungraded Only</MenuItem>
                  </Select>
                </FormControl>
              </Box>

              <Box sx={{ display: 'flex', alignItems: 'center', flexGrow: 1 }}>
                <StudentSearchIcon sx={{ mr: 1, color: 'action.active' }} />
                <TextField
                  label="Search Student"
                  variant="outlined"
                  size="small"
                  fullWidth
                  value={studentSearch}
                  onChange={(e) => setStudentSearch(e.target.value)}
                  disabled={grading}
                  InputProps={{
                    endAdornment: studentSearch ? (
                      <IconButton
                        size="small"
                        onClick={() => setStudentSearch('')}
                        edge="end"
                      >
                        <SearchIcon />
                      </IconButton>
                    ) : null,
                  }}
                />
              </Box>

              <Typography variant="body2" color="text.secondary">
                {filteredResponses.length} {filteredResponses.length === 1 ? 'response' : 'responses'} •{' '}
                {countUngradedResponses()} ungraded
              </Typography>
            </Box>
          </Grid>
        </Grid>
      </GradingActionCard>
    );
  };

  // Render responses list and details
  const renderResponsesContent = () => {
    if (loadingResponses) {
      return (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <CircularProgress />
        </Box>
      );
    }

    if (filteredResponses.length === 0) {
      return (
        <Alert severity="info" sx={{ mt: 3 }}>
          No responses found matching the current filters.
        </Alert>
      );
    }

    return (
      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Typography variant="h6" gutterBottom>
            Student Responses
          </Typography>

          <SelectableList
            items={filteredResponses}
            keyField="student_identifier"
            secondaryKeyField="question_index"
            selectedItems={selectedStudents}
            onSelectionChange={setSelectedStudents}
            onItemClick={handleSelectResponse}
            highlightedItem={selectedResponse}
            selectionMode={gradingMode === 'specific' ? 'multiple' : 'none'}
            renderItem={(response) => (
              <Box>
                <Typography variant="subtitle1" noWrap>
                  {response.student_identifier}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Question {response.question_index + 1}
                </Typography>
                <Box sx={{ mt: 1, display: 'flex', alignItems: 'center' }}>
                  {response.grade ? (
                    <>
                      <GradedIcon
                        fontSize="small"
                        color="success"
                        sx={{ mr: 0.5 }}
                      />
                      <Typography variant="body2" color="success.main">
                        Graded: {response.grade.points}/{response.grade.max_points} points
                      </Typography>
                    </>
                  ) : (
                    <Chip
                      label="Ungraded"
                      size="small"
                      color="warning"
                      variant="outlined"
                    />
                  )}
                </Box>
              </Box>
            )}
          />
        </Grid>

        <Grid item xs={12} md={8}>
          {selectedResponse ? (
            <>
              <Paper sx={{ mb: 3 }}>
                <Tabs
                  value={tabValue}
                  onChange={handleTabChange}
                  variant="fullWidth"
                  aria-label="response tabs"
                >
                  <Tab label="Response" icon={<QuestionIcon />} iconPosition="start" />
                  <Tab
                    label="Grade"
                    icon={<GradedIcon />}
                    iconPosition="start"
                    disabled={!selectedResponse.grade}
                  />
                </Tabs>
              </Paper>

              <TabPanel value={tabValue} index={0}>
                <ResponseCard>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                    <Typography variant="h6">
                      {selectedResponse.student_identifier}
                    </Typography>

                    <Chip
                      label={selectedResponse.grade ? 'Graded' : 'Ungraded'}
                      color={selectedResponse.grade ? 'success' : 'warning'}
                      variant="outlined"
                    />
                  </Box>

                  <Typography variant="subtitle1" gutterBottom>
                    Question {selectedResponse.question_index + 1}:
                  </Typography>

                  <Typography variant="body2" paragraph sx={{ mb: 3 }}>
                    {getQuestionText(selectedResponse.question_index)}
                  </Typography>

                  <Divider sx={{ mb: 3 }} />

                  <Typography variant="subtitle1" gutterBottom>
                    Student Response:
                  </Typography>

                  <Paper
                    elevation={0}
                    sx={{
                      p: 2,
                      bgcolor: 'background.default',
                      borderRadius: 1,
                      whiteSpace: 'pre-wrap',
                    }}
                  >
                    {/*
                      In a real implementation, this would render the response data
                      based on its type (text, file, etc.)
                    */}
                    {selectedResponse.data.content || 'No response content available'}
                  </Paper>
                </ResponseCard>
              </TabPanel>

              <TabPanel value={tabValue} index={1}>
                {selectedResponse.grade ? (
                  <GradeCard
                    gradePercent={calculateGradePercentage(
                      selectedResponse.grade.points,
                      selectedResponse.grade.max_points
                    )}
                  >
                    <Box
                      sx={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'flex-start',
                        mb: 2,
                      }}
                    >
                      <Typography variant="h6">
                        Grade for {selectedResponse.student_identifier}
                      </Typography>

                      <Box sx={{ textAlign: 'right' }}>
                        <Typography variant="h4" color="primary">
                          {selectedResponse.grade.points}/{selectedResponse.grade.max_points}
                        </Typography>
                        <Typography variant="subtitle1" color="text.secondary">
                          {calculateGradePercentage(
                            selectedResponse.grade.points,
                            selectedResponse.grade.max_points
                          ).toFixed(1)}
                          % ({getLetterGrade(
                            calculateGradePercentage(
                              selectedResponse.grade.points,
                              selectedResponse.grade.max_points
                            )
                          )})
                        </Typography>
                      </Box>
                    </Box>

                    <Divider sx={{ mb: 3 }} />

                    <Typography variant="subtitle1" gutterBottom>
                      Grading Explanation:
                    </Typography>

                    <Paper
                      elevation={0}
                      sx={{
                        p: 2,
                        bgcolor: 'background.default',
                        borderRadius: 1,
                        whiteSpace: 'pre-wrap',
                      }}
                    >
                      {selectedResponse.grade.explanation || 'No explanation provided'}
                    </Paper>
                  </GradeCard>
                ) : (
                  <Alert severity="info">
                    This response has not been graded yet.
                  </Alert>
                )}
              </TabPanel>
            </>
          ) : (
            <Paper
              sx={{
                p: 3,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                height: 300,
              }}
            >
              <AssignmentIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                No Response Selected
              </Typography>
              <Typography variant="body2" color="text.secondary" align="center">
                Select a student response from the list to view details and grading information.
              </Typography>
            </Paper>
          )}
        </Grid>
      </Grid>
    );
  };

  // Helper function to get question text
  const getQuestionText = (questionIndex) => {
    if (!selectedAssignment) return '';

    const question = selectedAssignment.questions.find(
      (q) => q.question_index === questionIndex
    );

    return question ? question.question_text : '';
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
          Grading Dashboard
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {renderAssignmentSelection()}

      {selectedAssignment && renderGradingActions()}

      {selectedAssignment && renderResponsesContent()}

      {/* Grading Confirmation Dialog */}
      <ConfirmationDialog
        open={confirmGradingOpen}
        title="Confirm Grading Action"
        message={
          gradingMode === 'specific'
            ? `You are about to grade ${selectedStudents.length} selected student ${
                selectedStudents.length === 1 ? 'response' : 'responses'
              }. This process may take some time. Do you want to continue?`
            : gradingMode === 'ungraded'
            ? `You are about to grade all ungraded responses${
                questionFilter !== 'all'
                  ? ` for Question ${parseInt(questionFilter) + 1}`
                  : ''
              }. This process may take some time. Do you want to continue?`
            : `You are about to grade/regrade ALL responses${
                questionFilter !== 'all'
                  ? ` for Question ${parseInt(questionFilter) + 1}`
                  : ''
              }. This will overwrite any existing grades. This process may take some time. Do you want to continue?`
        }
        confirmText="Start Grading"
        cancelText="Cancel"
        onConfirm={handleGradeSubmissions}
        onCancel={() => setConfirmGradingOpen(false)}
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