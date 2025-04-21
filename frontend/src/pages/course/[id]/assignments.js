/**
 * Course Assignments Page for BU MET Autograder
 * Allows management of assignments and their questions.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/router';
import {
  Alert, Box, Button, Card, CardActionArea, CardActions, CardContent,
  CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle,
  Divider, Grid, IconButton, List, ListItem, ListItemIcon, ListItemText,
  Paper, Snackbar, TextField, Typography, useTheme // Added useTheme
} from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  Add as AddIcon, ArrowBack as ArrowBackIcon, Assignment as AssignmentIcon,
  Delete as DeleteIcon, Edit as EditIcon, DragIndicator as DragIndicatorIcon,
} from '@mui/icons-material';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';
import { assignmentService } from '../../../api'; // Ensure this path is correct
import CardSkeleton from '../../../components/CardSkeleton';
import ConfirmationDialog from '../../../components/ConfirmationDialog';

// Styled Components
const AssignmentCard = styled(Card)(({ theme }) => ({
    height: '100%', display: 'flex', flexDirection: 'column', transition: 'transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out', '&:hover': { transform: 'translateY(-4px)', boxShadow: theme.shadows[6], },
}));
const AssignmentCardContent = styled(CardContent)({
    flexGrow: 1, display: 'flex', flexDirection: 'column', minHeight: '100px',
});
const QuestionItem = styled(ListItem)(({ theme, isDragging }) => ({
    border: `1px solid ${theme.palette.divider}`, borderRadius: theme.shape.borderRadius, marginBottom: theme.spacing(1), backgroundColor: isDragging ? theme.palette.action.hover : theme.palette.background.paper, boxShadow: isDragging ? theme.shadows[3] : 'none', paddingRight: theme.spacing(16), // Pad for actions
    position: 'relative',
}));
const NoAssignmentsBox = styled(Box)(({ theme }) => ({
    textAlign: 'center', padding: theme.spacing(4), backgroundColor: theme.palette.background.default, borderRadius: theme.shape.borderRadius, marginTop: theme.spacing(4), border: `1px dashed ${theme.palette.divider}`,
}));

export default function Assignments() {
  const router = useRouter();
  const theme = useTheme(); // Get theme for spacing/styling if needed

  // Extract validated course context from router
  const { id: courseIdParam, semester: semesterParam, assignment_id: assignmentIdFromUrlParam } = router.query;
  const courseId = typeof courseIdParam === 'string' ? courseIdParam : null;
  const semester = typeof semesterParam === 'string' ? semesterParam : null;
  const assignmentIdFromUrl = typeof assignmentIdFromUrlParam === 'string' ? assignmentIdFromUrlParam : null;

  // State
  const [assignments, setAssignments] = useState([]);
  const [loadingAssignments, setLoadingAssignments] = useState(true);
  const [listError, setListError] = useState(null);
  const [selectedAssignment, setSelectedAssignment] = useState(null); // Holds the FULL assignment object with questions
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [detailsError, setDetailsError] = useState(null);
  const [actionLoading, setActionLoading] = useState(false); // Generic loading for actions

  // Dialog States
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editAssignmentDialogOpen, setEditAssignmentDialogOpen] = useState(false);
  const [addQuestionDialogOpen, setAddQuestionDialogOpen] = useState(false);
  const [editQuestionDialogOpen, setEditQuestionDialogOpen] = useState(false); // <<<--- ADDED
  const [deleteAssignmentDialogOpen, setDeleteAssignmentDialogOpen] = useState(false);
  const [deleteQuestionDialogOpen, setDeleteQuestionDialogOpen] = useState(false);

  // Form Data States
  const [newAssignmentData, setNewAssignmentData] = useState({ assignment_guidelines: '', questions: [{ question_text: '' }] });
  const [editAssignmentFormData, setEditAssignmentFormData] = useState({ assignment_guidelines: '' });
  // State for the question being added or edited
  const [questionFormData, setQuestionFormData] = useState({ question_text: '', question_index: null }); // <<<--- MODIFIED: Store index for edit
  const [questionToDeleteIndex, setQuestionToDeleteIndex] = useState(null); // Store index of question marked for deletion

  // Alert State
  const [alertOpen, setAlertOpen] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [alertSeverity, setAlertSeverity] = useState('success');

  // --- UTILITY FUNCTIONS ---

  const showAlert = useCallback((message, severity = 'success') => {
    setAlertMessage(message);
    setAlertSeverity(severity);
    setAlertOpen(true);
  }, []);

  // --- ERROR FORMATTING UTILITY ---
  const formatApiError = (error, defaultMessage) => {
    let displayError = defaultMessage;
    if (error.response) {
      const detail = error.response.data?.detail;
      if (detail) {
        if (Array.isArray(detail)) {
          displayError = detail.map(err => `${err.loc?.join('.')} - ${err.msg}`).slice(0, 3).join('; ');
          if (detail.length > 3) displayError += '...';
        } else if (typeof detail === 'string') {
          displayError = detail;
        } else {
          try { displayError = JSON.stringify(detail); } catch { /* ignore */ }
        }
      } else if (error.response.statusText) {
        displayError = `Error: ${error.response.status} ${error.response.statusText}`;
      }
    } else if (error.request) {
      displayError = "Network Error: Could not contact server.";
    } else if (error.message) {
      displayError = error.message;
    }
    return displayError;
  };


  // --- DATA FETCHING ---

  const fetchAssignmentDetails = useCallback(async (idToFetch) => {
    if (!courseId || !semester || !idToFetch) {
      console.warn("fetchAssignmentDetails: Missing context or ID.", { courseId, semester, idToFetch });
      setSelectedAssignment(null);
      setDetailsError(null);
      return;
    }
    setLoadingDetails(true);
    setDetailsError(null);
    console.log(`FETCHING details for assignment ID: ${idToFetch}`);
    try {
      // Always include questions when fetching details for this page
      const response = await assignmentService.getAssignment(courseId, semester, idToFetch, true);
      const assignmentData = response?.data;

      if (assignmentData && typeof assignmentData === 'object' && typeof assignmentData.assignment_id !== 'undefined') { // Check ID presence
        console.log("RECEIVED assignment data:", assignmentData);
        if (!Array.isArray(assignmentData.questions)) {
             console.warn("Questions field not an array, setting to empty:", assignmentData.questions);
             assignmentData.questions = [];
        } else {
             // Sort questions by index for consistent display
             assignmentData.questions.sort((a, b) => (a.question_index ?? Infinity) - (b.question_index ?? Infinity));
        }
        setSelectedAssignment(assignmentData); // Set the clean data object
      } else {
        throw new Error(`Invalid data structure received for assignment ${idToFetch}. Expected object with assignment_id.`);
      }
    } catch (err) {
      console.error(`Error fetching assignment details for ID ${idToFetch}:`, err);
      const errorMsg = formatApiError(err, `Failed to load details for assignment ${idToFetch}.`);
      setDetailsError(errorMsg);
      setSelectedAssignment(null);
    } finally {
      setLoadingDetails(false);
    }
  }, [courseId, semester]); // No need for showAlert here

  useEffect(() => {
    if (courseId && semester) {
      const fetchAssignments = async () => {
        setLoadingAssignments(true);
        setListError(null);
        if (!assignmentIdFromUrl) { // Only clear selection if no specific assignment is targeted by URL
             setSelectedAssignment(null);
        }
        try {
          console.log(`FETCHING assignments list for ${courseId}/${semester}`);
          const response = await assignmentService.getAssignments(courseId, semester);
          const assignmentsArray = response?.data;

          if (Array.isArray(assignmentsArray)) {
             console.log("RECEIVED assignments list:", assignmentsArray);
             const validAssignments = assignmentsArray.filter(a => a && typeof a === 'object' && typeof a.assignment_id !== 'undefined'); // Check for ID existence
             if (validAssignments.length !== assignmentsArray.length) {
                console.warn("Some items in the fetched assignments list were invalid:", assignmentsArray);
             }
             setAssignments(validAssignments);

             // If an ID is in the URL, fetch its details *after* setting the list
             if (assignmentIdFromUrl) {
                const assignmentExists = validAssignments.some(a => a.assignment_id === assignmentIdFromUrl);
                if (assignmentExists) {
                    console.log(`URL includes assignment_id=${assignmentIdFromUrl}. Fetching its details.`);
                    // Avoid redundant fetch if only URL changed shallowly and details are already loaded for this ID
                    if (selectedAssignment?.assignment_id !== assignmentIdFromUrl || detailsError) {
                        fetchAssignmentDetails(assignmentIdFromUrl);
                    }
                } else {
                    console.warn(`Assignment ID ${assignmentIdFromUrl} from URL not found in list. Clearing selection and URL param.`);
                    handleClearSelection(); // Clear selection and update URL
                    showAlert(`Assignment with ID ${assignmentIdFromUrl} not found for this course/semester.`, 'warning');
                }
             }

          } else {
            console.error("Invalid data received for assignments list (expected array):", assignmentsArray);
            setAssignments([]);
            setListError("Received invalid data format for assignments list.");
          }
        } catch (err) {
          console.error("Error fetching assignments list:", err);
          const errorMsg = formatApiError(err, 'Failed to load assignments list.');
          setListError(errorMsg);
          setAssignments([]);
        } finally {
          setLoadingAssignments(false);
        }
      };
      fetchAssignments();
    } else {
      // Clear state if course context is missing
      setAssignments([]);
      setLoadingAssignments(false);
      setListError(null);
      setSelectedAssignment(null);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courseId, semester, assignmentIdFromUrl, fetchAssignmentDetails]); // Rerun if context or targeted ID changes

  // --- UI Handlers ---

  const handleSelectAssignment = useCallback((assignment) => {
    if (!courseId || !semester || !assignment?.assignment_id) return;
    const targetAssignmentId = assignment.assignment_id;
    console.log(`SELECTING assignment ID: ${targetAssignmentId}`);

    // Only fetch if it's a different assignment or if details previously failed
    const needsFetch = selectedAssignment?.assignment_id !== targetAssignmentId || detailsError;

    // Update URL if needed (use assignment_id consistently)
    const currentQueryAssignmentId = router.query.assignment_id;
    if (currentQueryAssignmentId !== targetAssignmentId) {
      router.push(
        `/course/${courseId}/assignments?semester=${semester}&assignment_id=${targetAssignmentId}`,
        undefined,
        { shallow: true } // Avoid full reload if just changing query param
      );
    }
    // Fetch details if necessary
    if (needsFetch) {
         fetchAssignmentDetails(targetAssignmentId);
    } else {
         // If not fetching, ensure the local state is updated (in case selection happened without URL change)
         setSelectedAssignment(assignment);
         setDetailsError(null); // Clear previous error if any
    }

  }, [courseId, semester, router, fetchAssignmentDetails, selectedAssignment, detailsError]); // Added selectedAssignment, detailsError

  const handleClearSelection = useCallback(() => {
    if (!courseId || !semester) return;
    setSelectedAssignment(null);
    setDetailsError(null);
    // Only update route if assignment_id param exists
    if (router.query.assignment_id) {
        console.log("CLEARING selection, removing assignment_id from URL.");
        router.push(
            `/course/${courseId}/assignments?semester=${semester}`,
            undefined,
            { shallow: true }
        );
    }
  }, [courseId, semester, router]);

  // --- ASSIGNMENT CRUD ---

  const openCreateDialog = () => {
    setNewAssignmentData({ assignment_guidelines: '', questions: [{ question_text: '' }] });
    setCreateDialogOpen(true);
  };

  // Handler for guidelines text field in create dialog
  const handleGuidelinesChange = (event) => {
        const { value } = event.target;
        setNewAssignmentData(prev => ({
            ...prev,
            assignment_guidelines: value
        }));
    };

 // Handler for adding a new empty question field to the create dialog
 const handleAddQuestionField = () => {
    setNewAssignmentData(prev => ({
      ...prev,
      questions: [...prev.questions, { question_text: '' }]
    }));
  };

  // Handler for removing a question field from the create dialog
  const handleRemoveQuestionField = (indexToRemove) => {
    if (newAssignmentData.questions.length <= 1) return;
    setNewAssignmentData(prev => ({
      ...prev,
      questions: prev.questions.filter((_, index) => index !== indexToRemove)
    }));
  };

  // Handler for updating the text of a specific question in the create dialog
  const handleQuestionTextChange = (indexToUpdate, newText) => {
    setNewAssignmentData(prev => ({
      ...prev,
      questions: prev.questions.map((q, index) =>
        index === indexToUpdate ? { ...q, question_text: newText } : q
      )
    }));
  };

  const handleCreateAssignment = async () => {
    if (!courseId || !semester) return showAlert('Course context missing.', 'warning');
    if (!newAssignmentData.questions.length || newAssignmentData.questions.some(q => !q.question_text?.trim())) {
        return showAlert('Please add at least one question and ensure all question fields are filled.', 'warning');
    }
    setActionLoading(true);
    try {
      const assignmentPayload = {
        course_id: courseId,
        semester: semester,
        // Send null if empty string, otherwise send the trimmed string
        assignment_guidelines: newAssignmentData.assignment_guidelines?.trim() || null,
        // Filter out empty questions and map to required structure
        questions: newAssignmentData.questions
                            .map(q => q.question_text?.trim()) // Get trimmed text
                            .filter(text => text) // Filter out empty/null strings
                            .map(text => ({ question_text: text, question_graphics_figures: null })), // Map to payload structure
      };
      console.log("CREATING assignment with payload:", assignmentPayload);
      const response = await assignmentService.createAssignment(assignmentPayload);
      const createdAssignmentData = response?.data;
      console.log("RESPONSE from createAssignment:", response);

      if (!createdAssignmentData || typeof createdAssignmentData.assignment_id === 'undefined') {
          throw new Error(createdAssignmentData?.detail || "Invalid response after creating assignment.");
      }
      // Prepare a simplified object for the list state if needed, or use the full one
      const assignmentForList = {
        assignment_id: createdAssignmentData.assignment_id,
        assignment_guidelines: createdAssignmentData.assignment_guidelines,
        // maybe other minimal fields returned by create...
      };
      setAssignments(prev => [...prev, assignmentForList]); // Add to list
      setNewAssignmentData({ assignment_guidelines: '', questions: [{ question_text: '' }] }); // Reset form
      setCreateDialogOpen(false);
      showAlert(`Assignment created (ID: ${createdAssignmentData.assignment_id}). Selecting it...`);
      handleSelectAssignment(createdAssignmentData); // Select the new one (pass the full object if available)
    } catch (error) {
      console.error("Failed to create assignment:", error);
      const displayError = formatApiError(error, 'Failed to create assignment.');
      showAlert(displayError, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const openEditAssignmentDialog = (assignmentToEdit) => {
    if (!assignmentToEdit || typeof assignmentToEdit.assignment_id === 'undefined') return;
    // Ensure we have the full details if selecting from the list card directly
    if (assignmentToEdit.assignment_id !== selectedAssignment?.assignment_id || !selectedAssignment?.questions) {
        setSelectedAssignment(assignmentToEdit); // Temporarily set for ID, full data might load via fetch later
    }
    setEditAssignmentFormData({ assignment_guidelines: assignmentToEdit.assignment_guidelines || '' });
    setEditAssignmentDialogOpen(true);
  };

  const handleUpdateAssignment = async () => {
    if (!selectedAssignment || typeof selectedAssignment.assignment_id === 'undefined' || !semester || !courseId) return;
    const { assignment_guidelines } = editAssignmentFormData;
    const updatePayload = { assignment_guidelines: assignment_guidelines?.trim() || null };
    const assignmentId = selectedAssignment.assignment_id; // Store ID before potential state changes

    setActionLoading(true);
    try {
      console.log(`UPDATING assignment ${assignmentId} metadata with payload:`, updatePayload);
      await assignmentService.updateAssignmentMetadata(semester, courseId, assignmentId, updatePayload);
      console.log("RESPONSE from updateAssignmentMetadata successful.");

      // Update the list item optimistically
      setAssignments(prevAssignments => prevAssignments.map(a =>
           a.assignment_id === assignmentId ? { ...a, assignment_guidelines: updatePayload.assignment_guidelines } : a
      ));

      // Refresh the detailed view
      showAlert('Assignment info updated. Refreshing details...');
      await fetchAssignmentDetails(assignmentId); // Refresh to get potentially other updated fields

    } catch (error) {
      console.error("Failed to update assignment:", error);
      const displayError = formatApiError(error, 'Failed to update assignment info.');
      showAlert(displayError, 'error');
    } finally {
      setEditAssignmentDialogOpen(false); // Close dialog
      setActionLoading(false);
    }
  };


  const handleDeleteAssignment = async () => {
     // Use selectedAssignment directly, which should be set when delete button is clicked
    const assignmentObjectToDelete = selectedAssignment;
    const idToDelete = assignmentObjectToDelete?.assignment_id;
    console.log("DELETE request for assignment ID:", idToDelete);
    if (typeof idToDelete === 'undefined' || !semester || !courseId) {
      showAlert(`Cannot delete: Missing required info (Assignment ID, Semester, or Course ID).`, 'error');
      console.error("Delete preconditions failed:", { idToDelete, semester, courseId });
      setDeleteAssignmentDialogOpen(false);
      return;
    }
    setActionLoading(true);
    setDeleteAssignmentDialogOpen(false);
    try {
      await assignmentService.deleteAssignment(courseId, semester, idToDelete);
      console.log(`Assignment ${idToDelete} reported as deleted by API.`);
      showAlert(`Assignment (ID: ${idToDelete}) deleted successfully.`);
      setAssignments(prev => prev.filter(a => a.assignment_id !== idToDelete)); // Update list
      handleClearSelection(); // Clear selection and URL param
    } catch (error) {
      console.error("Failed to delete assignment:", error);
       const displayError = formatApiError(error, `Failed to delete assignment (ID: ${idToDelete}).`);
      showAlert(displayError, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  // --- QUESTION CRUD --- (Triggered from Details Section)

  const openAddQuestionDialog = () => {
    if (!selectedAssignment || typeof selectedAssignment.assignment_id === 'undefined') {
      return showAlert('Select an assignment first.', 'warning');
    }
    // Reset form state specifically for adding
    setQuestionFormData({ question_text: '', question_index: null }); // Clear index for adding
    setAddQuestionDialogOpen(true);
  };

  const handleAddQuestion = async () => {
    if (!selectedAssignment || typeof selectedAssignment.assignment_id === 'undefined' || !semester || !courseId) {
         return showAlert("Cannot add question: context missing.", "warning");
    }
     if (!questionFormData.question_text?.trim()) {
        return showAlert('Question text is required.', 'warning');
     }
    const assignmentId = selectedAssignment.assignment_id; // Store ID
    // Payload for the backend API
    const questionPayload = { question_text: questionFormData.question_text.trim(), question_graphics_figures: null };
    setActionLoading(true);
    try {
      console.log(`ADDING question to assignment ${assignmentId}:`, questionPayload);
      // API might return the new question object or just confirmation/index
      const response = await assignmentService.addQuestion(semester, courseId, assignmentId, questionPayload);
      console.log("RESPONSE from addQuestion:", response);

      // Check if the backend response indicates success (e.g., status 201 or returns data)
      // We don't strictly need the new index if we refetch details.
      if (response?.status >= 200 && response?.status < 300) { // Check status code range
        showAlert('Question added. Refreshing details...');
        await fetchAssignmentDetails(assignmentId); // Refresh to get updated list and indices
      } else {
        // If status code is not success or response is unexpected
        throw new Error(response?.data?.detail || "Failed to add question, invalid response received.");
      }
    } catch (error) {
      console.error("Failed to add question:", error);
      const displayError = formatApiError(error, 'Failed to add question.');
      showAlert(displayError, 'error');
    } finally {
      setAddQuestionDialogOpen(false); // Close dialog
      setActionLoading(false);
    }
  };

  // <<<--- NEW: Function to open the edit dialog --- >>>
  const openEditQuestionDialog = (question) => {
    if (!question || typeof question.question_index !== 'number') {
        console.error("Cannot edit question: Invalid question object provided.", question);
        showAlert("Cannot edit question: Invalid data.", "warning");
        return;
    }
    if (!selectedAssignment || typeof selectedAssignment.assignment_id === 'undefined') {
        return showAlert("Cannot edit question: No assignment selected.", "warning");
    }
    // Set form state with the data of the question being edited
    setQuestionFormData({
      question_text: question.question_text || '',
      question_index: question.question_index, // Store the index being edited
    });
    setEditQuestionDialogOpen(true);
  };

  // <<<--- NEW: Function to handle the edit API call --- >>>
  const handleEditQuestion = async () => {
    const { question_text, question_index } = questionFormData;

    if (!selectedAssignment || typeof selectedAssignment.assignment_id === 'undefined' || typeof question_index !== 'number' || !semester || !courseId) {
      return showAlert('Invalid context for editing question.', 'warning');
    }
    if (!question_text?.trim()) {
         return showAlert('Question text cannot be empty.', 'warning');
    }

    const assignmentId = selectedAssignment.assignment_id; // Store ID
    // API expects updated question data in the body
    const questionPayload = { question_text: question_text.trim(), question_graphics_figures: null }; // Add other fields if needed
    const indexToEdit = question_index;

    setActionLoading(true);
    try {
      console.log(`EDITING question index ${indexToEdit} for assignment ${assignmentId}:`, questionPayload);
      // Assume assignmentService has an editQuestion method
      await assignmentService.editQuestion(semester, courseId, assignmentId, indexToEdit, questionPayload);
      console.log("RESPONSE from editQuestion successful.");

      showAlert('Question updated. Refreshing details...');
      await fetchAssignmentDetails(assignmentId); // Refresh to get updated list

    } catch (error) {
      console.error(`Failed to edit question index ${indexToEdit}:`, error);
      const displayError = formatApiError(error, 'Failed to edit question.');
      showAlert(displayError, 'error');
      // No UI revert needed, fetchAssignmentDetails will get the correct state
    } finally {
      setEditQuestionDialogOpen(false); // Close dialog
      setActionLoading(false);
    }
  };

  const onDragEnd = useCallback(async (result) => {
    const { source, destination } = result;
    // Basic validation
    if (!destination || !selectedAssignment?.assignment_id || !Array.isArray(selectedAssignment.questions) || selectedAssignment.questions.length < 2 || !semester || !courseId) return;
    // Check if dropped in the same place
    if (destination.droppableId === source.droppableId && destination.index === source.index) return;

    console.log(`Dragging Q index ${source.index} to ${destination.index}`);
    const currentQuestions = Array.from(selectedAssignment.questions);
    const [reorderedItem] = currentQuestions.splice(source.index, 1);
    currentQuestions.splice(destination.index, 0, reorderedItem);

    // Optimistic UI Update
    setSelectedAssignment(prev => ({ ...prev, questions: currentQuestions }));

    // Payload for backend is the list of ORIGINAL question_index values in the NEW order
    const newIndexOrder = currentQuestions.map(q => q.question_index);
    if (newIndexOrder.some(idx => typeof idx !== 'number')) {
        console.error("Error preparing reorder payload: Some questions missing original index.", currentQuestions);
        showAlert("Error preparing reorder data. Please refresh.", "error");
        fetchAssignmentDetails(selectedAssignment.assignment_id); // Revert optimistic update
        return;
    }
    console.log("SENDING new index order:", newIndexOrder);
    const assignmentId = selectedAssignment.assignment_id; // Store ID

    setActionLoading(true);
    try {
      await assignmentService.modifyQuestionOrder(semester, courseId, assignmentId, newIndexOrder);
      showAlert('Order updated. Refreshing details...');
      await fetchAssignmentDetails(assignmentId); // Refresh from backend to confirm final order and indices
    } catch (error) {
      console.error("Failed to update question order:", error);
      const displayError = formatApiError(error, 'Failed to update question order.');
      showAlert(displayError, 'error');
      // Revert UI on error by fetching original state
      showAlert('Reverting local order changes...', 'warning');
      await fetchAssignmentDetails(assignmentId); // Revert optimistic update
    } finally {
      setActionLoading(false);
    }
  }, [selectedAssignment, semester, courseId, fetchAssignmentDetails, showAlert]); // Added showAlert

  const openDeleteQuestionDialog = (index) => {
    if (typeof index !== 'number') {
        console.error("Cannot delete question: Invalid index provided.", index);
        showAlert("Cannot delete question: Invalid index.", "warning");
        return;
    }
    console.log("Opening delete confirmation for question index:", index);
    setQuestionToDeleteIndex(index);
    setDeleteQuestionDialogOpen(true);
  };

  const handleDeleteQuestion = async () => {
    if (!selectedAssignment || typeof selectedAssignment.assignment_id === 'undefined' || typeof questionToDeleteIndex !== 'number' || !semester || !courseId) {
        return showAlert("Cannot delete question: context or index missing.", "warning");
    }
    const assignmentId = selectedAssignment.assignment_id; // Store ID
    const indexToDelete = questionToDeleteIndex; // Store index

    setActionLoading(true);
    setDeleteQuestionDialogOpen(false); // Close dialog
    try {
      console.log(`DELETING question index ${indexToDelete} from assignment ${assignmentId}`);
      await assignmentService.removeQuestion(semester, courseId, assignmentId, indexToDelete);
      console.log("RESPONSE from removeQuestion successful.");
      showAlert('Question deleted. Refreshing details...');
      await fetchAssignmentDetails(assignmentId); // Refresh to get updated list
    } catch (error) {
      console.error(`Failed to delete question index ${indexToDelete}:`, error);
      const displayError = formatApiError(error, 'Failed to delete question.');
      showAlert(displayError, 'error');
      // No need to revert UI, fetchAssignmentDetails handles it
    } finally {
      setQuestionToDeleteIndex(null); // Reset index
      setActionLoading(false);
    }
  };

  // --- RENDER FUNCTIONS ---

  const renderAssignmentList = () => {
    if (loadingAssignments) {
        return <Grid container spacing={3} sx={{ mb: 4 }}>{[1, 2, 3].map(n => <Grid item xs={12} sm={6} md={4} key={`skeleton-${n}`}><CardSkeleton height={150} /></Grid>)}</Grid>;
    }
    if (listError) return <Alert severity="error" sx={{ mb: 3 }}>Error loading assignments: {listError}</Alert>;
    if (!Array.isArray(assignments) || !assignments.length) {
        return <NoAssignmentsBox><AssignmentIcon sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} /><Typography variant="h6">No assignments found.</Typography><Typography color="text.secondary" sx={{ mb: 2 }}>Create one to get started.</Typography><Button variant="contained" startIcon={<AddIcon />} onClick={openCreateDialog} disabled={actionLoading || !courseId || !semester}>Create Assignment</Button></NoAssignmentsBox>;
    }
    return (
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {assignments.map(assignment => (
          <Grid item xs={12} sm={6} md={4} key={assignment.assignment_id}>
            <AssignmentCard variant="outlined" sx={{ borderColor: selectedAssignment?.assignment_id === assignment.assignment_id ? 'primary.main' : 'divider' }}>
              <CardActionArea onClick={() => !actionLoading && handleSelectAssignment(assignment)} sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }} disabled={actionLoading}>
                <AssignmentCardContent>
                  <Typography gutterBottom variant="h6" noWrap title={`Assignment ID: ${assignment.assignment_id}`}>
                     Assignment {assignment.assignment_id} {/* Display ID */}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', flexGrow: 1, minHeight: '60px' /* Ensure some min height */ }}>
                    {assignment.assignment_guidelines || 'No guidelines provided.'}
                  </Typography>
                </AssignmentCardContent>
              </CardActionArea>
              <CardActions sx={{ justifyContent: 'flex-end', pt: 0, pb: 1, px: 1 }}>
                <IconButton title="Edit Assignment Info" size="small" onClick={(e) => { e.stopPropagation(); openEditAssignmentDialog(assignment); }} disabled={actionLoading}> <EditIcon fontSize="small" /> </IconButton>
                <IconButton title="Delete Assignment" size="small" onClick={(e) => { e.stopPropagation(); console.log("--- Delete Button Click ---"); console.log("Setting selected assignment for delete:", assignment); setSelectedAssignment(assignment); setDeleteAssignmentDialogOpen(true); }} disabled={actionLoading} color="error"> <DeleteIcon fontSize="small" /> </IconButton>
              </CardActions>
            </AssignmentCard>
          </Grid>
        ))}
      </Grid>
    );
  };

  const renderAssignmentDetails = () => {
    // Handle loading/error states *before* checking selectedAssignment
    if (loadingDetails) {
        return <Paper elevation={0} sx={{ mt: 4, p: 3, textAlign: 'center' }}><CircularProgress /><Typography sx={{ mt: 1 }}>Loading details...</Typography></Paper>;
    }
     // Show error specific to details fetch
    if (detailsError && (!selectedAssignment || !selectedAssignment.assignment_id)) {
         return <Paper elevation={0} sx={{ mt: 4, p: 3 }}><Alert severity="error">Could not load assignment details: {detailsError}</Alert></Paper>;
    }
     // If URL has ID, list is loaded, but details are not yet loading/loaded/failed, show placeholder
     if (!selectedAssignment && assignmentIdFromUrl && !loadingAssignments && assignments.length > 0 && !listError && !detailsError) {
        return (
             <Paper elevation={0} variant="outlined" sx={{ mt: 4, p: 3, textAlign: 'center', borderStyle: 'dashed' }}>
                <Typography color="text.secondary">Loading assignment details...</Typography>
                <CircularProgress size={20} sx={{ml: 1}}/>
             </Paper>
        );
    }
    // Prompt to select if list is loaded and no assignment is selected or targeted by URL
    if (!selectedAssignment || typeof selectedAssignment.assignment_id === 'undefined') {
      if (!loadingAssignments && assignments.length > 0) {
        return <Paper elevation={0} variant="outlined" sx={{ mt: 4, p: 3, textAlign: 'center', borderStyle: 'dashed' }}><Typography color="text.secondary">Select an assignment from the list above to view its details.</Typography></Paper>;
      }
      return null; // Don't show anything if list is loading or empty
    }

    // --- Render Details Section ---
    const questions = selectedAssignment.questions || []; // Ensure questions is an array

    return (
      <Paper elevation={3} sx={{ mt: 4, p: { xs: 1.5, sm: 2, md: 3 } }}>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 1 }}>
          <Typography variant="h5" component="h2">{`Assignment ${selectedAssignment.assignment_id}`}</Typography>
          <Box>
             {/* Pass the currently selected (and loaded) assignment object */}
            <Button variant="outlined" size="small" startIcon={<EditIcon />} onClick={() => openEditAssignmentDialog(selectedAssignment)} sx={{ mr: 1 }} disabled={actionLoading}> Edit Info </Button>
            <Button variant="outlined" size="small" color="error" startIcon={<DeleteIcon />} onClick={() => setDeleteAssignmentDialogOpen(true)} disabled={actionLoading}> Delete Assignment </Button>
          </Box>
        </Box>
        {/* Guidelines */}
        <Typography variant="subtitle2" sx={{ color: 'text.secondary', mb: 0.5 }}>Guidelines:</Typography>
        <Paper variant="outlined" sx={{ p: 1.5, mb: 2, bgcolor: 'action.hover', maxHeight: '150px', overflowY: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
            {selectedAssignment.assignment_guidelines || <Typography component="em" sx={{color: 'text.disabled'}}>No guidelines specified.</Typography>}
        </Paper>

        <Divider sx={{ my: 3 }} />

        {/* Questions Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Questions ({questions.length})</Typography>
          <Button variant="contained" size="small" startIcon={<AddIcon />} onClick={openAddQuestionDialog} disabled={actionLoading}> Add Question </Button>
        </Box>

        {/* Questions List or Placeholder */}
        {(!Array.isArray(questions) || !questions.length) ? (
          <Typography color="text.secondary" sx={{ fontStyle: 'italic', textAlign: 'center', py: 2 }}> No questions added yet. </Typography>
        ) : (
          <DragDropContext onDragEnd={onDragEnd}>
            <Droppable droppableId={`questions-${selectedAssignment.assignment_id}`}>
              {(provided) => (
                <List {...provided.droppableProps} ref={provided.innerRef} disablePadding>
                  {questions.map((question, index) => (
                     <Draggable
                        key={`${selectedAssignment.assignment_id}-${question.question_index}`} // Use original index as key
                        draggableId={`${selectedAssignment.assignment_id}-${question.question_index}`} // Use original index for ID
                        index={index} // Use current array index for DnD logic
                        isDragDisabled={actionLoading}
                     >
                      {(providedDraggable, snapshot) => (
                        <QuestionItem
                            ref={providedDraggable.innerRef}
                            {...providedDraggable.draggableProps}
                            isDragging={snapshot.isDragging}
                            sx={{pr: 18 }} // Ensure enough padding for all buttons
                            secondaryAction={ /* Actions: Edit, Delete, Drag Handle */
                                <Box sx={{ display: 'flex', alignItems: 'center', position: 'absolute', right: theme.spacing(1), top: '50%', transform: 'translateY(-50%)' }}>
                                    {/* <<<--- ADDED Edit Button --- >>> */}
                                    <IconButton edge="end" title="Edit Question" sx={{ mr: 0.5 }} onClick={() => openEditQuestionDialog(question)} disabled={actionLoading}>
                                        <EditIcon fontSize="small"/>
                                    </IconButton>
                                    <IconButton edge="end" title="Delete Question" onClick={() => openDeleteQuestionDialog(question.question_index)} disabled={actionLoading} color="error" sx={{ mr: 0.5 }}>
                                        <DeleteIcon fontSize="small"/>
                                    </IconButton>
                                    {/* Drag Handle */}
                                    <Box {...providedDraggable.dragHandleProps} sx={{ display: 'inline-flex', alignItems: 'center', cursor: actionLoading ? 'not-allowed' : 'grab', color: 'action.active', '&:hover': { color: 'text.primary' } }} title="Drag to reorder">
                                        <DragIndicatorIcon />
                                    </Box>
                                </Box>
                            }
                        >
                          <ListItemIcon sx={{ minWidth: 'auto', mr: 1.5, alignSelf: 'flex-start', pt: 1 }}>
                             {/* Display current visual order */}
                             <Typography variant="body2" sx={{ fontWeight: 'bold' }}>{`Q${index + 1}:`}</Typography>
                           </ListItemIcon>
                          <ListItemText
                            primary={question.question_text || <Typography component="em" sx={{color: 'text.disabled'}}>(No text)</Typography>}
                            secondary={typeof question.question_index === 'number' ? `(Original Index: ${question.question_index})` : '(Index missing)'}
                            primaryTypographyProps={{ sx: { wordBreak: 'break-word', whiteSpace: 'pre-wrap', pr: 1 } }}
                            secondaryTypographyProps={{ sx: { fontSize: '0.75rem', color: 'text.disabled', mt: 0.5 } }}
                          />
                        </QuestionItem>
                      )}
                    </Draggable>
                  ))}
                  {provided.placeholder}
                </List>
              )}
            </Droppable>
          </DragDropContext>
        )}
         {detailsError && selectedAssignment?.assignment_id && (
             <Alert severity="warning" sx={{ mt: 2 }}>
                There was an error refreshing details ({detailsError}). Some information might be outdated.
             </Alert>
         )}
      </Paper>
    );
  };


  // --- MAIN RETURN ---
  return (
    <Box sx={{ p: { xs: 1, sm: 2, md: 3 } }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 1 }}>
        <IconButton title="Back to Course Overview" aria-label="back" onClick={() => (courseId && semester) && router.push(`/course/${courseId}?semester=${semester}`)} disabled={!courseId || !semester || actionLoading} sx={{ mr: 1 }}> <ArrowBackIcon /> </IconButton>
        <Typography variant="h4" component="h1" sx={{ flexGrow: 1, mr: 1 }}>Course Assignments</Typography>
        <Button variant="contained" color="primary" size="small" startIcon={<AddIcon />} onClick={openCreateDialog} disabled={actionLoading || !courseId || !semester}> Create Assignment </Button>
      </Box>

      {/* Assignment List Section */}
      <Typography variant="h5" sx={{ mb: 2 }}>Assignments List</Typography>
      {renderAssignmentList()}

      <Divider sx={{ my: 4 }} />

      {/* Assignment Details Section */}
      <Typography variant="h5" sx={{ mb: 2 }}>Selected Assignment Details</Typography>
      {renderAssignmentDetails()}

      {/* --- DIALOGS --- */}

      {/* Create Assignment Dialog */}
      <Dialog open={createDialogOpen} onClose={() => !actionLoading && setCreateDialogOpen(false)} maxWidth="md" fullWidth scroll="paper">
        <DialogTitle>Create New Assignment</DialogTitle>
        <DialogContent dividers> {/* Added dividers */}
          <TextField autoFocus id="new-assignment-guidelines" name="assignment_guidelines" label="Assignment Guidelines (Optional)" fullWidth multiline minRows={3} maxRows={8} value={newAssignmentData.assignment_guidelines} onChange={handleGuidelinesChange} margin="dense" disabled={actionLoading} sx={{ mb: 3 }} />
          <Divider sx={{ my: 2 }}>Questions</Divider> {/* Use Divider with text */}
          {newAssignmentData.questions.map((q, index) => (
            <Box key={index} sx={{ display: 'flex', alignItems: 'flex-start', mb: 1.5 }}> {/* Align items start */}
              <TextField id={`new-question-${index}`} name={`question_text_${index}`} label={`Question ${index + 1} Text`} fullWidth multiline minRows={2} maxRows={6} value={q.question_text} onChange={(e) => handleQuestionTextChange(index, e.target.value)} margin="dense" required error={!q.question_text?.trim() && q.question_text !== ''} helperText={!q.question_text?.trim() && q.question_text !== '' ? "Question text is required" : ""} disabled={actionLoading} sx={{ mr: 1, flexGrow: 1 }} />
               {/* Only show delete if more than one question exists */}
              {newAssignmentData.questions.length > 1 && (
                 <IconButton title={`Remove Question ${index + 1}`} onClick={() => handleRemoveQuestionField(index)} disabled={actionLoading} color="error" size="small" sx={{ mt: 1.5 }}> {/* Adjust margin-top */}
                     <DeleteIcon />
                </IconButton>
             )}
            </Box>
          ))}
          <Button variant="outlined" size="small" startIcon={<AddIcon />} onClick={handleAddQuestionField} disabled={actionLoading} sx={{ mt: 1 }}> Add Another Question Field </Button>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)} disabled={actionLoading}>Cancel</Button>
          <Button onClick={handleCreateAssignment} variant="contained" color="primary" disabled={actionLoading || !newAssignmentData.questions.length || newAssignmentData.questions.some(q => !q.question_text?.trim())}> {actionLoading ? <CircularProgress size={24}/> : 'Create Assignment'} </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Assignment Dialog */}
      <Dialog open={editAssignmentDialogOpen} onClose={() => !actionLoading && setEditAssignmentDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Edit Assignment Info (ID: {selectedAssignment?.assignment_id ?? 'N/A'})</DialogTitle>
        <DialogContent>
          <TextField autoFocus id="edit-assignment-guidelines" name="assignment_guidelines" label="Assignment Guidelines (Optional)" fullWidth multiline minRows={4} maxRows={10} value={editAssignmentFormData.assignment_guidelines} onChange={(e) => setEditAssignmentFormData({ assignment_guidelines: e.target.value })} margin="dense" disabled={actionLoading}/>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditAssignmentDialogOpen(false)} disabled={actionLoading}>Cancel</Button>
          <Button onClick={handleUpdateAssignment} variant="contained" color="primary" disabled={actionLoading}> {actionLoading ? <CircularProgress size={24}/> : 'Save Changes'} </Button>
        </DialogActions>
      </Dialog>

      {/* Add Question Dialog */}
      <Dialog open={addQuestionDialogOpen} onClose={() => !actionLoading && setAddQuestionDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Add New Question to Assignment {selectedAssignment?.assignment_id ?? 'N/A'}</DialogTitle>
        <DialogContent>
          <TextField autoFocus id="add-question-text" name="question_text" label="Question Text" fullWidth multiline minRows={4} maxRows={10} value={questionFormData.question_text} onChange={(e) => setQuestionFormData(prev => ({...prev, question_text: e.target.value }))} margin="dense" required error={!questionFormData.question_text?.trim() && questionFormData.question_text !== ''} helperText={!questionFormData.question_text?.trim() && questionFormData.question_text !== '' ? "Question text is required" : ""} disabled={actionLoading}/>
          <Typography variant="caption" display="block" sx={{ mt: 1, color: 'text.secondary' }}>Graphics/Figures are not currently supported via this interface.</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddQuestionDialogOpen(false)} disabled={actionLoading}>Cancel</Button>
          <Button onClick={handleAddQuestion} variant="contained" color="primary" disabled={actionLoading || !questionFormData.question_text?.trim()}> {actionLoading ? <CircularProgress size={24}/> : 'Add Question'} </Button>
        </DialogActions>
      </Dialog>

      {/* <<<--- NEW: Edit Question Dialog --- >>> */}
      <Dialog open={editQuestionDialogOpen} onClose={() => !actionLoading && setEditQuestionDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Edit Question (Assignment {selectedAssignment?.assignment_id ?? 'N/A'}, Original Index {questionFormData.question_index ?? 'N/A'})</DialogTitle>
        <DialogContent>
          <TextField autoFocus id="edit-question-text" name="question_text" label="Question Text" fullWidth multiline minRows={4} maxRows={10} value={questionFormData.question_text} onChange={(e) => setQuestionFormData(prev => ({...prev, question_text: e.target.value }))} margin="dense" required error={!questionFormData.question_text?.trim() && questionFormData.question_text !== ''} helperText={!questionFormData.question_text?.trim() && questionFormData.question_text !== '' ? "Question text is required" : ""} disabled={actionLoading}/>
           <Typography variant="caption" display="block" sx={{ mt: 1, color: 'text.secondary' }}>Graphics/Figures are not currently supported via this interface.</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditQuestionDialogOpen(false)} disabled={actionLoading}>Cancel</Button>
          <Button onClick={handleEditQuestion} variant="contained" color="primary" disabled={actionLoading || !questionFormData.question_text?.trim()}> {actionLoading ? <CircularProgress size={24}/> : 'Save Changes'} </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Assignment Confirmation Dialog */}
      <ConfirmationDialog open={deleteAssignmentDialogOpen} onClose={() => !actionLoading && setDeleteAssignmentDialogOpen(false)} onConfirm={handleDeleteAssignment} title="Delete Assignment?" description={`Are you sure you want to permanently delete assignment (ID: ${selectedAssignment?.assignment_id ?? 'N/A'}) and all its questions? This action cannot be undone.`} confirmText="Delete" cancelText="Cancel" confirmColor="error" loading={actionLoading}/>

      {/* Delete Question Confirmation Dialog */}
      <ConfirmationDialog open={deleteQuestionDialogOpen} onClose={() => !actionLoading && setDeleteQuestionDialogOpen(false)} onConfirm={handleDeleteQuestion} title="Delete Question?" description={`Are you sure you want to permanently delete question (Original Index ${questionToDeleteIndex ?? 'N/A'}) from assignment (ID: ${selectedAssignment?.assignment_id ?? 'N/A'})? This action cannot be undone.`} confirmText="Delete" cancelText="Cancel" confirmColor="error" loading={actionLoading}/>

      {/* Alert Snackbar */}
      <Snackbar open={alertOpen} autoHideDuration={6000} onClose={() => setAlertOpen(false)} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert onClose={() => setAlertOpen(false)} severity={alertSeverity} variant="filled" sx={{ width: '100%' }}> {alertMessage} </Alert>
      </Snackbar>
    </Box>
  );
}