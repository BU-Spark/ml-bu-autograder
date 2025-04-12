/**
 * Rubric Management Page for BU MET Autograder
 * Create, edit, and apply grading rubrics
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link'; // Added Link
import {
  Alert,
  Avatar, // Added
  Box,
  Button,
  Card,
  CardActionArea, // Added
  CardActions, // Added
  CardContent,
  Chip,
  CircularProgress, // Added
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  FormControlLabel,
  FormGroup, // Keep for Switches
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
  HelpOutline as HelpIcon, // Changed icon
  Info as InfoIcon, // Added
  PlaylistAddCheck as CriteriaIcon, // Added
} from '@mui/icons-material';
// Assuming api.js is correctly imported
import { assignmentService, rubricService } from '../../../api'; // Adjust path if needed
import CardSkeleton from '../../../components/CardSkeleton'; // Assuming exists
import AISuggestionCard from '../../../components/AISuggestionCard'; // Assuming exists
import ConfirmationDialog from '../../../components/ConfirmationDialog'; // Assuming exists

// Styled components
const AssignmentSelectionCard = styled(Card)(({ theme, selected }) => ({ // Renamed and added selected prop
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
  border: `1px solid ${theme.palette.divider}`, // Add subtle border
}));

const CriteriaCard = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(2),
  marginBottom: theme.spacing(2),
  borderLeft: `4px solid ${theme.palette.primary.light}`, // Lighter primary border
  backgroundColor: theme.palette.background.default, // Use default background
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
      {/* Render only if value matches index, avoid mounting inactive tabs */}
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
};

// Grading flags definition (can be moved to config or constants file)
const GRADING_FLAGS_CONFIG = [
  { value: 'IGNORE_SPELLINGS', label: 'Ignore Spelling', description: 'AI ignores minor spelling mistakes during grading.' },
  { value: 'IGNORE_GRAMMAR', label: 'Ignore Grammar', description: 'AI ignores minor grammatical errors during grading.' },
  { value: 'ORIGINALITY', label: 'Reward Originality', description: 'AI rewards originality and may deduct for unoriginal ideas/plagiarism (experimental).' },
  { value: 'IGNORE_FORMATTING', label: 'Ignore Formatting', description: 'AI ignores formatting inconsistencies (e.g., spacing, list styles) during grading.' },
];

