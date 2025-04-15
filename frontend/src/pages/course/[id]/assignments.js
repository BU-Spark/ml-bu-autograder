/**
 * Course Assignments Page for BU MET Autograder
 * Allows instructors to manage assignments and their questions (CRUD).
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/router';
import {
  Alert, Box, Button, Card, CardActionArea, CardActions, CardContent,
  CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle,
  Divider, Grid, IconButton, List, ListItem, ListItemIcon, ListItemText,
  Paper, Snackbar, TextField, Typography,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  Add as AddIcon, ArrowBack as ArrowBackIcon, Assignment as AssignmentIcon,
  Delete as DeleteIcon, Edit as EditIcon, DragIndicator as DragIndicatorIcon,
  QuestionAnswer as QuestionIcon,
} from '@mui/icons-material';
import { DragDropContext, Droppable, Draggable, DropResult } from 'react-beautiful-dnd';
// ** VERIFY THIS IMPORT PATH is correct for your project structure **
import { assignmentService } from '../../../api'; // Ensure this path is correct
import CardSkeleton from '../../../components/CardSkeleton';
import ConfirmationDialog from '../../../components/ConfirmationDialog';

// Styled components (Keep as is)
const AssignmentCard = styled(Card)(({ theme }) => ({
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    transition: 'transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out',
    '&:hover': {
      transform: 'translateY(-4px)',
      boxShadow: theme.shadows[6],
    },
}));
const AssignmentCardContent = styled(CardContent)({
    flexGrow: 1,
    display: 'flex',
    flexDirection: 'column',
    minHeight: '100px',
 });
const QuestionItem = styled(ListItem)(({ theme, isDragging }) => ({
    border: `1px solid ${theme.palette.divider}`,
    borderRadius: theme.shape.borderRadius,
    marginBottom: theme.spacing(1),
    backgroundColor: isDragging ? theme.palette.action.hover : theme.palette.background.paper,
    boxShadow: isDragging ? theme.shadows[3] : 'none',
    paddingRight: theme.spacing(16), // Ensure space for actions
    position: 'relative',
 }));
const NoAssignmentsBox = styled(Box)(({ theme }) => ({
    textAlign: 'center',
    padding: theme.spacing(4),
    backgroundColor: theme.palette.background.default,
    borderRadius: theme.shape.borderRadius,
    marginTop: theme.spacing(4),
    border: `1px dashed ${theme.palette.divider}`,
}));

// Main component
export default function Assignments() {
  const router = useRouter();
  const { id: courseIdParam, semester: semesterParam} = router.query;
  const courseId = typeof courseIdParam === 'string' ? courseIdParam : null;
  const semester = typeof semesterParam === 'string' ? semesterParam : null;
  // Parse ID from URL as integer for selection logic and comparisons


  // States
  const [assignments, setAssignments] = useState([]);
  const [loadingAssignments, setLoadingAssignments] = useState(true);
  const [listError, setListError] = useState(null);
  const [selectedAssignment, setSelectedAssignment] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [detailsError, setDetailsError] = useState(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editAssignmentDialogOpen, setEditAssignmentDialogOpen] = useState(false);
  const [addQuestionDialogOpen, setAddQuestionDialogOpen] = useState(false);
  const [editQuestionDialogOpen, setEditQuestionDialogOpen] = useState(false);
  const [deleteAssignmentDialogOpen, setDeleteAssignmentDialogOpen] = useState(false);
  const [deleteQuestionDialogOpen, setDeleteQuestionDialogOpen] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [newAssignmentData, setNewAssignmentData] = useState({ assignment_title: '', assignment_guidelines: '' });
  const [editAssignmentFormData, setEditAssignmentFormData] = useState({ assignment_title: '', assignment_guidelines: '' });
  const [questionData, setQuestionData] = useState({ question_text: '', question_index: null, question_graphics_figures: null });
  const [questionToDeleteIndex, setQuestionToDeleteIndex] = useState(null);
  const [alertOpen, setAlertOpen] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [alertSeverity, setAlertSeverity] = useState('success');


  // --- Helper Functions ---
  const handleInputChange = useCallback((event, setter) => {
    const { name, value } = event.target;
    setter((prevData) => ({ ...prevData, [name]: value }));
    console.log(`[Input Change] Field: ${name}, New Value: ${value}`);
  }, []);

  const showAlert = useCallback((message, severity = 'success') => {
    console.log(`[Show Alert] Severity: ${severity}, Message: ${message}`);
    setAlertMessage(message);
    setAlertSeverity(severity);
    setAlertOpen(true);
  }, []);

  // --- Data Fetching ---
  // Fetch details - ensures it sends and expects numeric ID
  const fetchAssignmentDetails = useCallback(async (idToFetch) => {
    if (!courseId || !semester || typeof idToFetch !== 'number') {
         console.warn('[fetchAssignmentDetails] Skipping fetch, invalid params:', { courseId, semester, idToFetch});
         return;
    }
    setLoadingDetails(true);
    setDetailsError(null);
    console.log(`[fetchAssignmentDetails] Fetching: C=${courseId}, S=${semester}, A=${idToFetch}`);
    try {
      // Ensure service call sends integer ID
      const assignmentWithQuestions = await assignmentService.getAssignment(courseId, semester, idToFetch, true);
      // Validate received ID type
      if (typeof assignmentWithQuestions?.assignment_id !== 'number') {
          console.error("Received assignment detail with non-numeric ID:", assignmentWithQuestions);
          throw new Error("Invalid assignment data received from server.");
      }
      if (assignmentWithQuestions.questions && Array.isArray(assignmentWithQuestions.questions)) {
         assignmentWithQuestions.questions.sort((a, b) => a.question_index - b.question_index);
      } else {
         assignmentWithQuestions.questions = [];
      }
      setSelectedAssignment(assignmentWithQuestions);
    } catch (err) {
      console.error(`[fetchAssignmentDetails] Error fetching assignment ${idToFetch}:`, err);
      setDetailsError(err.message || `Failed to load details.`);
      setSelectedAssignment(null);
    } finally {
      setLoadingDetails(false);
    }
   }, [courseId, semester]);

  // Fetch list - ensures it handles numeric IDs in response
  useEffect(() => {
    console.log('[useEffect - List] Running. Params:', { courseId, semester });
    if (courseId && semester) {
        const fetchAssignments = async () => {
        setLoadingAssignments(true);
        setListError(null);
        setAssignments([]);
        try {
          const assignmentsData = await assignmentService.getAssignments(courseId, semester);
          // Validate assignments have numeric IDs if needed upon fetch
          const validAssignments = Array.isArray(assignmentsData)
             ? assignmentsData.filter(a => typeof a.assignment_id === 'number')
             : [];
          if (validAssignments.length !== (assignmentsData?.length || 0)) {
             console.warn("[useEffect - List] Filtered out assignments with non-numeric IDs from API response.");
          }
          setAssignments(validAssignments);
        } catch (err) {
          console.error('[useEffect - List] Error fetching assignments:', err);
          setListError(err.message || 'Failed to load assignments list.');
          setAssignments([]);
        } finally {
          setLoadingAssignments(false);
        }
      };
      fetchAssignments();
     } else {
      setAssignments([]);
      setLoadingAssignments(false);
      setListError(null);
      setSelectedAssignment(null);
    }
  }, [courseId, semester]);

  // Fetch Detail based on URL param (numeric ID)

  // --- Event Handlers ---
  const handleSelectAssignment = (assignment) => {
     // Ensure assignment_id is a number before navigating
     const assignmentId = assignment?.assignment_id;
     if (!courseId || !semester || typeof assignment?.assignment_id !== 'number') return;
    const newRoute = `/course/${courseId}/assignments?semester=${semester}&assignmentId=${assignmentId}`; // Use numeric ID
    if (router.asPath !== newRoute) {
      router.push(newRoute, undefined, { shallow: true });
    }
   };
  const handleClearSelection = () => {
     if (!courseId || !semester) return;
    const newRoute = `/course/${courseId}/assignments?semester=${semester}`;
    if (router.asPath !== newRoute) {
      router.push(newRoute, undefined, { shallow: true });
    }
   };

  // --- Assignment CRUD ---

  // CREATE (Assignment) - Open Dialog
  const openCreateDialog = () => {
      console.log('[Open Create Dialog]');
      setNewAssignmentData({ assignment_title: '', assignment_guidelines: '' });
      setCreateDialogOpen(true);
  };

  // CREATE (Assignment) - Submit Handler (Aligned with Backend Auto-Increment)
  const handleCreateAssignment = async () => {
    console.log('[handleCreateAssignment] Triggered. Form data:', newAssignmentData);
    if (!courseId || !semester || !newAssignmentData.assignment_title?.trim()) {
      showAlert(!courseId || !semester ? 'Course context missing.' : 'Title is required.', 'warning');
      return;
    }
    setActionLoading(true);
    try {
      // --- PAYLOAD WITHOUT assignment_id ---
      // Backend will check `if assignment.assignment_id is None:` and generate the ID
      const assignmentPayload = {
        // assignment_id is OMITTED from payload
        course_id: courseId,
        semester: semester,
        assignment_title: newAssignmentData.assignment_title.trim(),
        assignment_guidelines: newAssignmentData.assignment_guidelines || null,
        questions: [],
      };
      // ------------------------------------
      console.log('[handleCreateAssignment] Calling API with payload (NO ID):', assignmentPayload);

      // Call API - expects backend to return full Assignment with the *generated integer ID*
      const newAssignment = await assignmentService.createAssignment(assignmentPayload);
      console.log('[handleCreateAssignment] API Success. Received:', newAssignment);

      // Validate backend returned a numeric ID

      // Update Frontend State
      setAssignments(prev => [...prev, newAssignment]);
      setNewAssignmentData({ assignment_title: '', assignment_guidelines: '' }); // Reset form
      setCreateDialogOpen(false);
      showAlert(`Assignment "${newAssignment.assignment_title}" created (ID: ${newAssignment.assignmentId}).`);
      handleSelectAssignment(newAssignment); // Select it

    } catch (error) {
      console.error('[handleCreateAssignment] API Error:', error);
      showAlert(error.response?.data?.detail || error.message || 'Failed to create assignment.', 'error');
    } finally {
      setActionLoading(false);
      console.log('[handleCreateAssignment] Finished.');
    }
  };


  // UPDATE (Assignment) - Open Dialog
  const openEditAssignmentDialog = (assignmentToEdit) => {
     if (!assignmentToEdit || typeof assignmentToEdit.assignment_id !== 'number') return; // Check ID type
    setSelectedAssignment(assignmentToEdit); // Ensure context
    setEditAssignmentFormData({
      assignment_title: assignmentToEdit.assignment_title || '',
      assignment_guidelines: assignmentToEdit.assignment_guidelines || '',
    });
    setEditAssignmentDialogOpen(true);
   };
  // UPDATE (Assignment) - Submit
  const handleUpdateAssignment = async () => {
    // Ensure selectedAssignment and its ID are valid numbers
    if (!selectedAssignment || typeof selectedAssignment.assignment_id !== 'number' || !semester || !courseId) return;
    const { assignment_title, assignment_guidelines } = editAssignmentFormData;
    if (assignment_title !== null && !assignment_title?.trim()) {
      showAlert('Title cannot be empty.', 'warning'); return;
    }
    const updatePayload = {
        assignment_title: assignment_title?.trim() || null,
        assignment_guidelines: assignment_guidelines || null
    };
    // Prevent no-change update
    if ((updatePayload.assignment_title === (selectedAssignment.assignment_title || null) &&
         updatePayload.assignment_guidelines === (selectedAssignment.assignment_guidelines || null)) ||
        (updatePayload.assignment_title === null && updatePayload.assignment_guidelines === null)) {
       setEditAssignmentDialogOpen(false); return;
    }
    setActionLoading(true);
    try {
      // Ensure service call expects and sends numeric ID
      const updatedAssignment = await assignmentService.updateAssignmentMetadata(semester, courseId, selectedAssignment.assignment_id, updatePayload);
       // Validate response ID type
      setAssignments(prev => prev.map(a => a.assignment_id === selectedAssignment.assignment_id ? { ...a, ...updatedAssignment } : a));
      setSelectedAssignment(prev => ({ ...prev, ...updatedAssignment }));
      setEditAssignmentDialogOpen(false);
      showAlert('Assignment updated.');
    } catch (error) {
      console.error('Update Assignment Error:', error);
      showAlert(error.message || 'Failed to update assignment.', 'error');
    } finally {
      setActionLoading(false);
    }
   };
  // DELETE (Assignment) - Confirm Submit
    // DELETE (Assignment) - Confirm Submit
    const handleDeleteAssignment = async () => {
      // Basic guard: Ensure we have the necessary context before proceeding.
      // We assume selectedAssignment and its ID are valid here based on how the dialog was opened.
      if (!selectedAssignment || !semester || !courseId) {
          console.error('[handleDeleteAssignment] Missing context:', { selectedAssignment, semester, courseId });
          showAlert('Cannot delete: context is missing.', 'error');
          setDeleteAssignmentDialogOpen(false); // Ensure dialog closes if somehow opened incorrectly
          return;
      }
  
      // Set loading and close the confirmation dialog immediately for better UX
      setActionLoading(true);
      setDeleteAssignmentDialogOpen(false);
      console.log(`[handleDeleteAssignment] Attempting to delete assignment ID: ${selectedAssignment.assignment_id}`);
  
      try {
        // Call the API service - Ensure it sends the assignment_id correctly (as a number)
        // Expects a simple success response or throws error on failure
        await assignmentService.deleteAssignment(
            courseId,
            semester,
            selectedAssignment.assignment_id // Assumed to be a number here
          );
        console.log(`[handleDeleteAssignment] API call successful for ID: ${selectedAssignment.assignment_id}`);
  
        // --- Success State Updates ---
        // Remove the assignment from the list
        setAssignments(prev => prev.filter(a => a.assignment_id !== selectedAssignment.assignment_id));
  
        // Show success alert
        showAlert(`Assignment "${selectedAssignment.assignment_title || selectedAssignment.assignment_id}" deleted successfully.`);
  
        // Clear the selected assignment detail view and URL parameter
        handleClearSelection();
        // --- End Success State Updates ---
  
      } catch (error) {
        // --- Error Handling ---
        console.error('[handleDeleteAssignment] API Error:', error);
        // Extract the best error message to display
        const displayError = error.response?.data?.detail || error.message || 'Failed to delete assignment.';
        showAlert(displayError, 'error');
        // --- End Error Handling ---
  
      } finally {
        // --- Cleanup ---
        setActionLoading(false); // Ensure loading indicator stops
        console.log('[handleDeleteAssignment] Finished.');
        // --- End Cleanup ---
      }
    };

  // --- Question CRUD ---
  const openAddQuestionDialog = () => {
     if (!selectedAssignment || typeof selectedAssignment.assignment_id !== 'number') {
         showAlert('Select a valid assignment first.', 'warning');
         return;
     }
    setQuestionData({ question_text: '', question_index: null, question_graphics_figures: null });
    setAddQuestionDialogOpen(true);
   };
  const handleAddQuestion = async () => {
     // Ensure selectedAssignment and its ID are valid numbers
    if (!selectedAssignment || typeof selectedAssignment.assignment_id !== 'number' || !semester || !courseId || !questionData.question_text?.trim()) {
      showAlert(!selectedAssignment ? 'No assignment selected.' : 'Question text required.', 'warning'); return;
    }
    const questionPayload = { question_text: questionData.question_text.trim(), question_graphics_figures: null };
    setActionLoading(true);
    try {
       // Ensure service call expects and sends numeric assignment_id
      const response = await assignmentService.addQuestion(semester, courseId, selectedAssignment.assignment_id, questionPayload);
      // Backend returns { question_index: number }
      const newQuestion = { ...questionPayload, question_index: response.question_index };
      setSelectedAssignment(prev => {
         const updatedQuestions = [...(prev?.questions || []), newQuestion].sort((a, b) => a.question_index - b.question_index);
         return { ...prev, questions: updatedQuestions };
      });
      setAddQuestionDialogOpen(false);
      showAlert('Question added.');
      setQuestionData({ question_text: '', question_index: null, question_graphics_figures: null });
    } catch (error) {
      console.error('Add Question Error:', error);
      showAlert(error.message || 'Failed to add question.', 'error');
    } finally {
      setActionLoading(false);
    }
   };
  const openEditQuestionDialog = (question) => {
     if (!question || typeof question.question_index !== 'number') return; // Check question index type
    setQuestionData({
      question_text: question.question_text || '',
      question_index: question.question_index, // Store numeric index
      question_graphics_figures: question.question_graphics_figures || null,
    });
    setEditQuestionDialogOpen(true);
   };
  const handleEditQuestion = async () => {
     // Ensure selectedAssignment and its ID are valid numbers, and question index is valid
    if (!selectedAssignment || typeof selectedAssignment.assignment_id !== 'number' || questionData.question_index === null || typeof questionData.question_index !== 'number' || !semester || !courseId || !questionData.question_text?.trim()) {
      showAlert('Invalid data or context for editing question.', 'warning'); return;
    }
    const questionPayload = { question_text: questionData.question_text.trim(), question_graphics_figures: null };
    setActionLoading(true);
    try {
       // Ensure service call expects and sends numeric assignment_id and question_index
      const updatedQuestion = await assignmentService.editQuestion(semester, courseId, selectedAssignment.assignment_id, questionData.question_index, questionPayload);
      // Backend returns the updated Question object
      setSelectedAssignment(prev => {
        const updatedQuestions = (prev?.questions || [])
            .map(q => q.question_index === questionData.question_index ? updatedQuestion : q)
            .sort((a, b) => a.question_index - b.question_index);
         return { ...prev, questions: updatedQuestions };
      });
      setEditQuestionDialogOpen(false);
      showAlert('Question updated.');
      setQuestionData({ question_text: '', question_index: null, question_graphics_figures: null });
    } catch (error) {
      console.error('Edit Question Error:', error);
      showAlert(error.message || 'Failed to edit question.', 'error');
    } finally {
      setActionLoading(false);
    }
   };
  const onDragEnd = useCallback(async (result) => {
     const { source, destination } = result;
     // Ensure selectedAssignment and its ID are valid numbers
     if (!destination || !selectedAssignment || typeof selectedAssignment.assignment_id !== 'number' || !selectedAssignment.questions || selectedAssignment.questions.length < 2 || !semester || !courseId) return;
     if (destination.droppableId === source.droppableId && destination.index === source.index) return;

    const currentQuestions = Array.from(selectedAssignment.questions).sort((a,b) => a.question_index - b.question_index);
    const [reorderedItem] = currentQuestions.splice(source.index, 1);
    currentQuestions.splice(destination.index, 0, reorderedItem);
    setSelectedAssignment(prev => ({ ...prev, questions: currentQuestions })); // Optimistic update

    const newIndexOrder = currentQuestions.map(q => q.question_index);
    setActionLoading(true);
    try {
       // Ensure service call expects and sends numeric assignment_id
      await assignmentService.modifyQuestionOrder(semester, courseId, selectedAssignment.assignment_id, newIndexOrder);
      showAlert('Order updated. Refreshing details...');
      await fetchAssignmentDetails(selectedAssignment.assignment_id); // Re-fetch takes numeric ID
    } catch (error) {
      console.error('Modify Order Error:', error);
      showAlert(error.message || 'Failed to update order.', 'error');
      showAlert('Reverting order due to error. Refreshing...', 'warning');
      await fetchAssignmentDetails(selectedAssignment.assignment_id); // Re-fetch to revert
    } finally {
      setActionLoading(false);
    }
   }, [selectedAssignment, semester, courseId, showAlert, fetchAssignmentDetails]);
  const openDeleteQuestionDialog = (index) => {
     // Ensure index is a number
     if (typeof index !== 'number') return;
     setQuestionToDeleteIndex(index);
     setDeleteQuestionDialogOpen(true);
   };
  const handleDeleteQuestion = async () => {
     // Ensure selectedAssignment and its ID are valid numbers, and index is valid number
     if (!selectedAssignment || typeof selectedAssignment.assignment_id !== 'number' || questionToDeleteIndex === null || typeof questionToDeleteIndex !== 'number' || !semester || !courseId) return;
    setActionLoading(true);
    try {
       // Ensure service call expects and sends numeric assignment_id and question_index
      await assignmentService.removeQuestion(semester, courseId, selectedAssignment.assignment_id, questionToDeleteIndex);
      showAlert('Question deleted. Refreshing details...');
      await fetchAssignmentDetails(selectedAssignment.assignment_id); // Re-fetch takes numeric ID
    } catch (error) {
      console.error('Delete Question Error:', error);
      showAlert(error.message || 'Failed to delete question.', 'error');
    } finally {
      setDeleteQuestionDialogOpen(false);
      setQuestionToDeleteIndex(null);
      setActionLoading(false);
    }
   };

  // --- Render Functions ---
  const renderAssignmentList = () => {
    if (loadingAssignments) return <Grid container spacing={3} sx={{ mb: 4 }}>{[1, 2, 3].map((n) => (<Grid item xs={12} sm={6} md={4} key={n}><CardSkeleton /></Grid>))}</Grid>;
    if (listError) return <Alert severity="error" sx={{ mb: 3 }}>{listError}</Alert>;
    if (!assignments.length) return <NoAssignmentsBox><AssignmentIcon sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} /><Typography variant="h6">No assignments found.</Typography><Typography color="text.secondary" sx={{ mb: 2 }}>Create one to get started.</Typography><Button variant="contained" startIcon={<AddIcon />} onClick={openCreateDialog}>Create Assignment</Button></NoAssignmentsBox>;

    return (
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {assignments.map((assignment) => (
          // Ensure assignment.assignment_id is treated as number for key/comparison
          <Grid item xs={12} sm={6} md={4} key={assignment.assignment_id}>
            <AssignmentCard variant="outlined" sx={{ borderColor: selectedAssignment?.assignment_id === assignment.assignment_id ? 'primary.main' : 'divider' }}>
              <CardActionArea onClick={() => handleSelectAssignment(assignment)} sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                <AssignmentCardContent>
                  <Typography gutterBottom variant="h6" component="div" noWrap title={assignment.assignment_title || `Assignment ${assignment.assignment_id}`}>{assignment.assignment_title || `Assignment ${assignment.assignment_id}`}</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>ID: {assignment.assignment_id}</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', flexGrow: 1 }}>{assignment.assignment_guidelines || 'No guidelines.'}</Typography>
                </AssignmentCardContent>
              </CardActionArea>
              <CardActions sx={{ justifyContent: 'flex-end', pt: 0, pb: 1, px: 1 }}>
                <IconButton title="Edit Assignment Info" size="small" onClick={(e) => { e.stopPropagation(); openEditAssignmentDialog(assignment); }} disabled={actionLoading}><EditIcon fontSize="small" /></IconButton>
                <IconButton title="Delete Assignment" size="small" onClick={(e) => { e.stopPropagation(); setSelectedAssignment(assignment); setDeleteAssignmentDialogOpen(true); }} disabled={actionLoading} color="error"><DeleteIcon fontSize="small" /></IconButton>
              </CardActions>
            </AssignmentCard>
          </Grid>
        ))}
      </Grid>
    );
   };
  const renderAssignmentDetails = () => {
     if (loadingDetails) return <Paper elevation={0} sx={{ mt: 4, p: 3, textAlign: 'center' }}><CircularProgress /><Typography sx={{ mt: 1 }}>Loading details...</Typography></Paper>;
    if (detailsError) return <Paper elevation={0} sx={{ mt: 4, p: 3 }}><Alert severity="error">{detailsError}</Alert></Paper>;
    if (!selectedAssignment || typeof selectedAssignment.assignment_id !== 'number') { // Check if valid assignment selected
        if (!loadingAssignments && assignments.length > 0) {
             return <Paper elevation={0} variant="outlined" sx={{ mt: 4, p: 3, textAlign: 'center' }}><Typography color="text.secondary">Select an assignment to view details.</Typography></Paper>;
        }
        return null;
    }

    return (
      <Paper elevation={3} sx={{ mt: 4, p: {xs: 1, sm: 2, md: 3} }}>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 1 }}>
          <Typography variant="h5" component="h2">{selectedAssignment.assignment_title}</Typography>
          <Box>
            <Button variant="outlined" size="small" startIcon={<EditIcon />} onClick={() => openEditAssignmentDialog(selectedAssignment)} sx={{ mr: 1 }} disabled={actionLoading}>Edit Info</Button>
            <Button variant="outlined" size="small" color="error" startIcon={<DeleteIcon />} onClick={() => setDeleteAssignmentDialogOpen(true)} disabled={actionLoading}>Delete Assignment</Button>
          </Box>
        </Box>
        {/* Guidelines */}
        <Typography variant="body2" color="text.secondary" paragraph sx={{ whiteSpace: 'pre-wrap', maxHeight: '150px', overflowY: 'auto', border: '1px solid #eee', p: 1, borderRadius: 1, background: '#f9f9f9' }}>{selectedAssignment.assignment_guidelines || 'No guidelines.'}</Typography>
        <Divider sx={{ my: 3 }} />
        {/* Questions Section */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Questions</Typography>
          <Button variant="contained" size="small" startIcon={<AddIcon />} onClick={openAddQuestionDialog} disabled={actionLoading}>Add Question</Button>
        </Box>
        {(!selectedAssignment.questions || !selectedAssignment.questions.length) && <Typography color="text.secondary" sx={{ fontStyle: 'italic', textAlign: 'center', py: 2 }}>No questions added yet.</Typography>}
        {/* Drag and Drop List */}
        {selectedAssignment.questions && selectedAssignment.questions.length > 0 && (
          <DragDropContext onDragEnd={onDragEnd}>
            <Droppable droppableId="questions">
              {(provided) => (
                <List {...provided.droppableProps} ref={provided.innerRef}>
                  {selectedAssignment.questions.map((question, index) => (
                    // Ensure keys and draggableId use numeric assignment_id and question_index
                    <Draggable key={`${selectedAssignment.assignment_id}-${question.question_index}`} draggableId={`${selectedAssignment.assignment_id}-${question.question_index}`} index={index} isDragDisabled={actionLoading}>
                      {(providedDraggable, snapshot) => (
                        <QuestionItem ref={providedDraggable.innerRef} {...providedDraggable.draggableProps} isDragging={snapshot.isDragging}
                          secondaryAction={
                            <Box sx={{ display: 'flex', alignItems: 'center' }}>
                              <IconButton edge="end" title="Edit Question" sx={{ mr: 0.5 }} onClick={() => openEditQuestionDialog(question)} disabled={actionLoading}><EditIcon fontSize="small"/></IconButton>
                              <IconButton edge="end" title="Delete Question" onClick={() => openDeleteQuestionDialog(question.question_index)} disabled={actionLoading}><DeleteIcon fontSize="small"/></IconButton>
                              <Box {...providedDraggable.dragHandleProps} sx={{ display: 'inline-flex', alignItems: 'center', ml: 1, cursor: actionLoading ? 'not-allowed' : 'grab', color: actionLoading ? 'text.disabled' : 'inherit' }} title="Drag to reorder"><DragIndicatorIcon /></Box>
                            </Box>
                          }>
                          <ListItemIcon sx={{ minWidth: 'auto', mr: 1.5 }}><Typography variant="body2" sx={{ fontWeight: 'bold' }}>Q{index + 1}:</Typography></ListItemIcon>
                          <ListItemText primary={`${question.question_text}`} primaryTypographyProps={{ sx: { wordBreak: 'break-word' } }} />
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


  // --- Main Component Return ---
  return (
    <Box sx={{ p: { xs: 1, sm: 2, md: 3 } }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 1 }}>
        <IconButton title="Back" aria-label="back" onClick={() => (courseId && semester) && router.push(`/course/${courseId}?semester=${semester}`)} disabled={!courseId || !semester} sx={{ mr: 1 }} ><ArrowBackIcon /></IconButton>
        <Typography variant="h4" component="h1" sx={{ flexGrow: 1 }}>Course Assignments</Typography>
        <Button variant="contained" color="primary" size="small" startIcon={<AddIcon />} onClick={openCreateDialog} disabled={actionLoading || !courseId || !semester} >Create Assignment</Button>
      </Box>

      {/* Assignment List */}
      <Typography variant="h5" sx={{ mb: 2 }}>Assignments List</Typography>
      {renderAssignmentList()}

      <Divider sx={{ my: 4 }} />

      {/* Selected Assignment Details */}
      <Typography variant="h5" sx={{ mb: 2 }}>Selected Assignment Details</Typography>
      {renderAssignmentDetails()}

      {/* --- All Dialogs --- */}
      {/* Create Assignment Dialog */}
       <Dialog open={createDialogOpen} onClose={() => !actionLoading && setCreateDialogOpen(false)} maxWidth="sm" fullWidth aria-labelledby="create-assignment-dialog-title">
         <DialogTitle id="create-assignment-dialog-title">Create New Assignment</DialogTitle>
         <DialogContent>
            <TextField autoFocus id="new-assignment-title" name="assignment_title" label="Assignment Title" fullWidth value={newAssignmentData.assignment_title} onChange={(e) => handleInputChange(e, setNewAssignmentData)} margin="dense" required error={!newAssignmentData.assignment_title?.trim() && newAssignmentData.assignment_title !== ''} helperText={!newAssignmentData.assignment_title?.trim() && newAssignmentData.assignment_title !== '' ? "Title is required" : ""}/>
            <TextField id="new-assignment-guidelines" name="assignment_guidelines" label="Assignment Guidelines (Optional)" fullWidth multiline rows={4} value={newAssignmentData.assignment_guidelines} onChange={(e) => handleInputChange(e, setNewAssignmentData)} margin="dense"/>
         </DialogContent>
         <DialogActions>
            <Button onClick={() => setCreateDialogOpen(false)} disabled={actionLoading}>Cancel</Button>
            <Button onClick={handleCreateAssignment} variant="contained" color="primary" disabled={actionLoading || !newAssignmentData.assignment_title?.trim()}>{actionLoading ? <CircularProgress size={24} /> : 'Create'}</Button>
         </DialogActions>
      </Dialog>
      {/* Edit Assignment Dialog */}
      <Dialog open={editAssignmentDialogOpen} onClose={() => !actionLoading && setEditAssignmentDialogOpen(false)} maxWidth="sm" fullWidth aria-labelledby="edit-assignment-dialog-title">
         <DialogTitle id="edit-assignment-dialog-title">Edit Assignment Info</DialogTitle>
         <DialogContent>
            <TextField autoFocus id="edit-assignment-title" name="assignment_title" label="Assignment Title" fullWidth value={editAssignmentFormData.assignment_title} onChange={(e) => handleInputChange(e, setEditAssignmentFormData)} margin="dense" required error={!editAssignmentFormData.assignment_title?.trim() && editAssignmentFormData.assignment_title !== ''} helperText={!editAssignmentFormData.assignment_title?.trim() && editAssignmentFormData.assignment_title !== '' ? "Title is required" : ""}/>
            <TextField id="edit-assignment-guidelines" name="assignment_guidelines" label="Assignment Guidelines (Optional)" fullWidth multiline rows={4} value={editAssignmentFormData.assignment_guidelines} onChange={(e) => handleInputChange(e, setEditAssignmentFormData)} margin="dense"/>
         </DialogContent>
         <DialogActions>
            <Button onClick={() => setEditAssignmentDialogOpen(false)} disabled={actionLoading}>Cancel</Button>
            <Button onClick={handleUpdateAssignment} variant="contained" color="primary" disabled={actionLoading || !editAssignmentFormData.assignment_title?.trim()}>{actionLoading ? <CircularProgress size={24} /> : 'Save Changes'}</Button>
         </DialogActions>
       </Dialog>
       {/* Add Question Dialog */}
      <Dialog open={addQuestionDialogOpen} onClose={() => !actionLoading && setAddQuestionDialogOpen(false)} maxWidth="md" fullWidth aria-labelledby="add-question-dialog-title">
         <DialogTitle id="add-question-dialog-title">Add New Question</DialogTitle>
         <DialogContent>
             <TextField autoFocus id="add-question-text" name="question_text" label="Question Text" fullWidth multiline rows={6} value={questionData.question_text} onChange={(e) => handleInputChange(e, setQuestionData)} margin="dense" required error={!questionData.question_text?.trim() && questionData.question_text !== ''} helperText={!questionData.question_text?.trim() && questionData.question_text !== '' ? "Question text is required" : ""}/>
             <Typography variant="caption" display="block" sx={{ mt: 1 }}>Graphics/Figures not yet supported.</Typography>
         </DialogContent>
         <DialogActions>
            <Button onClick={() => setAddQuestionDialogOpen(false)} disabled={actionLoading}>Cancel</Button>
            <Button onClick={handleAddQuestion} variant="contained" color="primary" disabled={actionLoading || !questionData.question_text?.trim()}>{actionLoading ? <CircularProgress size={24} /> : 'Add Question'}</Button>
         </DialogActions>
       </Dialog>
       {/* Edit Question Dialog */}
      <Dialog open={editQuestionDialogOpen} onClose={() => !actionLoading && setEditQuestionDialogOpen(false)} maxWidth="md" fullWidth aria-labelledby="edit-question-dialog-title">
          <DialogTitle id="edit-question-dialog-title">Edit Question {questionData.question_index !== null ? `(Original Index ${questionData.question_index})` : ''}</DialogTitle>
          <DialogContent>
             <TextField autoFocus id="edit-question-text" name="question_text" label="Question Text" fullWidth multiline rows={6} value={questionData.question_text} onChange={(e) => handleInputChange(e, setQuestionData)} margin="dense" required error={!questionData.question_text?.trim() && questionData.question_text !== ''} helperText={!questionData.question_text?.trim() && questionData.question_text !== '' ? "Question text is required" : ""}/>
             <Typography variant="caption" display="block" sx={{ mt: 1 }}>Graphics/Figures not yet supported.</Typography>
          </DialogContent>
          <DialogActions>
             <Button onClick={() => setEditQuestionDialogOpen(false)} disabled={actionLoading}>Cancel</Button>
             <Button onClick={handleEditQuestion} variant="contained" color="primary" disabled={actionLoading || !questionData.question_text?.trim()}>{actionLoading ? <CircularProgress size={24} /> : 'Save Changes'}</Button>
          </DialogActions>
       </Dialog>
       {/* Delete Assignment Confirmation Dialog */}
      <ConfirmationDialog open={deleteAssignmentDialogOpen} onClose={() => !actionLoading && setDeleteAssignmentDialogOpen(false)} onConfirm={handleDeleteAssignment} title="Delete Assignment?" description={`Delete "${selectedAssignment?.assignment_title || 'this assignment'}" (ID: ${selectedAssignment?.assignment_id}) and all its questions/data? Cannot be undone.`} confirmText="Delete" cancelText="Cancel" confirmColor="error" loading={actionLoading}/>
      {/* Delete Question Confirmation Dialog */}
      <ConfirmationDialog open={deleteQuestionDialogOpen} onClose={() => !actionLoading && setDeleteQuestionDialogOpen(false)} onConfirm={handleDeleteQuestion} title="Delete Question?" description={`Delete question (Original Index ${questionToDeleteIndex !== null ? questionToDeleteIndex : ''}) from "${selectedAssignment?.assignment_title}"? Cannot be undone.`} confirmText="Delete" cancelText="Cancel" confirmColor="error" loading={actionLoading}/>
      {/* Alert Snackbar */}
      <Snackbar open={alertOpen} autoHideDuration={6000} onClose={() => setAlertOpen(false)} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}><Alert onClose={() => setAlertOpen(false)} severity={alertSeverity} variant="filled" sx={{ width: '100%' }}>{alertMessage}</Alert></Snackbar>

    </Box>
  );
}