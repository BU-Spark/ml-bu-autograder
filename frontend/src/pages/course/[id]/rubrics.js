/**
 * Rubric Management Page for BU MET Autograder
 * Create, edit, and apply grading rubrics
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import {
  Alert,
  Avatar,
  Box,
  Button,
  Card,
  CardActionArea,
  CardActions,
  CardContent,
  Chip,
  CircularProgress,
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
  Link as MuiLink, // Imported MuiLink
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
  HelpOutline as HelpIcon,
  Info as InfoIcon,
  PlaylistAddCheck as CriteriaIcon,
} from '@mui/icons-material';
// Assuming api.js is correctly imported
import { assignmentService, rubricService } from '../../../api'; // Adjust path if needed
import CardSkeleton from '../../../components/CardSkeleton'; // Assuming exists
import AISuggestionCard from '../../../components/AISuggestionCard'; // Assuming exists
import ConfirmationDialog from '../../../components/ConfirmationDialog'; // Assuming exists

// Styled components
const AssignmentSelectionCard = styled(Card)(({ theme, selected }) => ({
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
  border: selected ? `2px solid ${theme.palette.primary.main}` : `1px solid ${theme.palette.divider}`,
  transition: 'transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out, border 0.2s ease-in-out',
  cursor: 'pointer',
  '&:hover': {
    transform: 'translateY(-4px)',
    boxShadow: theme.shadows[4],
  },
}));

const RubricSection = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  marginBottom: theme.spacing(3),
  border: `1px solid ${theme.palette.divider}`,
}));

const CriteriaCard = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(2),
  marginBottom: theme.spacing(2),
  borderLeft: `4px solid ${theme.palette.primary.light}`,
  backgroundColor: theme.palette.background.default,
  '&:last-child': {
    marginBottom: 0,
  },
}));

// Tab Panel Helper
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

// Grading flags definition
const GRADING_FLAGS_CONFIG = [
  { value: 'IGNORE_SPELLINGS', label: 'Ignore Spelling', description: 'AI ignores minor spelling mistakes during grading.' },
  { value: 'IGNORE_GRAMMAR', label: 'Ignore Grammar', description: 'AI ignores minor grammatical errors during grading.' },
  { value: 'ORIGINALITY', label: 'Reward Originality', description: 'AI rewards originality and may deduct for unoriginal ideas/plagiarism (experimental).' },
  { value: 'IGNORE_FORMATTING', label: 'Ignore Formatting', description: 'AI ignores formatting inconsistencies (e.g., spacing, list styles) during grading.' },
];

// Main component
export default function RubricManagement() {
  const router = useRouter();
  const { id: courseId, semester, assignmentId: assignmentIdParam } = router.query;
  // Keep assignmentId as string or null
  const selectedAssignmentId = typeof assignmentIdParam === 'string' ? assignmentIdParam : null;

  // State
  const [assignments, setAssignments] = useState([]);
  const [selectedAssignment, setSelectedAssignment] = useState(null);
  const [rubric, setRubric] = useState(null);
  const [aiRubricSuggestion, setAiRubricSuggestion] = useState(null);
  const [loadingAssignments, setLoadingAssignments] = useState(true);
  const [loadingRubric, setLoadingRubric] = useState(false);
  const [loadingAI, setLoadingAI] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);
  const [tabValue, setTabValue] = useState(0);
  const [editMode, setEditMode] = useState(false);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0); // Stores the actual question_index (number)
  const [criteriaDialogOpen, setCriteriaDialogOpen] = useState(false);
  const [editingCriteriaIndex, setEditingCriteriaIndex] = useState(null); // Stores array index for editing
  const [deleteCriteriaDialogOpen, setDeleteCriteriaDialogOpen] = useState(false);
  const [aiInstructionsDialogOpen, setAiInstructionsDialogOpen] = useState(false);
  const [criteriaFormData, setCriteriaFormData] = useState({ criteria_id: '', criteria: '', points: 0 });
  const [criteriaToDelete, setCriteriaToDelete] = useState(null); // Stores { criteriaArrayIndex }
  const [aiInstructions, setAiInstructions] = useState('');
  const [alertOpen, setAlertOpen] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [alertSeverity, setAlertSeverity] = useState('success');

  // --- Helper Functions ---
  const showAlert = useCallback((message, severity = 'success') => {
    setAlertMessage(message);
    setAlertSeverity(severity);
    setAlertOpen(true);
  }, []);

  const formatApiError = useCallback((err, defaultMessage) => {
    console.error("API Error:", err);
    if (err?.response?.data?.detail) {
        if (Array.isArray(err.response.data.detail)) {
            return err.response.data.detail.map(d => `${d.loc?.join('.') || 'error'}: ${d.msg}`).join('; ');
        }
        return String(err.response.data.detail);
    }
    if (err?.message) {
      return err.message;
    }
    return defaultMessage;
  }, []);

  // Defined as regular function before usage
  function calculateTotalPoints(subRubric) {
    return subRubric?.grading_criteria?.reduce((sum, c) => {
        const points = parseFloat(String(c?.points));
        return sum + (isNaN(points) ? 0 : points);
    }, 0) ?? 0;
  }

  const createEmptyRubric = useCallback((assignment) => {
    if (!assignment || !semester || !courseId) {
        console.error("Cannot create empty rubric: missing assignment, semester, or courseId");
        return null;
    }
    const currentAssignmentId = String(assignment.assignment_id); // Ensure string
    const sortedQuestions = [...(assignment.questions || [])].sort((a,b) => (a.question_index ?? Infinity) - (b.question_index ?? Infinity));
    const subRubrics = sortedQuestions.map(question => ({
        question_index: question.question_index,
        max_points: 10,
        instructor_guideline: '',
        leniency: null,
        grading_criteria: [],
    }));
    return {
        semester: semester,
        course_id: courseId,
        assignment_id: currentAssignmentId, // Store as string
        grading_flags: [],
        leniency: 3,
        overall_instructor_guidelines: '',
        sub_rubrics: subRubrics,
    };
  }, [semester, courseId]);


  // --- Data Fetching ---
  const fetchRubric = useCallback(async (assignment) => {
    if (!semester || !courseId || !assignment?.assignment_id) {
        console.warn("Cannot fetch rubric: Missing context or assignmentId.", { semester, courseId, assignment });
        setRubric(createEmptyRubric(assignment)); setTabValue(0);
        setCurrentQuestionIndex(assignment?.questions?.[0]?.question_index ?? 0);
        setLoadingRubric(false); return;
    }
    setLoadingRubric(true); setError(null);
    const assignmentIdStr = String(assignment.assignment_id); // Use string for API
    try {
        const response = await rubricService.getRubric(semester, courseId, assignmentIdStr);
        let fetchedRubricData = response.data;
        let completeRubric;

        if (fetchedRubricData && typeof fetchedRubricData === 'object') {
            if (typeof fetchedRubricData.assignment_id !== 'string') { fetchedRubricData.assignment_id = String(fetchedRubricData.assignment_id); } // Ensure string ID
            completeRubric = { ...createEmptyRubric(assignment), ...fetchedRubricData };
            // Align sub-rubrics with current questions
            const currentQuestionIndices = new Set(assignment.questions?.map(q => q.question_index) ?? []);
            completeRubric.sub_rubrics = completeRubric.sub_rubrics?.filter(sr => currentQuestionIndices.has(sr.question_index)) ?? [];
            assignment.questions?.forEach(q => {
                if (!completeRubric.sub_rubrics.some(sr => sr.question_index === q.question_index)) {
                    completeRubric.sub_rubrics.push({ question_index: q.question_index, max_points: 10, leniency: null, instructor_guideline: '', grading_criteria: [] });
                }
            });
        } else {
            console.log(`No rubric/invalid data for assignment ${assignmentIdStr}. Creating empty.`);
            completeRubric = createEmptyRubric(assignment);
        }
        completeRubric.sub_rubrics.sort((a, b) => (a.question_index ?? Infinity) - (b.question_index ?? Infinity));
        setRubric(completeRubric); setAiRubricSuggestion(null); setTabValue(0);
        setCurrentQuestionIndex(completeRubric.sub_rubrics[0]?.question_index ?? 0);
    } catch (err) {
      console.error('Error fetching rubric:', err);
       if (err.message?.includes('404') || err.message?.toLowerCase().includes('not found') || err?.response?.status === 404) {
          console.log(`No rubric found for assignment ${assignmentIdStr}. Creating empty.`);
          setRubric(createEmptyRubric(assignment)); setTabValue(0);
          setCurrentQuestionIndex(assignment?.questions?.[0]?.question_index ?? 0);
       } else {
          const errorMsg = formatApiError(err, 'Failed to load rubric');
          setError(errorMsg); showAlert(errorMsg, 'error'); setRubric(null);
       }
    } finally { setLoadingRubric(false); }
  }, [semester, courseId, createEmptyRubric, showAlert, formatApiError]);

  useEffect(() => {
    const fetchAssignmentsAndRubric = async () => {
      if (!courseId || !semester) { setLoadingAssignments(false); setError("Course ID or Semester missing."); return; }
      setLoadingAssignments(true); setLoadingRubric(true); setError(null); setRubric(null); setSelectedAssignment(null);
      try {
        const assignmentsResponse = await assignmentService.getAssignments(courseId, semester, true);
        const assignmentsData = assignmentsResponse?.data;
        if (!Array.isArray(assignmentsData)) throw new Error("Invalid assignment data.");
        assignmentsData.sort((a,b) => String(a.assignment_id).localeCompare(String(b.assignment_id)));
        setAssignments(assignmentsData);

        let assignmentToSelect = null;
        if (selectedAssignmentId !== null) { // selectedAssignmentId is string
             assignmentToSelect = assignmentsData.find(a => String(a.assignment_id) === selectedAssignmentId); // Compare strings
             if (!assignmentToSelect) {
                showAlert(`Assignment ID ${selectedAssignmentId} from URL not found. Loading first.`, 'warning');
                assignmentToSelect = assignmentsData[0] ?? null;
                const firstId = assignmentsData[0]?.assignment_id;
                router.replace(`/course/${courseId}/rubrics?semester=${semester}${firstId ? `&assignmentId=${firstId}` : ''}`, undefined, { shallow: true });
             }
        } else {
            assignmentToSelect = assignmentsData[0] ?? null;
             if(assignmentToSelect) { router.replace(`/course/${courseId}/rubrics?semester=${semester}&assignmentId=${assignmentToSelect.assignment_id}`, undefined, { shallow: true }); }
        }

        if (assignmentToSelect) {
             if(assignmentToSelect.questions) { assignmentToSelect.questions.sort((a, b) => (a.question_index ?? Infinity) - (b.question_index ?? Infinity)); }
             setSelectedAssignment(assignmentToSelect); // Has string ID
             await fetchRubric(assignmentToSelect); // Pass assignment with string ID
        } else { console.log("No assignments found."); setError("No assignments available."); setLoadingRubric(false); }
      } catch (err) {
        console.error('Error fetching initial data:', err); const errorMsg = formatApiError(err, 'Failed loading data'); setError(errorMsg); showAlert(errorMsg, 'error'); setLoadingRubric(false);
      } finally { setLoadingAssignments(false); }
    };
    fetchAssignmentsAndRubric();
  }, [courseId, semester, selectedAssignmentId, formatApiError, showAlert, fetchRubric, router]); // Dependencies updated


  // --- Event Handlers ---
  const handleSelectAssignment = useCallback((assignment) => {
    const newAssignmentId = String(assignment?.assignment_id); const currentAssignmentId = String(selectedAssignment?.assignment_id);
    if (!assignment || newAssignmentId === currentAssignmentId) return;
    router.push(`/course/${courseId}/rubrics?semester=${semester}&assignmentId=${newAssignmentId}`, undefined, { shallow: true });
    setTabValue(0); setEditMode(false); setAiRubricSuggestion(null); setRubric(null); setError(null);
    setSelectedAssignment(assignment); setLoadingRubric(true);
  }, [courseId, semester, selectedAssignment?.assignment_id, router]);

  const getAIRubricSuggestions = useCallback(async () => {
    if (!selectedAssignment || !semester || !courseId) { showAlert("Select assignment.", "warning"); return; }
    setLoadingAI(true);
    try {
      const response = await rubricService.getAIRubric( semester, courseId, String(selectedAssignment.assignment_id), aiInstructions || null ); // Pass string ID
      const aiRubricData = response?.data;
      if (!aiRubricData || typeof aiRubricData !== 'object') throw new Error("Invalid AI response.");
      setAiRubricSuggestion(aiRubricData); setAiInstructionsDialogOpen(false);
      showAlert('AI suggestions generated!');
    } catch (err) { const errorMsg = formatApiError(err, 'Failed AI suggestions'); showAlert(errorMsg, 'error'); }
    finally { setLoadingAI(false); }
  }, [selectedAssignment, semester, courseId, aiInstructions, showAlert, formatApiError]);

  const applyAIRubricSuggestions = useCallback(() => {
    if (!aiRubricSuggestion) return;
    // Compare string IDs
    if (aiRubricSuggestion.semester === semester && aiRubricSuggestion.course_id === courseId && String(aiRubricSuggestion.assignment_id) === String(selectedAssignment?.assignment_id)) {
        const alignedRubric = { ...createEmptyRubric(selectedAssignment), ...aiRubricSuggestion };
        alignedRubric.assignment_id = String(alignedRubric.assignment_id); // Ensure string
        const currentQuestionIndices = new Set(selectedAssignment.questions?.map(q => q.question_index) ?? []);
        alignedRubric.sub_rubrics = alignedRubric.sub_rubrics.filter(sr => currentQuestionIndices.has(sr.question_index));
        selectedAssignment.questions?.forEach(q => { if (!alignedRubric.sub_rubrics.some(sr => sr.question_index === q.question_index)) { alignedRubric.sub_rubrics.push({ question_index: q.question_index, max_points: 10, leniency: null, instructor_guideline: '', grading_criteria: [] }); } });
        alignedRubric.sub_rubrics.sort((a, b) => (a.question_index ?? Infinity) - (b.question_index ?? Infinity));
        setRubric(alignedRubric); setAiRubricSuggestion(null); setEditMode(true);
        showAlert('AI suggestions applied.', 'info');
    } else { showAlert('Cannot apply: Identifiers mismatch.', 'error'); }
  }, [aiRubricSuggestion, semester, courseId, selectedAssignment, showAlert, createEmptyRubric]);

  const saveRubric = useCallback(async () => {
    if (!rubric || !rubric.semester || !rubric.course_id || typeof rubric.assignment_id !== 'string') { showAlert("Cannot save: Missing identifiers.", "error"); return; }
    let pointsMismatch = false; let mismatchDetails = [];
    (rubric.sub_rubrics || []).forEach(sr => { const total = calculateTotalPoints(sr); if (total !== (sr.max_points ?? 0)) { pointsMismatch = true; mismatchDetails.push(`Q${sr.question_index + 1}`); } });
    if (pointsMismatch) { showAlert(`Warning: Points mismatch for ${mismatchDetails.join(', ')}.`, "warning"); /* Optionally return */ }
    setIsSaving(true);
    try {
      await rubricService.createRubric(rubric); // API expects string ID
      setEditMode(false); showAlert('Rubric saved.', 'success');
      if(selectedAssignment) { await fetchRubric(selectedAssignment); }
    } catch (err) { const errorMsg = formatApiError(err, 'Failed to save.'); showAlert(errorMsg, 'error'); }
    finally { setIsSaving(false); }
  }, [rubric, selectedAssignment, fetchRubric, showAlert, formatApiError]); // calculateTotalPoints not needed as dependency

  const handleRubricSettingChange = useCallback((field, value) => { setRubric(prev => prev ? { ...prev, [field]: value } : null); }, []);
  const handleSubRubricChange = useCallback((questionIndex, field, value) => { setRubric(prev => { if (!prev) return null; const newSubRubrics = prev.sub_rubrics.map(sr => sr.question_index === questionIndex ? { ...sr, [field]: value } : sr ); return { ...prev, sub_rubrics: newSubRubrics }; }); }, []);
  const handleGradingFlagToggle = useCallback((flagValue) => { setRubric(prev => { if (!prev) return null; const currentFlags = prev.grading_flags || []; const updatedFlags = currentFlags.includes(flagValue) ? currentFlags.filter(f => f !== flagValue) : [...currentFlags, flagValue]; return { ...prev, grading_flags: updatedFlags }; }); }, []);
  const handleTabChange = useCallback((event, newValue) => { setTabValue(newValue); if (newValue > 0 && rubric?.sub_rubrics?.[newValue - 1]) { setCurrentQuestionIndex(rubric.sub_rubrics[newValue - 1].question_index); } }, [rubric]);

  // --- Criteria Management ---
  const openCriteriaDialog = (criteriaArrayIndex = null) => {
      const targetSubRubric = rubric?.sub_rubrics.find(sr => sr.question_index === currentQuestionIndex);
      if (!targetSubRubric) { showAlert("Sub-rubric not found.", "error"); return; }
      if (criteriaArrayIndex !== null) {
          const criteria = targetSubRubric.grading_criteria?.[criteriaArrayIndex];
          if (criteria) { setCriteriaFormData({ criteria_id: criteria.criteria_id || '', criteria: criteria.criteria || '', points: criteria.points ?? 0, }); setEditingCriteriaIndex(criteriaArrayIndex); }
          else { showAlert(`Criteria index ${criteriaArrayIndex} not found.`, "error"); return; }
      } else { setCriteriaFormData({ criteria_id: '', criteria: '', points: 0 }); setEditingCriteriaIndex(null); }
      setCriteriaDialogOpen(true);
  };

  const handleSaveCriteria = () => {
      if (!criteriaFormData.criteria_id?.trim()) return showAlert('Criteria Title/ID required.', 'warning');
      if (!criteriaFormData.criteria?.trim()) return showAlert('Criteria Description required.', 'warning');
      if (criteriaFormData.points === '' || criteriaFormData.points === null || isNaN(parseFloat(criteriaFormData.points)) || parseFloat(criteriaFormData.points) < 0) return showAlert('Points must be >= 0.', 'warning');
      const pointsValue = parseFloat(criteriaFormData.points); const newOrUpdatedCriteria = { criteria_id: criteriaFormData.criteria_id.trim(), criteria: criteriaFormData.criteria.trim(), points: pointsValue, };
      const targetSubRubricArrayIndex = rubric?.sub_rubrics.findIndex(sr => sr.question_index === currentQuestionIndex);
      if (targetSubRubricArrayIndex === -1 || targetSubRubricArrayIndex === undefined) { showAlert("Sub-rubric index not found.", "error"); return; }
      setRubric(prev => {
           if (!prev) return null; const newSubRubrics = [...prev.sub_rubrics]; const targetSubRubric = { ...(newSubRubrics[targetSubRubricArrayIndex] || {}) }; targetSubRubric.grading_criteria = [...(targetSubRubric.grading_criteria || [])];
          if (editingCriteriaIndex !== null) { if (editingCriteriaIndex < targetSubRubric.grading_criteria.length) { targetSubRubric.grading_criteria[editingCriteriaIndex] = newOrUpdatedCriteria; } else { console.error("Edit index OOB!"); return prev; } }
          else { targetSubRubric.grading_criteria.push(newOrUpdatedCriteria); }
          newSubRubrics[targetSubRubricArrayIndex] = targetSubRubric; return { ...prev, sub_rubrics: newSubRubrics };
      });
      setCriteriaDialogOpen(false);
  };

   const openDeleteCriteriaDialog = (criteriaArrayIndex) => { if (typeof criteriaArrayIndex !== 'number' || criteriaArrayIndex < 0) return; setCriteriaToDelete({ criteriaArrayIndex }); setDeleteCriteriaDialogOpen(true); };

  const handleDeleteCriteria = () => {
    if (!rubric || !editMode || criteriaToDelete === null) return; const { criteriaArrayIndex } = criteriaToDelete; const targetSubRubricArrayIndex = rubric.sub_rubrics.findIndex(sr => sr.question_index === currentQuestionIndex);
    if (targetSubRubricArrayIndex === -1 || targetSubRubricArrayIndex === undefined) { showAlert("Sub-rubric index not found.", "error"); setDeleteCriteriaDialogOpen(false); setCriteriaToDelete(null); return; }
    setRubric(prev => {
        if (!prev) return null; const newSubRubrics = [...prev.sub_rubrics]; const targetSubRubric = { ...(newSubRubrics[targetSubRubricArrayIndex] || {}) }; targetSubRubric.grading_criteria = [...(targetSubRubric.grading_criteria || [])];
        if (criteriaArrayIndex < targetSubRubric.grading_criteria.length) { targetSubRubric.grading_criteria.splice(criteriaArrayIndex, 1); newSubRubrics[targetSubRubricArrayIndex] = targetSubRubric; return { ...prev, sub_rubrics: newSubRubrics }; }
        else { console.error("Delete index OOB!"); return prev; }
    });
    setDeleteCriteriaDialogOpen(false); setCriteriaToDelete(null);
  };

  const getQuestionText = useCallback((qIndex) => { const question = selectedAssignment?.questions?.find(q => q.question_index === qIndex); return question ? question.question_text : `Question Text (Index ${qIndex}) Not Found`; }, [selectedAssignment]);

  // --- Render Functions ---
  const renderAssignmentSelection = () => {
    if (loadingAssignments) return <Typography sx={{ mb: 3, fontStyle: 'italic' }}>Loading assignments...</Typography>;
    if (!assignments || assignments.length === 0) return <Alert severity="warning" sx={{ mb: 3 }}>No assignments found. {courseId && semester && <Link href={`/course/${courseId}/assignments?semester=${semester}`} passHref><MuiLink sx={{ ml: 1 }}>Create one?</MuiLink></Link>}</Alert>;
    return ( <FormControl fullWidth variant="outlined" sx={{ mb: 3 }}> <InputLabel id="assignment-select-label">Select Assignment</InputLabel> <Select labelId="assignment-select-label" value={selectedAssignment?.assignment_id ?? ''} onChange={(e) => { const assignment = assignments.find((a) => String(a.assignment_id) === e.target.value); if (assignment) handleSelectAssignment(assignment); }} label="Select Assignment" disabled={loadingAssignments || loadingRubric || isSaving} > {assignments.map((assignment) => ( <MenuItem key={assignment.assignment_id} value={assignment.assignment_id}> {`Assignment ID: ${assignment.assignment_id}`} ({assignment.questions?.length ?? 0} Qs) </MenuItem> ))} </Select> </FormControl> );
  };

  const renderRubricContent = () => {
    if (loadingRubric) return <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}><CircularProgress /> <Typography sx={{ ml: 2 }}>Loading rubric...</Typography></Box>;
    if (!selectedAssignment) { if(!loadingAssignments && assignments.length > 0) return <Alert severity="info">Select assignment.</Alert>; if(!loadingAssignments && assignments.length === 0) return null; if(loadingAssignments) return null; return <Alert severity="warning">Select assignment.</Alert>; }
    if (!rubric) { if(!loadingRubric) return <Alert severity="error">Could not load rubric. {error || ''}</Alert>; return null; }

    return (
      <>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 1 }}> <Typography variant="h5">Rubric for Assignment ID: {selectedAssignment.assignment_id}</Typography> <Box> {editMode ? ( <> <Button variant="contained" color="primary" startIcon={isSaving ? <CircularProgress size={20} color="inherit" /> : <SaveIcon />} onClick={saveRubric} sx={{ mr: 1 }} disabled={isSaving}>Save</Button> <Button variant="outlined" onClick={() => { setEditMode(false); fetchRubric(selectedAssignment); }} disabled={isSaving}>Cancel</Button> </> ) : ( <> <Button variant="outlined" startIcon={<LightbulbIcon />} onClick={() => setAiInstructionsDialogOpen(true)} sx={{ mr: 1 }} disabled={loadingAI || isSaving}>{loadingAI ? 'Generating...' : 'AI Suggestions'}</Button> <Button variant="contained" startIcon={<EditIcon />} onClick={() => setEditMode(true)} disabled={isSaving}>Edit</Button> </> )} </Box> </Box>
        {aiRubricSuggestion && !editMode && ( <AISuggestionCard rubric={aiRubricSuggestion} onApply={applyAIRubricSuggestions} onDismiss={() => setAiRubricSuggestion(null)} sx={{ mb: 3 }} /> )}
        <Paper sx={{ mb: 3, borderBottom: 1, borderColor: 'divider' }}> <Tabs value={tabValue} onChange={handleTabChange} variant="scrollable" scrollButtons="auto" aria-label="rubric sections"> <Tab label="Overall Settings" id="rubric-tab-0" aria-controls="rubric-tabpanel-0" /> {(rubric.sub_rubrics || []).map((subRubric, index) => ( <Tab key={`question-tab-${subRubric.question_index}`} label={ <Box component="span" sx={{ display: 'flex', alignItems: 'center' }}> Q{subRubric.question_index + 1} {editMode && calculateTotalPoints(subRubric) !== (subRubric.max_points ?? 0) && ( <Tooltip title={`Points mismatch: Max(${subRubric.max_points ?? 0}), Criteria(${calculateTotalPoints(subRubric)})`}><InfoIcon color="warning" sx={{ ml: 1, fontSize: '1rem' }} /></Tooltip> )} </Box> } id={`rubric-tab-${index + 1}`} aria-controls={`rubric-tabpanel-${index + 1}`} /> ))} </Tabs> </Paper>
        <TabPanel value={tabValue} index={0}> <RubricSection variant="outlined"> <Typography variant="h6" gutterBottom>General Settings</Typography> <Grid container spacing={3} alignItems="flex-start"> <Grid item xs={12} md={6}> <TextField label="Overall Guidelines" multiline minRows={4} maxRows={10} fullWidth value={rubric.overall_instructor_guidelines || ''} onChange={(e) => handleRubricSettingChange('overall_instructor_guidelines', e.target.value)} disabled={!editMode || isSaving} variant="outlined" margin="dense" placeholder="General instructions..."/> </Grid> <Grid item xs={12} md={6}> <Box sx={{mb: 2}}> <Typography gutterBottom id="global-leniency-label">Global Leniency</Typography> <Tooltip title="1=Strict, 5=Lenient."> <Slider value={rubric.leniency ?? 3} min={1} max={5} step={1} marks={[{ value: 1, label: '1' }, { value: 3, label: '3' }, { value: 5, label: '5' }]} valueLabelDisplay="auto" onChange={(e, value) => handleRubricSettingChange('leniency', value)} disabled={!editMode || isSaving} sx={{mt: 2, mb: 1, px: 1 }} aria-labelledby="global-leniency-label"/> </Tooltip> <Typography variant="caption" color="text.secondary" display="block">Grading strictness.</Typography> </Box> </Grid> <Grid item xs={12}> <Typography variant="subtitle1" gutterBottom>Grading Flags</Typography> <Typography variant="caption" color="text.secondary" display="block" sx={{mb: 1}}>Instruct AI.</Typography> <FormGroup row> {GRADING_FLAGS_CONFIG.map((flag) => ( <Tooltip key={flag.value} title={flag.description} arrow placement="top"> <FormControlLabel control={<Switch checked={(rubric.grading_flags || []).includes(flag.value)} onChange={() => handleGradingFlagToggle(flag.value)} disabled={!editMode || isSaving} color="primary" size="small"/>} label={flag.label} sx={{mr: 2}} /> </Tooltip> ))} </FormGroup> </Grid> </Grid> </RubricSection> </TabPanel>
        {(rubric.sub_rubrics || []).map((subRubric, arrayIndex) => (
          <TabPanel key={`subPanel-${subRubric.question_index}`} value={tabValue} index={arrayIndex + 1}>
             <RubricSection variant="outlined"> <Typography variant="h6" gutterBottom>Question {subRubric.question_index + 1} Settings</Typography> <Paper variant="outlined" sx={{ p: 2, bgcolor: 'action.hover', mb: 3 }}><Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>{getQuestionText(subRubric.question_index)}</Typography></Paper> <Grid container spacing={2}> <Grid item xs={12} md={6}> <TextField label="Question Guideline" multiline minRows={3} maxRows={8} fullWidth value={subRubric.instructor_guideline || ''} onChange={(e) => handleSubRubricChange(subRubric.question_index, 'instructor_guideline', e.target.value)} disabled={!editMode || isSaving} variant="outlined" margin="dense" placeholder={`Instructions for Q${subRubric.question_index + 1} (optional)`}/> </Grid> <Grid item xs={12} sm={6} md={3}> <TextField label="Max Points" type="number" fullWidth value={subRubric.max_points ?? 0} onChange={(e) => handleSubRubricChange(subRubric.question_index, 'max_points', parseFloat(e.target.value) || 0)} disabled={!editMode || isSaving} InputProps={{ inputProps: { min: 0, step: 0.5 } }} variant="outlined" margin="dense" required/> </Grid> <Grid item xs={12} sm={6} md={3}> <FormControl fullWidth margin="dense" variant="outlined"> <InputLabel id={`q-leniency-label-${subRubric.question_index}`}>Leniency</InputLabel> <Select labelId={`q-leniency-label-${subRubric.question_index}`} value={subRubric.leniency ?? ''} onChange={(e) => handleSubRubricChange(subRubric.question_index, 'leniency', e.target.value === '' ? null : parseInt(e.target.value))} disabled={!editMode || isSaving} label="Leniency"> <MenuItem value=""><em>Global ({rubric.leniency ?? 3})</em></MenuItem> {[1, 2, 3, 4, 5].map(val => <MenuItem key={val} value={val}>{val}</MenuItem>)} </Select> </FormControl> </Grid> </Grid> </RubricSection>
            <RubricSection variant="outlined">
               <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}> <Typography variant="h6">Grading Criteria</Typography> {editMode && <Button variant="contained" size="small" startIcon={<AddIcon />} onClick={() => openCriteriaDialog()} disabled={isSaving}>Add Criteria</Button>} </Box>
               {(!subRubric.grading_criteria || subRubric.grading_criteria.length === 0) ? ( <Box sx={{ textAlign: 'center', py: 3, border: `1px dashed ${theme.palette.divider}`, borderRadius: 1 }}> <CriteriaIcon sx={{ fontSize: 40, color: 'text.disabled', mb: 1 }} /> <Typography color="text.secondary">No criteria defined.</Typography> {editMode && <Button variant="text" startIcon={<AddIcon />} onClick={() => openCriteriaDialog()} sx={{ mt: 1 }} disabled={isSaving}>Add First</Button>} </Box> )
               : ( <> {subRubric.grading_criteria.map((criteria, criteriaArrayIndex) => ( <CriteriaCard key={`criteria-${subRubric.question_index}-${criteriaArrayIndex}`} variant="outlined"> <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 1 }}> <Box sx={{ flexGrow: 1, mr: 1 }}> <Typography variant="subtitle1" fontWeight="medium" component="div">{criteria.criteria_id}</Typography> <Typography variant="body2" sx={{ mt: 0.5, whiteSpace: 'pre-wrap' }}>{criteria.criteria}</Typography> </Box> <Box sx={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}> <Chip label={`${criteria.points} pts`} color="primary" size="small" variant="outlined" sx={{ mr: 0.5 }} /> {editMode && ( <> <Tooltip title="Edit"><IconButton color="primary" size="small" onClick={() => openCriteriaDialog(criteriaArrayIndex)} disabled={isSaving}><EditIcon fontSize="small" /></IconButton></Tooltip> <Tooltip title="Delete"><IconButton color="error" size="small" onClick={() => openDeleteCriteriaDialog(criteriaArrayIndex)} disabled={isSaving}><DeleteIcon fontSize="small" /></IconButton></Tooltip> </> )} </Box> </Box> </CriteriaCard> ))} <Divider sx={{ my: 2 }} /> <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1 }}> <Typography variant="subtitle1" fontWeight="bold">Total:</Typography> <Typography variant="subtitle1" fontWeight="bold" color={calculateTotalPoints(subRubric) === (subRubric.max_points ?? 0) ? 'text.primary' : 'error.main'}> {calculateTotalPoints(subRubric)} / {subRubric.max_points ?? 0} </Typography> </Box> {calculateTotalPoints(subRubric) !== (subRubric.max_points ?? 0) && ( <Typography variant="caption" color="error" display="block" textAlign="right">Points mismatch!</Typography> )} </> )}
            </RubricSection>
          </TabPanel>
        ))}
      </>
    );
  };

  // --- Main Component Return ---
  return (
    <Box sx={{ p: { xs: 1, sm: 2, md: 3 } }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <IconButton edge="start" title="Back to Course" aria-label="back to course" onClick={() => router.push(`/course/${courseId}?semester=${semester}`)} sx={{ mr: 1 }} disabled={!courseId || !semester} > <ArrowBackIcon /> </IconButton>
        <Typography variant="h4" component="h1">Rubric Management</Typography>
      </Box>
      {error && !loadingAssignments && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}
      {renderAssignmentSelection()}
      <Divider sx={{ my: 4 }} />
      {renderRubricContent()}

      {/* --- DIALOGS --- */}
      <Dialog open={criteriaDialogOpen} onClose={() => setCriteriaDialogOpen(false)} maxWidth="sm" fullWidth>
          <DialogTitle>{editingCriteriaIndex !== null ? 'Edit' : 'Add'} Grading Criteria {typeof currentQuestionIndex === 'number' ? `for Q${currentQuestionIndex + 1}` : ''}</DialogTitle>
          <DialogContent>
              <TextField autoFocus label="Criteria Title/ID" fullWidth value={criteriaFormData.criteria_id} onChange={(e) => setCriteriaFormData({ ...criteriaFormData, criteria_id: e.target.value })} margin="dense" required placeholder="e.g., Code Correctness" error={!criteriaFormData.criteria_id?.trim()} helperText={!criteriaFormData.criteria_id?.trim() ? "Title is required" : ""} />
              <TextField label="Criteria Description" fullWidth multiline rows={3} value={criteriaFormData.criteria} onChange={(e) => setCriteriaFormData({ ...criteriaFormData, criteria: e.target.value })} margin="dense" required placeholder="Description of criteria..." error={!criteriaFormData.criteria?.trim()} helperText={!criteriaFormData.criteria?.trim() ? "Description is required" : ""} />
              <TextField label="Points" type="number" fullWidth value={criteriaFormData.points} onChange={(e) => setCriteriaFormData({ ...criteriaFormData, points: e.target.value })} margin="dense" required InputProps={{ inputProps: { min: 0, step: 0.5 }, endAdornment: <InputAdornment position="end">pts</InputAdornment> }} error={!(parseFloat(criteriaFormData.points) >= 0 && criteriaFormData.points !== '')} helperText={!(parseFloat(criteriaFormData.points) >= 0 && criteriaFormData.points !== '') ? "Points must be 0 or greater" : ""} />
          </DialogContent>
          <DialogActions>
              <Button onClick={() => setCriteriaDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleSaveCriteria} variant="contained" color="primary" disabled={!criteriaFormData.criteria_id?.trim() || !criteriaFormData.criteria?.trim() || !(parseFloat(criteriaFormData.points) >= 0 && criteriaFormData.points !== '')}> {editingCriteriaIndex !== null ? 'Save Changes' : 'Add Criteria'} </Button>
          </DialogActions>
      </Dialog>
      <ConfirmationDialog open={deleteCriteriaDialogOpen} onClose={() => setDeleteCriteriaDialogOpen(false)} title="Delete Grading Criteria?" description="Are you sure you want to delete this grading criteria? This action cannot be undone." confirmText="Delete" cancelText="Cancel" confirmColor="error" onConfirm={handleDeleteCriteria}/>
      <Dialog open={aiInstructionsDialogOpen} onClose={() => !loadingAI && setAiInstructionsDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle><Box sx={{ display: 'flex', alignItems: 'center' }}><LightbulbIcon sx={{ mr: 1, color: 'warning.main' }} />AI Rubric Suggestions</Box></DialogTitle>
        <DialogContent>
          <Typography variant="body2" paragraph>The AI will analyze the selected assignment's questions ({selectedAssignment?.questions?.length ?? 0} questions) to suggest rubric criteria. Add specific instructions below if needed.</Typography>
          <TextField label="Instructions for AI (Optional)" fullWidth multiline rows={4} value={aiInstructions} onChange={(e) => setAiInstructions(e.target.value)} margin="dense" placeholder="e.g., Focus on logical reasoning..." disabled={loadingAI} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAiInstructionsDialogOpen(false)} disabled={loadingAI}>Cancel</Button>
          <Button onClick={getAIRubricSuggestions} variant="contained" color="primary" disabled={loadingAI} startIcon={loadingAI ? <CircularProgress size={20} color="inherit"/> : <LightbulbIcon />}> {loadingAI ? 'Generating...' : 'Get AI Suggestions'} </Button>
        </DialogActions>
      </Dialog>
      <Snackbar open={alertOpen} autoHideDuration={6000} onClose={() => setAlertOpen(false)} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
          <Alert onClose={() => setAlertOpen(false)} severity={alertSeverity} variant="filled" sx={{ width: '100%' }}>{alertMessage}</Alert>
      </Snackbar>
    </Box>
  );
}