// Main component
export default function RubricManagement() {
  const router = useRouter();
  // Ensure IDs are treated correctly (string/number)
  const { id: courseId, semester, assignmentId: assignmentIdParam } = router.query;
  const selectedAssignmentId = assignmentIdParam ? parseInt(assignmentIdParam, 10) : null;

  // State for assignments and rubrics
  const [assignments, setAssignments] = useState([]);
  const [selectedAssignment, setSelectedAssignment] = useState(null); // Holds full Assignment object including questions
  const [rubric, setRubric] = useState(null); // Holds the Rubric object being viewed/edited
  const [aiRubricSuggestion, setAiRubricSuggestion] = useState(null); // Separate state for AI suggestion

  // Loading states
  const [loadingAssignments, setLoadingAssignments] = useState(true);
  const [loadingRubric, setLoadingRubric] = useState(false); // Specific loading for rubric
  const [loadingAI, setLoadingAI] = useState(false);
  const [isSaving, setIsSaving] = useState(false); // Specific state for save operation
  const [error, setError] = useState(null); // General page errors

  // State for UI control
  const [tabValue, setTabValue] = useState(0); // 0 = Overall, 1+ = Question index + 1
  const [editMode, setEditMode] = useState(false); // Is the rubric editable?
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0); // Tracks which *question index* corresponds to the active tab

  // State for dialog controls
  const [criteriaDialogOpen, setCriteriaDialogOpen] = useState(false);
  const [editingCriteriaIndex, setEditingCriteriaIndex] = useState(null); // null for add, criteria list index for edit
  const [deleteCriteriaDialogOpen, setDeleteCriteriaDialogOpen] = useState(false);
  const [aiInstructionsDialogOpen, setAiInstructionsDialogOpen] = useState(false);

  // State for form data
  const [criteriaFormData, setCriteriaFormData] = useState({ criteria_id: '', criteria: '', points: 0 }); // For Add/Edit Criteria Dialog
  const [criteriaToDelete, setCriteriaToDelete] = useState(null); // { subRubricArrayIndex, criteriaArrayIndex } - USE ARRAY INDICES
  const [aiInstructions, setAiInstructions] = useState(''); // For AI Dialog

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

  // Creates an empty rubric structure, now ensuring semester/courseId are included
  const createEmptyRubric = useCallback((assignment) => {
    // Requires the full assignment object with questions
    if (!assignment || !semester || !courseId) {
        console.error("Cannot create empty rubric: missing assignment, semester, or courseId");
        return null;
    }
    const subRubrics = (assignment.questions || []).map((question, index) => ({
        question_index: question.question_index, // Use the actual index from the question object
        max_points: 10, // Default
        instructor_guideline: '',
        leniency: null, // Default to null (use global)
        grading_criteria: [],
    })).sort((a, b) => a.question_index - b.question_index); // Ensure sorted by question index

    return {
        semester: semester, // Include semester
        course_id: courseId, // Include courseId
        assignment_id: assignment.assignment_id, // Include assignmentId
        grading_flags: [],
        leniency: 3, // Default global leniency (1-5)
        overall_instructor_guidelines: '',
        sub_rubrics: subRubrics,
    };
  }, [semester, courseId]); // Dependencies


  // --- Data Fetching ---

  // Fetches rubric, creating an empty one if not found
  const fetchRubric = useCallback(async (assignment) => {
    if (!semester || !courseId || !assignment?.assignment_id) {
        console.warn("Cannot fetch rubric: Missing semester, courseId, or assignmentId.");
        setRubric(createEmptyRubric(assignment)); // Create empty structure if assignment provided but IDs missing
        setTabValue(0);
        setLoadingRubric(false);
        return;
    }
    setLoadingRubric(true);
    setError(null); // Clear previous errors
    try {
      const rubricData = await rubricService.getRubric(
          semester, // <<< Pass semester
          courseId, // <<< Pass courseId
          assignment.assignment_id
        );
      // Ensure sub_rubrics match the number of questions in the assignment
       const completeRubric = { ...createEmptyRubric(assignment), ...rubricData }; // Start with empty, merge fetched
       // Make sure all questions have a sub-rubric entry
       assignment.questions?.forEach(q => {
           if (!completeRubric.sub_rubrics.some(sr => sr.question_index === q.question_index)) {
               completeRubric.sub_rubrics.push({
                   question_index: q.question_index, max_points: 10, leniency: null, instructor_guideline: '', grading_criteria: []
               });
           }
       });
       // Remove sub-rubrics for questions that no longer exist
        completeRubric.sub_rubrics = completeRubric.sub_rubrics.filter(sr =>
            assignment.questions?.some(q => q.question_index === sr.question_index)
        );
       completeRubric.sub_rubrics.sort((a, b) => a.question_index - b.question_index); // Sort by index

      setRubric(completeRubric);
      setAiRubricSuggestion(null); // Clear previous AI suggestions

      // Set default tab/sub-rubric index
      setTabValue(0); // Default to overall guidelines initially
      setCurrentQuestionIndex(completeRubric.sub_rubrics[0]?.question_index ?? 0); // Use index of first sub-rubric

    } catch (err) {
      console.error('Error fetching rubric:', err);
       if (err.message?.includes('404') || err.message?.toLowerCase().includes('not found')) {
          console.log(`No rubric found for assignment ${assignment.assignment_id}. Creating empty structure.`);
          setRubric(createEmptyRubric(assignment)); // Use the passed assignment object
          setTabValue(0);
       } else {
          const errorMsg = err.message || 'Failed to load rubric';
          setError(errorMsg);
          showAlert(errorMsg, 'error');
          setRubric(null);
       }
    } finally {
       setLoadingRubric(false);
    }
  }, [semester, courseId, createEmptyRubric, showAlert]); // Dependencies


  // Fetch assignments list and load rubric for selected/first assignment
  useEffect(() => {
    const fetchAssignmentsAndRubric = async () => {
      if (!courseId || !semester) {
        setLoadingAssignments(false); return;
      }
      setLoadingAssignments(true); setLoadingRubric(true); setError(null); setRubric(null); setSelectedAssignment(null);
      try {
        // Fetch assignments *with questions* needed for creating empty rubric
        const assignmentsData = await assignmentService.getAssignments(courseId, semester, true); // include_questions = true
        setAssignments(assignmentsData || []);

        // Determine which assignment to initially select and fetch rubric for
        const currentAssignmentId = selectedAssignmentId ?? assignmentsData?.[0]?.assignment_id; // Use URL ID or first assignment ID

        if (currentAssignmentId) {
          const assignment = assignmentsData.find(a => a.assignment_id === currentAssignmentId);
          if (assignment) {
             setSelectedAssignment(assignment); // Set the selected assignment object
             await fetchRubric(assignment); // Pass the assignment object to fetchRubric
          } else {
              // Assignment ID from URL not found in list
              setError(`Assignment with ID ${selectedAssignmentId} not found in this course/semester.`);
              showAlert(`Assignment with ID ${selectedAssignmentId} not found.`, 'error');
          }
        } else {
             // No assignments exist for this course
             console.log("No assignments found, cannot load or create rubric yet.");
        }

      } catch (err) {
        console.error('Error fetching initial data:', err);
        const errorMsg = err.message || 'Failed to load assignments or rubric';
        setError(errorMsg);
        showAlert(errorMsg, 'error');
      } finally {
        setLoadingAssignments(false);
        // setLoadingRubric is handled by fetchRubric
      }
    };
    fetchAssignmentsAndRubric();
  }, [courseId, semester, selectedAssignmentId, fetchRubric, showAlert]); // Dependencies


  // --- Event Handlers ---

  // Handle selecting an assignment card
  const handleSelectAssignment = useCallback((assignment) => {
    if (!assignment || assignment.assignment_id === selectedAssignment?.assignment_id) return;
    // Update URL, which will trigger the main useEffect to fetch data for the new ID
    router.push(`/course/${courseId}/rubrics?semester=${semester}&assignmentId=${assignment.assignment_id}`, undefined, { shallow: true });
    // Reset UI states immediately for better feedback
    setTabValue(0);
    setEditMode(false);
    setAiRubricSuggestion(null);
    // Let the main useEffect handle setting selectedAssignment and fetching the rubric
  }, [courseId, semester, selectedAssignment?.assignment_id, router]);


  // Get AI rubric suggestions (now includes semester, courseId)
  const getAIRubricSuggestions = useCallback(async () => {
    if (!selectedAssignment || !semester || !courseId) {
        showAlert("Select an assignment first.", "warning");
        return;
    }
    setLoadingAI(true);
    try {
      const aiRubricData = await rubricService.getAIRubric(
        semester, // <<< Pass semester
        courseId, // <<< Pass courseId
        selectedAssignment.assignment_id,
        aiInstructions || null // Pass instructions if provided
      );
      setAiRubricSuggestion(aiRubricData); // Store suggestion separately
      setAiInstructionsDialogOpen(false); // Close instruction dialog
      showAlert('AI rubric suggestions generated successfully!');
    } catch (err) {
      console.error('Error getting AI rubric suggestions:', err);
      showAlert(err.message || 'Failed to get AI suggestions', 'error');
    } finally {
      setLoadingAI(false);
    }
  }, [selectedAssignment, semester, courseId, aiInstructions, showAlert]); // Dependencies


  // Apply AI suggestions to the main rubric state
  const applyAIRubricSuggestions = useCallback(() => {
    if (!aiRubricSuggestion) return;
    // Make sure the core identifiers match before applying
    if (aiRubricSuggestion.semester === semester && aiRubricSuggestion.course_id === courseId && aiRubricSuggestion.assignment_id === selectedAssignment?.assignment_id) {
        setRubric(aiRubricSuggestion); // Overwrite current rubric state with AI version
        setAiRubricSuggestion(null); // Clear suggestion after applying
        setEditMode(true); // Enter edit mode after applying AI suggestions
        showAlert('AI suggestions applied. Review and save changes.', 'info');
    } else {
         showAlert('Cannot apply suggestions: Identifiers do not match current selection.', 'error');
    }
  }, [aiRubricSuggestion, semester, courseId, selectedAssignment?.assignment_id, showAlert]);


  // Save rubric changes (PUT request)
  const saveRubric = useCallback(async () => {
    if (!rubric || !rubric.semester || !rubric.course_id || !rubric.assignment_id) {
        showAlert("Cannot save rubric: Missing required identifiers.", "error");
        return;
    }
    // Optional: Validate point totals match max_points per sub-rubric before saving
    let pointsMismatch = false;
    (rubric.sub_rubrics || []).forEach(sr => {
        if (calculateTotalPoints(sr) !== (sr.max_points ?? 0)) {
            pointsMismatch = true;
        }
    });
    if (pointsMismatch) {
        showAlert("Warning: Total points for criteria may not match maximum points for some questions.", "warning");
        // Decide whether to proceed or force user to fix points first
    }

    setIsSaving(true);
    try {
      // Use createRubric which performs a PUT (create or replace)
      // The 'rubric' state object must contain semester, course_id, assignment_id
      await rubricService.createRubric(rubric);
      setEditMode(false); // Exit edit mode on successful save
      showAlert('Rubric saved successfully', 'success');
      // Re-fetch after save to get the definitive state from the server
      if(selectedAssignment) {
          await fetchRubric(selectedAssignment);
      }
    } catch (err) {
      console.error('Error saving rubric:', err);
      showAlert(err.message || 'Failed to save rubric', 'error');
    } finally {
        setIsSaving(false);
    }
  }, [rubric, selectedAssignment, fetchRubric, showAlert]); // Dependencies


  // --- Input Change Handlers (Immutable Updates) ---

  const handleRubricSettingChange = useCallback((field, value) => {
      setRubric(prev => prev ? { ...prev, [field]: value } : null);
  }, []);

  const handleSubRubricChange = useCallback((questionIndex, field, value) => {
      setRubric(prev => {
          if (!prev) return null;
          const newSubRubrics = prev.sub_rubrics.map(sr =>
              sr.question_index === questionIndex ? { ...sr, [field]: value } : sr
          );
          return { ...prev, sub_rubrics: newSubRubrics };
      });
  }, []);

   const handleGradingFlagToggle = useCallback((flagValue) => {
        setRubric(prev => {
            if (!prev) return null;
            const currentFlags = prev.grading_flags || [];
            const updatedFlags = currentFlags.includes(flagValue)
                ? currentFlags.filter(f => f !== flagValue)
                : [...currentFlags, flagValue];
            return { ...prev, grading_flags: updatedFlags };
        });
    }, []);

  // Handle tab change
  const handleTabChange = useCallback((event, newValue) => {
    setTabValue(newValue);
    // Update currentQuestionIndex based on the new tab value
    // Assumes tab index 0 is "Overall", 1 is first question, etc.
    if (newValue > 0 && rubric?.sub_rubrics?.[newValue - 1]) {
        setCurrentQuestionIndex(rubric.sub_rubrics[newValue - 1].question_index);
    }
    // If switching back to Overall (index 0), maybe reset currentQuestionIndex or leave it?
    // Leaving it might be useful if they quickly switch back.
  }, [rubric]); // Dependency on rubric to access sub_rubrics


  // --- Criteria Management ---
  const openCriteriaDialog = (criteriaIdx = null) => {
      // Find the sub-rubric array index based on the *question_index* being viewed
       const subRubricArrayIndex = rubric?.sub_rubrics.findIndex(sr => sr.question_index === currentQuestionIndex);

       if (subRubricArrayIndex === -1 || subRubricArrayIndex === undefined) {
            showAlert("Cannot add/edit criteria: Current sub-rubric not found.", "error");
            return;
       }

      if (criteriaIdx !== null && rubric) {
          // Editing existing criteria
          const criteria = rubric.sub_rubrics[subRubricArrayIndex]?.grading_criteria?.[criteriaIdx];
          if (criteria) {
              setCriteriaFormData({ // Populate form
                  criteria_id: criteria.criteria_id || '',
                  criteria: criteria.criteria || '',
                  points: criteria.points ?? 0,
              });
              setEditingCriteriaIndex(criteriaIdx); // Store the *array index* being edited
          } else { return; } // Criteria not found at index
      } else {
          // Adding new criteria
          setCriteriaFormData({ criteria_id: '', criteria: '', points: 0 }); // Reset form
          setEditingCriteriaIndex(null); // Ensure null for add mode
      }
      setCriteriaDialogOpen(true);
  };

  // Handles save for both Add and Edit criteria
  const handleSaveCriteria = () => {
      if (!rubric || criteriaFormData.points === null || criteriaFormData.points < 0 || !criteriaFormData.criteria_id?.trim() || !criteriaFormData.criteria?.trim()) {
          showAlert('Criteria Title, Description, and non-negative Points are required.', 'warning');
          return;
      }

      const pointsValue = parseFloat(criteriaFormData.points);
      if (isNaN(pointsValue)) {
           showAlert('Points must be a valid number.', 'warning');
           return;
      }

      const newOrUpdatedCriteria = {
          criteria_id: criteriaFormData.criteria_id.trim(),
          criteria: criteriaFormData.criteria.trim(),
          points: pointsValue,
      };

      // Find the index of the sub-rubric array corresponding to the question being viewed
      const targetSubRubricArrayIndex = rubric.sub_rubrics.findIndex(sr => sr.question_index === currentQuestionIndex);
      if (targetSubRubricArrayIndex === -1) {
          showAlert("Cannot save criteria: Current sub-rubric not found.", "error");
          return;
      }

      setRubric(prev => {
           if (!prev) return null;
          const newSubRubrics = [...prev.sub_rubrics]; // Copy sub_rubrics array
          const targetSubRubric = { ...newSubRubrics[targetSubRubricArrayIndex] }; // Copy target sub-rubric

          let updatedCriteriaList;
          if (editingCriteriaIndex !== null) {
              // --- Update existing ---
              updatedCriteriaList = [...(targetSubRubric.grading_criteria || [])]; // Copy criteria list
              if (editingCriteriaIndex < updatedCriteriaList.length) {
                  updatedCriteriaList[editingCriteriaIndex] = newOrUpdatedCriteria; // Update in place
              } else {
                  console.error("Editing index out of bounds!"); // Should not happen
                  return prev; // Return previous state on error
              }
          } else {
              // --- Add new ---
              updatedCriteriaList = [...(targetSubRubric.grading_criteria || []), newOrUpdatedCriteria]; // Append new
          }

          targetSubRubric.grading_criteria = updatedCriteriaList; // Assign updated list back
          newSubRubrics[targetSubRubricArrayIndex] = targetSubRubric; // Put updated sub-rubric back into array
          return { ...prev, sub_rubrics: newSubRubrics }; // Return updated rubric state
      });

      setCriteriaDialogOpen(false); // Close dialog after saving
  };

  // Opens the delete confirmation dialog
   const openDeleteCriteriaDialog = (criteriaArrayIndex) => {
       // Store the *array index* of the criteria within the currently viewed sub-rubric
       if (criteriaArrayIndex !== null) {
            setCriteriaToDelete({ criteriaArrayIndex }); // Store the index to delete
            setDeleteCriteriaDialogOpen(true);
       }
   };

  // Handles the actual deletion after confirmation
  const handleDeleteCriteria = () => {
    if (!rubric || !editMode || criteriaToDelete === null) return;
    const { criteriaArrayIndex } = criteriaToDelete; // This is the ARRAY index

     // Find the index of the sub-rubric array corresponding to the question being viewed
    const targetSubRubricArrayIndex = rubric.sub_rubrics.findIndex(sr => sr.question_index === currentQuestionIndex);
    if (targetSubRubricArrayIndex === -1) {
        showAlert("Cannot delete criteria: Current sub-rubric not found.", "error");
        setDeleteCriteriaDialogOpen(false);
        setCriteriaToDelete(null);
        return;
    }

    setRubric(prev => {
        if (!prev) return null;
        const newSubRubrics = [...prev.sub_rubrics];
        const targetSubRubric = { ...newSubRubrics[targetSubRubricArrayIndex] };

        if (targetSubRubric.grading_criteria && criteriaArrayIndex < targetSubRubric.grading_criteria.length) {
             // Create new list excluding the item at criteriaArrayIndex
             targetSubRubric.grading_criteria = [
                 ...targetSubRubric.grading_criteria.slice(0, criteriaArrayIndex),
                 ...targetSubRubric.grading_criteria.slice(criteriaArrayIndex + 1)
             ];
             newSubRubrics[targetSubRubricArrayIndex] = targetSubRubric;
             return { ...prev, sub_rubrics: newSubRubrics };
        }
        return prev; // Return previous state if indices were invalid
    });

    setDeleteCriteriaDialogOpen(false);
    setCriteriaToDelete(null);
  };


  // --- Calculation Helpers ---
  const getQuestionText = useCallback((questionIndex) => {
    const question = selectedAssignment?.questions?.find(q => q.question_index === questionIndex);
    return question ? question.question_text : `Question Text (Index ${questionIndex}) Not Found`;
  }, [selectedAssignment]);

  const calculateTotalPoints = useCallback((subRubric) => {
    return subRubric?.grading_criteria?.reduce((sum, c) => sum + (parseFloat(c.points) || 0), 0) ?? 0;
  }, []); // No dependency needed as subRubric is passed in


  // --- Render Functions ---

  const renderAssignmentSelection = () => {
    if (loadingAssignments) {
      return <Typography sx={{ mb: 3, fontStyle: 'italic' }}>Loading assignments...</Typography>;
    }
    if (!assignments || assignments.length === 0) {
      return (
        <Alert severity="warning" sx={{ mb: 3 }}>
          No assignments found for this course. <Link href={`/course/${courseId}/assignments?semester=${semester}`}>Create an assignment</Link> first.
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
          disabled={loadingAssignments || loadingRubric || isSaving || editMode} // Disable if editing rubric
        >
          {assignments.map((assignment) => (
            <MenuItem key={assignment.assignment_id} value={assignment.assignment_id}>
              {assignment.assignment_title || `Assignment ID: ${assignment.assignment_id}`} ({assignment.questions?.length ?? 0} Qs)
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    );
  };

  const renderRubricContent = () => {
    if (loadingRubric) {
         return (
            <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
              <CircularProgress /> <Typography sx={{ ml: 2 }}>Loading rubric...</Typography>
            </Box>
        );
    }
    if (!selectedAssignment) {
         return <Alert severity="info">Please select an assignment above.</Alert>;
    }
     if (!rubric) {
         return <Alert severity="warning">Could not load or create rubric structure. Try selecting the assignment again.</Alert>;
    }

    // Find the currently selected sub-rubric object based on currentQuestionIndex
    const activeSubRubricData = rubric.sub_rubrics.find(sr => sr.question_index === currentQuestionIndex);
    const activeSubRubricArrayIndex = rubric.sub_rubrics.findIndex(sr => sr.question_index === currentQuestionIndex);


    return (
      <>
        {/* Header Actions */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 1 }}>
          <Typography variant="h5">
            Rubric for "{selectedAssignment.assignment_title || 'Selected Assignment'}"
          </Typography>
          <Box>
            {editMode ? (
              <>
                <Button variant="contained" color="primary" startIcon={isSaving ? <CircularProgress size={20}/> :<SaveIcon />} onClick={saveRubric} sx={{ mr: 1 }} disabled={isSaving}>
                  Save Rubric
                </Button>
                <Button variant="outlined" onClick={() => { setEditMode(false); fetchRubric(selectedAssignment); /* Refetch on cancel */ }} disabled={isSaving}>
                  Cancel Edit
                </Button>
              </>
            ) : (
              <>
                <Button variant="outlined" startIcon={<LightbulbIcon />} onClick={() => setAiInstructionsDialogOpen(true)} sx={{ mr: 1 }} disabled={loadingAI || isSaving}>
                  {loadingAI ? 'Generating...' : 'AI Suggestions'}
                </Button>
                <Button variant="contained" startIcon={<EditIcon />} onClick={() => setEditMode(true)} disabled={isSaving}>
                  Edit Rubric
                </Button>
              </>
            )}
          </Box>
        </Box>

        {/* AI Suggestion Card (If available and not editing) */}
        {aiRubricSuggestion && !editMode && (
            <AISuggestionCard
            rubric={aiRubricSuggestion}
            onApply={applyAIRubricSuggestions}
            onDismiss={() => setAiRubricSuggestion(null)}
            sx={{ mb: 3 }}
            />
        )}

        {/* Tabs */}
        <Paper sx={{ mb: 3, borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={handleTabChange} variant="scrollable" scrollButtons="auto" aria-label="rubric sections">
            <Tab label="Overall Settings" id="rubric-tab-0" aria-controls="rubric-tabpanel-0" />
            {(rubric.sub_rubrics || []).map((subRubric, index) => (
              <Tab
                key={`question-tab-${subRubric.question_index}`}
                label={
                    <Box component="span" sx={{ display: 'flex', alignItems: 'center' }}>
                       Q{subRubric.question_index + 1}
                       {calculateTotalPoints(subRubric) !== (subRubric.max_points ?? 0) && editMode && (
                         <Tooltip title={`Warning: Criteria points (${calculateTotalPoints(subRubric)}) do not match max points (${subRubric.max_points ?? 0})`}>
                           <InfoIcon color="warning" sx={{ ml: 1, fontSize: '1rem' }} />
                         </Tooltip>
                       )}
                    </Box>
                }
                id={`rubric-tab-${index + 1}`}
                aria-controls={`rubric-tabpanel-${index + 1}`}
              />
            ))}
          </Tabs>
        </Paper>

        {/* --- Tab Panels --- */}

        {/* Overall Guidelines Tab Panel */}
        <TabPanel value={tabValue} index={0}>
          <RubricSection variant="outlined">
            <Typography variant="h6" gutterBottom>General Rubric Settings</Typography>
            <Grid container spacing={3} alignItems="center">
              {/* Guidelines */}
              <Grid item xs={12} md={6}>
                <TextField label="Overall Instructor Guidelines" multiline rows={4} fullWidth
                           value={rubric.overall_instructor_guidelines || ''}
                           onChange={(e) => handleRubricSettingChange('overall_instructor_guidelines', e.target.value)}
                           disabled={!editMode || isSaving} variant="outlined" margin="dense"
                           placeholder="General grading instructions for all questions (optional)"/>
              </Grid>
              {/* Leniency */}
              <Grid item xs={12} md={6}>
                <Typography gutterBottom id="global-leniency-label">Global Leniency</Typography>
                <Tooltip title="Sets the default strictness for grading all questions unless overridden below. 1=Strict, 5=Lenient.">
                      <Slider value={rubric.leniency ?? 3} // Default to 3 if null
                              min={1} max={5} step={1}
                              marks={[{ value: 1, label: '1' }, { value: 3, label: '3' }, { value: 5, label: '5' }]}
                              valueLabelDisplay="auto"
                              onChange={(e, value) => handleRubricSettingChange('leniency', value)}
                              disabled={!editMode || isSaving} sx={{mt: 2, mb: 1, px: 1 }}
                              aria-labelledby="global-leniency-label"/>
                 </Tooltip>
                 <Typography variant="caption" color="text.secondary" display="block">Affects grading strictness (higher is more lenient).</Typography>
              </Grid>
              {/* Grading Flags */}
              <Grid item xs={12}>
                <Typography variant="subtitle1" gutterBottom>Grading Flags</Typography>
                 <Typography variant="caption" color="text.secondary" display="block" sx={{mb: 1}}>Instruct the AI grader on specific behaviours.</Typography>
                <FormGroup row>
                  {GRADING_FLAGS_CONFIG.map((flag) => (
                    <Tooltip key={flag.value} title={flag.description} arrow placement="top">
                      <FormControlLabel
                        control={<Switch checked={(rubric.grading_flags || []).includes(flag.value)}
                                         onChange={() => handleGradingFlagToggle(flag.value)}
                                         disabled={!editMode || isSaving} color="primary" size="small"/>} // Use small switch
                        label={flag.label} sx={{mr: 2}} // Add margin
                      />
                    </Tooltip>
                  ))}
                </FormGroup>
              </Grid>
            </Grid>
          </RubricSection>
        </TabPanel>

        {/* Question Sub-rubric Tab Panels */}
        {(rubric.sub_rubrics || []).map((subRubric, index) => (
          <TabPanel key={`subPanel-${subRubric.question_index}`} value={tabValue} index={index + 1}>
             {/* Section 1: Question Info & SubRubric Settings */}
             <RubricSection variant="outlined">
                <Typography variant="h6" gutterBottom>Question {subRubric.question_index + 1} Settings</Typography>
                 <Paper variant="outlined" sx={{ p: 2, bgcolor: 'action.hover', mb: 3 }}>
                    <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                        {getQuestionText(subRubric.question_index)}
                    </Typography>
                </Paper>
                <Grid container spacing={2}>
                   <Grid item xs={12} md={6}>
                       <TextField label="Question-Specific Guideline" multiline rows={3} fullWidth
                                  value={subRubric.instructor_guideline || ''}
                                  onChange={(e) => handleSubRubricChange(subRubric.question_index, 'instructor_guideline', e.target.value)}
                                  disabled={!editMode || isSaving} variant="outlined" margin="dense"
                                  placeholder={`Instructions specific to Q${subRubric.question_index + 1} (optional)`}/>
                   </Grid>
                   <Grid item xs={12} sm={6} md={3}>
                       <TextField label="Maximum Points" type="number" fullWidth
                                  value={subRubric.max_points ?? 0} // Default to 0 if null/undefined
                                  onChange={(e) => handleSubRubricChange(subRubric.question_index, 'max_points', parseFloat(e.target.value) || 0)}
                                  disabled={!editMode || isSaving} InputProps={{ inputProps: { min: 0, step: 0.5 } }}
                                  variant="outlined" margin="dense" required/>
                   </Grid>
                    <Grid item xs={12} sm={6} md={3}>
                        <FormControl fullWidth margin="dense" variant="outlined">
                          <InputLabel id={`q-leniency-label-${subRubric.question_index}`}>Leniency</InputLabel>
                          <Select labelId={`q-leniency-label-${subRubric.question_index}`}
                                  value={subRubric.leniency ?? ''} // Use empty string for 'Use Global'
                                  onChange={(e) => handleSubRubricChange(subRubric.question_index, 'leniency', e.target.value === '' ? null : parseInt(e.target.value))}
                                  disabled={!editMode || isSaving} label="Leniency">
                              <MenuItem value=""><em>Global ({rubric.leniency ?? 3})</em></MenuItem>
                              {[1, 2, 3, 4, 5].map(val => <MenuItem key={val} value={val}>{val}</MenuItem>)}
                          </Select>
                        </FormControl>
                   </Grid>
                </Grid>
             </RubricSection>

            {/* Section 2: Grading Criteria */}
            <RubricSection variant="outlined">
               <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6">Grading Criteria</Typography>
                  {editMode && <Button variant="contained" size="small" startIcon={<AddIcon />} onClick={() => openCriteriaDialog()} disabled={isSaving}>Add Criteria</Button>}
               </Box>
               {(!subRubric.grading_criteria || subRubric.grading_criteria.length === 0) ? (
                 <Box sx={{ textAlign: 'center', py: 3, border: `1px dashed ${theme.palette.divider}`, borderRadius: 1 }}>
                      <CriteriaIcon sx={{ fontSize: 40, color: 'text.disabled', mb: 1 }} />
                      <Typography color="text.secondary">No criteria defined yet.</Typography>
                      {editMode && <Button variant="text" startIcon={<AddIcon />} onClick={() => openCriteriaDialog()} sx={{ mt: 1 }} disabled={isSaving}>Add First Criteria</Button>}
                 </Box>
               ) : (
                 <>
                   {subRubric.grading_criteria.map((criteria, criteriaIndex) => (
                     <CriteriaCard key={`criteria-${subRubric.question_index}-${criteriaIndex}`} variant="outlined">
                       <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 1 }}>
                         {/* Criteria Text */}
                         <Box sx={{ flexGrow: 1, mr: 1 }}>
                           <Typography variant="subtitle1" fontWeight="medium" component="div">{criteria.criteria_id}</Typography>
                           <Typography variant="body2" sx={{ mt: 0.5, whiteSpace: 'pre-wrap' }}>{criteria.criteria}</Typography>
                         </Box>
                         {/* Points and Actions */}
                         <Box sx={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}>
                           <Chip label={`${criteria.points} pts`} color="primary" size="small" variant="outlined" sx={{ mr: 0.5 }} />
                           {editMode && (
                             <>
                               <Tooltip title="Edit Criteria">
                                 {/* Pass the criteria's array index to the handler */}
                                 <IconButton color="primary" size="small" onClick={() => openCriteriaDialog(activeSubRubricArrayIndex, criteriaIndex)} disabled={isSaving}>
                                   <EditIcon fontSize="small" />
                                 </IconButton>
                               </Tooltip>
                               <Tooltip title="Delete Criteria">
                                  {/* Pass the criteria's array index to the handler */}
                                 <IconButton color="error" size="small" onClick={() => openDeleteCriteriaDialog(criteriaIndex)} disabled={isSaving}>
                                   <DeleteIcon fontSize="small" />
                                 </IconButton>
                               </Tooltip>
                             </>
                           )}
                         </Box>
                       </Box>
                     </CriteriaCard>
                   ))}
                   <Divider sx={{ my: 2 }} />
                   {/* Points Summary */}
                   <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1 }}>
                     <Typography variant="subtitle1" fontWeight="bold">Total Criteria Points:</Typography>
                     <Typography variant="subtitle1" fontWeight="bold"
                                 color={calculateTotalPoints(subRubric) === (subRubric.max_points ?? 0) ? 'text.primary' : 'error.main'}>
                       {calculateTotalPoints(subRubric)} / {subRubric.max_points ?? 0}
                     </Typography>
                   </Box>
                   {calculateTotalPoints(subRubric) !== (subRubric.max_points ?? 0) && (
                     <Typography variant="caption" color="error" display="block" textAlign="right">
                       Warning: Total points don't match question's maximum points.
                     </Typography>
                   )}
                 </>
               )}
            </RubricSection>
          </TabPanel>
        ))}
      </>
    );
  };


  // --- Main Component Return ---
  return (
    <Box sx={{ p: { xs: 1, sm: 2, md: 3 } }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <IconButton edge="start" title="Back to Course" aria-label="back to course" onClick={() => router.push(`/course/${courseId}?semester=${semester}`)} sx={{ mr: 1 }} >
          <ArrowBackIcon />
        </IconButton>
        <Typography variant="h4" component="h1">Rubric Management</Typography>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      {/* Assignment Selection */}
      <Typography variant="h5" sx={{ mb: 2 }}>Select Assignment</Typography>
      {renderAssignmentSelection()}

      <Divider sx={{ my: 4 }} />

      {/* Rubric Editor/Viewer */}
      {renderRubricContent()}

      {/* --- DIALOGS --- */}

      {/* Add/Edit Criteria Dialog */}
      <Dialog open={criteriaDialogOpen} onClose={() => setCriteriaDialogOpen(false)} maxWidth="sm" fullWidth>
          <DialogTitle>{editingCriteriaIndex !== null ? 'Edit' : 'Add'} Grading Criteria {activeSubRubricData ? `for Q${activeSubRubricData.question_index + 1}` : ''}</DialogTitle>
          <DialogContent>
              <TextField autoFocus label="Criteria Title/ID" fullWidth value={criteriaFormData.criteria_id} onChange={(e) => setCriteriaFormData({ ...criteriaFormData, criteria_id: e.target.value })} margin="dense" required placeholder="e.g., Code Correctness" error={!criteriaFormData.criteria_id?.trim()} helperText={!criteriaFormData.criteria_id?.trim() ? "Title is required" : ""} />
              <TextField label="Criteria Description" fullWidth multiline rows={3} value={criteriaFormData.criteria} onChange={(e) => setCriteriaFormData({ ...criteriaFormData, criteria: e.target.value })} margin="dense" required placeholder="Description of criteria..." error={!criteriaFormData.criteria?.trim()} helperText={!criteriaFormData.criteria?.trim() ? "Description is required" : ""} />
              <TextField label="Points" type="number" fullWidth value={criteriaFormData.points} onChange={(e) => setCriteriaFormData({ ...criteriaFormData, points: e.target.value })} margin="dense" required InputProps={{ inputProps: { min: 0, step: 0.5 }, endAdornment: <InputAdornment position="end">pts</InputAdornment> }} error={!(parseFloat(criteriaFormData.points) >= 0)} helperText={!(parseFloat(criteriaFormData.points) >= 0) ? "Points must be 0 or greater" : ""} />
          </DialogContent>
          <DialogActions>
              <Button onClick={() => setCriteriaDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleSaveCriteria} variant="contained" color="primary" disabled={!criteriaFormData.criteria_id?.trim() || !criteriaFormData.criteria?.trim() || !(parseFloat(criteriaFormData.points) >= 0)}>
                  {editingCriteriaIndex !== null ? 'Save Changes' : 'Add Criteria'}
              </Button>
          </DialogActions>
      </Dialog>

      {/* Delete Criteria Confirmation */}
      <ConfirmationDialog
          open={deleteCriteriaDialogOpen}
          onClose={() => setDeleteCriteriaDialogOpen(false)}
          title="Delete Grading Criteria?"
          description="Are you sure you want to delete this grading criteria? This action cannot be undone."
          confirmText="Delete"
          cancelText="Cancel"
          confirmColor="error" // Pass color string
          onConfirm={handleDeleteCriteria}
      />

      {/* AI Instructions Dialog */}
      <Dialog open={aiInstructionsDialogOpen} onClose={() => !loadingAI && setAiInstructionsDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle><Box sx={{ display: 'flex', alignItems: 'center' }}><LightbulbIcon sx={{ mr: 1, color: 'warning.main' }} />AI Rubric Suggestions</Box></DialogTitle>
        <DialogContent>
          <Typography variant="body2" paragraph>The AI will analyze the selected assignment's questions ({selectedAssignment?.questions?.length ?? 0} questions) to suggest rubric criteria. Add specific instructions below if needed.</Typography>
          <TextField label="Instructions for AI (Optional)" fullWidth multiline rows={4} value={aiInstructions} onChange={(e) => setAiInstructions(e.target.value)} margin="dense" placeholder="e.g., Focus on logical reasoning, deduct points for syntax errors..." disabled={loadingAI} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAiInstructionsDialogOpen(false)} disabled={loadingAI}>Cancel</Button>
          <Button onClick={getAIRubricSuggestions} variant="contained" color="primary" disabled={loadingAI} startIcon={loadingAI ? <CircularProgress size={20} color="inherit"/> : <LightbulbIcon />}>
            {loadingAI ? 'Generating...' : 'Get AI Suggestions'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Alert Snackbar */}
      <Snackbar open={alertOpen} autoHideDuration={6000} onClose={() => setAlertOpen(false)} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
          <Alert onClose={() => setAlertOpen(false)} severity={alertSeverity} variant="filled" sx={{ width: '100%' }}>{alertMessage}</Alert>
      </Snackbar>
    </Box>
  );
}