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
  Paper, Snackbar, TextField, Tooltip, Typography, useTheme // Added Tooltip
} from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  Add as AddIcon, ArrowBack as ArrowBackIcon, Assignment as AssignmentIcon,
  Delete as DeleteIcon, Edit as EditIcon, DragIndicator as DragIndicatorIcon,
  Assessment as AssessmentIcon // <-- Added Grading Icon
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
    border: `1px solid ${theme.palette.divider}`, borderRadius: theme.shape.borderRadius, marginBottom: theme.spacing(1), backgroundColor: isDragging ? theme.palette.action.hover : theme.palette.background.paper, boxShadow: isDragging ? theme.shadows[3] : 'none', paddingRight: theme.spacing(18), // <-- Increased paddingRight slightly more for 3 icons
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
  // assignment_id is expected to be a string by the backend
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
  const [questionFormData, setQuestionFormData] = useState({ question_text: '', question_index: null }); // Store index for edit
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
    // Log the full error structure for debugging backend issues
    console.error(`API Error occurred (${defaultMessage}):`, error.response || error.request || error);
    if (error.response) {
      const detail = error.response.data?.detail;
      const status = error.response.status;
      if (detail) {
        if (Array.isArray(detail)) {
          // Handle Pydantic validation errors
          displayError = detail.map(err => `${err.loc?.join('.')} - ${err.msg}`).slice(0, 3).join('; ');
          if (detail.length > 3) displayError += '...';
          // Add status code for context
          displayError = `[${status}] ${displayError}`;
        } else if (typeof detail === 'string') {
          displayError = `[${status}] ${detail}`; // Add status code
        } else {
          try { displayError = `[${status}] ${JSON.stringify(detail)}`; } catch { /* ignore */ }
        }
      } else if (error.response.statusText) {
        displayError = `Error: ${status} ${error.response.statusText}`;
      } else {
         displayError = `Error: Received status code ${status}`;
      }
    } else if (error.request) {
      displayError = "Network Error: Could not contact server.";
    } else if (error.message) {
      displayError = error.message;
    }
    // Return the formatted error message
    return displayError;
  };


  // --- DATA FETCHING ---

    // Memoized function to clear selection and URL parameter
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
  }, [courseId, semester, router]); // router likely stable, but included


  const fetchAssignmentDetails = useCallback(async (idToFetch) => {
    // Expect idToFetch to be the string ID
    if (!courseId || !semester || !idToFetch) {
      console.warn("fetchAssignmentDetails: Missing context or ID.", { courseId, semester, idToFetch });
      setSelectedAssignment(null);
      setDetailsError(null); // Clear error when context is missing
      return;
    }
    setLoadingDetails(true);
    setDetailsError(null);
    console.log(`FETCHING details for assignment ID: ${idToFetch} (Type: ${typeof idToFetch})`); // Log type
    try {
      // Pass the string ID directly to the service
      const response = await assignmentService.getAssignment(courseId, semester, idToFetch, true);
      const assignmentData = response?.data;

      if (assignmentData && typeof assignmentData === 'object' && typeof assignmentData.assignment_id !== 'undefined') {
        console.log("RECEIVED assignment data:", assignmentData);
        if (!Array.isArray(assignmentData.questions)) {
             console.warn("Questions field not an array, setting to empty:", assignmentData.questions);
             assignmentData.questions = [];
        } else {
             // Sort questions by index for consistent display
             assignmentData.questions.sort((a, b) => (a.question_index ?? Infinity) - (b.question_index ?? Infinity));
        }
        setSelectedAssignment(assignmentData);
      } else {
        throw new Error(`Invalid data structure received for assignment ${idToFetch}. Expected object with assignment_id.`);
      }
    } catch (err) {
      // The error here could be the one from the backend if it failed validation or lookup
      console.error(`Error fetching assignment details for ID ${idToFetch}:`, err);
      const errorMsg = formatApiError(err, `Failed to load details for assignment ID: ${idToFetch}.`);
      setDetailsError(errorMsg);
      setSelectedAssignment(null); // Clear selection on error
    } finally {
      setLoadingDetails(false);
    }
  }, [courseId, semester]); // Dependencies


  // useEffect to fetch assignments list and handle URL parameter
  useEffect(() => {
    if (courseId && semester) {
      const fetchAssignments = async () => {
        setLoadingAssignments(true);
        setListError(null);
        // Clear selection ONLY if no ID in URL initially
        if (!assignmentIdFromUrl) {
          setSelectedAssignment(null);
          setDetailsError(null);
        }

        try {
          console.log(`FETCHING assignments list for ${courseId}/${semester}`);
          // Adapt based on how assignmentService.getAssignments returns data
          const response = await assignmentService.getAssignments(courseId, semester);
          // Assuming response structure might be { data: [...] } or just [...]
          const assignmentsArray = Array.isArray(response) ? response : response?.data;

          if (Array.isArray(assignmentsArray)) {
             console.log("RECEIVED assignments list:", assignmentsArray);
             // Basic validation: filter out items without an assignment_id
             const validAssignments = assignmentsArray.filter(a => a && typeof a === 'object' && typeof a.assignment_id !== 'undefined');
             if (validAssignments.length !== assignmentsArray.length) {
                console.warn("Some items in the fetched assignments list were invalid:", assignmentsArray);
             }
             setAssignments(validAssignments);

             // --- Handle assignment ID from URL ---
             if (assignmentIdFromUrl) {
                // Check if the string ID exists in the fetched list
                // Compare as strings for consistency
                const assignmentExists = validAssignments.some(a => String(a.assignment_id) === assignmentIdFromUrl);

                if (assignmentExists) {
                    console.log(`URL includes assignment_id=${assignmentIdFromUrl}. Fetching its details.`);
                    // Fetch if not already selected, if details failed previously, or if data seems stale
                    // Compare assignment_id as string here too
                    if (String(selectedAssignment?.assignment_id) !== assignmentIdFromUrl || detailsError || !selectedAssignment) {
                        fetchAssignmentDetails(assignmentIdFromUrl); // Pass the string ID
                    } else {
                        console.log(`Assignment ${assignmentIdFromUrl} is already selected and loaded.`);
                    }
                } else {
                    console.warn(`Assignment ID ${assignmentIdFromUrl} from URL not found in list. Clearing selection and URL param.`);
                    showAlert(`Assignment with ID '${assignmentIdFromUrl}' not found for this course/semester.`, 'warning');
                    handleClearSelection(); // Clear selection and update URL
                }
             } else {
                 // If no assignment ID in URL, ensure selection is cleared (might be redundant if handled above)
                 handleClearSelection();
             }

          } else {
            console.error("Invalid data received for assignments list (expected array or object with data array):", response);
            setAssignments([]);
            setListError("Received invalid data format for assignments list.");
             // If URL had an ID, clear it since we can't verify it
            if (assignmentIdFromUrl) handleClearSelection();
          }
        } catch (err) {
          console.error("Error fetching assignments list:", err);
          const errorMsg = formatApiError(err, 'Failed to load assignments list.');
          setListError(errorMsg);
          setAssignments([]); // Set empty array on error
           // If URL had an ID, clear it on error
          if (assignmentIdFromUrl) handleClearSelection();
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
      setDetailsError(null);
    }
  // Include dependencies. Use stable functions where possible.
  }, [courseId, semester, assignmentIdFromUrl, fetchAssignmentDetails, handleClearSelection, showAlert]);


  // --- UI Handlers ---

  const handleSelectAssignment = useCallback((assignment) => {
    if (!courseId || !semester || !assignment?.assignment_id) return;
    // Use the assignment_id directly (it's already the correct type, string or number, from the assignments list)
    const targetAssignmentId = String(assignment.assignment_id); // Ensure comparison/URL update uses string
    console.log(`SELECTING assignment ID: ${targetAssignmentId}`);

    const needsFetch = String(selectedAssignment?.assignment_id) !== targetAssignmentId || detailsError || !selectedAssignment?.questions; // Fetch if different, failed, or lacks details

    const currentQueryAssignmentId = router.query.assignment_id;
    // Update URL only if it differs from the target or isn't present
    if (String(currentQueryAssignmentId) !== targetAssignmentId) {
      console.log(`Updating URL to include assignment_id=${targetAssignmentId}`);
      router.push(
        // Use the targetAssignmentId (string) in the URL
        `/course/${courseId}/assignments?semester=${semester}&assignment_id=${targetAssignmentId}`,
        undefined,
        { shallow: true } // Avoid full reload if just changing query param
      );
    }

    // Fetch details if necessary, otherwise just update local state
    if (needsFetch) {
         fetchAssignmentDetails(targetAssignmentId); // Pass the string ID
    } else {
         // Update local state if not fetching
         setSelectedAssignment(assignment);
         setDetailsError(null); // Clear previous error if any
    }

  }, [courseId, semester, router, fetchAssignmentDetails, selectedAssignment, detailsError]);

   // <<<--- NEW Handler for navigating to the grading page --- >>>
   const handleGoToGrading = useCallback((assignment) => {
        if (!courseId || !semester || !assignment?.assignment_id) {
             showAlert('Cannot navigate to grading: Missing course, semester, or assignment ID.', 'error');
             console.error("handleGoToGrading preconditions failed:", { courseId, semester, assignment });
             return;
        }
        const targetAssignmentId = String(assignment.assignment_id); // Ensure string ID
        const gradingUrl = `/course/${courseId}/grading?semester=${semester}&assignment_id=${targetAssignmentId}`;
        console.log(`Navigating to grading page: ${gradingUrl}`);
        router.push(gradingUrl);
   }, [courseId, semester, router, showAlert]); // Dependencies


  // --- ASSIGNMENT CRUD ---

  const openCreateDialog = () => {
    setNewAssignmentData({ assignment_guidelines: '', questions: [{ question_text: '' }] });
    setCreateDialogOpen(true);
  };

  const handleGuidelinesChange = (event) => {
        const { value } = event.target;
        setNewAssignmentData(prev => ({
            ...prev,
            assignment_guidelines: value
        }));
    };

 const handleAddQuestionField = () => {
    setNewAssignmentData(prev => ({
      ...prev,
      questions: [...prev.questions, { question_text: '' }]
    }));
  };

  const handleRemoveQuestionField = (indexToRemove) => {
    if (newAssignmentData.questions.length <= 1) return;
    setNewAssignmentData(prev => ({
      ...prev,
      questions: prev.questions.filter((_, index) => index !== indexToRemove)
    }));
  };

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
        assignment_guidelines: newAssignmentData.assignment_guidelines?.trim() || null,
        questions: newAssignmentData.questions
                            .map(q => q.question_text?.trim())
                            .filter(text => text)
                            .map(text => ({ question_text: text, question_graphics_figures: null })), // Backend handles indexing
      };
      console.log("CREATING assignment with payload:", assignmentPayload);
      const response = await assignmentService.createAssignment(assignmentPayload);
      const createdAssignmentData = response?.data;
      console.log("RESPONSE from createAssignment:", response);

      if (!createdAssignmentData || typeof createdAssignmentData.assignment_id === 'undefined') {
          // Use formatApiError if the response contains error details
          throw new Error(formatApiError({ response }, "Invalid response after creating assignment.") || "Invalid response after creating assignment.");
      }

      // Add to list using the *full* data returned if possible
      setAssignments(prev => [...prev, createdAssignmentData]);

      setNewAssignmentData({ assignment_guidelines: '', questions: [{ question_text: '' }] });
      setCreateDialogOpen(false);
      showAlert(`Assignment created (ID: ${createdAssignmentData.assignment_id}). Selecting it...`);
      // Select the new one - pass the full object from response
      handleSelectAssignment(createdAssignmentData);

    } catch (error) {
      console.error("Failed to create assignment:", error);
      // Display formatted error from catch or the one thrown above
      const displayError = (error instanceof Error && error.message.includes("Invalid response"))
                             ? error.message
                             : formatApiError(error, 'Failed to create assignment.');
      showAlert(displayError, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const openEditAssignmentDialog = (assignmentToEdit) => {
    if (!assignmentToEdit || typeof assignmentToEdit.assignment_id === 'undefined') return;
    // Ensure the selected assignment state is updated for the dialog title and subsequent update action
    setSelectedAssignment(assignmentToEdit);
    setEditAssignmentFormData({ assignment_guidelines: assignmentToEdit.assignment_guidelines || '' });
    setEditAssignmentDialogOpen(true);
  };

  const handleUpdateAssignment = async () => {
    // Use the selectedAssignment state which was set when opening the dialog
    if (!selectedAssignment || typeof selectedAssignment.assignment_id === 'undefined' || !semester || !courseId) {
         return showAlert("Cannot update: Missing required info.", 'error');
    }
    const { assignment_guidelines } = editAssignmentFormData;
    const updatePayload = { assignment_guidelines: assignment_guidelines?.trim() || null };
    const assignmentId = selectedAssignment.assignment_id; // Get ID (string or number)

    setActionLoading(true);
    try {
      console.log(`UPDATING assignment ${assignmentId} metadata with payload:`, updatePayload);
      // Pass semester, courseId, assignmentId (as string/number), and payload
      await assignmentService.updateAssignmentMetadata(semester, courseId, assignmentId, updatePayload);
      console.log("RESPONSE from updateAssignmentMetadata successful.");

      // Optimistic UI Update for the list (compare IDs carefully)
      setAssignments(prevAssignments => prevAssignments.map(a =>
           String(a.assignment_id) === String(assignmentId) // Compare as strings
            ? { ...a, assignment_guidelines: updatePayload.assignment_guidelines }
            : a
      ));

      // Optimistic UI Update for the details view
      setSelectedAssignment(prev => prev ? { ...prev, assignment_guidelines: updatePayload.assignment_guidelines } : null);

      showAlert('Assignment info updated successfully.');

    } catch (error) {
      console.error("Failed to update assignment:", error);
      const displayError = formatApiError(error, 'Failed to update assignment info.');
      showAlert(displayError, 'error');
      // Consider reverting optimistic update or just fetching fresh data on error
      // await fetchAssignmentDetails(assignmentId);
    } finally {
      setEditAssignmentDialogOpen(false); // Close dialog
      setActionLoading(false);
    }
  };

  // Ensure selectedAssignment is set before opening the delete dialog
  const openDeleteAssignmentDialog = (assignmentToDelete) => {
    if (!assignmentToDelete || typeof assignmentToDelete.assignment_id === 'undefined') return;
    console.log("Setting selected assignment for delete:", assignmentToDelete);
    setSelectedAssignment(assignmentToDelete); // Crucial step
    setDeleteAssignmentDialogOpen(true);
  };

  const handleDeleteAssignment = async () => {
    const assignmentObjectToDelete = selectedAssignment; // Use the one set by openDeleteAssignmentDialog
    const idToDelete = assignmentObjectToDelete?.assignment_id; // Get ID (string or number)

    console.log("DELETE request for assignment ID:", idToDelete);
    if (typeof idToDelete === 'undefined' || idToDelete === null || !semester || !courseId) {
      showAlert(`Cannot delete: Missing required info (Assignment ID, Semester, or Course ID).`, 'error');
      console.error("Delete preconditions failed:", { idToDelete, semester, courseId });
      setDeleteAssignmentDialogOpen(false); // Close dialog even on precondition failure
      return;
    }

    setActionLoading(true);
    setDeleteAssignmentDialogOpen(false); // Close dialog immediately

    try {
      // Pass courseId, semester, idToDelete (as string/number)
      await assignmentService.deleteAssignment(courseId, semester, idToDelete);
      console.log(`Assignment ${idToDelete} reported as deleted by API.`);
      showAlert(`Assignment (ID: ${idToDelete}) deleted successfully.`);

      // Update list state (compare IDs carefully)
      setAssignments(prev => prev.filter(a => String(a.assignment_id) !== String(idToDelete))); // Compare as strings

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
    const assignmentId = selectedAssignment.assignment_id; // Store ID (string or number)
    // Payload for the backend API
    const questionPayload = { question_text: questionFormData.question_text.trim(), question_graphics_figures: null };
    setActionLoading(true);
    try {
      console.log(`ADDING question to assignment ${assignmentId}:`, questionPayload);
      // API might return the new question object or just confirmation/index
      // Pass semester, courseId, assignmentId (as string/number), and payload
      const response = await assignmentService.addQuestion(semester, courseId, assignmentId, questionPayload);
      console.log("RESPONSE from addQuestion:", response);

      if (response?.status >= 200 && response?.status < 300) {
        showAlert('Question added. Refreshing details...');
        await fetchAssignmentDetails(assignmentId); // Refresh to get updated list and indices
      } else {
         // Use formatApiError if the response contains error details
        throw new Error(formatApiError({ response }, "Failed to add question, invalid response received.") || "Failed to add question, invalid response received.");
      }
    } catch (error) {
      console.error("Failed to add question:", error);
      // Display formatted error
      const displayError = (error instanceof Error && error.message.includes("invalid response"))
                             ? error.message
                             : formatApiError(error, 'Failed to add question.');
      showAlert(displayError, 'error');
    } finally {
      setAddQuestionDialogOpen(false); // Close dialog
      setActionLoading(false);
    }
  };

  // Function to open the edit dialog
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

  // Function to handle the edit API call
  const handleEditQuestion = async () => {
    const { question_text, question_index } = questionFormData;

    if (!selectedAssignment || typeof selectedAssignment.assignment_id === 'undefined' || typeof question_index !== 'number' || !semester || !courseId) {
      return showAlert('Invalid context for editing question.', 'warning');
    }
    if (!question_text?.trim()) {
         return showAlert('Question text cannot be empty.', 'warning');
    }

    const assignmentId = selectedAssignment.assignment_id; // Store ID (string or number)
    // API expects updated question data in the body
    const questionPayload = { question_text: question_text.trim(), question_graphics_figures: null }; // Add other fields if needed
    const indexToEdit = question_index;

    setActionLoading(true);
    try {
      console.log(`EDITING question index ${indexToEdit} for assignment ${assignmentId}:`, questionPayload);
      // Pass semester, courseId, assignmentId (as string/number), index, and payload
      await assignmentService.editQuestion(semester, courseId, assignmentId, indexToEdit, questionPayload);
      console.log("RESPONSE from editQuestion successful.");

      showAlert('Question updated. Refreshing details...');
      await fetchAssignmentDetails(assignmentId); // Refresh to get updated list

    } catch (error) {
      console.error(`Failed to edit question index ${indexToEdit}:`, error);
      const displayError = formatApiError(error, 'Failed to edit question.');
      showAlert(displayError, 'error');
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
    const assignmentId = selectedAssignment.assignment_id; // Store ID (string or number)

    setActionLoading(true);
    try {
       // Pass semester, courseId, assignmentId (as string/number), and new order array
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
    const assignmentId = selectedAssignment.assignment_id; // Store ID (string or number)
    const indexToDelete = questionToDeleteIndex; // Store index

    setActionLoading(true);
    setDeleteQuestionDialogOpen(false); // Close dialog
    try {
      console.log(`DELETING question index ${indexToDelete} from assignment ${assignmentId}`);
       // Pass semester, courseId, assignmentId (as string/number), and index
      await assignmentService.removeQuestion(semester, courseId, assignmentId, indexToDelete);
      console.log("RESPONSE from removeQuestion successful.");
      showAlert('Question deleted. Refreshing details...');
      await fetchAssignmentDetails(assignmentId); // Refresh to get updated list
    } catch (error) {
      console.error(`Failed to delete question index ${indexToDelete}:`, error);
      const displayError = formatApiError(error, 'Failed to delete question.');
      showAlert(displayError, 'error');
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
            <AssignmentCard variant="outlined" sx={{ borderColor: String(selectedAssignment?.assignment_id) === String(assignment.assignment_id) ? 'primary.main' : 'divider' }}> {/* Compare as strings */}
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
                 {/* <<<--- NEW Grading Icon Button --- >>> */}
                <Tooltip title="Grade Submissions">
                    <span> {/* Span needed for tooltip on disabled button */}
                        <IconButton
                            size="small"
                            onClick={(e) => { e.stopPropagation(); handleGoToGrading(assignment); }}
                            disabled={actionLoading || !courseId || !semester} // Disable if context missing
                            color="primary" // Or default color
                        >
                            <AssessmentIcon fontSize="small" />
                        </IconButton>
                    </span>
                </Tooltip>
                <IconButton title="Edit Assignment Info" size="small" onClick={(e) => { e.stopPropagation(); openEditAssignmentDialog(assignment); }} disabled={actionLoading}> <EditIcon fontSize="small" /> </IconButton>
                <IconButton title="Delete Assignment" size="small" onClick={(e) => { e.stopPropagation(); openDeleteAssignmentDialog(assignment); }} disabled={actionLoading} color="error"> <DeleteIcon fontSize="small" /> </IconButton> {/* openDeleteAssignmentDialog sets selectedAssignment */}
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
     // Show error specific to details fetch IF an assignment ID was targeted (or selected)
    if (detailsError && (assignmentIdFromUrl || selectedAssignment)) {
         return <Paper elevation={0} sx={{ mt: 4, p: 3 }}><Alert severity="error">Could not load assignment details: {detailsError}</Alert></Paper>;
    }
     // If URL has ID, list is loaded, but details are not yet loading/loaded/failed, show placeholder
     if (!selectedAssignment && assignmentIdFromUrl && !loadingAssignments && assignments.length > 0 && !listError && !detailsError) {
        return (
             <Paper elevation={0} variant="outlined" sx={{ mt: 4, p: 3, textAlign: 'center', borderStyle: 'dashed' }}>
                <Typography color="text.secondary">Loading assignment details for ID {assignmentIdFromUrl}...</Typography>
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
             {/* <<<--- NEW Grading Button --- >>> */}
            <Button
                variant="contained"
                color="primary"
                size="small"
                startIcon={<AssessmentIcon />}
                onClick={() => handleGoToGrading(selectedAssignment)}
                disabled={actionLoading || !selectedAssignment?.assignment_id || !courseId || !semester}
                sx={{ mr: 1 }}
            >
                Grade Submissions
            </Button>
             {/* Pass the currently selected (and loaded) assignment object */}
            <Button variant="outlined" size="small" startIcon={<EditIcon />} onClick={() => openEditAssignmentDialog(selectedAssignment)} sx={{ mr: 1 }} disabled={actionLoading}> Edit Info </Button>
            <Button variant="outlined" size="small" color="error" startIcon={<DeleteIcon />} onClick={() => openDeleteAssignmentDialog(selectedAssignment)} disabled={actionLoading}> Delete Assignment </Button> {/* openDeleteAssignmentDialog sets selectedAssignment */}
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
                        // Key needs to be unique and stable, original index should work
                        key={`${selectedAssignment.assignment_id}-qIndex-${question.question_index}`}
                        // Draggable ID should also be unique based on original index
                        draggableId={`${selectedAssignment.assignment_id}-qIndex-${question.question_index}`}
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
                                    <IconButton edge="end" title="Edit Question" sx={{ mr: 0.5 }} onClick={() => openEditQuestionDialog(question)} disabled={actionLoading}>
                                        <EditIcon fontSize="small"/>
                                    </IconButton>
                                    <IconButton edge="end" title="Delete Question" onClick={() => openDeleteQuestionDialog(question.question_index)} disabled={actionLoading} color="error" sx={{ mr: 0.5 }}>
                                        <DeleteIcon fontSize="small"/>
                                    </IconButton>
                                    {/* Drag Handle */}
                                    <Box {...providedDraggable.dragHandleProps} sx={{ display: 'inline-flex', alignItems: 'center', cursor: actionLoading ? 'not-allowed' : 'grab', color: actionLoading ? 'text.disabled' : 'action.active', '&:hover': { color: actionLoading ? 'text.disabled' : 'text.primary' } }} title="Drag to reorder">
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
                            // Optional: Show original index if helpful for debugging reordering
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
         {/* Show detailsError only if it occurred AFTER successfully selecting an assignment */}
         {detailsError && selectedAssignment?.assignment_id && !loadingDetails && (
             <Alert severity="warning" sx={{ mt: 2 }}>
                Warning: There was an error refreshing details ({detailsError}). Some information might be outdated. Try refreshing the page or reselecting the assignment.
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
        <DialogContent dividers>
          <TextField autoFocus id="new-assignment-guidelines" name="assignment_guidelines" label="Assignment Guidelines (Optional)" fullWidth multiline minRows={3} maxRows={8} value={newAssignmentData.assignment_guidelines} onChange={handleGuidelinesChange} margin="dense" disabled={actionLoading} sx={{ mb: 3 }} />
          <Divider sx={{ my: 2 }} textAlign="left"><Typography variant="overline">Questions</Typography></Divider>
          {newAssignmentData.questions.map((q, index) => (
            <Box key={index} sx={{ display: 'flex', alignItems: 'flex-start', mb: 1.5 }}>
              <TextField id={`new-question-${index}`} name={`question_text_${index}`} label={`Question ${index + 1} Text`} fullWidth multiline minRows={2} maxRows={6} value={q.question_text} onChange={(e) => handleQuestionTextChange(index, e.target.value)} margin="dense" required error={!q.question_text?.trim() && newAssignmentData.questions.length > 0} helperText={!q.question_text?.trim() && newAssignmentData.questions.length > 0 ? "Question text is required" : ""} disabled={actionLoading} sx={{ mr: 1, flexGrow: 1 }} />
              {newAssignmentData.questions.length > 1 && (
                 <IconButton title={`Remove Question ${index + 1}`} onClick={() => handleRemoveQuestionField(index)} disabled={actionLoading} color="error" size="small" sx={{ mt: 1.5, flexShrink: 0 }}>
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

      {/* Edit Question Dialog */}
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
      <ConfirmationDialog
        open={deleteAssignmentDialogOpen}
        onClose={() => !actionLoading && setDeleteAssignmentDialogOpen(false)}
        onConfirm={handleDeleteAssignment}
        title="Delete Assignment?"
        description={`Are you sure you want to permanently delete assignment (ID: ${selectedAssignment?.assignment_id ?? 'N/A'}) and all its questions? This action cannot be undone.`}
        confirmText="Delete" cancelText="Cancel" confirmColor="error" loading={actionLoading}
       />

      {/* Delete Question Confirmation Dialog */}
      <ConfirmationDialog
        open={deleteQuestionDialogOpen}
        onClose={() => !actionLoading && setDeleteQuestionDialogOpen(false)}
        onConfirm={handleDeleteQuestion}
        title="Delete Question?"
        description={`Are you sure you want to permanently delete question (Original Index ${questionToDeleteIndex ?? 'N/A'}) from assignment (ID: ${selectedAssignment?.assignment_id ?? 'N/A'})? This action cannot be undone.`}
        confirmText="Delete" cancelText="Cancel" confirmColor="error" loading={actionLoading}
       />

      {/* Alert Snackbar */}
      <Snackbar open={alertOpen} autoHideDuration={6000} onClose={() => setAlertOpen(false)} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert onClose={() => setAlertOpen(false)} severity={alertSeverity} variant="filled" sx={{ width: '100%' }}> {alertMessage} </Alert>
      </Snackbar>
    </Box>
  );
}