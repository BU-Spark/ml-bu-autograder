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

// Styled Components (kept as before)
const AssignmentCard = styled(Card)(({ theme }) => ({ /* ... styles ... */
    height: '100%', display: 'flex', flexDirection: 'column', transition: 'transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out', '&:hover': { transform: 'translateY(-4px)', boxShadow: theme.shadows[6], },
}));
const AssignmentCardContent = styled(CardContent)({ /* ... styles ... */
    flexGrow: 1, display: 'flex', flexDirection: 'column', minHeight: '100px',
});
const QuestionItem = styled(ListItem)(({ theme, isDragging }) => ({ /* ... styles ... */
    border: `1px solid ${theme.palette.divider}`, borderRadius: theme.shape.borderRadius, marginBottom: theme.spacing(1), backgroundColor: isDragging ? theme.palette.action.hover : theme.palette.background.paper, boxShadow: isDragging ? theme.shadows[3] : 'none', paddingRight: theme.spacing(16), // Pad for actions
    position: 'relative',
}));
const NoAssignmentsBox = styled(Box)(({ theme }) => ({ /* ... styles ... */
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
  const [editQuestionDialogOpen, setEditQuestionDialogOpen] = useState(false);
  const [deleteAssignmentDialogOpen, setDeleteAssignmentDialogOpen] = useState(false);
  const [deleteQuestionDialogOpen, setDeleteQuestionDialogOpen] = useState(false);

  // Form Data States
  const [newAssignmentData, setNewAssignmentData] = useState({ assignment_guidelines: '', questions: [{ question_text: '' }] });
  const [editAssignmentFormData, setEditAssignmentFormData] = useState({ assignment_guidelines: '' });
  // State for the question being added or edited
  const [questionFormData, setQuestionFormData] = useState({ question_text: '', question_index: null }); // Removed graphics for now
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
      const response = await assignmentService.getAssignment(courseId, semester, idToFetch, true); // Always include questions
      const assignmentData = response?.data;

      if (assignmentData && typeof assignmentData === 'object' && assignmentData.assignment_id) {
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
        throw new Error(`Invalid data structure received for assignment ${idToFetch}.`);
      }
    } catch (err) {
      console.error(`Error fetching assignment details for ID ${idToFetch}:`, err);
      const errorMsg = err.response?.data?.detail || err.message || `Failed to load details for assignment ${idToFetch}.`;
      setDetailsError(errorMsg);
      setSelectedAssignment(null);
    } finally {
      setLoadingDetails(false);
    }
  }, [courseId, semester]);

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
                    // Check if it's already selected to avoid redundant fetch if only URL changed shallowly
                    if (selectedAssignment?.assignment_id !== assignmentIdFromUrl) {
                        fetchAssignmentDetails(assignmentIdFromUrl);
                    }
                } else {
                    console.warn(`Assignment ID ${assignmentIdFromUrl} from URL not found in list. Clearing selection and URL param.`);
                    handleClearSelection(); // Clear selection and update URL
                }
             }

          } else {
            console.error("Invalid data received for assignments list (expected array):", assignmentsArray);
            setAssignments([]);
            setListError("Received invalid data format for assignments list.");
          }
        } catch (err) {
          console.error("Error fetching assignments list:", err);
          const errorMsg = err.response?.data?.detail || err.message || 'Failed to load assignments list.';
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
    // Update URL if needed (use assignment_id consistently)
    const currentQueryAssignmentId = router.query.assignment_id;
    if (currentQueryAssignmentId !== targetAssignmentId) {
      router.push(
        `/course/${courseId}/assignments?semester=${semester}&assignment_id=${targetAssignmentId}`,
        undefined,
        { shallow: true } // Avoid full reload if just changing query param
      );
    }
    // Fetch details even if ID is the same in URL, ensures latest data is shown
    fetchAssignmentDetails(targetAssignmentId);
  }, [courseId, semester, router, fetchAssignmentDetails]);

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
    // Reset form state completely for a new assignment
    setNewAssignmentData({ assignment_guidelines: '', questions: [{ question_text: '' }] });
    setCreateDialogOpen(true);
  };

  // Handler for guidelines text field in create dialog
  const handleGuidelinesChange = (event) => {
        const { value } = event.target;
        setNewAssignmentData(prev => ({
            ...prev, // Keep existing questions array
            assignment_guidelines: value // Update only guidelines
        }));
    };

 // Handler for adding a new empty question field to the create dialog
 const handleAddQuestionField = () => {
    setNewAssignmentData(prev => ({
      ...prev,
      questions: [...prev.questions, { question_text: '' }] // Add new empty question object
    }));
  };

  // Handler for removing a question field from the create dialog
  const handleRemoveQuestionField = (indexToRemove) => {
    // Prevent removing the last field
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
        return showAlert('Please add at least one question and ensure no question fields are empty.', 'warning');
    }
    setActionLoading(true);
    try {
      const assignmentPayload = {
        course_id: courseId,
        semester: semester,
        assignment_guidelines: newAssignmentData.assignment_guidelines || null,
        questions: newAssignmentData.questions
                            .filter(q => q.question_text?.trim())
                            .map(q => ({ question_text: q.question_text.trim(), question_graphics_figures: null })),
      };
      console.log("CREATING assignment with payload:", assignmentPayload);
      const response = await assignmentService.createAssignment(assignmentPayload);
      const createdAssignmentData = response?.data;
      console.log("RESPONSE from createAssignment:", response);

      if (!createdAssignmentData || !createdAssignmentData.assignment_id) {
          throw new Error(createdAssignmentData?.detail || "Invalid response after creating assignment.");
      }
      setAssignments(prev => [...prev, createdAssignmentData]); // Add to list
      setNewAssignmentData({ assignment_guidelines: '', questions: [{ question_text: '' }] }); // Reset form
      setCreateDialogOpen(false);
      showAlert(`Assignment created (ID: ${createdAssignmentData.assignment_id}).`);
      handleSelectAssignment(createdAssignmentData); // Select the new one
    } catch (error) {
      console.error("Failed to create assignment:", error);
       let displayError = 'Failed to create assignment.';
       if (error.response) { /* ... detailed error formatting ... */
            const detail = error.response.data?.detail; if (detail) { if (Array.isArray(detail)) { displayError = detail.map(err => `${err.loc?.join('.')} - ${err.msg}`).slice(0, 2).join('; '); if (detail.length > 2) displayError += '...'; } else if (typeof detail === 'string') { displayError = detail; } else { displayError = JSON.stringify(detail); } } else if (error.response.statusText) { displayError = `Error: ${error.response.status} ${error.response.statusText}`; }
       } else if (error.request) { displayError = "Could not contact server."; } else { displayError = error.message || "An unexpected error occurred."; }
      showAlert(displayError, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const openEditAssignmentDialog = (assignmentToEdit) => {
    if (!assignmentToEdit || !assignmentToEdit.assignment_id) return;
    setSelectedAssignment(assignmentToEdit); // Keep the selected assignment state
    setEditAssignmentFormData({ assignment_guidelines: assignmentToEdit.assignment_guidelines || '' });
    setEditAssignmentDialogOpen(true);
  };

  const handleUpdateAssignment = async () => {
    if (!selectedAssignment || !selectedAssignment.assignment_id || !semester || !courseId) return;
    const { assignment_guidelines } = editAssignmentFormData;
    const updatePayload = { assignment_guidelines: assignment_guidelines || null }; // Only send guidelines
    setActionLoading(true);
    try {
      console.log(`UPDATING assignment ${selectedAssignment.assignment_id} with payload:`, updatePayload);
      // API might return only updated fields or the whole object
      const response = await assignmentService.updateAssignmentMetadata(semester, courseId, selectedAssignment.assignment_id, updatePayload);
      const updatedAssignmentData = response?.data; // Expecting updated data back
      console.log("RESPONSE from updateAssignmentMetadata:", response);

      // Best practice: Refetch the details to ensure complete consistency,
      // especially if the backend response isn't guaranteed to be the full object.
      showAlert('Assignment updated. Refreshing details...');
      await fetchAssignmentDetails(selectedAssignment.assignment_id); // Refresh

      // Update the list optimistically *after* successful refresh potentially
      // Or just rely on list refetch if needed elsewhere

    } catch (error) {
      console.error("Failed to update assignment:", error);
       let displayError = 'Failed to update assignment.';
       if (error.response) { /* ... detailed error formatting ... */
            const detail = error.response.data?.detail; if (detail) { if (Array.isArray(detail)) { displayError = detail.map(err => `${err.loc?.join('.')} - ${err.msg}`).slice(0, 2).join('; '); if (detail.length > 2) displayError += '...'; } else if (typeof detail === 'string') { displayError = detail; } else { displayError = JSON.stringify(detail); } } else if (error.response.statusText) { displayError = `Error: ${error.response.status} ${error.response.statusText}`; }
       } else if (error.request) { displayError = "Could not contact server."; } else { displayError = error.message || "An unexpected error occurred."; }
      showAlert(displayError, 'error');
    } finally {
      setEditAssignmentDialogOpen(false); // Close dialog even if refresh fails
      setActionLoading(false);
    }
  };

  const handleDeleteAssignment = async () => {
    const assignmentObjectToDelete = selectedAssignment;
    const idToDelete = assignmentObjectToDelete?.assignment_id;
    console.log("DELETE request for assignment ID:", idToDelete);
    if (!idToDelete || !semester || !courseId) {
      showAlert(`Cannot delete: Missing required info.`, 'error');
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
      handleClearSelection(); // Clear selection
    } catch (error) {
      console.error("Failed to delete assignment:", error);
      let displayError = `Failed to delete assignment (ID: ${idToDelete}).`;
       if (error.response) { /* ... detailed error formatting ... */
            const detail = error.response.data?.detail; if (detail) { if (Array.isArray(detail)) { displayError = detail.map(err => `${err.loc?.join('.')} - ${err.msg}`).slice(0, 2).join('; '); if (detail.length > 2) displayError += '...'; } else if (typeof detail === 'string') { displayError = detail; } else { displayError = JSON.stringify(detail); } } else if (error.response.statusText) { displayError = `Error: ${error.response.status} ${error.response.statusText}`; }
       } else if (error.request) { displayError = "Could not contact server."; } else { displayError = error.message || "An unexpected error occurred."; }
      showAlert(displayError, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  // --- QUESTION CRUD --- (Triggered from Details Section)

  const openAddQuestionDialog = () => {
    if (!selectedAssignment || !selectedAssignment.assignment_id) {
      return showAlert('Select an assignment first.', 'warning');
    }
    setQuestionFormData({ question_text: '', question_index: null }); // Reset form state
    setAddQuestionDialogOpen(true);
  };

  const handleAddQuestion = async () => {
    if (!selectedAssignment || !selectedAssignment.assignment_id || !semester || !courseId || !questionFormData.question_text?.trim()) {
      return showAlert(!selectedAssignment ? 'No assignment selected.' : 'Question text is required.', 'warning');
    }
    // Payload for the backend API
    const questionPayload = { question_text: questionFormData.question_text.trim(), question_graphics_figures: null };
    setActionLoading(true);
    try {
      console.log(`ADDING question to assignment ${selectedAssignment.assignment_id}:`, questionPayload);
      // Assuming API returns { question_index: new_index } or similar
      const response = await assignmentService.addQuestion(semester, courseId, selectedAssignment.assignment_id, questionPayload);
      console.log("RESPONSE from addQuestion:", response);

      if (typeof response?.data?.question_index !== 'number') { // Check response.data
          throw new Error(response?.data?.detail || "Invalid response after adding question (missing index).");
      }
      showAlert('Question added. Refreshing details...');
      await fetchAssignmentDetails(selectedAssignment.assignment_id); // Refresh to get updated list and indices
    } catch (error) {
      console.error("Failed to add question:", error);
      let displayError = 'Failed to add question.';
       if (error.response) { /* ... detailed error formatting ... */
            const detail = error.response.data?.detail; if (detail) { if (Array.isArray(detail)) { displayError = detail.map(err => `${err.loc?.join('.')} - ${err.msg}`).slice(0, 2).join('; '); if (detail.length > 2) displayError += '...'; } else if (typeof detail === 'string') { displayError = detail; } else { displayError = JSON.stringify(detail); } } else if (error.response.statusText) { displayError = `Error: ${error.response.status} ${error.response.statusText}`; }
       } else if (error.request) { displayError = "Could not contact server."; } else { displayError = error.message || "An unexpected error occurred."; }
      showAlert(displayError, 'error');
    } finally {
      setAddQuestionDialogOpen(false); // Close dialog
      setActionLoading(false);
    }
  };

  const openEditQuestionDialog = (question) => {
    if (!question || typeof question.question_index !== 'number') return;
    // Set form state with the data of the question being edited
    setQuestionFormData({
      question_text: question.question_text || '',
      question_index: question.question_index, // Store the index being edited
    });
    setEditQuestionDialogOpen(true);
  };

  const handleEditQuestion = async () => {
    if (!selectedAssignment || !selectedAssignment.assignment_id || typeof questionFormData.question_index !== 'number' || !semester || !courseId || !questionFormData.question_text?.trim()) {
      return showAlert('Invalid data or context for editing question.', 'warning');
    }
    // API expects updated question data in the body
    const questionPayload = { question_text: questionFormData.question_text.trim(), question_graphics_figures: null };
    const indexToEdit = questionFormData.question_index; // Keep track of the index
    setActionLoading(true);
    try {
      console.log(`EDITING question index ${indexToEdit} for assignment ${selectedAssignment.assignment_id}:`, questionPayload);
      await assignmentService.editQuestion(semester, courseId, selectedAssignment.assignment_id, indexToEdit, questionPayload);
      console.log("RESPONSE from editQuestion successful (likely no content or updated question)");
      showAlert('Question updated. Refreshing details...');
      await fetchAssignmentDetails(selectedAssignment.assignment_id); // Refresh to get updated list
    } catch (error) {
      console.error("Failed to edit question:", error);
      let displayError = 'Failed to edit question.';
       if (error.response) { /* ... detailed error formatting ... */
             const detail = error.response.data?.detail; if (detail) { if (Array.isArray(detail)) { displayError = detail.map(err => `${err.loc?.join('.')} - ${err.msg}`).slice(0, 2).join('; '); if (detail.length > 2) displayError += '...'; } else if (typeof detail === 'string') { displayError = detail; } else { displayError = JSON.stringify(detail); } } else if (error.response.statusText) { displayError = `Error: ${error.response.status} ${error.response.statusText}`; }
       } else if (error.request) { displayError = "Could not contact server."; } else { displayError = error.message || "An unexpected error occurred."; }
      showAlert(displayError, 'error');
    } finally {
      setEditQuestionDialogOpen(false); // Close dialog
      setActionLoading(false);
    }
  };

  const onDragEnd = useCallback(async (result) => {
    const { source, destination } = result;
    if (!destination || !selectedAssignment?.assignment_id || !Array.isArray(selectedAssignment.questions) || selectedAssignment.questions.length < 2 || !semester || !courseId) return;
    if (destination.droppableId === source.droppableId && destination.index === source.index) return;

    console.log(`Dragging Q index ${source.index} to ${destination.index}`);
    const currentQuestions = Array.from(selectedAssignment.questions);
    const [reorderedItem] = currentQuestions.splice(source.index, 1);
    currentQuestions.splice(destination.index, 0, reorderedItem);

    // Optimistic UI Update
    setSelectedAssignment(prev => ({ ...prev, questions: currentQuestions }));

    // Payload for backend is the list of ORIGINAL question_index values in the NEW order
    const newIndexOrder = currentQuestions.map(q => q.question_index);
    console.log("SENDING new index order:", newIndexOrder);

    setActionLoading(true);
    try {
      await assignmentService.modifyQuestionOrder(semester, courseId, selectedAssignment.assignment_id, newIndexOrder);
      showAlert('Order updated. Refreshing details...');
      await fetchAssignmentDetails(selectedAssignment.assignment_id); // Refresh from backend
    } catch (error) {
      console.error("Failed to update question order:", error);
      showAlert(error.response?.data?.detail || error.message || 'Failed to update order.', 'error');
      // Revert UI on error by fetching original state
      showAlert('Reverting local order changes...');
      await fetchAssignmentDetails(selectedAssignment.assignment_id);
    } finally {
      setActionLoading(false);
    }
  }, [selectedAssignment, semester, courseId, fetchAssignmentDetails, showAlert]); // Added showAlert

  const openDeleteQuestionDialog = (index) => {
    if (typeof index !== 'number') return;
    console.log("Opening delete confirmation for question index:", index);
    setQuestionToDeleteIndex(index);
    setDeleteQuestionDialogOpen(true);
  };

  const handleDeleteQuestion = async () => {
    if (!selectedAssignment || !selectedAssignment.assignment_id || typeof questionToDeleteIndex !== 'number' || !semester || !courseId) {
        return showAlert("Cannot delete question: context or index missing.", "warning");
    }
    const assignmentId = selectedAssignment.assignment_id; // Store ID before closing dialog potentially
    setActionLoading(true);
    setDeleteQuestionDialogOpen(false); // Close dialog
    try {
      console.log(`DELETING question index ${questionToDeleteIndex} from assignment ${assignmentId}`);
      await assignmentService.removeQuestion(semester, courseId, assignmentId, questionToDeleteIndex);
       console.log("RESPONSE from removeQuestion successful (likely no content)");
      showAlert('Question deleted. Refreshing details...');
      await fetchAssignmentDetails(assignmentId); // Refresh to get updated list
    } catch (error) {
      console.error("Failed to delete question:", error);
      let displayError = 'Failed to delete question.';
       if (error.response) { /* ... detailed error formatting ... */
             const detail = error.response.data?.detail; if (detail) { if (Array.isArray(detail)) { displayError = detail.map(err => `${err.loc?.join('.')} - ${err.msg}`).slice(0, 2).join('; '); if (detail.length > 2) displayError += '...'; } else if (typeof detail === 'string') { displayError = detail; } else { displayError = JSON.stringify(detail); } } else if (error.response.statusText) { displayError = `Error: ${error.response.status} ${error.response.statusText}`; }
       } else if (error.request) { displayError = "Could not contact server."; } else { displayError = error.message || "An unexpected error occurred."; }
      showAlert(displayError, 'error');
      // No need to revert UI, fetchAssignmentDetails handles it
    } finally {
      setQuestionToDeleteIndex(null); // Reset index
      setActionLoading(false);
    }
  };

  // --- RENDER FUNCTIONS ---

  const renderAssignmentList = () => {
    if (loadingAssignments) { /* ... skeleton loading ... */
        return <Grid container spacing={3} sx={{ mb: 4 }}>{[1, 2, 3].map(n => <Grid item xs={12} sm={6} md={4} key={`skeleton-${n}`}><CardSkeleton height={150} /></Grid>)}</Grid>;
    }
    if (listError) return <Alert severity="error" sx={{ mb: 3 }}>{listError}</Alert>;
    if (!Array.isArray(assignments) || !assignments.length) { /* ... no assignments box ... */
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
                  <Typography variant="body2" color="text.secondary" sx={{ overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', flexGrow: 1, }}>
                    {assignment.assignment_guidelines || 'No guidelines.'}
                  </Typography>
                </AssignmentCardContent>
              </CardActionArea>
              <CardActions sx={{ justifyContent: 'flex-end', pt: 0, pb: 1, px: 1 }}>
                <IconButton title="Edit Assignment Info" size="small" onClick={(e) => { e.stopPropagation(); openEditAssignmentDialog(assignment); }} disabled={actionLoading}> <EditIcon fontSize="small" /> </IconButton>
                 {/* Ensure log and setSelectedAssignment happens in delete button onClick */}
                <IconButton title="Delete Assignment" size="small" onClick={(e) => { e.stopPropagation(); console.log("--- Delete Button Click ---"); console.log("Assignment object from map:", assignment); console.log("ID in this object:", assignment?.assignment_id); console.log("---------------------------"); setSelectedAssignment(assignment); setDeleteAssignmentDialogOpen(true); }} disabled={actionLoading} color="error"> <DeleteIcon fontSize="small" /> </IconButton>
              </CardActions>
            </AssignmentCard>
          </Grid>
        ))}
      </Grid>
    );
  };

  const renderAssignmentDetails = () => {
    if (!selectedAssignment && assignmentIdFromUrl && !loadingAssignments && assignments.length > 0 && !listError) {
        // Case: URL has an ID, list is loaded, but details are not yet loading/loaded or failed
        return (
             <Paper elevation={0} variant="outlined" sx={{ mt: 4, p: 3, textAlign: 'center', borderStyle: 'dashed' }}>
                <Typography color="text.secondary">Loading assignment details...</Typography>
                <CircularProgress size={20} sx={{ml: 1}}/>
             </Paper>
        );
    }
    if (loadingDetails) { /* ... loading spinner ... */
        return <Paper elevation={0} sx={{ mt: 4, p: 3, textAlign: 'center' }}><CircularProgress /><Typography sx={{ mt: 1 }}>Loading details...</Typography></Paper>;
    }
    if (detailsError) { /* ... error alert ... */
        return <Paper elevation={0} sx={{ mt: 4, p: 3 }}><Alert severity="error">{detailsError}</Alert></Paper>;
    }
    if (!selectedAssignment || !selectedAssignment.assignment_id) { /* ... prompt to select ... */
      if (!loadingAssignments && assignments.length > 0) {
        return <Paper elevation={0} variant="outlined" sx={{ mt: 4, p: 3, textAlign: 'center', borderStyle: 'dashed' }}><Typography color="text.secondary">Select an assignment from the list above.</Typography></Paper>;
      }
      return null; // Don't show anything if list is loading or empty
    }

    // --- Render Details Section ---
    return (
      <Paper elevation={3} sx={{ mt: 4, p: { xs: 1, sm: 2, md: 3 } }}>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 1 }}>
          <Typography variant="h5" component="h2">{`Assignment ${selectedAssignment.assignment_id}`}</Typography>
          <Box>
            <Button variant="outlined" size="small" startIcon={<EditIcon />} onClick={() => openEditAssignmentDialog(selectedAssignment)} sx={{ mr: 1 }} disabled={actionLoading}> Edit Info </Button>
            <Button variant="outlined" size="small" color="error" startIcon={<DeleteIcon />} onClick={() => setDeleteAssignmentDialogOpen(true)} disabled={actionLoading}> Delete Assignment </Button>
          </Box>
        </Box>
        {/* Guidelines */}
        <Typography variant="body2" color="text.secondary" paragraph sx={{ whiteSpace: 'pre-wrap', maxHeight: '150px', overflowY: 'auto', border: '1px solid', borderColor: 'divider', p: 1, borderRadius: 1, bgcolor: 'action.hover', }}>
          {selectedAssignment.assignment_guidelines || 'No guidelines specified.'}
        </Typography>
        <Divider sx={{ my: 3 }} />
        {/* Questions Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Questions</Typography>
          <Button variant="contained" size="small" startIcon={<AddIcon />} onClick={openAddQuestionDialog} disabled={actionLoading}> Add Question </Button>
        </Box>
        {/* Questions List or Placeholder */}
        {(!Array.isArray(selectedAssignment.questions) || !selectedAssignment.questions.length) ? (
          <Typography color="text.secondary" sx={{ fontStyle: 'italic', textAlign: 'center', py: 2 }}> No questions added yet. </Typography>
        ) : (
          <DragDropContext onDragEnd={onDragEnd}>
            <Droppable droppableId={`questions-${selectedAssignment.assignment_id}`}>
              {(provided) => (
                <List {...provided.droppableProps} ref={provided.innerRef} disablePadding>
                  {selectedAssignment.questions.map((question, index) => (
                     <Draggable key={`${selectedAssignment.assignment_id}-${question.question_index}`} draggableId={`${selectedAssignment.assignment_id}-${question.question_index}`} index={index} isDragDisabled={actionLoading}>
                      {(providedDraggable, snapshot) => (
                        <QuestionItem ref={providedDraggable.innerRef} {...providedDraggable.draggableProps} isDragging={snapshot.isDragging}
                          secondaryAction={ /* Actions: Edit, Delete, Drag Handle */
                            <Box sx={{ display: 'flex', alignItems: 'center', position: 'absolute', right: theme.spacing(1), top: '50%', transform: 'translateY(-50%)' }}>
                              <IconButton edge="end" title="Edit Question" sx={{ mr: 0.5 }} onClick={() => openEditQuestionDialog(question)} disabled={actionLoading}> <EditIcon fontSize="small"/> </IconButton>
                              <IconButton edge="end" title="Delete Question" onClick={() => openDeleteQuestionDialog(question.question_index)} disabled={actionLoading} color="error"> <DeleteIcon fontSize="small"/> </IconButton>
                              <Box {...providedDraggable.dragHandleProps} sx={{ display: 'inline-flex', alignItems: 'center', ml: 1, cursor: actionLoading ? 'not-allowed' : 'grab', color: 'action.active' }} title="Drag to reorder"> <DragIndicatorIcon /> </Box>
                            </Box>
                          }>
                          <ListItemIcon sx={{ minWidth: 'auto', mr: 1.5, alignSelf: 'flex-start', pt: 1 }}> <Typography variant="body2" sx={{ fontWeight: 'bold' }}>{`Q${index + 1}:`}</Typography> </ListItemIcon>
                          <ListItemText primary={question.question_text || '(No text)'} primaryTypographyProps={{ sx: { wordBreak: 'break-word', whiteSpace: 'pre-wrap', pr: 1 } }}/>
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
      </Paper>
    );
  };


  // --- MAIN RETURN ---
  return (
    <Box sx={{ p: { xs: 1, sm: 2, md: 3 } }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 1 }}>
        <IconButton title="Back to Course Overview" aria-label="back" onClick={() => (courseId && semester) && router.push(`/course/${courseId}?semester=${semester}`)} disabled={!courseId || !semester} sx={{ mr: 1 }}> <ArrowBackIcon /> </IconButton>
        <Typography variant="h4" component="h1" sx={{ flexGrow: 1 }}>Course Assignments</Typography>
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
      <Dialog open={createDialogOpen} onClose={() => !actionLoading && setCreateDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Create New Assignment</DialogTitle>
        <DialogContent>
          <TextField autoFocus id="new-assignment-guidelines" name="assignment_guidelines" label="Assignment Guidelines (Optional)" fullWidth multiline rows={4} value={newAssignmentData.assignment_guidelines} onChange={handleGuidelinesChange} margin="dense" disabled={actionLoading} sx={{ mb: 3 }} />
          <Divider sx={{ my: 2 }} />
          <Typography variant="h6" gutterBottom>Questions</Typography>
          {newAssignmentData.questions.map((q, index) => (
            <Box key={index} sx={{ display: 'flex', alignItems: 'center', mb: 1.5 }}>
              <TextField id={`new-question-${index}`} name={`question_text_${index}`} label={`Question ${index + 1} Text`} fullWidth multiline rows={2} value={q.question_text} onChange={(e) => handleQuestionTextChange(index, e.target.value)} margin="dense" required error={!q.question_text?.trim() && q.question_text !== ''} disabled={actionLoading} sx={{ mr: 1 }} />
              {newAssignmentData.questions.length > 1 && ( <IconButton title={`Remove Question ${index + 1}`} onClick={() => handleRemoveQuestionField(index)} disabled={actionLoading} color="error" size="small"> <DeleteIcon /> </IconButton> )}
            </Box>
          ))}
          <Button variant="outlined" size="small" startIcon={<AddIcon />} onClick={handleAddQuestionField} disabled={actionLoading} sx={{ mt: 1 }}> Add Another Question </Button>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)} disabled={actionLoading}>Cancel</Button>
          <Button onClick={handleCreateAssignment} variant="contained" color="primary" disabled={actionLoading || newAssignmentData.questions.some(q => !q.question_text?.trim())}> {actionLoading ? <CircularProgress size={24}/> : 'Create Assignment'} </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Assignment Dialog */}
      <Dialog open={editAssignmentDialogOpen} onClose={() => !actionLoading && setEditAssignmentDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Edit Assignment Info (ID: {selectedAssignment?.assignment_id})</DialogTitle>
        <DialogContent>
          <TextField autoFocus id="edit-assignment-guidelines" name="assignment_guidelines" label="Assignment Guidelines (Optional)" fullWidth multiline rows={4} value={editAssignmentFormData.assignment_guidelines} onChange={(e) => setEditAssignmentFormData({ assignment_guidelines: e.target.value })} margin="dense" disabled={actionLoading}/>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditAssignmentDialogOpen(false)} disabled={actionLoading}>Cancel</Button>
          <Button onClick={handleUpdateAssignment} variant="contained" color="primary" disabled={actionLoading}> {actionLoading ? <CircularProgress size={24}/> : 'Save Changes'} </Button>
        </DialogActions>
      </Dialog>

      {/* Add Question Dialog */}
      <Dialog open={addQuestionDialogOpen} onClose={() => !actionLoading && setAddQuestionDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Add New Question to Assignment {selectedAssignment?.assignment_id}</DialogTitle>
        <DialogContent>
          <TextField autoFocus id="add-question-text" name="question_text" label="Question Text" fullWidth multiline rows={6} value={questionFormData.question_text} onChange={(e) => setQuestionFormData(prev => ({...prev, question_text: e.target.value }))} margin="dense" required error={!questionFormData.question_text?.trim() && questionFormData.question_text !== ''} helperText={!questionFormData.question_text?.trim() && questionFormData.question_text !== '' ? "Question text is required" : ""} disabled={actionLoading}/>
          <Typography variant="caption" display="block" sx={{ mt: 1 }}>Graphics/Figures not yet supported.</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddQuestionDialogOpen(false)} disabled={actionLoading}>Cancel</Button>
          {/* *** FIX: Call handleAddQuestion *** */}
          <Button onClick={handleAddQuestion} variant="contained" color="primary" disabled={actionLoading || !questionFormData.question_text?.trim()}> {actionLoading ? <CircularProgress size={24}/> : 'Add Question'} </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Question Dialog */}
      <Dialog open={editQuestionDialogOpen} onClose={() => !actionLoading && setEditQuestionDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Edit Question (Assignment {selectedAssignment?.assignment_id}, Original Index {questionFormData.question_index ?? 'N/A'})</DialogTitle>
        <DialogContent>
          <TextField autoFocus id="edit-question-text" name="question_text" label="Question Text" fullWidth multiline rows={6} value={questionFormData.question_text} onChange={(e) => setQuestionFormData(prev => ({...prev, question_text: e.target.value }))} margin="dense" required error={!questionFormData.question_text?.trim() && questionFormData.question_text !== ''} helperText={!questionFormData.question_text?.trim() && questionFormData.question_text !== '' ? "Question text is required" : ""} disabled={actionLoading}/>
          <Typography variant="caption" display="block" sx={{ mt: 1 }}>Graphics/Figures not yet supported.</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditQuestionDialogOpen(false)} disabled={actionLoading}>Cancel</Button>
           {/* *** FIX: Call handleEditQuestion *** */}
          <Button onClick={handleEditQuestion} variant="contained" color="primary" disabled={actionLoading || !questionFormData.question_text?.trim()}> {actionLoading ? <CircularProgress size={24}/> : 'Save Changes'} </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Assignment Confirmation Dialog */}
      <ConfirmationDialog open={deleteAssignmentDialogOpen} onClose={() => !actionLoading && setDeleteAssignmentDialogOpen(false)} onConfirm={handleDeleteAssignment} title="Delete Assignment?" description={`Are you sure you want to permanently delete assignment (ID: ${selectedAssignment?.assignment_id ?? 'N/A'}) and all its questions? This cannot be undone.`} confirmText="Delete" cancelText="Cancel" confirmColor="error" loading={actionLoading}/>

      {/* Delete Question Confirmation Dialog */}
      <ConfirmationDialog open={deleteQuestionDialogOpen} onClose={() => !actionLoading && setDeleteQuestionDialogOpen(false)} onConfirm={handleDeleteQuestion} title="Delete Question?" description={`Are you sure you want to permanently delete question (Original Index ${questionToDeleteIndex ?? 'N/A'}) from assignment (ID: ${selectedAssignment?.assignment_id ?? 'N/A'})? This cannot be undone.`} confirmText="Delete" cancelText="Cancel" confirmColor="error" loading={actionLoading}/>

      {/* Alert Snackbar */}
      <Snackbar open={alertOpen} autoHideDuration={6000} onClose={() => setAlertOpen(false)} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert onClose={() => setAlertOpen(false)} severity={alertSeverity} variant="filled" sx={{ width: '100%' }}> {alertMessage} </Alert>
      </Snackbar>
    </Box>
  );
}