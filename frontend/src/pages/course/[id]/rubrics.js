/**
 * Rubric Management Page for BU MET Autograder
 * Create, edit, and apply grading rubrics
 */

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
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
  DialogTitle,
  Divider,
  FormControl,
  FormControlLabel,
  FormGroup,
  Grid,
  IconButton,
  InputAdornment,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Slider,
  Snackbar,
  Switch,
  Tab,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  Add as AddIcon,
  ArrowBack as ArrowBackIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Lightbulb as LightbulbIcon,
  Save as SaveIcon,
  Assignment as AssignmentIcon,
  RuleFolder as RubricIcon,
  Help as HelpIcon,
} from '@mui/icons-material';
import { assignmentService, rubricService } from '../../../api';
import CardSkeleton from '../../../components/CardSkeleton';
import AISuggestionCard from '../../../components/AISuggestionCard';
import ConfirmationDialog from '../../../components/ConfirmationDialog';

// Styled components
const StyledCard = styled(Card)(({ theme }) => ({
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
  transition: 'transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out',
  '&:hover': {
    transform: 'translateY(-4px)',
    boxShadow: theme.shadows[4],
  },
}));

const RubricSection = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  marginBottom: theme.spacing(3),
}));

const CriteriaCard = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(2),
  marginBottom: theme.spacing(2),
  borderLeft: `4px solid ${theme.palette.primary.main}`,
}));

