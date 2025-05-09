/**
 * Rubric Management Page for BU MET Autograder
 * Create, edit, and apply grading rubrics
 * Located at: pages/course/[id]/rubrics.js
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import {
  Alert, Box, Button, Card, CardActionArea, CardContent, Chip, CircularProgress,
  Dialog, DialogActions, DialogContent, DialogTitle, Divider, FormControl, FormControlLabel,
  FormGroup, Grid, IconButton, InputAdornment, InputLabel, MenuItem, Paper, Select,
  Slider, Snackbar, Switch, Tab, Tabs, TextField, Tooltip, Typography, useTheme,
  Link as MuiLink
} from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  Add as AddIcon, ArrowBack as ArrowBackIcon, Delete as DeleteIcon, Edit as EditIcon,
  Lightbulb as LightbulbIcon, Save as SaveIcon, Assignment as AssignmentIcon,
  RuleFolder as RubricIcon, HelpOutline as HelpIcon, Info as InfoIcon,
  PlaylistAddCheck as CriteriaIcon,
} from '@mui/icons-material';
import { assignmentService, rubricService } from '../../../api'; // Ensure correct path
import CardSkeleton from '../../../components/CardSkeleton';
import AISuggestionCard from '../../../components/AISuggestionCard'; // Assuming path
import ConfirmationDialog from '../../../components/ConfirmationDialog';

// Styled components
const StyledCard = styled(Card)(({ theme, selected }) => ({ height: '100%', display: 'flex', flexDirection: 'column', border: selected ? `2px solid ${theme.palette.primary.main}` : `1px solid ${theme.palette.divider}`, transition: 'transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out, border 0.2s ease-in-out', cursor: 'pointer', '&:hover': { transform: 'translateY(-4px)', boxShadow: theme.shadows[4] }, }));
const RubricSection = styled(Paper)(({ theme }) => ({ padding: theme.spacing(3), marginBottom: theme.spacing(3), border: `1px solid ${theme.palette.divider}`, }));
const CriteriaCard = styled(Paper)(({ theme }) => ({ padding: theme.spacing(2), marginBottom: theme.spacing(2), borderLeft: `4px solid ${theme.palette.primary.light}`, backgroundColor: theme.palette.background.default, '&:last-child': { marginBottom: 0, }, position: 'relative', }));
const NoItemsBox = styled(Box)(({ theme }) => ({ textAlign: 'center', padding: theme.spacing(4), backgroundColor: theme.palette.background.default, borderRadius: theme.shape.borderRadius, marginTop: theme.spacing(4), border: `1px dashed ${theme.palette.divider}`, }));
const TabPanel = (props) => { const { children, value, index, ...other } = props; return ( <div role="tabpanel" hidden={value !== index} id={`rubric-tabpanel-${index}`} aria-labelledby={`rubric-tab-${index}`} {...other}> {value === index && <Box sx={{ pt: 3 }}>{children}</Box>} </div> ); };

// Grading flags definition
const GRADING_FLAGS_CONFIG = [ { value: 'IGNORE_SPELLINGS', label: 'Ignore Spelling', description: 'AI ignores minor spelling mistakes during grading.' }, { value: 'IGNORE_GRAMMAR', label: 'Ignore Grammar', description: 'AI ignores minor grammatical errors during grading.' }, { value: 'ORIGINALITY', label: 'Reward Originality', description: 'AI rewards originality and may deduct for unoriginal ideas/plagiarism (experimental).' }, { value: 'IGNORE_FORMATTING', label: 'Ignore Formatting', description: 'AI ignores formatting inconsistencies (e.g., spacing, list styles) during grading.' }, ];

// Main component
export default function RubricManagementPage() {
  const router = useRouter();
  const theme = useTheme();
  const { id: courseIdParam, semester: semesterParam, assignmentId: assignmentIdFromUrlParam } = router.query;
  const courseId = typeof courseIdParam === 'string' ? courseIdParam : null;
  const semester = typeof semesterParam === 'string' ? semesterParam : null;
  const assignmentIdFromUrl = typeof assignmentIdFromUrlParam === 'string' ? assignmentIdFromUrlParam : null;

  // State
  const [assignments, setAssignments] = useState([]);
  const [selectedAssignment, setSelectedAssignment] = useState(null);
  const [rubric, setRubric] = useState(null);
  const [aiRubricSuggestion, setAiRubricSuggestion] = useState(null);
  const [loadingAssignments, setLoadingAssignments] = useState(true);
  const [loadingRubric, setLoadingRubric] = useState(false);
  const [loadingAI, setLoadingAI] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null); // General/list error
  const [detailsError, setDetailsError] = useState(null); // Rubric fetch/save error
  const [actionLoading, setActionLoading] = useState(false); // Generic for other actions

  // UI State
  const [tabValue, setTabValue] = useState(0);
  const [editMode, setEditMode] = useState(false);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(null);

  // Dialog States
  const [criteriaDialogOpen, setCriteriaDialogOpen] = useState(false);
  const [editingCriteriaIndex, setEditingCriteriaIndex] = useState(null); // Index within the CURRENT sub-rubric's criteria array
  const [deleteCriteriaDialogOpen, setDeleteCriteriaDialogOpen] = useState(false);
  const [aiInstructionsDialogOpen, setAiInstructionsDialogOpen] = useState(false);

  // Form Data States
  const [criteriaFormData, setCriteriaFormData] = useState({ criteria_id: '', criteria: '', points: 0 });
  const [criteriaToDelete, setCriteriaToDelete] = useState(null); // { subRubricArrayIndex, criteriaArrayIndex, name }
  const [aiInstructions, setAiInstructions] = useState('');

  // Alert State
  const [alertOpen, setAlertOpen] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [alertSeverity, setAlertSeverity] = useState('success');


  // --- UTILITY FUNCTIONS ---
  const showAlert = useCallback((message, severity = 'success') => { setAlertMessage(message); setAlertSeverity(severity); setAlertOpen(true); }, []);
  const formatApiError = useCallback((err, defaultMessage) => { let displayError = defaultMessage; if(err.response){const detail = err.response.data?.detail; if(detail){if(Array.isArray(detail)){displayError = detail.map(d => `${d.loc?.join('.') || 'error'}: ${d.msg}`).join('; ');} else if(typeof detail === 'string'){displayError = detail;}}else if(err.response.statusText){displayError = `Error: ${err.response.status} ${err.response.statusText}`;}} else if(err.request){displayError="Network Error";} else if(err.message){displayError = err.message;} return displayError||defaultMessage; }, []);
  const calculateTotalPoints = (subRubric) => subRubric?.grading_criteria?.reduce((sum, c) => sum + (parseFloat(String(c?.points)) || 0), 0) ?? 0;
  const handleInputChange = (event, formSetter) => { const { name, value } = event.target; formSetter((prev) => ({ ...prev, [name]: value })); };


  // --- DATA FETCHING ---
  const createEmptyRubric = useCallback((assignment) => {
    if (!assignment || !semester || !courseId) { console.error("[createEmptyRubric] Missing context."); return null; }
    const assignmentIdStr = String(assignment.assignment_id);
    if (!assignmentIdStr) { console.error("[createEmptyRubric] Missing assignment ID."); return null; }
    const questions = Array.isArray(assignment.questions) ? assignment.questions : [];
    console.log(`[createEmptyRubric] Input questions for ${assignmentIdStr}:`, JSON.stringify(questions));
    const sortedQuestions = [...questions].sort((a,b) => (a?.question_index ?? Infinity) - (b?.question_index ?? Infinity));
    const subRubrics = sortedQuestions.map((question, index) => {
        const qIndex = (question && typeof question.question_index === 'number') ? question.question_index : index;
        if (typeof qIndex !== 'number') { console.error(`[createEmptyRubric] Failed to determine valid index for question:`, question); return null; }
        return { question_index: qIndex, max_points: 10, instructor_guideline: '', /* leniency: null, */ grading_criteria: [], };
    }).filter(sr => sr !== null);
    const result = { semester, course_id: courseId, assignment_id: assignmentIdStr, grading_flags: [], overall_instructor_guidelines: '', sub_rubrics: subRubrics };
    console.log("[createEmptyRubric] Generated structure:", JSON.stringify(result, null, 2));
    return result;
  }, [semester, courseId]);

  const fetchRubric = useCallback(async (assignment) => {
      if (!assignment?.assignment_id || !courseId || !semester) return;
      const assignmentIdToFetch = String(assignment.assignment_id);
      setLoadingRubric(true); setDetailsError(null); setAiRubricSuggestion(null); setEditMode(false);
      console.log(`FETCHING rubric for assignment ID: ${assignmentIdToFetch}`);
      try {
          const rubricData = await rubricService.getRubric({ semester, course_id: courseId, assignment_id: assignmentIdToFetch });
          console.log(`[fetchRubric] Raw data received for ${assignmentIdToFetch}:`, JSON.stringify(rubricData, null, 2));
          const baseEmpty = createEmptyRubric(assignment);
          if (!baseEmpty) throw new Error("Could not create base empty rubric.");
          let mergedRubric = { ...baseEmpty, ...(rubricData || {}), assignment_id: assignmentIdToFetch };
          const currentQuestionIndices = new Set(assignment.questions?.map(q => q.question_index).filter(idx => typeof idx === 'number') ?? []);
          let processedSubRubrics = (Array.isArray(mergedRubric.sub_rubrics) ? mergedRubric.sub_rubrics : [])
              .map(sr => { if (!sr || typeof sr.question_index !== 'number') return null; return { ...sr, grading_criteria: Array.isArray(sr.grading_criteria) ? sr.grading_criteria : [] }; })
              .filter(sr => sr !== null && currentQuestionIndices.has(sr.question_index));
          assignment.questions?.forEach(q => { const qIndex = q.question_index; if (typeof qIndex === 'number' && !processedSubRubrics.some(sr => sr.question_index === qIndex)) { console.log(`[fetchRubric] Adding missing sub-rubric for question index ${qIndex}`); processedSubRubrics.push({ question_index: qIndex, max_points: 10, instructor_guideline: '', grading_criteria: [] }); } }); // Removed leniency
          processedSubRubrics.sort((a, b) => a.question_index - b.question_index);
          mergedRubric.sub_rubrics = processedSubRubrics;
          console.log(`[fetchRubric] Final rubric state for ${assignmentIdToFetch}:`, JSON.stringify(mergedRubric, null, 2));
          setRubric(mergedRubric);
          if (mergedRubric.sub_rubrics.length > 0) { setCurrentQuestionIndex(mergedRubric.sub_rubrics[0].question_index); setTabValue(1); }
          else { setCurrentQuestionIndex(null); setTabValue(0); }
      } catch (err) {
          console.error(`Error fetching/processing rubric for ${assignmentIdToFetch}:`, err);
          if (err.response && err.response.status === 404) { console.log("Rubric not found (404), creating empty structure."); const emptyRubric = createEmptyRubric(assignment); setRubric(emptyRubric); if (emptyRubric?.sub_rubrics?.length > 0) { setCurrentQuestionIndex(emptyRubric.sub_rubrics[0].question_index); setTabValue(1); } else { setCurrentQuestionIndex(null); setTabValue(0); } setDetailsError(null); }
          else { setDetailsError(formatApiError(err, 'Failed to load rubric')); setRubric(null); }
      } finally { setLoadingRubric(false); }
  }, [courseId, semester, createEmptyRubric, formatApiError]);

  useEffect(() => {
    if (!router.isReady || !courseId || !semester) return;
    let isMounted = true;
    const fetchAssignmentsList = async () => {
      setLoadingAssignments(true); setError(null); setSelectedAssignment(null); setRubric(null); setLoadingRubric(false); setDetailsError(null);
      try {
        const assignmentsData = await assignmentService.getAssignments({ course_id: courseId, semester: semester, include_questions: true });
        if (isMounted) {
            if (Array.isArray(assignmentsData)) {
               const validAssignments = (assignmentsData || []).filter(a => a && typeof a === 'object' && typeof a.assignment_id !== 'undefined').map(a => ({...a, questions: (Array.isArray(a?.questions) ? a.questions : []).sort((qa, qb) => (qa.question_index ?? Infinity) - (qb.question_index ?? Infinity))}));
               validAssignments.sort((a,b) => String(a.assignment_id).localeCompare(String(b.assignment_id)));
               setAssignments(validAssignments);
               let assignmentToSelect = null;
               if (assignmentIdFromUrl) { assignmentToSelect = validAssignments.find(a => String(a.assignment_id) === assignmentIdFromUrl); }
               if (!assignmentToSelect && validAssignments.length > 0) { assignmentToSelect = validAssignments[0]; const newUrl = `/course/${courseId}/rubrics?semester=${semester}&assignmentId=${assignmentToSelect.assignment_id}`; if (assignmentIdFromUrl !== String(assignmentToSelect.assignment_id)) { if (assignmentIdFromUrl) { showAlert(`Assignment ID ${assignmentIdFromUrl} not found. Loading first assignment.`, 'warning'); } router.replace(newUrl, undefined, { shallow: true }); } }
               if (assignmentToSelect) { setSelectedAssignment(assignmentToSelect); await fetchRubric(assignmentToSelect); }
               else { setLoadingRubric(false); }
            } else { throw new Error("Invalid assignment data format."); }
        }
      } catch (err) { console.error("Error fetching assignments list:", err); if (isMounted) { setError(formatApiError(err, 'Failed to load assignments list.')); setAssignments([]); setLoadingRubric(false);} }
      finally { if (isMounted) { setLoadingAssignments(false); } }
    };
    fetchAssignmentsList();
    return () => { isMounted = false; };
  }, [router.isReady, courseId, semester, assignmentIdFromUrl, fetchRubric, formatApiError, showAlert, router]);


  // --- UI HANDLERS ---
  const handleSelectAssignment = useCallback((assignment) => { if (!assignment || !assignment.assignment_id) return; router.push(`/course/${courseId}/rubrics?semester=${semester}&assignmentId=${assignment.assignment_id}`, undefined, { shallow: false }); }, [courseId, semester, router]);
  const handleTabChange = useCallback((event, newValue) => { setTabValue(newValue); if (newValue > 0 && rubric?.sub_rubrics?.[newValue - 1]) { setCurrentQuestionIndex(rubric.sub_rubrics[newValue - 1].question_index); } else { setCurrentQuestionIndex(null); } }, [rubric]);
  const getQuestionText = useCallback((qIndex) => { const question = selectedAssignment?.questions?.find(q => q.question_index === qIndex); return question ? question.question_text : `Question Text (Index ${qIndex}) Not Found`; }, [selectedAssignment]);

  // --- RUBRIC ACTIONS ---
  const getAIRubricSuggestions = useCallback(async () => { if (!selectedAssignment?.assignment_id || !semester || !courseId) return showAlert("No assignment selected.", "warning"); setLoadingAI(true); setAiRubricSuggestion(null); try { const aiRubricData = await rubricService.getAIRubric({ semester, course_id: courseId, assignment_id: String(selectedAssignment.assignment_id), instructions: aiInstructions || null }); if (!aiRubricData || typeof aiRubricData !== 'object') throw new Error("Invalid AI response."); setAiRubricSuggestion(aiRubricData); setAiInstructionsDialogOpen(false); setAiInstructions(''); showAlert('AI suggestions generated!'); } catch (err) { console.error('Error getting AI rubric:', err); showAlert(formatApiError(err, 'Failed to get AI suggestions.'), 'error'); } finally { setLoadingAI(false); } }, [selectedAssignment, semester, courseId, aiInstructions, showAlert, formatApiError]);
  const applyAIRubricSuggestions = useCallback(() => { if (!aiRubricSuggestion || !selectedAssignment) return; if (aiRubricSuggestion.semester === semester && aiRubricSuggestion.course_id === courseId && String(aiRubricSuggestion.assignment_id) === String(selectedAssignment.assignment_id)) { const alignedRubric = { ...createEmptyRubric(selectedAssignment), ...aiRubricSuggestion }; alignedRubric.assignment_id = String(alignedRubric.assignment_id); const currentQuestionIndices = new Set(selectedAssignment.questions?.map(q => q.question_index) ?? []); alignedRubric.sub_rubrics = (alignedRubric.sub_rubrics || []).filter(sr => typeof sr.question_index === 'number' && currentQuestionIndices.has(sr.question_index)).map(sr => ({...sr, grading_criteria: Array.isArray(sr.grading_criteria) ? sr.grading_criteria : [] })); selectedAssignment.questions?.forEach(q => { if (typeof q.question_index === 'number' && !alignedRubric.sub_rubrics.some(sr => sr.question_index === q.question_index)) { alignedRubric.sub_rubrics.push({ question_index: q.question_index, max_points: 10, instructor_guideline: '', grading_criteria: [] }); } }); alignedRubric.sub_rubrics.sort((a, b) => (a.question_index ?? Infinity) - (b.question_index ?? Infinity)); setRubric(alignedRubric); setAiRubricSuggestion(null); setEditMode(true); showAlert('AI suggestions applied to the editor.', 'info'); } else { showAlert('Cannot apply: Identifiers mismatch.', 'error'); } }, [aiRubricSuggestion, semester, courseId, selectedAssignment, showAlert, createEmptyRubric]);
  const saveRubric = useCallback(async () => {
      if (!rubric || !courseId || !semester || !selectedAssignment?.assignment_id) return showAlert("Cannot save: Missing context.", "warning");
      const validationIssues = rubric.sub_rubrics?.filter(sr => calculateTotalPoints(sr) !== parseFloat(sr.max_points || 0));
      if (validationIssues?.length > 0) { const issueDetails = validationIssues.map(sr => `Q${(sr.question_index ?? '?') + 1}`).join(', '); showAlert(`Cannot save: Points mismatch for ${issueDetails}.`, 'error'); return; }

      setIsSaving(true); setDetailsError(null);
      try {
          const payload = {
              semester: semester, course_id: courseId, assignment_id: selectedAssignment.assignment_id,
              grading_flags: rubric.grading_flags || [],
              overall_instructor_guidelines: rubric.overall_instructor_guidelines || null,
              sub_rubrics: (rubric.sub_rubrics || []).map((sr, index) => {
                  const finalIndex = sr.question_index;
                  if (typeof finalIndex !== 'number') { console.error(`CRITICAL: SubRubric at index ${index} has invalid question_index before save!`, sr); throw new Error(`Invalid rubric structure: Missing question index for sub-rubric ${index}.`); }
                  return { question_index: finalIndex, max_points: sr.max_points ?? 0, instructor_guideline: sr.instructor_guideline || null, grading_criteria: (sr.grading_criteria || []).map(gc => ({ criteria_id: gc.criteria_id, criteria: gc.criteria, points: gc.points ?? 0 })) };
              })
          };
          console.log("Saving Rubric Payload:", JSON.stringify(payload, null, 2));
          await rubricService.createOrUpdateRubric(payload); // PUT request
          setEditMode(false);
          showAlert('Rubric saved successfully.');
          if(selectedAssignment) { await fetchRubric(selectedAssignment); } // Refetch
      } catch (err) {
          console.error('Error saving rubric:', err);
          const errorMsg = formatApiError(err, 'Failed to save rubric.');
          setDetailsError(errorMsg);
          showAlert(errorMsg, 'error');
      } finally { setIsSaving(false); }
  }, [rubric, courseId, semester, selectedAssignment, fetchRubric, showAlert, formatApiError]);

  // --- RUBRIC STATE MODIFICATION HANDLERS ---
  const handleRubricSettingChange = useCallback((field, value) => { setRubric(prev => prev ? ({ ...prev, [field]: value }) : null); }, []);
  const handleGradingFlagToggle = useCallback((flagValue) => { setRubric(prev => { if (!prev) return null; const currentFlags = prev.grading_flags || []; const updatedFlags = currentFlags.includes(flagValue) ? currentFlags.filter((f) => f !== flagValue) : [...currentFlags, flagValue]; return { ...prev, grading_flags: updatedFlags }; }); }, []);
  const handleSubRubricChange = useCallback((questionIndex, field, value) => { setRubric(prev => { if (!prev) return null; const newSubRubrics = (prev.sub_rubrics || []).map((sr) => sr.question_index === questionIndex ? { ...sr, [field]: value } : sr ); return { ...prev, sub_rubrics: newSubRubrics }; }); }, []);
  const openCriteriaDialog = useCallback((criteriaArrayIndex = null) => { const targetSubRubric = rubric?.sub_rubrics.find(sr => sr.question_index === currentQuestionIndex); if (!targetSubRubric) { showAlert("Select a question tab first.", "warning"); return; } if (criteriaArrayIndex !== null) { const criteria = targetSubRubric.grading_criteria?.[criteriaArrayIndex]; if (criteria) { setCriteriaFormData({ criteria_id: criteria.criteria_id || '', criteria: criteria.criteria || '', points: criteria.points ?? 0, }); setEditingCriteriaIndex(criteriaArrayIndex); } else { showAlert(`Criteria index ${criteriaArrayIndex} not found.`, "error"); return; } } else { setCriteriaFormData({ criteria_id: '', criteria: '', points: 0 }); setEditingCriteriaIndex(null); } setCriteriaDialogOpen(true); }, [rubric, currentQuestionIndex, showAlert]);
  const handleSaveCriteria = useCallback(() => { if (!rubric || currentQuestionIndex === null) return; if (!criteriaFormData.criteria_id?.trim() || !criteriaFormData.criteria?.trim()) return showAlert("Criteria Title and Description are required.", "warning"); const pointsValue = parseFloat(criteriaFormData.points); if (isNaN(pointsValue) || pointsValue < 0) return showAlert('Points must be >= 0.', 'warning'); const newOrUpdatedCriteria = { criteria_id: criteriaFormData.criteria_id.trim(), criteria: criteriaFormData.criteria.trim(), points: pointsValue }; const targetSubRubricArrayIndex = rubric.sub_rubrics.findIndex(sr => sr.question_index === currentQuestionIndex); if (targetSubRubricArrayIndex === -1) { showAlert("Sub-rubric not found.", "error"); return; } setRubric(prev => { if (!prev) return null; const newSubRubrics = [...prev.sub_rubrics]; const targetSubRubric = { ...(newSubRubrics[targetSubRubricArrayIndex] || {}) }; targetSubRubric.grading_criteria = [...(targetSubRubric.grading_criteria || [])]; if (editingCriteriaIndex !== null) { if (editingCriteriaIndex < targetSubRubric.grading_criteria.length) { targetSubRubric.grading_criteria[editingCriteriaIndex] = newOrUpdatedCriteria; } else { console.error("Edit index OOB!"); return prev; } } else { targetSubRubric.grading_criteria.push(newOrUpdatedCriteria); } newSubRubrics[targetSubRubricArrayIndex] = targetSubRubric; return { ...prev, sub_rubrics: newSubRubrics }; }); setCriteriaDialogOpen(false); setEditingCriteriaIndex(null); }, [rubric, currentQuestionIndex, criteriaFormData, editingCriteriaIndex, showAlert]);
  const openDeleteCriteriaDialog = useCallback((criteriaArrayIndex) => { if (typeof criteriaArrayIndex !== 'number' || criteriaArrayIndex < 0) return; const targetSubRubric = rubric?.sub_rubrics.find(sr => sr.question_index === currentQuestionIndex); const criteria = targetSubRubric?.grading_criteria?.[criteriaArrayIndex]; if (!criteria) { showAlert("Criteria not found for deletion.", "warning"); return; } setCriteriaToDelete({ criteriaArrayIndex, name: criteria.criteria_id }); setDeleteCriteriaDialogOpen(true); }, [rubric, currentQuestionIndex, showAlert]);
  const handleDeleteCriteria = useCallback(() => { if (!rubric || criteriaToDelete === null) return; const { criteriaArrayIndex } = criteriaToDelete; const targetSubRubricArrayIndex = rubric.sub_rubrics.findIndex(sr => sr.question_index === currentQuestionIndex); if (targetSubRubricArrayIndex === -1) { showAlert("Sub-rubric not found.", "error"); setDeleteCriteriaDialogOpen(false); setCriteriaToDelete(null); return; } setRubric(prev => { if (!prev) return null; const newSubRubrics = [...prev.sub_rubrics]; const targetSubRubric = { ...(newSubRubrics[targetSubRubricArrayIndex] || {}) }; targetSubRubric.grading_criteria = [...(targetSubRubric.grading_criteria || [])]; if (criteriaArrayIndex < targetSubRubric.grading_criteria.length) { targetSubRubric.grading_criteria.splice(criteriaArrayIndex, 1); newSubRubrics[targetSubRubricArrayIndex] = targetSubRubric; return { ...prev, sub_rubrics: newSubRubrics }; } else { console.error("Delete index OOB!"); return prev; } }); setDeleteCriteriaDialogOpen(false); setCriteriaToDelete(null); }, [rubric, currentQuestionIndex, criteriaToDelete, showAlert]);

  // --- RENDER FUNCTIONS ---
  const renderAssignmentSelection = () => { if (loadingAssignments) return <CardSkeleton height={100} sx={{mb: 4}} />; if (error) return <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>; if (!Array.isArray(assignments) || !assignments.length) return <NoItemsBox><AssignmentIcon sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} /><Typography variant="h6">No assignments found for {courseId}/{semester}.</Typography><Typography color="text.secondary">Create assignments first.</Typography></NoItemsBox>; return ( <FormControl fullWidth variant="outlined" sx={{ mb: 3 }}> <InputLabel id="assignment-select-label">Select Assignment</InputLabel> <Select labelId="assignment-select-label" value={selectedAssignment?.assignment_id ?? ''} onChange={(e) => { const assignment = assignments.find((a) => String(a.assignment_id) === e.target.value); if (assignment) handleSelectAssignment(assignment); }} label="Select Assignment" disabled={loadingAssignments || loadingRubric || isSaving || actionLoading} > {assignments.map((assignment) => ( <MenuItem key={assignment.assignment_id} value={assignment.assignment_id}> {assignment.assignment_id} ({assignment.questions?.length ?? 0} Qs) </MenuItem> ))} </Select> </FormControl> ); };
  const renderRubricContent = () => { if (loadingRubric) return <Box sx={{ display: 'flex', justifyContent: 'center', p: 5 }}><CircularProgress /> <Typography sx={{ ml: 2 }}>Loading rubric...</Typography></Box>; if (!selectedAssignment && !loadingAssignments && assignments.length > 0) return <Alert severity="info" sx={{ mt: 2 }}>Please select an assignment above to view or edit its rubric.</Alert>; if (detailsError && !rubric) return <Alert severity="error" sx={{ mt: 2 }}>{detailsError}</Alert>; if (!rubric && selectedAssignment && !loadingRubric) return <Alert severity="warning" sx={{ mt: 2 }}>Rubric data unavailable or failed to create default. Try re-selecting the assignment.</Alert>; if (!selectedAssignment || !rubric) return null; const currentSubRubric = rubric.sub_rubrics?.find(sr => sr.question_index === currentQuestionIndex); return ( <> <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 1 }}> <Typography variant="h5">{`Rubric: ${selectedAssignment.assignment_id}`}</Typography> <Box> {editMode ? (<> <Button variant="contained" color="primary" size="small" startIcon={isSaving ? <CircularProgress size={20} color="inherit" /> : <SaveIcon />} onClick={saveRubric} sx={{ mr: 1 }} disabled={isSaving || loadingAI}> Save Rubric </Button> <Button variant="outlined" size="small" onClick={() => { setEditMode(false); fetchRubric(selectedAssignment); }} disabled={isSaving}> Cancel Edit </Button> </>) : (<> <Button variant="outlined" size="small" startIcon={<LightbulbIcon />} onClick={() => setAiInstructionsDialogOpen(true)} sx={{ mr: 1 }} disabled={loadingAI || isSaving}>{loadingAI ? 'Generating...' : 'AI Suggestions'}</Button> <Button variant="contained" size="small" startIcon={<EditIcon />} onClick={() => setEditMode(true)} disabled={isSaving}> Edit Rubric </Button> </>)} </Box> </Box> {aiRubricSuggestion && !editMode && ( <AISuggestionCard rubric={aiRubricSuggestion} onApply={applyAIRubricSuggestions} onDismiss={() => setAiRubricSuggestion(null)} sx={{ mb: 3 }} /> )} <Paper sx={{ mb: 3, borderBottom: 1, borderColor: 'divider' }}><Tabs value={tabValue} onChange={handleTabChange} variant="scrollable" scrollButtons="auto" aria-label="rubric sections"> <Tab label="Overall Settings" id="rubric-tab-0" aria-controls="rubric-tabpanel-0" /> {(rubric.sub_rubrics || []).map((subRubric, index) => ( <Tab key={`question-tab-${subRubric.question_index}`} label={ <Box component="span" sx={{ display: 'flex', alignItems: 'center' }}> Q{index + 1} {editMode && calculateTotalPoints(subRubric) !== (subRubric.max_points ?? 0) && ( <Tooltip title={`Points mismatch: Max(${subRubric.max_points ?? 0}), Criteria(${calculateTotalPoints(subRubric)})`}><InfoIcon color="warning" sx={{ ml: 1, fontSize: '1rem' }} /></Tooltip> )} </Box> } id={`rubric-tab-${index + 1}`} aria-controls={`rubric-tabpanel-${index + 1}`} /> ))} </Tabs></Paper>
      <TabPanel value={tabValue} index={0}> <RubricSection variant="outlined"> <Typography variant="h6" gutterBottom>General Settings</Typography> <Grid container spacing={3} alignItems="flex-start"> <Grid item xs={12} md={6}> <TextField label="Overall Guidelines" multiline minRows={4} maxRows={10} fullWidth value={rubric.overall_instructor_guidelines || ''} onChange={(e) => handleRubricSettingChange('overall_instructor_guidelines', e.target.value)} disabled={!editMode || isSaving} variant="outlined" margin="dense" placeholder="General instructions..."/> </Grid> <Grid item xs={12}> <Typography variant="subtitle1" gutterBottom>Grading Flags</Typography> <Typography variant="caption" color="text.secondary" display="block" sx={{mb: 1}}>Instruct AI.</Typography> <FormGroup row> {GRADING_FLAGS_CONFIG.map((flag) => ( <Tooltip key={flag.value} title={flag.description} arrow placement="top"><FormControlLabel control={<Switch checked={(rubric.grading_flags || []).includes(flag.value)} onChange={() => handleGradingFlagToggle(flag.value)} disabled={!editMode || isSaving} color="primary" size="small"/>} label={flag.label} sx={{mr: 2}} /></Tooltip> ))} </FormGroup> </Grid> </Grid> </RubricSection> </TabPanel>
      {(rubric.sub_rubrics || []).map((subRubric, index) => ( <TabPanel key={`subPanel-${subRubric.question_index}`} value={tabValue} index={index + 1}> <RubricSection variant="outlined"> <Typography variant="h6" gutterBottom>Question {index + 1} Settings</Typography> <Paper variant="outlined" sx={{ p: 1.5, mb: 2, bgcolor: 'action.hover' }}><Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>{getQuestionText(subRubric.question_index)}</Typography></Paper> <Grid container spacing={2}> <Grid item xs={12} md={6}><TextField label="Question Guideline" multiline minRows={3} maxRows={8} fullWidth value={subRubric.instructor_guideline || ''} onChange={(e) => handleSubRubricChange(subRubric.question_index, 'instructor_guideline', e.target.value )} disabled={!editMode || isSaving} variant="outlined" margin="dense" placeholder={`Instructions for Q${index + 1} (optional)`}/></Grid> <Grid item xs={12} sm={6} md={3}><TextField label="Max Points" type="number" fullWidth value={subRubric.max_points ?? 0} onChange={(e) => handleSubRubricChange(subRubric.question_index, 'max_points', parseFloat(e.target.value) || 0)} disabled={!editMode || isSaving} InputProps={{ inputProps: { min: 0, step: 0.5 } }} variant="outlined" margin="dense" required/></Grid> </Grid> </RubricSection> <RubricSection variant="outlined"> <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}><Typography variant="h6">Grading Criteria</Typography> {editMode && <Button variant="contained" size="small" startIcon={<AddIcon />} onClick={() => openCriteriaDialog()} disabled={isSaving}>Add Criteria</Button>} </Box> {(!subRubric.grading_criteria || subRubric.grading_criteria.length === 0) ? ( <Box sx={{ textAlign: 'center', py: 2, border: `1px dashed ${theme.palette.divider}`, borderRadius: 1 }}> <CriteriaIcon sx={{ fontSize: 40, color: 'text.disabled', mb: 1 }} /> <Typography color="text.secondary">No criteria defined.</Typography> {editMode && <Button variant="text" startIcon={<AddIcon />} onClick={() => openCriteriaDialog()} sx={{ mt: 1 }} disabled={isSaving}>Add First</Button>} </Box> ) : ( <> {subRubric.grading_criteria.map((criteria, criteriaArrayIndex) => ( <CriteriaCard key={`criteria-${subRubric.question_index}-${criteriaArrayIndex}`} variant="outlined"> <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 1 }}> <Box sx={{ flexGrow: 1, mr: 1 }}> <Typography variant="subtitle1" fontWeight="medium" component="div">{criteria.criteria_id}</Typography> <Typography variant="body2" sx={{ mt: 0.5, whiteSpace: 'pre-wrap' }}>{criteria.criteria}</Typography> </Box> <Box sx={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}> <Chip label={`${criteria.points} pts`} color="primary" size="small" variant="outlined" sx={{ mr: 0.5 }} /> {editMode && ( <> <Tooltip title="Edit"><IconButton color="primary" size="small" onClick={() => openCriteriaDialog(criteriaArrayIndex)} disabled={isSaving} sx={{ p: 0.5 }}><EditIcon fontSize="small" /></IconButton></Tooltip> <Tooltip title="Delete"><IconButton color="error" size="small" onClick={() => openDeleteCriteriaDialog(index, criteriaArrayIndex)} disabled={isSaving} sx={{ p: 0.5 }}><DeleteIcon fontSize="small" /></IconButton></Tooltip> </> )} </Box> </Box> </CriteriaCard> ))} <Divider sx={{ my: 2 }} /> <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1 }}> <Typography variant="subtitle1" fontWeight="bold">Total:</Typography> <Typography variant="subtitle1" fontWeight="bold" color={calculateTotalPoints(subRubric) === (subRubric.max_points ?? 0) ? 'text.primary' : 'error.main'}> {calculateTotalPoints(subRubric)} / {subRubric.max_points ?? 0} </Typography> </Box> {calculateTotalPoints(subRubric) !== (subRubric.max_points ?? 0) && ( <Typography variant="caption" color="error" display="block" textAlign="right">Points mismatch!</Typography> )} </> )} </RubricSection> </TabPanel> ))} </> );};


  // --- MAIN COMPONENT RETURN ---
  return (
    <Box sx={{ p: { xs: 1, sm: 2, md: 3 } }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 1 }}> <IconButton title="Back to Course Overview" aria-label="back" onClick={() => (courseId && semester) && router.push(`/course/${courseId}?semester=${semester}`)} disabled={!courseId || !semester || actionLoading || loadingAssignments || loadingRubric || isSaving} sx={{ mr: 1 }}> <ArrowBackIcon /> </IconButton> <Typography variant="h4" component="h1" sx={{ flexGrow: 1, mr: 1 }}>Rubric Management</Typography> </Box>
      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}
      {renderAssignmentSelection()}
      <Divider sx={{ my: 3 }} />
      {selectedAssignment && renderRubricContent()}
      <Dialog open={criteriaDialogOpen} onClose={() => !actionLoading && setCriteriaDialogOpen(false)} maxWidth="sm" fullWidth> <DialogTitle>{editingCriteriaIndex !== null ? 'Edit' : 'Add'} Grading Criteria {typeof currentQuestionIndex === 'number' ? `for Q${currentQuestionIndex + 1}` : ''}</DialogTitle> <DialogContent> <TextField autoFocus name="criteria_id" label="Criteria Title/ID" fullWidth value={criteriaFormData.criteria_id} onChange={(e) => handleInputChange(e, setCriteriaFormData)} margin="dense" required error={!criteriaFormData.criteria_id?.trim() && criteriaFormData.criteria_id !==''} helperText={!criteriaFormData.criteria_id?.trim() && criteriaFormData.criteria_id !=='' ? "Required" : "Short identifier"} disabled={actionLoading}/> <TextField name="criteria" label="Criteria Description" fullWidth multiline minRows={3} value={criteriaFormData.criteria} onChange={(e) => handleInputChange(e, setCriteriaFormData)} margin="dense" required error={!criteriaFormData.criteria?.trim() && criteriaFormData.criteria !==''} helperText={!criteriaFormData.criteria?.trim() && criteriaFormData.criteria !=='' ? "Required" : "Describe how points are awarded"} disabled={actionLoading}/> <TextField name="points" label="Points" type="number" fullWidth value={criteriaFormData.points} onChange={(e) => handleInputChange(e, setCriteriaFormData)} margin="dense" required InputProps={{ inputProps: { min: 0, step: 0.5 }, endAdornment: <InputAdornment position="end">pts</InputAdornment>, }} disabled={actionLoading} error={!(parseFloat(criteriaFormData.points) >= 0 && criteriaFormData.points !== '')} helperText={!(parseFloat(criteriaFormData.points) >= 0 && criteriaFormData.points !== '') ? "Points must be >= 0" : ""} /> </DialogContent> <DialogActions> <Button onClick={() => setCriteriaDialogOpen(false)} disabled={actionLoading}>Cancel</Button> <Button onClick={handleSaveCriteria} variant="contained" color="primary" disabled={actionLoading || !criteriaFormData.criteria_id?.trim() || !criteriaFormData.criteria?.trim() || !(parseFloat(criteriaFormData.points) >= 0 && criteriaFormData.points !== '')}>{actionLoading ? <CircularProgress size={24}/> : (editingCriteriaIndex !== null ? 'Save Criteria' : 'Add Criteria')}</Button> </DialogActions> </Dialog>
      <ConfirmationDialog open={deleteCriteriaDialogOpen} onClose={() => !actionLoading && setDeleteCriteriaDialogOpen(false)} onConfirm={handleDeleteCriteria} title="Delete Criteria?" description={`Permanently delete criteria "${criteriaToDelete?.name || 'this criteria'}"?`} confirmText="Delete" cancelText="Cancel" confirmColor="error" loading={actionLoading}/>
      <Dialog open={aiInstructionsDialogOpen} onClose={() => !loadingAI && setAiInstructionsDialogOpen(false)} maxWidth="sm" fullWidth> <DialogTitle><Box sx={{ display: 'flex', alignItems: 'center' }}><LightbulbIcon sx={{ mr: 1, color: 'warning.main' }} />AI Rubric Suggestions</Box></DialogTitle> <DialogContent><Typography variant="body2" paragraph>Provide specific instructions to guide the AI, or leave blank for general suggestions based on assignment content.</Typography><TextField label="Instructions for AI (Optional)" fullWidth multiline rows={4} value={aiInstructions} onChange={(e) => setAiInstructions(e.target.value)} margin="normal" placeholder="e.g., Focus on accuracy, deduct for syntax errors, give partial credit for..." disabled={loadingAI} /></DialogContent> <DialogActions><Button onClick={() => setAiInstructionsDialogOpen(false)} disabled={loadingAI}>Cancel</Button><Button onClick={getAIRubricSuggestions} variant="contained" color="primary" disabled={loadingAI || !selectedAssignment} startIcon={loadingAI ? <CircularProgress size={20} color="inherit"/> : <LightbulbIcon />}>{loadingAI ? 'Generating...' : 'Get Suggestions'}</Button></DialogActions> </Dialog>
      <Snackbar open={alertOpen} autoHideDuration={6000} onClose={() => setAlertOpen(false)} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}><Alert onClose={() => setAlertOpen(false)} severity={alertSeverity} variant="filled" sx={{ width: '100%' }}> {alertMessage} </Alert></Snackbar>
    </Box>
  );
}