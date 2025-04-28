/**
 * Rubric Management Page for BU MET Autograder
 * Create, edit, and apply grading rubrics
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react'; // Added useMemo
import { useRouter } from 'next/router';
import Link from 'next/link';
import {
  Alert,
  // Avatar, // Removed unused
  Box,
  Button,
  Card, // Keep for potential future use? User had it.
  // CardActionArea, // Removed unused
  // CardActions, // Removed unused
  // CardContent, // Removed unused
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
  // Slider, // Removed - Leniency not in Pydantic model
  Snackbar,
  Switch,
  Tab,
  Tabs,
  TextField,
  Tooltip,
  Typography,
  Link as MuiLink,
  useTheme, // Re-added
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
  // RuleFolder as RubricIcon, // Removed unused
  // HelpOutline as HelpIcon, // Removed unused
  Info as InfoIcon, // Keep for mismatch icon
  PlaylistAddCheck as CriteriaIcon,
  WarningAmber as WarningIcon, // Added for mismatch warning
} from '@mui/icons-material';
// Assuming api.js is correctly imported
import { assignmentService, rubricService } from '../../../api'; // Adjust path if needed
// import { ERROR_MESSAGES } from '../../../api/config'; // Removed this import
// import CardSkeleton from '../../../components/CardSkeleton'; // Assuming exists - Keep if needed
import AISuggestionCard from '../../../components/AISuggestionCard'; // Assuming exists
import ConfirmationDialog from '../../../components/ConfirmationDialog'; // Assuming exists
// Removed logger import

// Styled components - These need 'theme'
const RubricSection = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  marginBottom: theme.spacing(3),
  border: `1px solid ${theme.palette.divider}`,
  borderRadius: theme.shape.borderRadius, // Added for consistency
}));

const CriteriaCard = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(2),
  marginBottom: theme.spacing(2),
  borderLeft: `4px solid ${theme.palette.info.light}`, // Adjusted color
  backgroundColor: theme.palette.background.paper, // Use paper bg
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
      {/* Render content only when the tab is active */}
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
};

// Grading flags definition (aligned with Pydantic Enum)
const GRADING_FLAGS_CONFIG = [
  { value: 'IGNORE_SPELLINGS', label: 'Ignore Spelling', description: 'AI ignores minor spelling mistakes during grading.' },
  { value: 'IGNORE_GRAMMAR', label: 'Ignore Grammar', description: 'AI ignores minor grammatical errors during grading.' },
  { value: 'ORIGINALITY', label: 'Reward Originality', description: 'AI rewards originality and may deduct for unoriginal ideas/plagiarism (experimental).' },
  { value: 'IGNORE_FORMATTING', label: 'Ignore Formatting', description: 'AI ignores formatting inconsistencies (e.g., spacing, list styles) during grading.' },
];