const TabPanel = (props) => {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`rubric-tabpanel-${index}`}
      aria-labelledby={`rubric-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
};

// Main component
export default function RubricManagement() {
  const router = useRouter();
  const { id: courseId, semester, assignmentId: selectedAssignmentId } = router.query;

  // State for assignments and rubrics
  const [assignments, setAssignments] = useState([]);
  const [selectedAssignment, setSelectedAssignment] = useState(null);
  const [rubric, setRubric] = useState(null);
  const [aiRubric, setAiRubric] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingAI, setLoadingAI] = useState(false);
  const [error, setError] = useState(null);

  // State for tabs and editing
  const [tabValue, setTabValue] = useState(0);
  const [editMode, setEditMode] = useState(false);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);

  // State for dialog controls
  const [criteriaDialogOpen, setCriteriaDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [aiInstructionsDialogOpen, setAiInstructionsDialogOpen] = useState(false);

  // State for form data
  const [criteriaData, setCriteriaData] = useState({
    criteria_id: '',
    criteria: '',
    points: 0,
  });

  const [criteriaToDelete, setCriteriaToDelete] = useState(null);
  const [aiInstructions, setAiInstructions] = useState('');

  // State for alerts
  const [alertOpen, setAlertOpen] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [alertSeverity, setAlertSeverity] = useState('success');

  // Define grading flags
  const gradingFlags = [
    { value: 'IGNORE_SPELLINGS', label: 'Ignore Spellings', description: 'Ignore minor spelling mistakes' },
    { value: 'IGNORE_GRAMMAR', label: 'Ignore Grammar', description: 'Ignore minor grammar issues' },
    { value: 'ORIGINALITY', label: 'Reward Originality', description: 'Reward originality and deduct for unoriginal ideas' },
    { value: 'IGNORE_FORMATTING', label: 'Ignore Formatting', description: 'Ignore formatting issues' },
  ];

  // Fetch assignments and selected assignment data
  useEffect(() => {
    const fetchAssignments = async () => {
      if (!courseId || !semester) return;

      setLoading(true);
      try {
        const assignmentsData = await assignmentService.getAssignments(courseId, semester);
        setAssignments(assignmentsData || []);

        // If an assignment ID is provided in the URL, select it
        if (selectedAssignmentId) {
          const assignment = assignmentsData.find(
            (a) => a.assignment_id === selectedAssignmentId
          );

          if (assignment) {
            setSelectedAssignment(assignment);
            await fetchRubric(assignment.assignment_id);
          }
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
  }, [courseId, semester, selectedAssignmentId]);

  // Fetch rubric for selected assignment
  const fetchRubric = async (assignmentId) => {
    try {
      const rubricData = await rubricService.getRubric(assignmentId);
      setRubric(rubricData);

      // Set default current question index
      if (rubricData && rubricData.sub_rubrics && rubricData.sub_rubrics.length > 0) {
        setCurrentQuestionIndex(rubricData.sub_rubrics[0].question_index);
      }

      return rubricData;
    } catch (err) {
      console.error('Error fetching rubric:', err);
      // If no rubric exists, create an empty one
      const emptyRubric = createEmptyRubric(assignmentId);
      setRubric(emptyRubric);
      return emptyRubric;
    }
  };

  // Create an empty rubric structure
  const createEmptyRubric = (assignmentId) => {
    const assignment = assignments.find((a) => a.assignment_id === assignmentId);

    if (!assignment) return null;

    const subRubrics = assignment.questions.map((question) => ({
      question_index: question.question_index,
      max_points: 10, // Default max points
      instructor_guideline: '',
      grading_criteria: [],
    }));

    return {
      assignment_id: assignmentId,
      grading_flags: [],
      leniency: 3, // Default leniency (1-5)
      overall_instructor_guidelines: '',
      sub_rubrics: subRubrics,
    };
  };

  // Handle selecting an assignment
  const handleSelectAssignment = async (assignment) => {
    setSelectedAssignment(assignment);
    setTabValue(0); // Reset to the first tab

    // Fetch or create rubric for this assignment
    await fetchRubric(assignment.assignment_id);

    // Update URL with selected assignment ID
    router.push(`/course/${courseId}/rubrics?semester=${semester}&assignmentId=${assignment.assignment_id}`, undefined, { shallow: true });
  };

  // Get AI-generated rubric suggestions
  const getAIRubricSuggestions = async () => {
    if (!selectedAssignment) return;

    setLoadingAI(true);
    try {
      const aiRubricData = await rubricService.getAIRubric(
        selectedAssignment.assignment_id,
        aiInstructions || null
      );

      setAiRubric(aiRubricData);
      setAiInstructionsDialogOpen(false);
      setAiInstructions('');

      // Show success alert
      setAlertMessage('AI-generated rubric suggestions received');
      setAlertSeverity('success');
      setAlertOpen(true);
    } catch (err) {
      console.error('Error getting AI rubric suggestions:', err);
      setAlertMessage(err.message || 'Failed to get AI rubric suggestions');
      setAlertSeverity('error');
      setAlertOpen(true);
    } finally {
      setLoadingAI(false);
    }
  };

  // Apply AI rubric suggestions to current rubric
  const applyAIRubricSuggestions = () => {
    if (!aiRubric) return;

    setRubric(aiRubric);
    setAiRubric(null);

    // Show success alert
    setAlertMessage('AI rubric suggestions applied');
    setAlertSeverity('success');
    setAlertOpen(true);
  };

  // Save rubric changes
  const saveRubric = async () => {
    if (!rubric) return;

    try {
      await rubricService.createRubric(rubric);

      setEditMode(false);

      // Show success alert
      setAlertMessage('Rubric saved successfully');
      setAlertSeverity('success');
      setAlertOpen(true);
    } catch (err) {
      console.error('Error saving rubric:', err);
      setAlertMessage(err.message || 'Failed to save rubric');
      setAlertSeverity('error');
      setAlertOpen(true);
    }
  };

  // Handle adding a grading criteria
  const handleAddCriteria = () => {
    if (!rubric || !selectedAssignment) return;

    // Find the current sub-rubric
    const currentSubRubric = rubric.sub_rubrics.find(
      (sr) => sr.question_index === currentQuestionIndex
    );

    if (!currentSubRubric) return;

    // Add the new criteria
    const newCriteria = {
      criteria_id: criteriaData.criteria_id,
      criteria: criteriaData.criteria,
      points: parseFloat(criteriaData.points),
    };

    // Update the sub-rubric's grading criteria
    const updatedSubRubrics = rubric.sub_rubrics.map((sr) => {
      if (sr.question_index === currentQuestionIndex) {
        return {
          ...sr,
          grading_criteria: [...(sr.grading_criteria || []), newCriteria],
        };
      }
      return sr;
    });

    // Update the rubric
    setRubric({
      ...rubric,
      sub_rubrics: updatedSubRubrics,
    });

    // Reset form and close dialog
    setCriteriaData({
      criteria_id: '',
      criteria: '',
      points: 0,
    });
    setCriteriaDialogOpen(false);
  };

  // Handle editing a grading criteria
  const handleEditCriteria = (subRubricIndex, criteriaIndex, updatedCriteria) => {
    if (!rubric) return;

    // Create a deep copy of the sub_rubrics array
    const updatedSubRubrics = [...rubric.sub_rubrics];

    // Update the specific criteria
    if (updatedSubRubrics[subRubricIndex].grading_criteria) {
      updatedSubRubrics[subRubricIndex].grading_criteria[criteriaIndex] = updatedCriteria;
    }

    // Update the rubric
    setRubric({
      ...rubric,
      sub_rubrics: updatedSubRubrics,
    });
  };

  // Handle deleting a grading criteria
  const handleDeleteCriteria = () => {
    if (!rubric || !criteriaToDelete) return;

    const { subRubricIndex, criteriaIndex } = criteriaToDelete;

    // Create a deep copy of the sub_rubrics array
    const updatedSubRubrics = [...rubric.sub_rubrics];

    // Remove the criteria
    if (updatedSubRubrics[subRubricIndex].grading_criteria) {
      updatedSubRubrics[subRubricIndex].grading_criteria.splice(criteriaIndex, 1);
    }

    // Update the rubric
    setRubric({
      ...rubric,
      sub_rubrics: updatedSubRubrics,
    });

    // Close dialog
    setDeleteDialogOpen(false);
    setCriteriaToDelete(null);
  };

  // Handle updating overall rubric settings
  const handleRubricSettingChange = (field, value) => {
    if (!rubric) return;

    setRubric({
      ...rubric,
      [field]: value,
    });
  };

  // Handle updating sub-rubric settings
  const handleSubRubricChange = (questionIndex, field, value) => {
    if (!rubric) return;

    const updatedSubRubrics = rubric.sub_rubrics.map((sr) => {
      if (sr.question_index === questionIndex) {
        return {
          ...sr,
          [field]: value,
        };
      }
      return sr;
    });

    setRubric({
      ...rubric,
      sub_rubrics: updatedSubRubrics,
    });
  };

  // Handle toggling grading flags
  const handleGradingFlagToggle = (flag) => {
    if (!rubric) return;

    const currentFlags = rubric.grading_flags || [];
    const updatedFlags = currentFlags.includes(flag)
      ? currentFlags.filter((f) => f !== flag)
      : [...currentFlags, flag];

    setRubric({
      ...rubric,
      grading_flags: updatedFlags,
    });
  };

  // Handle tab change
  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  // Get the question text for a given index
  const getQuestionText = (questionIndex) => {
    if (!selectedAssignment) return '';

    const question = selectedAssignment.questions.find(
      (q) => q.question_index === questionIndex
    );

    return question ? question.question_text : '';
  };

  // Calculate total points for a sub-rubric
  const calculateTotalPoints = (subRubric) => {
    if (!subRubric || !subRubric.grading_criteria) return 0;

    return subRubric.grading_criteria.reduce(
      (sum, criteria) => sum + parseFloat(criteria.points),
      0
    );
  };

  // Render assignment selection section
  const renderAssignmentSelection = () => {
    if (loading) {
      return <CardSkeleton height={100} />;
    }

    if (assignments.length === 0) {
      return (
        <Alert severity="info" sx={{ mb: 3 }}>
          No assignments found. Create an assignment first to define rubrics.
        </Alert>
      );
    }

    return (
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {assignments.map((assignment) => (
          <Grid item xs={12} sm={6} md={4} key={assignment.assignment_id}>
            <StyledCard
              raised={selectedAssignment?.assignment_id === assignment.assignment_id}
              onClick={() => handleSelectAssignment(assignment)}
              sx={{ cursor: 'pointer' }}
            >
              <CardContent>
                <Typography variant="h6" component="h2" noWrap>
                  {assignment.assignment_title || 'Untitled Assignment'}
                </Typography>

                <Typography variant="body2" color="text.secondary">
                  {assignment.questions.length} {assignment.questions.length === 1 ? 'question' : 'questions'}
                </Typography>

                <Chip
                  label={selectedAssignment?.assignment_id === assignment.assignment_id ? 'Selected' : 'Select'}
                  color={selectedAssignment?.assignment_id === assignment.assignment_id ? 'primary' : 'default'}
                  size="small"
                  sx={{ mt: 1 }}
                />
              </CardContent>
            </StyledCard>
          </Grid>
        ))}
      </Grid>
    );
  };

  // Render rubric tabs and content
  const renderRubricContent = () => {
    if (!selectedAssignment || !rubric) return null;

    return (
      <>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h5">
            Rubric for {selectedAssignment.assignment_title || 'Untitled Assignment'}
          </Typography>

          <Box>
            {editMode ? (
              <>
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<SaveIcon />}
                  onClick={saveRubric}
                  sx={{ mr: 1 }}
                >
                  Save
                </Button>
                <Button
                  variant="outlined"
                  onClick={() => setEditMode(false)}
                >
                  Cancel
                </Button>
              </>
            ) : (
              <>
                <Button
                  variant="outlined"
                  startIcon={<LightbulbIcon />}
                  onClick={() => setAiInstructionsDialogOpen(true)}
                  sx={{ mr: 1 }}
                >
                  Get AI Suggestions
                </Button>
                <Button
                  variant="contained"
                  startIcon={<EditIcon />}
                  onClick={() => setEditMode(true)}
                >
                  Edit Rubric
                </Button>
              </>
            )}
          </Box>
        </Box>

        <Paper sx={{ mb: 3 }}>
          <Tabs
            value={tabValue}
            onChange={handleTabChange}
            variant="scrollable"
            scrollButtons="auto"
            aria-label="rubric tabs"
          >
            <Tab label="Overall Guidelines" />
            {rubric.sub_rubrics.map((subRubric) => (
              <Tab
                key={`question-${subRubric.question_index}`}
                label={`Question ${subRubric.question_index + 1}`}
                onClick={() => setCurrentQuestionIndex(subRubric.question_index)}
              />
            ))}
          </Tabs>
        </Paper>

        {/* Overall Guidelines Tab */}
        <TabPanel value={tabValue} index={0}>
          <RubricSection>
            <Typography variant="h6" gutterBottom>
              General Rubric Settings
            </Typography>

            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <TextField
                  label="Overall Instructor Guidelines"
                  multiline
                  rows={4}
                  fullWidth
                  value={rubric.overall_instructor_guidelines || ''}
                  onChange={(e) => handleRubricSettingChange('overall_instructor_guidelines', e.target.value)}
                  disabled={!editMode}
                  placeholder="Enter general grading instructions applicable to all questions"
                  variant="outlined"
                  margin="normal"
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <Typography variant="subtitle1" gutterBottom>
                  Leniency Level
                </Typography>

                <Box sx={{ px: 2 }}>
                  <Slider
                    value={rubric.leniency || 3}
                    min={1}
                    max={5}
                    step={1}
                    marks={[
                      { value: 1, label: 'Strict' },
                      { value: 2, label: '' },
                      { value: 3, label: 'Moderate' },
                      { value: 4, label: '' },
                      { value: 5, label: 'Lenient' },
                    ]}
                    valueLabelDisplay="auto"
                    onChange={(e, value) => handleRubricSettingChange('leniency', value)}
                    disabled={!editMode}
                  />
                </Box>

                <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                  Leniency determines how strictly the responses will be graded. Higher leniency allows for more flexibility in answers.
                </Typography>
              </Grid>

              <Grid item xs={12}>
                <Typography variant="subtitle1" gutterBottom>
                  Grading Flags
                </Typography>

                <FormGroup row>
                  {gradingFlags.map((flag) => (
                    <Tooltip key={flag.value} title={flag.description} arrow>
                      <FormControlLabel
                        control={
                          <Switch
                            checked={(rubric.grading_flags || []).includes(flag.value)}
                            onChange={() => handleGradingFlagToggle(flag.value)}
                            disabled={!editMode}
                            color="primary"
                          />
                        }
                        label={flag.label}
                      />
                    </Tooltip>
                  ))}
                </FormGroup>
              </Grid>
            </Grid>
          </RubricSection>
        </TabPanel>

        {/* Question-specific Sub-rubric Tabs */}
        {rubric.sub_rubrics.map((subRubric, subRubricIndex) => (
          <TabPanel
            key={`subRubric-${subRubric.question_index}`}
            value={tabValue}
            index={subRubricIndex + 1}
          >
            <RubricSection>
              <Typography variant="h6" gutterBottom>
                Question {subRubric.question_index + 1}
              </Typography>

              <Typography
                variant="body1"
                sx={{
                  bgcolor: 'background.default',
                  p: 2,
                  borderRadius: 1,
                  mb: 3,
                }}
              >
                {getQuestionText(subRubric.question_index)}
              </Typography>

              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <TextField
                    label="Instructor Guideline"
                    multiline
                    rows={4}
                    fullWidth
                    value={subRubric.instructor_guideline || ''}
                    onChange={(e) =>
                      handleSubRubricChange(
                        subRubric.question_index,
                        'instructor_guideline',
                        e.target.value
                      )
                    }
                    disabled={!editMode}
                    placeholder="Enter specific instructions for grading this question"
                    variant="outlined"
                    margin="normal"
                  />
                </Grid>

                <Grid item xs={12} md={6}>
                  <TextField
                    label="Maximum Points"
                    type="number"
                    fullWidth
                    value={subRubric.max_points || 0}
                    onChange={(e) =>
                      handleSubRubricChange(
                        subRubric.question_index,
                        'max_points',
                        parseFloat(e.target.value)
                      )
                    }
                    disabled={!editMode}
                    InputProps={{
                      inputProps: { min: 0, step: 0.5 },
                    }}
                    variant="outlined"
                    margin="normal"
                  />

                  <FormControl fullWidth margin="normal">
                    <InputLabel id={`leniency-select-${subRubric.question_index}`}>
                      Question-specific Leniency
                    </InputLabel>
                    <Select
                      labelId={`leniency-select-${subRubric.question_index}`}
                      value={subRubric.leniency || ''}
                      onChange={(e) =>
                        handleSubRubricChange(
                          subRubric.question_index,
                          'leniency',
                          e.target.value === '' ? null : parseInt(e.target.value)
                        )
                      }
                      disabled={!editMode}
                      label="Question-specific Leniency"
                    >
                      <MenuItem value="">
                        <em>Use global leniency</em>
                      </MenuItem>
                      <MenuItem value={1}>1 - Very Strict</MenuItem>
                      <MenuItem value={2}>2 - Strict</MenuItem>
                      <MenuItem value={3}>3 - Moderate</MenuItem>
                      <MenuItem value={4}>4 - Lenient</MenuItem>
                      <MenuItem value={5}>5 - Very Lenient</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
              </Grid>
            </RubricSection>

            <RubricSection>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">
                  Grading Criteria
                </Typography>

                {editMode && (
                  <Button
                    variant="contained"
                    color="primary"
                    startIcon={<AddIcon />}
                    onClick={() => setCriteriaDialogOpen(true)}
                  >
                    Add Criteria
                  </Button>
                )}
              </Box>

              {(!subRubric.grading_criteria || subRubric.grading_criteria.length === 0) ? (
                <Box sx={{ textAlign: 'center', py: 3 }}>
                  <RubricIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
                  <Typography variant="body1" color="text.secondary">
                    No grading criteria defined yet.
                  </Typography>
                  {editMode && (
                    <Button
                      variant="contained"
                      color="primary"
                      startIcon={<AddIcon />}
                      onClick={() => setCriteriaDialogOpen(true)}
                      sx={{ mt: 2 }}
                    >
                      Add Criteria
                    </Button>
                  )}
                </Box>
              ) : (
                <>
                  {subRubric.grading_criteria.map((criteria, criteriaIndex) => (
                    <CriteriaCard key={`criteria-${criteriaIndex}`}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <Box>
                          <Typography variant="subtitle1" fontWeight="bold">
                            {criteria.criteria_id || `Criteria ${criteriaIndex + 1}`}
                          </Typography>

                          <Typography variant="body2" sx={{ mt: 1 }}>
                            {criteria.criteria}
                          </Typography>
                        </Box>

                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <Chip
                            label={`${criteria.points} points`}
                            color="primary"
                            variant="outlined"
                          />

                          {editMode && (
                            <IconButton
                              color="error"
                              size="small"
                              onClick={() => {
                                setCriteriaToDelete({
                                  subRubricIndex,
                                  criteriaIndex,
                                });
                                setDeleteDialogOpen(true);
                              }}
                              sx={{ ml: 1 }}
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          )}
                        </Box>
                      </Box>
                    </CriteriaCard>
                  ))}

                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 2 }}>
                    <Typography variant="subtitle1">
                      Total Points: {calculateTotalPoints(subRubric)}
                    </Typography>

                    <Typography
                      variant="subtitle1"
                      color={
                        calculateTotalPoints(subRubric) === parseFloat(subRubric.max_points)
                          ? 'success.main'
                          : 'error.main'
                      }
                    >
                      {calculateTotalPoints(subRubric) === parseFloat(subRubric.max_points)
                        ? 'Points match maximum'
                        : `Warning: Total (${calculateTotalPoints(subRubric)}) doesn't match maximum (${subRubric.max_points})`}
                    </Typography>
                  </Box>
                </>
              )}
            </RubricSection>
          </TabPanel>
        ))}
      </>
    );
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
          Rubric Management
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Typography variant="h5" sx={{ mb: 2 }}>
        Select an Assignment
      </Typography>

      {renderAssignmentSelection()}

      {renderRubricContent()}

      {/* AI Suggestion Card */}
      {aiRubric && (
        <AISuggestionCard
          rubric={aiRubric}
          onApply={applyAIRubricSuggestions}
          onDismiss={() => setAiRubric(null)}
        />
      )}

      {/* Add Criteria Dialog */}
      <Dialog
        open={criteriaDialogOpen}
        onClose={() => setCriteriaDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Add Grading Criteria</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            label="Criteria Title"
            fullWidth
            value={criteriaData.criteria_id}
            onChange={(e) => setCriteriaData({ ...criteriaData, criteria_id: e.target.value })}
            margin="normal"
            required
            placeholder="e.g., Correct Logic, Proper Format, etc."
          />

          <TextField
            label="Criteria Description"
            fullWidth
            multiline
            rows={3}
            value={criteriaData.criteria}
            onChange={(e) => setCriteriaData({ ...criteriaData, criteria: e.target.value })}
            margin="normal"
            required
            placeholder="Describe what constitutes fulfilling this criteria"
          />

          <TextField
            label="Points"
            type="number"
            fullWidth
            value={criteriaData.points}
            onChange={(e) => setCriteriaData({ ...criteriaData, points: e.target.value })}
            margin="normal"
            required
            InputProps={{
              inputProps: { min: 0, step: 0.5 },
              endAdornment: <InputAdornment position="end">points</InputAdornment>,
            }}
          />
        </DialogContent>

        <DialogActions>
          <Button onClick={() => setCriteriaDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleAddCriteria}
            variant="contained"
            color="primary"
            disabled={!criteriaData.criteria_id || !criteriaData.criteria || criteriaData.points <= 0}
          >
            Add
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Criteria Confirmation Dialog */}
      <ConfirmationDialog
        open={deleteDialogOpen}
        title="Delete Grading Criteria"
        message="Are you sure you want to delete this grading criteria? This action cannot be undone."
        confirmText="Delete"
        cancelText="Cancel"
        confirmButtonProps={{ color: 'error' }}
        onConfirm={handleDeleteCriteria}
        onCancel={() => {
          setDeleteDialogOpen(false);
          setCriteriaToDelete(null);
        }}
      />

      {/* AI Instructions Dialog */}
      <Dialog
        open={aiInstructionsDialogOpen}
        onClose={() => !loadingAI && setAiInstructionsDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <LightbulbIcon sx={{ mr: 1, color: 'warning.main' }} />
            AI Rubric Suggestions
          </Box>
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" paragraph>
            Our AI can analyze your assignment and questions to suggest a comprehensive rubric.
            You can provide specific instructions to guide the AI.
          </Typography>

          <TextField
            label="Instructions for AI (Optional)"
            fullWidth
            multiline
            rows={4}
            value={aiInstructions}
            onChange={(e) => setAiInstructions(e.target.value)}
            margin="normal"
            placeholder="e.g., Focus on logical reasoning, prioritize code efficiency, etc."
            disabled={loadingAI}
          />
        </DialogContent>

        <DialogActions>
          <Button
            onClick={() => setAiInstructionsDialogOpen(false)}
            disabled={loadingAI}
          >
            Cancel
          </Button>
          <Button
            onClick={getAIRubricSuggestions}
            variant="contained"
            color="primary"
            disabled={loadingAI}
            startIcon={loadingAI ? null : <LightbulbIcon />}
          >
            {loadingAI ? 'Generating...' : 'Get AI Suggestions'}
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