// Main component
export default function RubricManagement() {
  const router = useRouter();
  const theme = useTheme(); // Re-added useTheme hook
  const { id: courseIdParam, semester: semesterParam, assignmentId: assignmentIdParam } = router.query;

  // Normalize and memoize route parameters
  const courseId = useMemo(() => typeof courseIdParam === 'string' ? courseIdParam.toLowerCase().trim() : null, [courseIdParam]);
  const semester = useMemo(() => typeof semesterParam === 'string' ? semesterParam.toLowerCase().trim() : null, [semesterParam]);
  const selectedAssignmentIdQuery = useMemo(() => typeof assignmentIdParam === 'string' ? assignmentIdParam : null, [assignmentIdParam]);

  // State declarations
  const [assignments, setAssignments] = useState([]);
  const [selectedAssignment, setSelectedAssignment] = useState(null);
  const [rubric, setRubric] = useState(null);
  const [rubricNotFound, setRubricNotFound] = useState(false);
  const [aiRubricSuggestion, setAiRubricSuggestion] = useState(null);
  const [loadingAssignments, setLoadingAssignments] = useState(true);
  const [loadingRubric, setLoadingRubric] = useState(false);
  const [loadingAI, setLoadingAI] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);
  const [saveError, setSaveError] = useState(null);
  const [tabValue, setTabValue] = useState(0);
  const [editMode, setEditMode] = useState(false);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(null);
  const [criteriaDialogOpen, setCriteriaDialogOpen] = useState(false);
  const [editingCriteriaIndex, setEditingCriteriaIndex] = useState(null);
  const [deleteCriteriaDialogOpen, setDeleteCriteriaDialogOpen] = useState(false);
  const [aiInstructionsDialogOpen, setAiInstructionsDialogOpen] = useState(false);
  const [criteriaFormData, setCriteriaFormData] = useState({ criteria_id: '', criteria: '', points: 0 });
  const [criteriaToDelete, setCriteriaToDelete] = useState(null);
  const [aiInstructions, setAiInstructions] = useState('');
  const [alertOpen, setAlertOpen] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [alertSeverity, setAlertSeverity] = useState('success');

  // --- Helper Functions ---
  const showAlert = useCallback((message, severity = 'success') => {
    setAlertMessage(message); setAlertSeverity(severity); setAlertOpen(true);
    if (severity === 'error') console.error(`ALERT: ${message}`);
    else if (severity === 'warning') console.warn(`ALERT: ${message}`);
    else console.log(`ALERT: ${message}`);
  }, []);

  const formatApiError = useCallback((err, defaultMessage) => {
    console.error("API Error Encountered:", err);
    if (err instanceof Error && err.message && !err.response) {
        if (err.isNotFoundError) return "The requested resource was not found (404).";
        return err.message;
    }
    if (err?.response?.data?.detail) {
      if (Array.isArray(err.response.data.detail)) {
        return err.response.data.detail
           .map(d => `${d.loc?.slice(1).join('.') || 'Validation Error'}: ${d.msg}`)
           .join('; ');
      }
      return String(err.response.data.detail);
    }
    return defaultMessage || "An unexpected error occurred.";
  }, []);

  const calculateTotalPoints = useCallback((subRubric) => {
    if (!Array.isArray(subRubric?.grading_criteria)) { return 0; }
    return subRubric.grading_criteria.reduce((sum, c) => {
      const points = parseFloat(String(c?.points));
      return sum + (isNaN(points) || points < 0 ? 0 : points);
    }, 0);
  }, []);

  // --- Creates an empty rubric structure matching Pydantic model ---
  const createEmptyRubric = useCallback((assignment) => {
    if (!assignment?.assignment_id || !semester || !courseId) {
      console.error("Cannot create empty rubric: missing context", { assignmentId: assignment?.assignment_id, semester, courseId });
      return null;
    }
    const assignmentIdStr = String(assignment.assignment_id);
    console.log(`Creating empty Pydantic-aligned rubric structure for assignment ${assignmentIdStr}`);

    const sortedQuestions = (assignment.questions && Array.isArray(assignment.questions))
      ? [...assignment.questions].sort((a, b) => (a.question_index ?? Infinity) - (b.question_index ?? Infinity))
      : [];

    const subRubrics = sortedQuestions.map(question => ({
      question_index: question.question_index,
      max_points: typeof question.max_points === 'number' ? question.max_points : 10.0,
      instructor_guideline: null,
      grading_criteria: [],
    }));

    return {
      semester: semester,
      course_id: courseId,
      assignment_id: assignmentIdStr,
      grading_flags: [],
      overall_instructor_guidelines: null,
      sub_rubrics: subRubrics,
    };
  }, [semester, courseId]); // Dependencies


  // --- Data Fetching ---
  const fetchRubric = useCallback(async (assignmentToFetch) => {
    if (!semester || !courseId || !assignmentToFetch?.assignment_id) {
      console.warn("fetchRubric skipped: Missing context.", { semester, courseId, assignmentId: assignmentToFetch?.assignment_id });
      setRubric(null); setRubricNotFound(true); setLoadingRubric(false); setError(null); return;
    }

    const assignmentIdStr = String(assignmentToFetch.assignment_id);
    setLoadingRubric(true); setError(null); setSaveError(null); setRubricNotFound(false);
    console.log(`Fetching rubric for assignment: ${assignmentIdStr}`);

    try {
      const response = await rubricService.getRubric(semester, courseId, assignmentIdStr);
      const fetchedRubricData = response.data;
      console.log("Fetched rubric data:", fetchedRubricData);

      if (!fetchedRubricData || typeof fetchedRubricData !== 'object' || !fetchedRubricData.assignment_id) {
        console.warn(`Invalid rubric data received for ${assignmentIdStr}. Treating as 404.`);
        throw new Error("Not Found");
      }

      const baseRubric = createEmptyRubric(assignmentToFetch);
      if (!baseRubric) throw new Error("Internal error: Failed to create base rubric.");

      let completeRubric = {
        ...baseRubric,
        grading_flags: Array.isArray(fetchedRubricData.grading_flags) ? fetchedRubricData.grading_flags : [],
        overall_instructor_guidelines: fetchedRubricData.overall_instructor_guidelines ?? null,
      };

      const fetchedSubRubricsMap = new Map((fetchedRubricData.sub_rubrics || []).map(sr => [sr.question_index, sr]));

      completeRubric.sub_rubrics = baseRubric.sub_rubrics.map(baseSr => {
        const fetchedSr = fetchedSubRubricsMap.get(baseSr.question_index);
        if (fetchedSr) {
          return {
            ...baseSr,
            max_points: typeof fetchedSr.max_points === 'number' ? fetchedSr.max_points : baseSr.max_points,
            instructor_guideline: fetchedSr.instructor_guideline ?? null,
            grading_criteria: Array.isArray(fetchedSr.grading_criteria)
              ? fetchedSr.grading_criteria.map(c => ({
                  criteria_id: c.criteria_id ?? '', criteria: c.criteria ?? '', points: typeof c.points === 'number' ? c.points : 0,
                }))
              : [],
          };
        }
        return baseSr;
      });

      completeRubric.sub_rubrics.sort((a, b) => (a.question_index ?? Infinity) - (b.question_index ?? Infinity));

      setRubric(completeRubric); setAiRubricSuggestion(null); setEditMode(false); setTabValue(0);
      setCurrentQuestionIndex(completeRubric.sub_rubrics[0]?.question_index ?? null);

    } catch (err) {
      const isNotFoundError = err?.isNotFoundError || err?.message === "Not Found";
      if (isNotFoundError) {
        console.log(`No rubric found for ${assignmentIdStr}. Initializing empty rubric.`);
        const emptyRubric = createEmptyRubric(assignmentToFetch);
        if (emptyRubric) {
             setRubric(emptyRubric); setRubricNotFound(true); setEditMode(true); setTabValue(0);
             setCurrentQuestionIndex(emptyRubric.sub_rubrics[0]?.question_index ?? null); setError(null);
        } else {
             console.error("Failed to create empty rubric after 404."); setError("Could not initialize new rubric."); setRubric(null);
        }
      } else {
        console.error('Error fetching rubric:', err);
        const errorMsg = formatApiError(err, 'Failed to load rubric'); setError(errorMsg); showAlert(errorMsg, 'error'); setRubric(null);
      }
    } finally {
      setLoadingRubric(false);
    }
  }, [semester, courseId, createEmptyRubric, showAlert, formatApiError]);


  // --- Initial Data Load Effect ---
  useEffect(() => {
    const fetchAssignmentsAndInitialRubric = async () => {
      if (!courseId || !semester) { setLoadingAssignments(false); return; }
      console.log(`Initial fetch effect: ${courseId}/${semester}, param=${selectedAssignmentIdQuery}`);
      setLoadingAssignments(true); setLoadingRubric(false);
      setError(null); setSaveError(null); setRubric(null); setRubricNotFound(false); setSelectedAssignment(null); setAssignments([]);
      setAiRubricSuggestion(null); setEditMode(false); setTabValue(0); setCurrentQuestionIndex(null);

      try {
        const assignmentsResponse = await assignmentService.getAssignments(courseId, semester, true);
        const assignmentsData = assignmentsResponse?.data;
        if (!Array.isArray(assignmentsData)) throw new Error("Invalid assignment data.");
        assignmentsData.sort((a, b) => String(a.assignment_id).localeCompare(String(b.assignment_id)));
        setAssignments(assignmentsData);
        console.log(`Fetched ${assignmentsData.length} assignments.`);

        let assignmentToSelect = null; let targetAssignmentId = selectedAssignmentIdQuery;

        if (assignmentsData.length > 0) {
          if (targetAssignmentId) {
            assignmentToSelect = assignmentsData.find(a => String(a.assignment_id) === targetAssignmentId);
            if (!assignmentToSelect) {
              showAlert(`Assignment ${targetAssignmentId} not found. Loading first.`, 'warning');
              assignmentToSelect = assignmentsData[0]; targetAssignmentId = String(assignmentToSelect.assignment_id);
              router.replace(`/course/${courseId}/rubrics?semester=${semester}&assignmentId=${targetAssignmentId}`, undefined, { shallow: true });
            }
          } else {
            assignmentToSelect = assignmentsData[0]; targetAssignmentId = String(assignmentToSelect.assignment_id);
            router.replace(`/course/${courseId}/rubrics?semester=${semester}&assignmentId=${targetAssignmentId}`, undefined, { shallow: true });
          }

          if (assignmentToSelect) {
            if (!assignmentToSelect.questions || !Array.isArray(assignmentToSelect.questions)) assignmentToSelect.questions = [];
            assignmentToSelect.questions.sort((a, b) => (a.question_index ?? Infinity) - (b.question_index ?? Infinity));
            setSelectedAssignment(assignmentToSelect);
            console.log(`Selected initial assignment: ${assignmentToSelect.assignment_id}`);
            await fetchRubric(assignmentToSelect);
          } else { console.error("Could not determine assignment to select."); setLoadingRubric(false); }
        } else { console.warn("No assignments found."); setLoadingRubric(false); }

      } catch (err) {
        console.error('Error during initial load:', err);
        const errorMsg = formatApiError(err, 'Failed loading initial data'); setError(errorMsg); showAlert(errorMsg, 'error');
        setLoadingRubric(false); setLoadingAssignments(false);
      } finally {
        setLoadingAssignments(false);
        console.log("Initial fetch effect finished.");
      }
    };
    if (courseId && semester) { fetchAssignmentsAndInitialRubric(); }
     else { setLoadingAssignments(false); }
  }, [courseId, semester, selectedAssignmentIdQuery, router, fetchRubric, formatApiError, showAlert]);


  // --- Event Handlers ---
  const handleSelectAssignment = useCallback((assignment) => {
    const newAssignmentIdStr = String(assignment?.assignment_id);
    const currentAssignmentIdStr = String(selectedAssignment?.assignment_id);
    if (!assignment || newAssignmentIdStr === currentAssignmentIdStr) return;
    console.log(`Switching to assignment: ${newAssignmentIdStr}`);
    if (!assignment.questions || !Array.isArray(assignment.questions)) assignment.questions = [];
    assignment.questions.sort((a, b) => (a.question_index ?? Infinity) - (b.question_index ?? Infinity));
    if (courseId && semester) router.push(`/course/${courseId}/rubrics?semester=${semester}&assignmentId=${newAssignmentIdStr}`, undefined, { shallow: true });
    setSelectedAssignment(assignment); setRubric(null); setRubricNotFound(false); setAiRubricSuggestion(null);
    setEditMode(false); setTabValue(0); setCurrentQuestionIndex(null); setError(null); setSaveError(null);
    setLoadingRubric(true);
    fetchRubric(assignment);
  }, [courseId, semester, selectedAssignment?.assignment_id, router, fetchRubric]);

  const getAIRubricSuggestions = useCallback(async () => {
    if (!selectedAssignment || !semester || !courseId) { showAlert("Select assignment first.", "warning"); return; }
    const assignmentIdStr = String(selectedAssignment.assignment_id);
    console.log(`Requesting AI suggestions for ${assignmentIdStr}. Instructions: "${aiInstructions || 'None'}"`);
    setLoadingAI(true); setError(null); setSaveError(null);
    try {
      const response = await rubricService.getAIRubric(semester, courseId, assignmentIdStr, aiInstructions || null);
      const aiRubricData = response?.data;
      if (!aiRubricData || typeof aiRubricData !== 'object' || !aiRubricData.assignment_id) throw new Error("Invalid AI response data.");
      if (aiRubricData.semester !== semester || aiRubricData.course_id !== courseId || String(aiRubricData.assignment_id) !== assignmentIdStr) throw new Error("AI suggestion context mismatch.");
      setAiRubricSuggestion(aiRubricData); setAiInstructionsDialogOpen(false);
      showAlert('AI suggestions generated! Review below.', 'success');
    } catch (err) { const errorMsg = formatApiError(err, 'Failed to get AI suggestions'); setError(errorMsg); showAlert(errorMsg, 'error'); }
    finally { setLoadingAI(false); }
  }, [selectedAssignment, semester, courseId, aiInstructions, showAlert, formatApiError]);

  const applyAIRubricSuggestions = useCallback(() => {
    if (!aiRubricSuggestion || !selectedAssignment) { console.warn("Apply AI suggestions cancelled: Missing suggestion or assignment context."); return; }
    console.log("Applying AI suggestions...");
    const baseRubric = createEmptyRubric(selectedAssignment);
    if (!baseRubric) { showAlert("Internal error creating base rubric.", "error"); return; }
    const alignedRubric = {
      ...baseRubric,
      grading_flags: Array.isArray(aiRubricSuggestion.grading_flags) ? aiRubricSuggestion.grading_flags : [],
      overall_instructor_guidelines: aiRubricSuggestion.overall_instructor_guidelines ?? null,
    };
    const aiSubRubricsMap = new Map((aiRubricSuggestion.sub_rubrics || []).map(sr => [sr.question_index, sr]));
    alignedRubric.sub_rubrics = baseRubric.sub_rubrics.map(baseSr => {
      const aiSr = aiSubRubricsMap.get(baseSr.question_index);
      if (aiSr) {
        return { ...baseSr, max_points: typeof aiSr.max_points === 'number' ? aiSr.max_points : baseSr.max_points, instructor_guideline: aiSr.instructor_guideline ?? null,
          grading_criteria: Array.isArray(aiSr.grading_criteria) ? aiSr.grading_criteria.map(c => ({ criteria_id: c.criteria_id ?? '', criteria: c.criteria ?? '', points: typeof c.points === 'number' ? c.points : 0 })) : [],
        };
      } return baseSr;
    });
    alignedRubric.sub_rubrics.sort((a, b) => (a.question_index ?? Infinity) - (b.question_index ?? Infinity));
    setRubric(alignedRubric); setAiRubricSuggestion(null); setEditMode(true); setRubricNotFound(false); setTabValue(0);
    setCurrentQuestionIndex(alignedRubric.sub_rubrics[0]?.question_index ?? null);
    showAlert('AI suggestions applied. Review and save changes.', 'info');
  }, [aiRubricSuggestion, selectedAssignment, createEmptyRubric, showAlert, semester, courseId]);

  const saveRubric = useCallback(async () => {
    if (!rubric || !rubric.semester || !rubric.course_id || !rubric.assignment_id) { showAlert("Cannot save: Rubric data incomplete.", "error"); return; }
    if (!selectedAssignment || String(rubric.assignment_id) !== String(selectedAssignment.assignment_id)) { showAlert("Cannot save: Assignment mismatch.", "error"); setSaveError("Assignment mismatch"); return; }
    console.log("Validating rubric before save...");
    let pointsMismatch = false, mismatchDetails = [], invalidCriteria = false, invalidCriteriaDetails = [];
    (rubric.sub_rubrics || []).forEach(sr => {
      const qNum = sr.question_index + 1; const total = calculateTotalPoints(sr); const max = sr.max_points ?? 0;
      if (Math.abs(total - max) > 0.001) { pointsMismatch = true; mismatchDetails.push(`Q${qNum}`); }
      (sr.grading_criteria || []).forEach((c, i) => { if (!c.criteria_id?.trim() || !c.criteria?.trim() || !(typeof c.points === 'number' && c.points >= 0)) { invalidCriteria = true; invalidCriteriaDetails.push(`Q${qNum} Crit#${i+1}`); } });
    });
    if (invalidCriteria) { const msg = `Cannot save: Invalid criteria found (${invalidCriteriaDetails.join(', ')}). Check Title, Description, Points.`; showAlert(msg, "error"); setSaveError(msg); return; }
    if (pointsMismatch) { showAlert(`Warning: Points mismatch for ${mismatchDetails.join(', ')}. Saving anyway.`, "warning"); }

    setIsSaving(true); setError(null); setSaveError(null);
    const payload = {
        semester: rubric.semester, course_id: rubric.course_id, assignment_id: String(rubric.assignment_id),
        grading_flags: rubric.grading_flags || [], overall_instructor_guidelines: rubric.overall_instructor_guidelines || null,
        sub_rubrics: (rubric.sub_rubrics || []).map(sr => ({
            question_index: sr.question_index, max_points: sr.max_points ?? 0, instructor_guideline: sr.instructor_guideline || null,
            grading_criteria: (sr.grading_criteria || []).map(c => ({ criteria_id: c.criteria_id, criteria: c.criteria, points: c.points })),
        })),
    };
    console.log("Sending payload to PUT /rubric:", payload);
    try {
      await rubricService.createRubric(payload); console.log("Rubric saved.");
      setEditMode(false); setRubricNotFound(false); showAlert('Rubric saved successfully.', 'success');
      if(selectedAssignment) await fetchRubric(selectedAssignment);
    } catch (err) { const errorMsg = formatApiError(err, 'Failed to save rubric.'); setSaveError(errorMsg); showAlert(errorMsg, 'error'); console.error("Save failed:", err); }
    finally { setIsSaving(false); }
  }, [rubric, selectedAssignment, fetchRubric, showAlert, formatApiError, calculateTotalPoints]);


  // --- State Change Handlers ---
  const handleRubricSettingChange = useCallback((field, value) => {
      setRubric(prev => (prev ? { ...prev, [field]: value } : null));
      setSaveError(null);
  }, []);

  const handleSubRubricChange = useCallback((questionIndex, field, value) => {
     if (questionIndex === null || typeof questionIndex !== 'number') return;
     setRubric(prev => {
       if (!prev || !Array.isArray(prev.sub_rubrics)) return prev;
       let found = false;
       const newSubRubrics = prev.sub_rubrics.map(sr => {
         if (sr.question_index === questionIndex) { found = true; return { ...sr, [field]: value }; }
         return sr;
       });
       if (!found) console.warn(`SubRubric QIndex ${questionIndex} not found for update.`);
       return found ? { ...prev, sub_rubrics: newSubRubrics } : prev;
     });
     setSaveError(null);
   }, []);

  const handleGradingFlagToggle = useCallback((flagValue) => {
    setRubric(prev => {
      if (!prev) return null;
      const currentFlags = prev.grading_flags || [];
      const updatedFlags = currentFlags.includes(flagValue) ? currentFlags.filter(f => f !== flagValue) : [...currentFlags, flagValue];
      return { ...prev, grading_flags: updatedFlags };
    });
    setSaveError(null);
  }, []);

  const handleTabChange = useCallback((event, newValue) => {
    setTabValue(newValue);
    const targetQuestionIndex = newValue > 0 ? rubric?.sub_rubrics?.[newValue - 1]?.question_index : null;
    setCurrentQuestionIndex(typeof targetQuestionIndex === 'number' ? targetQuestionIndex : null);
    console.debug(`Tab changed to ${newValue}, currentQuestionIndex set to ${targetQuestionIndex ?? 'null'}`);
  }, [rubric]);

  // --- Criteria Management ---
  const openCriteriaDialog = useCallback((criteriaArrayIndex = null) => {
    if (currentQuestionIndex === null) { showAlert("Select a question tab first.", "warning"); return; }
    const targetSubRubric = rubric?.sub_rubrics?.find(sr => sr.question_index === currentQuestionIndex);
    if (!targetSubRubric) { showAlert("Cannot find data for current question.", "error"); return; }
    setEditingCriteriaIndex(criteriaArrayIndex);
    if (criteriaArrayIndex !== null) {
      const criteria = targetSubRubric.grading_criteria?.[criteriaArrayIndex];
      if (criteria) setCriteriaFormData({ criteria_id: criteria.criteria_id ?? '', criteria: criteria.criteria ?? '', points: criteria.points ?? 0 });
      else { showAlert(`Criteria index ${criteriaArrayIndex} invalid.`, "error"); return; }
    } else { setCriteriaFormData({ criteria_id: '', criteria: '', points: 0 }); }
    setCriteriaDialogOpen(true);
  }, [rubric, currentQuestionIndex, showAlert]);

  const handleSaveCriteria = useCallback(() => {
    if (currentQuestionIndex === null) { showAlert("No question selected.", "error"); return; }
    const { criteria_id, criteria } = criteriaFormData; const pointsString = String(criteriaFormData.points).trim(); const pointsValue = parseFloat(pointsString);
    if (!criteria_id?.trim()) { showAlert('Criteria Title/ID required.', 'warning'); return; }
    if (!criteria?.trim()) { showAlert('Criteria Description required.', 'warning'); return; }
    if (pointsString === '' || isNaN(pointsValue) || pointsValue < 0) { showAlert('Points must be number >= 0.', 'warning'); return; }
    const newOrUpdatedCriteria = { criteria_id: criteria_id.trim(), criteria: criteria.trim(), points: pointsValue };
    setRubric(prev => {
      if (!prev) return null;
      const targetIdx = prev.sub_rubrics.findIndex(sr => sr.question_index === currentQuestionIndex); if (targetIdx === -1) return prev;
      const newRubric = structuredClone(prev); const targetSr = newRubric.sub_rubrics[targetIdx];
      if (!Array.isArray(targetSr.grading_criteria)) targetSr.grading_criteria = [];
      if (editingCriteriaIndex !== null) { if (editingCriteriaIndex < targetSr.grading_criteria.length) targetSr.grading_criteria[editingCriteriaIndex] = newOrUpdatedCriteria; else { console.error("Edit index OOB!"); return prev; } }
      else { targetSr.grading_criteria.push(newOrUpdatedCriteria); }
      return newRubric;
    });
    setCriteriaDialogOpen(false); setEditingCriteriaIndex(null); setCriteriaFormData({ criteria_id: '', criteria: '', points: 0 }); setSaveError(null);
  }, [criteriaFormData, currentQuestionIndex, editingCriteriaIndex, showAlert]);

   const openDeleteCriteriaDialog = useCallback((criteriaArrayIndex) => {
     if (currentQuestionIndex === null) { showAlert("Select question tab first.", "warning"); return; }
     if (typeof criteriaArrayIndex !== 'number' || criteriaArrayIndex < 0) return;
     const text = rubric?.sub_rubrics?.find(sr => sr.question_index === currentQuestionIndex)?.grading_criteria?.[criteriaArrayIndex]?.criteria_id || `Crit#${criteriaArrayIndex+1}`;
     setCriteriaToDelete({ criteriaArrayIndex, text }); setDeleteCriteriaDialogOpen(true);
   }, [rubric, currentQuestionIndex, showAlert]);

  const handleDeleteCriteria = useCallback(() => {
    if (!rubric || !editMode || criteriaToDelete === null || currentQuestionIndex === null) { setDeleteCriteriaDialogOpen(false); setCriteriaToDelete(null); return; }
    const { criteriaArrayIndex } = criteriaToDelete;
    setRubric(prev => {
      if (!prev) return null; const targetIdx = prev.sub_rubrics.findIndex(sr => sr.question_index === currentQuestionIndex); if (targetIdx === -1) return prev;
      const newRubric = structuredClone(prev); const targetSr = newRubric.sub_rubrics[targetIdx];
      if (Array.isArray(targetSr.grading_criteria) && criteriaArrayIndex >= 0 && criteriaArrayIndex < targetSr.grading_criteria.length) { targetSr.grading_criteria.splice(criteriaArrayIndex, 1); }
      else { console.error(`Delete index ${criteriaArrayIndex} OOB!`); return prev; }
      return newRubric;
    });
    setDeleteCriteriaDialogOpen(false); setCriteriaToDelete(null); setSaveError(null);
  }, [rubric, editMode, criteriaToDelete, currentQuestionIndex]);

  const getQuestionText = useCallback((qIndex) => { const question = selectedAssignment?.questions?.find(q => q.question_index === qIndex); return question ? (question.question_text || `(Q${qIndex+1} No Text)`) : `Question Text (Index ${qIndex}) Not Found`; }, [selectedAssignment]);

  // --- Calculate hasAnyMismatch at the top level ---
  const currentSubRubricsForMemo = rubric?.sub_rubrics || [];
  const hasAnyMismatch = useMemo(() =>
      currentSubRubricsForMemo.some(sr => Math.abs(calculateTotalPoints(sr) - (sr.max_points ?? 0)) > 0.001)
  , [currentSubRubricsForMemo, calculateTotalPoints]); // Use derived variable

  // --- Render Functions ---
  const renderAssignmentSelection = () => {
    if (loadingAssignments) return <Typography sx={{ mb: 3, fontStyle: 'italic', color: 'text.secondary' }}>Loading assignments...</Typography>;
    if (!Array.isArray(assignments)) return <Alert severity="error" sx={{ mb: 3 }}>Failed to load assignments.</Alert>;
    if (assignments.length === 0) return <Alert severity="info" sx={{ mb: 3 }}>No assignments found. {courseId && semester && <Link href={`/course/${courseId}/assignments?semester=${semester}`} passHref><MuiLink sx={{ ml: 1 }}>Create one?</MuiLink></Link>}</Alert>;
    return (<FormControl fullWidth variant="outlined" sx={{ mb: 3 }} disabled={loadingRubric || isSaving || loadingAI}> <InputLabel id="assignment-select-label">Select Assignment</InputLabel> <Select labelId="assignment-select-label" value={selectedAssignment?.assignment_id ?? ''} onChange={(e) => { const assignment = assignments.find((a) => String(a.assignment_id) === e.target.value); if (assignment) handleSelectAssignment(assignment); }} label="Select Assignment"> {assignments.map((a) => ( <MenuItem key={a.assignment_id} value={a.assignment_id}>{`ID: ${a.assignment_id} (${a.questions?.length ?? 0} Qs)`}</MenuItem> ))} </Select> </FormControl>);
  };

  // --- Render Rubric Content --- Moved hasAnyMismatch calculation outside ---
  const renderRubricContent = () => {
    if (loadingRubric) return <Box sx={{ display: 'flex', justifyContent: 'center', my: 5 }}><CircularProgress size={24} sx={{ mr: 2 }} /><Typography color="text.secondary">Loading rubric...</Typography></Box>;
    if (!selectedAssignment) { if (!loadingAssignments && assignments.length > 0) return <Alert severity="info" icon={<AssignmentIcon />} sx={{ mt: 2 }}>Select an assignment.</Alert>; return null; }
    if (!rubric && error && !rubricNotFound) return <Alert severity="error" sx={{ mt: 2 }}>Error loading rubric: {error}</Alert>;
    if (!rubric && rubricNotFound && editMode) { /* Message shown below */ }
    else if (!rubric) { console.error("Render error: Rubric is null unexpectedly."); return <Alert severity="error" sx={{ mt: 2 }}>Rubric data unavailable.</Alert>; }

    const currentSubRubrics = rubric.sub_rubrics || [];
    // hasAnyMismatch is now calculated outside using useMemo

    return (<>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 2 }}> <Typography variant="h5" component="h2" sx={{ flexGrow: 1, mr: 2 }}> Rubric Editor <Chip label={`Assignment: ${selectedAssignment.assignment_id}`} size="small" variant='outlined' sx={{ ml: 1.5 }} /> </Typography> <Box sx={{ display: 'flex', gap: 1 }}> {editMode ? (<> <Button variant="contained" onClick={saveRubric} disabled={isSaving} startIcon={isSaving ? <CircularProgress size={20} /> : <SaveIcon />}>{isSaving ? 'Saving...' : 'Save Rubric'}</Button> <Button variant="outlined" onClick={() => { setEditMode(false); setSaveError(null); if (selectedAssignment) fetchRubric(selectedAssignment); }} disabled={isSaving}>Cancel</Button> </>) : (<> {selectedAssignment && <Button variant="outlined" onClick={() => setAiInstructionsDialogOpen(true)} disabled={loadingAI || isSaving} startIcon={loadingAI ? <CircularProgress size={20}/> : <LightbulbIcon />}>{loadingAI ? 'Generating...' : 'AI Suggestions'}</Button>} <Button variant="contained" onClick={() => setEditMode(true)} disabled={isSaving || loadingAI || !rubric} startIcon={<EditIcon />}>Edit Rubric</Button> </>)} </Box> </Box>
        {editMode && saveError && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setSaveError(null)}>Save failed: {saveError}</Alert>}
        {editMode && !saveError && hasAnyMismatch && <Alert severity="warning" icon={<WarningIcon />} sx={{ mb: 2 }}>Points mismatch detected in one or more questions.</Alert>}
        {editMode && rubricNotFound && !saveError && <Alert severity="info" sx={{ mb: 2 }}>Creating a new rubric. Fill details and save.</Alert>}
        {aiRubricSuggestion && !editMode && <AISuggestionCard rubricSuggestion={aiRubricSuggestion} onApply={applyAIRubricSuggestions} onDismiss={() => setAiRubricSuggestion(null)} sx={{ mb: 3 }} />}

        <Paper elevation={0} sx={{ borderBottom: 1, borderColor: 'divider', mb: 0 }}> <Tabs value={tabValue} onChange={handleTabChange} variant="scrollable" scrollButtons="auto" aria-label="rubric tabs"> <Tab label="Overall Settings" id="tab-0" aria-controls="panel-0" sx={{ textTransform: 'none', fontWeight: tabValue === 0 ? 'bold' : 'normal' }} /> {currentSubRubrics.map((sr, i) => { const qNum = sr.question_index + 1; const match = Math.abs(calculateTotalPoints(sr) - (sr.max_points ?? 0)) < 0.001; return (<Tab key={`tab-${qNum}`} id={`tab-${i+1}`} aria-controls={`panel-${i+1}`} label={<Box sx={{ display: 'flex', alignItems: 'center' }}>Q{qNum}{!match && <Tooltip title="Points Mismatch"><WarningIcon color="warning" sx={{ ml: 0.5, fontSize: '1.1rem' }} /></Tooltip>}</Box>} sx={{ textTransform: 'none', fontWeight: tabValue === (i + 1) ? 'bold' : 'normal' }} />); })} </Tabs> </Paper>

        <Box sx={{ mt: 0 }}>
            <TabPanel value={tabValue} index={0}> <RubricSection variant="outlined"> <Typography variant="h6" gutterBottom>Overall Settings</Typography> <Grid container spacing={3}> <Grid item xs={12} md={7}> <TextField label="Overall Guidelines" multiline minRows={4} fullWidth value={rubric.overall_instructor_guidelines ?? ''} onChange={(e) => handleRubricSettingChange('overall_instructor_guidelines', e.target.value || null)} disabled={!editMode || isSaving} variant="outlined" margin="none" helperText="Optional overall grading instructions." /> </Grid> <Grid item xs={12} md={5}> <Typography variant="subtitle1" gutterBottom>AI Grading Flags</Typography> <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>Instruct AI grader behavior.</Typography> <FormGroup> {GRADING_FLAGS_CONFIG.map(f => (<Tooltip key={f.value} title={f.description}><FormControlLabel control={<Switch checked={(rubric.grading_flags || []).includes(f.value)} onChange={() => handleGradingFlagToggle(f.value)} disabled={!editMode || isSaving} size="small" />} label={f.label} sx={{ mr: 2, mb: 0.5 }} /></Tooltip>))} </FormGroup> </Grid> </Grid> </RubricSection> </TabPanel>
            {currentSubRubrics.map((sr, i) => { const qNum = sr.question_index + 1; const totalPts = calculateTotalPoints(sr); const maxPts = sr.max_points ?? 0; const ptsMatch = Math.abs(totalPts - maxPts) < 0.001; return (
                <TabPanel key={`panel-${qNum}`} value={tabValue} index={i + 1}>
                    <RubricSection variant="outlined"> <Typography variant="h6" gutterBottom>Question {qNum} Settings</Typography> <Paper variant="outlined" sx={{ p: 2, bgcolor: 'grey.100', mb: 3 }}><Typography sx={{ whiteSpace: 'pre-wrap', fontStyle: 'italic' }}>{getQuestionText(sr.question_index)}</Typography></Paper> <Grid container spacing={2}> <Grid item xs={12} md={8}> <TextField label={`Q${qNum} Guideline`} multiline minRows={3} fullWidth value={sr.instructor_guideline ?? ''} onChange={(e) => handleSubRubricChange(sr.question_index, 'instructor_guideline', e.target.value || null)} disabled={!editMode || isSaving} variant="outlined" margin="none" helperText="Optional guideline for this question."/> </Grid> <Grid item xs={12} md={4}> <TextField label="Max Points" type="number" fullWidth required value={maxPts} onChange={(e) => handleSubRubricChange(sr.question_index, 'max_points', parseFloat(e.target.value) || 0)} disabled={!editMode || isSaving} InputProps={{ inputProps: { min: 0, step: 0.1 } }} variant="outlined" margin="none" error={editMode && !ptsMatch} helperText={editMode && !ptsMatch ? `≠ Criteria Sum (${totalPts.toFixed(1)})` : "Points for this question."} /> </Grid> </Grid> </RubricSection>
                    <RubricSection variant="outlined"> <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}> <Typography variant="h6">Grading Criteria</Typography> {editMode && <Button variant="outlined" size="small" startIcon={<AddIcon />} onClick={() => openCriteriaDialog()} disabled={isSaving}>Add Criteria</Button>} </Box> {(!sr.grading_criteria || sr.grading_criteria.length === 0) ? (<Box sx={{ textAlign: 'center', py: 3, border: `1px dashed ${theme.palette.divider}` }}> <CriteriaIcon sx={{ fontSize: 40, color: 'text.disabled', mb: 1 }} /> <Typography color="text.secondary">No criteria defined.</Typography> {editMode && <Button variant="text" startIcon={<AddIcon />} onClick={() => openCriteriaDialog()} sx={{ mt: 1 }} disabled={isSaving}>Add First</Button>} </Box>) : (<> {sr.grading_criteria.map((c, cIdx) => (<CriteriaCard key={`crit-${qNum}-${cIdx}`} variant="outlined"> <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1 }}> <Box sx={{ flexGrow: 1, mr: 1, overflow: 'hidden' }}> <Typography variant="subtitle1" fontWeight="medium" noWrap title={c.criteria_id}>{c.criteria_id || '(No Title)'}</Typography> <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, whiteSpace: 'pre-wrap' }}>{c.criteria || '(No Description)'}</Typography> </Box> <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', flexShrink: 0 }}> <Chip label={`${c.points ?? 0} pts`} size="small" variant="outlined" sx={{ mb: editMode ? 0.5 : 0 }} /> {editMode && <Box sx={{ display: 'flex' }}> <Tooltip title="Edit"><span><IconButton color="primary" size="small" onClick={() => openCriteriaDialog(cIdx)} disabled={isSaving} sx={{ p: 0.5 }}><EditIcon fontSize="small" /></IconButton></span></Tooltip> <Tooltip title="Delete"><span><IconButton color="error" size="small" onClick={() => openDeleteCriteriaDialog(cIdx)} disabled={isSaving} sx={{ p: 0.5 }}><DeleteIcon fontSize="small" /></IconButton></span></Tooltip> </Box>} </Box> </Box> </CriteriaCard>))} <Divider sx={{ my: 2 }} /> <Box sx={{ display: 'flex', justifyContent: 'space-between' }}> <Typography variant="body1" fontWeight="bold">Criteria Total:</Typography> <Typography variant="body1" fontWeight="bold" color={ptsMatch ? 'text.primary' : 'error.main'}>{totalPts.toFixed(1)} / {maxPts.toFixed(1)} pts</Typography> </Box> {!ptsMatch && <Typography variant="caption" color="error.main" display="block" textAlign="right" sx={{ mt: 0.5 }}>Sum doesn't match Max Points!</Typography>} </>)} </RubricSection>
                </TabPanel>
            );})}
        </Box>
      </>
    );
  };


  // --- Main Component Return ---
  return (
    <Box sx={{ p: { xs: 1, sm: 2, md: 3 }, maxWidth: 1200, mx: 'auto' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        {courseId && semester ? <Tooltip title="Back to Course"><IconButton onClick={() => router.push(`/course/${courseId}?semester=${semester}`)} sx={{ mr: 1 }}><ArrowBackIcon /></IconButton></Tooltip> : <IconButton sx={{ mr: 1 }} disabled><ArrowBackIcon /></IconButton>}
        <Typography variant="h4" component="h1">Rubric Management</Typography>
        {courseId && <Chip label={courseId.toUpperCase()} size="small" sx={{ ml: 1.5 }} />} {semester && <Chip label={semester} size="small" variant="outlined" sx={{ ml: 0.5 }} />}
      </Box>
      {error && !loadingAssignments && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}
      {renderAssignmentSelection()}
      <Divider sx={{ my: 3 }} />
      {renderRubricContent()}

      {/* --- DIALOGS --- */}
      <Dialog open={criteriaDialogOpen} onClose={() => setCriteriaDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editingCriteriaIndex !== null ? 'Edit' : 'Add'} Grading Criteria {typeof currentQuestionIndex === 'number' ? `for Q${currentQuestionIndex + 1}` : ''}</DialogTitle>
        <DialogContent> <TextField autoFocus label="Criteria Title/ID" fullWidth value={criteriaFormData.criteria_id} onChange={(e) => setCriteriaFormData(prev => ({ ...prev, criteria_id: e.target.value }))} margin="dense" required error={!criteriaFormData.criteria_id?.trim()} helperText={!criteriaFormData.criteria_id?.trim() ? "Required" : ""} /> <TextField label="Criteria Description" fullWidth multiline rows={3} value={criteriaFormData.criteria} onChange={(e) => setCriteriaFormData(prev => ({ ...prev, criteria: e.target.value }))} margin="dense" required error={!criteriaFormData.criteria?.trim()} helperText={!criteriaFormData.criteria?.trim() ? "Required" : ""} /> <TextField label="Points" type="number" fullWidth value={criteriaFormData.points} onChange={(e) => setCriteriaFormData(prev => ({ ...prev, points: e.target.value }))} margin="dense" required InputProps={{ inputProps: { min: 0, step: 0.1 }, endAdornment: <InputAdornment position="end">pts</InputAdornment> }} error={!(parseFloat(String(criteriaFormData.points).trim()) >= 0 && String(criteriaFormData.points).trim() !== '')} helperText={!(parseFloat(String(criteriaFormData.points).trim()) >= 0 && String(criteriaFormData.points).trim() !== '') ? "Must be >= 0" : ""} /> </DialogContent>
        <DialogActions> <Button onClick={() => setCriteriaDialogOpen(false)}>Cancel</Button> <Button onClick={handleSaveCriteria} variant="contained" disabled={!criteriaFormData.criteria_id?.trim() || !criteriaFormData.criteria?.trim() || !(parseFloat(String(criteriaFormData.points).trim()) >= 0 && String(criteriaFormData.points).trim() !== '')}> {editingCriteriaIndex !== null ? 'Save Changes' : 'Add Criteria'} </Button> </DialogActions>
      </Dialog>
      <ConfirmationDialog open={deleteCriteriaDialogOpen} onClose={() => setDeleteCriteriaDialogOpen(false)} title="Delete Grading Criteria?" description={`Delete criteria "${criteriaToDelete?.text ?? 'this criteria'}"? Cannot be undone.`} confirmText="Delete" confirmColor="error" onConfirm={handleDeleteCriteria}/>
      <Dialog open={aiInstructionsDialogOpen} onClose={() => !loadingAI && setAiInstructionsDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle><Box sx={{ display: 'flex', alignItems: 'center' }}><LightbulbIcon sx={{ mr: 1 }} color="warning" /> AI Rubric Suggestions</Box></DialogTitle>
        <DialogContent> <Typography variant="body2" paragraph>AI will analyze assignment ({selectedAssignment?.assignment_id}, {selectedAssignment?.questions?.length ?? 0} Qs){rubric && !rubricNotFound ? ' & current rubric' : ''} to suggest improvements. Add optional instructions.</Typography> <TextField label="Instructions for AI (Optional)" fullWidth multiline rows={4} value={aiInstructions} onChange={(e) => setAiInstructions(e.target.value)} margin="dense" placeholder="e.g., Focus on reasoning..." disabled={loadingAI} /> </DialogContent>
        <DialogActions> <Button onClick={() => setAiInstructionsDialogOpen(false)} disabled={loadingAI}>Cancel</Button> <Button onClick={getAIRubricSuggestions} variant="contained" disabled={loadingAI || !selectedAssignment} startIcon={loadingAI ? <CircularProgress size={20}/> : <LightbulbIcon />}> {loadingAI ? 'Generating...' : 'Get Suggestions'} </Button> </DialogActions>
      </Dialog>
      <Snackbar open={alertOpen} autoHideDuration={6000} onClose={(evt, reason) => { if(reason === 'clickaway') return; setAlertOpen(false);}} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
          <Alert onClose={() => setAlertOpen(false)} severity={alertSeverity} variant="filled" sx={{ width: '100%' }}>{alertMessage}</Alert>
      </Snackbar>
    </Box>
  );
}