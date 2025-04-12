import React, { useState, useEffect, useCallback } from 'react'; // Added useCallback
import { useRouter } from 'next/router';
import {
  Alert,
  Box,
  Button,
  Card,
  CardActionArea,
  CardActions, // Added for potential buttons on card
  CardContent,
  CircularProgress, // Added for loading states
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Grid,
  IconButton,
  List,
  ListItem,
  ListItemIcon,
  ListItemSecondaryAction,
  ListItemText,
  Paper,
  Snackbar,
  TextField,
  Typography,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  Add as AddIcon,
  ArrowBack as ArrowBackIcon,
  Assignment as AssignmentIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  DragIndicator as DragIndicatorIcon,
  QuestionAnswer as QuestionIcon,
} from '@mui/icons-material';
import { DragDropContext, Droppable, Draggable, DropResult } from 'react-beautiful-dnd'; // Added DropResult type
// Assuming these exist and are correctly implemented (api.js needs to be imported)
import { assignmentService } from '../../../api'; // Make sure path is correct
import CardSkeleton from '../../../components/CardSkeleton'; // Assuming this exists
import ConfirmationDialog from '../../../components/ConfirmationDialog'; // Assuming this exists

// Styled components (Keep as they are)
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
  minHeight: '100px', // Ensure minimum height
});

const QuestionItem = styled(ListItem)(({ theme, isDragging }) => ({
  border: `1px solid ${theme.palette.divider}`,
  borderRadius: theme.shape.borderRadius,
  marginBottom: theme.spacing(1),
  backgroundColor: isDragging ? theme.palette.action.hover : theme.palette.background.paper,
  boxShadow: isDragging ? theme.shadows[3] : 'none',
  // Ensure enough space for actions
  paddingRight: theme.spacing(16), // Adjust as needed
}));

const NoAssignmentsBox = styled(Box)(({ theme }) => ({
  textAlign: 'center',
  padding: theme.spacing(4),
  backgroundColor: theme.palette.background.default, // Use default background
  borderRadius: theme.shape.borderRadius,
  marginTop: theme.spacing(4),
  border: `1px dashed ${theme.palette.divider}`,
}));

// Main component
export default function Assignments() {
  const router = useRouter();
  // Ensure assignmentId query param is treated as string/number if present
  const { id: courseId, semester, assignmentId: assignmentIdParam } = router.query;
  const selectedAssignmentId = assignmentIdParam ? parseInt(assignmentIdParam, 10) : null; // Parse ID to integer

  // State for assignments list
  const [assignments, setAssignments] = useState([]);
  const [loadingAssignments, setLoadingAssignments] = useState(true); // Specific loading for list
  const [listError, setListError] = useState(null); // Specific error for list

  // State for the currently selected assignment details
  const [selectedAssignment, setSelectedAssignment] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false); // Specific loading for details
  const [detailsError, setDetailsError] = useState(null); // Specific error for details

  // State for dialogs
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editAssignmentDialogOpen, setEditAssignmentDialogOpen] = useState(false);
  const [addQuestionDialogOpen, setAddQuestionDialogOpen] = useState(false);
  const [editQuestionDialogOpen, setEditQuestionDialogOpen] = useState(false);
  const [deleteAssignmentDialogOpen, setDeleteAssignmentDialogOpen] = useState(false);
  const [deleteQuestionDialogOpen, setDeleteQuestionDialogOpen] = useState(false);

  // State for general loading (e.g., during updates/deletes)
  const [actionLoading, setActionLoading] = useState(false);

  // State for form data
  const [newAssignmentData, setNewAssignmentData] = useState({
    assignment_title: '',
    assignment_guidelines: '',
  });

  // Holds the data being edited in the assignment metadata dialog
  const [editAssignmentFormData, setEditAssignmentFormData] = useState({
    assignment_title: '',
    assignment_guidelines: '',
  });

  // State for question form (add/edit)
  const [questionData, setQuestionData] = useState({
    question_text: '',
    question_index: null, // Use null when no question is being edited/added context
    question_graphics_figures: null, // Base64 string or null
  });

  const [questionToDeleteIndex, setQuestionToDeleteIndex] = useState(null); // Holds the index to delete

  // State for alerts
  const [alertOpen, setAlertOpen] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [alertSeverity, setAlertSeverity] = useState('success'); // 'success' | 'error' | 'warning' | 'info'


  // --- Helper Functions ---

  // Function to handle input changes for forms
  const handleInputChange = useCallback((event, setter) => {
    const { name, value } = event.target;
    setter((prevData) => ({
      ...prevData,
      [name]: value,
    }));
  }, []); // Empty dependency array means this function is stable

  // Function to show alerts
  const showAlert = useCallback((message, severity = 'success') => {
    setAlertMessage(message);
    setAlertSeverity(severity);
    setAlertOpen(true);
  }, []); // Empty dependency array

  // Fetches full assignment details (including questions)
  const fetchAssignmentDetails = useCallback(async (idToFetch) => {
    if (!courseId || !semester || idToFetch === null) return;
    setLoadingDetails(true);
    setDetailsError(null);
    try {
        const assignmentWithQuestions = await assignmentService.getAssignment(
            courseId,
            semester,
            idToFetch,
            true // include_questions = true
        );
        setSelectedAssignment(assignmentWithQuestions);
    } catch (err) {
        console.error(`Error fetching details for assignment ${idToFetch}:`, err);
        const errorMsg = err.message || `Failed to load details for assignment ${idToFetch}.`;
        setDetailsError(errorMsg);
        showAlert(errorMsg, 'error');
        setSelectedAssignment(null); // Reset selection on error
        // Optionally clear the assignmentId param from URL if fetch fails
        router.replace(`/course/${courseId}/assignments?semester=${semester}`, undefined, { shallow: true });
    } finally {
        setLoadingDetails(false);
    }
  }, [courseId, semester, showAlert, router]); // Dependencies for fetchAssignmentDetails

  // --- useEffect Hooks ---

  // Fetch assignment list
  useEffect(() => {
    const fetchAssignments = async () => {
      if (!courseId || !semester) {
        setLoadingAssignments(false); // Stop loading if params missing
        return;
      }
      setLoadingAssignments(true);
      setListError(null);
      try {
        const assignmentsData = await assignmentService.getAssignments(courseId, semester);
        setAssignments(assignmentsData || []);
      } catch (err) {
        console.error('Error fetching assignments:', err);
        const errorMsg = err.message || 'Failed to load assignments list.';
        setListError(errorMsg);
        showAlert(errorMsg, 'error');
      } finally {
        setLoadingAssignments(false);
      }
    };
    fetchAssignments();
  }, [courseId, semester, showAlert]); // Fetch list when course/semester changes

  // Fetch details when selectedAssignmentId from URL changes
  useEffect(() => {
      if (selectedAssignmentId !== null) {
          fetchAssignmentDetails(selectedAssignmentId);
      } else {
          setSelectedAssignment(null); // Clear details if no ID in URL
          setDetailsError(null);
      }
  }, [selectedAssignmentId, fetchAssignmentDetails]); // Depend on ID from URL and the fetch function

  // --- Event Handlers ---

  // Function to handle selecting an assignment card
  const handleSelectAssignment = (assignment) => {
    // Update URL, which will trigger the useEffect hook to fetch details
    const newRoute = `/course/${courseId}/assignments?semester=${semester}&assignmentId=${assignment.assignment_id}`;
    if (router.asPath !== newRoute) {
        router.push(newRoute, undefined, { shallow: true }); // Use shallow routing
    }
    // No need to call fetchAssignmentDetails here, useEffect handles it
  };

  // Function to clear selection
  const handleClearSelection = () => {
      const newRoute = `/course/${courseId}/assignments?semester=${semester}`;
      if (router.asPath !== newRoute) {
          router.push(newRoute, undefined, { shallow: true });
      }
      // useEffect will clear selectedAssignment based on assignmentIdParam being null
  };


  // Open Edit Assignment Dialog
  const openEditAssignmentDialog = (assignmentToEdit) => {
      if (!assignmentToEdit) return;
      setEditAssignmentFormData({
          assignment_title: assignmentToEdit.assignment_title || '',
          assignment_guidelines: assignmentToEdit.assignment_guidelines || '',
      });
      setEditAssignmentDialogOpen(true);
  };


  // Handle updating assignment metadata using the corrected service function
  const handleUpdateAssignment = async () => {
    if (!selectedAssignment) return;

    const updatePayload = {
      assignment_title: editAssignmentFormData.assignment_title?.trim(), // Trim whitespace
      assignment_guidelines: editAssignmentFormData.assignment_guidelines, // Allow empty string maybe? Or trim?
    };

    // Basic validation
    if (!updatePayload.assignment_title) {
        showAlert('Assignment Title cannot be empty.', 'warning');
        return;
    }

    // Prevent sending update if nothing changed
    if (updatePayload.assignment_title === selectedAssignment.assignment_title &&
        updatePayload.assignment_guidelines === selectedAssignment.assignment_guidelines) {
        setEditAssignmentDialogOpen(false);
        return;
    }

    setActionLoading(true);
    try {
      // Call the *correct* service function: updateAssignmentMetadata
      const updatedAssignmentFromServer = await assignmentService.updateAssignmentMetadata(
          semester, // query param
          courseId, // query param
          selectedAssignment.assignment_id, // query param
          updatePayload // request body
      );

      // Update the assignments list state
      setAssignments(prevAssignments => prevAssignments.map(a =>
        a.assignment_id === selectedAssignment.assignment_id
         ? { ...a, ...updatedAssignmentFromServer } // Merge updates
         : a
      ));

      // Update the selected assignment state (keeping existing questions)
      setSelectedAssignment(prev => ({
          ...prev,
          ...updatedAssignmentFromServer // Apply updates from server response
      }));

      setEditAssignmentDialogOpen(false);
      showAlert('Assignment updated successfully');

    } catch (error) {
      console.error('Error updating assignment:', error);
      showAlert(error.message || 'Failed to update assignment', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  // Handle creating a new assignment
  const handleCreateAssignment = async () => {
    if (!newAssignmentData.assignment_title?.trim()) {
        showAlert('Assignment Title is required.', 'warning');
        return;
    }
    setActionLoading(true);
    try {
      // Backend needs { course_id, semester, assignment_title?, assignment_guidelines?, questions? }
      // Backend assigns assignment_id
      const assignmentPayload = {
        // assignment_id: should be assigned by backend
        course_id: courseId,
        semester: semester,
        assignment_title: newAssignmentData.assignment_title,
        assignment_guidelines: newAssignmentData.assignment_guidelines || null,
        questions: [], // Start empty
      };

      const newAssignment = await assignmentService.createAssignment(assignmentPayload);

      setAssignments(prev => [...prev, newAssignment]); // Add to list
      setNewAssignmentData({ // Reset form
        assignment_title: '',
        assignment_guidelines: '',
      });
      setCreateDialogOpen(false);
      showAlert('Assignment created successfully');

      // Select the new assignment
      handleSelectAssignment(newAssignment); // Updates URL -> triggers useEffect for details

    } catch (error) {
      console.error('Error creating assignment:', error);
      showAlert(error.message || 'Failed to create assignment', 'error');
    } finally {
        setActionLoading(false);
    }
  };

  // Handle deleting an assignment
  const handleDeleteAssignment = async () => {
    if (!selectedAssignment) return;
    setActionLoading(true);
    try {
      await assignmentService.deleteAssignment(
          semester,
          courseId,
          selectedAssignment.assignment_id
        );

      setAssignments(prev => prev.filter(
        (a) => a.assignment_id !== selectedAssignment.assignment_id
      ));
      setDeleteAssignmentDialogOpen(false);
      showAlert('Assignment deleted successfully');
      handleClearSelection(); // Clear selection and update URL

    } catch (error) {
      console.error('Error deleting assignment:', error);
      showAlert(error.message || 'Failed to delete assignment', 'error');
    } finally {
      setActionLoading(false);
    }
  };


  // --- Question Handlers ---

  // Open Add Question Dialog
  const openAddQuestionDialog = () => {
      setQuestionData({ // Reset form
          question_text: '',
          question_index: null,
          question_graphics_figures: null,
      });
      setAddQuestionDialogOpen(true);
  };

  // Handle adding a question using the corrected service function
  const handleAddQuestion = async () => {
    if (!selectedAssignment || !questionData.question_text?.trim()) {
        showAlert('Question text cannot be empty.', 'warning');
        return;
    }

    const questionPayload = {
        question_text: questionData.question_text,
        question_graphics_figures: questionData.question_graphics_figures
    };

    setActionLoading(true);
    try {
      // Call the *correct* service function
      const response = await assignmentService.addQuestion(
          semester, // Now part of the body via service func
          courseId, // Now part of the body via service func
          selectedAssignment.assignment_id, // Now part of the body via service func
          questionPayload // This is the 'question' part of the body
        );

      // Construct the new question using index from response
      const newQuestionFromServer = {
          ...questionPayload,
          question_index: response.question_index
      };

      // Update state
      setSelectedAssignment(prev => ({
          ...prev,
          questions: [...(prev?.questions || []), newQuestionFromServer]
      }));
       setAssignments(prevAssignments => prevAssignments.map(a =>
          a.assignment_id === selectedAssignment.assignment_id
              ? { ...a, questions: [...(a.questions || []), newQuestionFromServer] }
              : a
      ));


      setAddQuestionDialogOpen(false);
      showAlert('Question added successfully');

    } catch (error) {
      console.error('Error adding question:', error);
      showAlert(error.message || 'Failed to add question', 'error');
    } finally {
        setActionLoading(false);
    }
  };

  // Open Edit Question Dialog
  const openEditQuestionDialog = (question) => {
      if (!question) return;
      setQuestionData({
          question_text: question.question_text || '',
          question_index: question.question_index,
          question_graphics_figures: question.question_graphics_figures || null,
      });
      setEditQuestionDialogOpen(true);
  };

  // Handle editing a question using the corrected service function
  const handleEditQuestion = async () => {
    if (!selectedAssignment || questionData.question_index === null || !questionData.question_text?.trim()) {
        showAlert('Question text cannot be empty.', 'warning');
        return;
    }

    const questionPayload = {
        question_text: questionData.question_text,
        question_graphics_figures: questionData.question_graphics_figures
    };

    setActionLoading(true);
    try {
      // Call the *correct* service function
      const updatedQuestionFromServer = await assignmentService.editQuestion(
          semester, // Now part of the body via service func
          courseId, // Now part of the body via service func
          selectedAssignment.assignment_id, // Now part of the body via service func
          questionData.question_index, // Now part of the body via service func
          questionPayload // This is the 'question' part of the body
        );

      // Update state
      setSelectedAssignment(prev => ({
          ...prev,
          questions: (prev?.questions || []).map(q =>
              q.question_index === questionData.question_index
                  ? { ...q, ...updatedQuestionFromServer } // Use data from server
                  : q
          )
      }));
       setAssignments(prevAssignments => prevAssignments.map(a => {
           if (a.assignment_id === selectedAssignment.assignment_id) {
               return {
                   ...a,
                   questions: (a.questions || []).map(q =>
                       q.question_index === questionData.question_index
                           ? { ...q, ...updatedQuestionFromServer }
                           : q
                   )
               };
           }
           return a;
       }));

      setEditQuestionDialogOpen(false);
      showAlert('Question updated successfully');

    } catch (error) {
      console.error('Error editing question:', error);
      showAlert(error.message || 'Failed to edit question', 'error');
    } finally {
        setActionLoading(false);
    }
  };

  // Open Delete Question Dialog
  const openDeleteQuestionDialog = (index) => {
      setQuestionToDeleteIndex(index);
      setDeleteQuestionDialogOpen(true);
  };

  // Handle deleting a question using the corrected service function
  const handleDeleteQuestion = async () => {
    if (!selectedAssignment || questionToDeleteIndex === null) return;

    setActionLoading(true);
    try {
      // Call the *correct* service function
      await assignmentService.removeQuestion(
          semester, // Query param
          courseId, // Query param
          selectedAssignment.assignment_id, // Query param
          questionToDeleteIndex // Query param
        );

        showAlert('Question deleted successfully. Refreshing assignment details...');

        // Re-fetch the entire assignment to get the correctly re-indexed questions from backend
        await fetchAssignmentDetails(selectedAssignment.assignment_id);

        // Also update the main assignments list state (metadata is same, but questions updated)
        setAssignments(prev => prev.map(a =>
            a.assignment_id === selectedAssignment.assignment_id
                ? selectedAssignment // Use the newly fetched assignment data
                : a
        ));


    } catch (error) {
      console.error('Error deleting question:', error);
      showAlert(error.message || 'Failed to delete question', 'error');
    } finally {
      setDeleteQuestionDialogOpen(false);
      setQuestionToDeleteIndex(null);
      setActionLoading(false);
    }
  };


  // Handle Drag and Drop using the corrected service function
  const onDragEnd = useCallback(async (result) => {
      const { source, destination } = result;

      if (!destination || !selectedAssignment || !selectedAssignment.questions || selectedAssignment.questions.length < 2) {
          return; // No drop target, no assignment, or not enough items to reorder
      }
      if (destination.droppableId === source.droppableId && destination.index === source.index) {
          return; // Dropped in the same place
      }

      // --- Optimistic UI Update ---
      const currentQuestions = Array.from(selectedAssignment.questions);
      const [reorderedItem] = currentQuestions.splice(source.index, 1);
      currentQuestions.splice(destination.index, 0, reorderedItem);

      // Update local state immediately
      setSelectedAssignment(prev => ({ ...prev, questions: currentQuestions }));
      setAssignments(prevAssignments => prevAssignments.map(a =>
          a.assignment_id === selectedAssignment.assignment_id
              ? { ...a, questions: currentQuestions }
              : a
      ));
      // --- End Optimistic Update ---

      // Prepare the payload for the backend: list of the *original* question indexes in the new order
      const newIndexOrder = currentQuestions.map(q => q.question_index);

      setActionLoading(true); // Indicate network activity
      try {
          // Call the *correct* service function
          await assignmentService.modifyQuestionOrder(
              semester, // Part of body via service
              courseId, // Part of body via service
              selectedAssignment.assignment_id, // Part of body via service
              newIndexOrder // This is list_of_question_indexes in body
          );
          showAlert('Question order updated successfully. Refreshing...');

          // Re-fetch the assignment to get the source-of-truth order and indexes
          await fetchAssignmentDetails(selectedAssignment.assignment_id);

      } catch (error) {
           console.error('Error modifying question order:', error);
           showAlert(error.message || 'Failed to update question order.', 'error');
           // Revert optimistic update by re-fetching
           showAlert('Reverting order due to error. Refreshing...', 'warning');
           await fetchAssignmentDetails(selectedAssignment.assignment_id); // Re-fetch to revert
      } finally {
          setActionLoading(false);
      }
  }, [selectedAssignment, semester, courseId, showAlert, fetchAssignmentDetails]); // Dependencies


  // --- Render Functions ---

  const renderAssignmentList = () => {
    if (loadingAssignments) {
        return (
            <Grid container spacing={3} sx={{ mb: 4 }}>
                {[1, 2, 3].map((n) => (
                    <Grid item xs={12} sm={6} md={4} key={n}>
                        <CardSkeleton />
                    </Grid>
                ))}
            </Grid>
        );
    }

    if (!loadingAssignments && assignments.length === 0 && !listError) {
        return (
            <NoAssignmentsBox>
                <AssignmentIcon sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} />
                <Typography variant="h6">No assignments found for this course.</Typography>
                <Typography color="text.secondary" sx={{ mb: 2 }}>
                    Get started by creating a new assignment.
                </Typography>
                <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    onClick={() => setCreateDialogOpen(true)}
                    >
                    Create First Assignment
                </Button>
            </NoAssignmentsBox>
        );
    }

     if (listError) {
        return <Alert severity="error" sx={{ mb: 3 }}>{listError}</Alert>;
     }

    return (
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {assignments.map((assignment) => (
          <Grid item xs={12} sm={6} md={4} key={assignment.assignment_id}>
            <AssignmentCard variant="outlined" sx={{ borderColor: selectedAssignment?.assignment_id === assignment.assignment_id ? 'primary.main' : undefined }}>
              <CardActionArea onClick={() => handleSelectAssignment(assignment)} sx={{ flexGrow: 1 }}>
                <AssignmentCardContent>
                  <Typography gutterBottom variant="h6" component="div" noWrap title={assignment.assignment_title || `Assignment ${assignment.assignment_id}`}>
                    {assignment.assignment_title || `Assignment ${assignment.assignment_id}`}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    ID: {assignment.assignment_id}
                  </Typography>
                   <Typography variant="body2" color="text.secondary" sx={{
                       overflow: 'hidden',
                       textOverflow: 'ellipsis',
                       display: '-webkit-box',
                       WebkitLineClamp: 3, // Show max 3 lines
                       WebkitBoxOrient: 'vertical',
                       flexGrow: 1, // Allow text to take available space
                   }}>
                    {assignment.assignment_guidelines || 'No guidelines provided.'}
                  </Typography>
                </AssignmentCardContent>
              </CardActionArea>
               <CardActions sx={{ justifyContent: 'flex-end', pt: 0 }}>
                   <IconButton title="Edit Assignment Info" size="small" onClick={(e) => { e.stopPropagation(); openEditAssignmentDialog(assignment); }}>
                       <EditIcon fontSize="small" />
                   </IconButton>
                   <IconButton title="Delete Assignment" size="small" onClick={(e) => { e.stopPropagation(); setSelectedAssignment(assignment); setDeleteAssignmentDialogOpen(true); }}>
                       <DeleteIcon fontSize="small" />
                   </IconButton>
               </CardActions>
            </AssignmentCard>
          </Grid>
        ))}
      </Grid>
    );
  };


  const renderAssignmentDetails = () => {
    if (loadingDetails) {
        return (
            <Paper elevation={0} sx={{ mt: 4, p: 3, textAlign: 'center' }}>
                <CircularProgress />
                <Typography sx={{ mt: 1 }}>Loading assignment details...</Typography>
            </Paper>
        );
    }

    if (detailsError) {
         return (
            <Paper elevation={0} sx={{ mt: 4, p: 3 }}>
                <Alert severity="error">{detailsError}</Alert>
            </Paper>
         );
    }

    if (!selectedAssignment) {
        // Only show this if assignments exist but none are selected
        if (assignments.length > 0 && !loadingAssignments) {
             return (
                <Paper elevation={0} variant="outlined" sx={{ mt: 4, p: 3, textAlign: 'center' }}>
                    <Typography color="text.secondary">Select an assignment above to view its details and questions.</Typography>
                </Paper>
             );
        }
        return null; // Don't render anything if still loading assignments or none exist
    }


    return (
      <Paper elevation={3} sx={{ mt: 4, p: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 1 }}>
              <Typography variant="h5" component="h2">
                  {selectedAssignment.assignment_title} - Details
              </Typography>
              <Box>
                   <Button
                      variant="outlined"
                      size="small"
                      startIcon={<EditIcon />}
                      onClick={() => openEditAssignmentDialog(selectedAssignment)}
                      sx={{ mr: 1 }}
                      disabled={actionLoading}
                   >
                      Edit Info
                   </Button>
                   <Button
                      variant="outlined"
                      size="small"
                      color="error"
                      startIcon={<DeleteIcon />}
                      onClick={() => setDeleteAssignmentDialogOpen(true)}
                      disabled={actionLoading}
                   >
                      Delete Assignment
                   </Button>
              </Box>
          </Box>

         <Typography variant="body1" color="text.secondary" paragraph sx={{ whiteSpace: 'pre-wrap' }}>
          {selectedAssignment.assignment_guidelines || 'No guidelines provided.'}
        </Typography>

        <Divider sx={{ my: 3 }} />

        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">Questions</Typography>
            <Button
              variant="contained"
              size="small"
              startIcon={<AddIcon />}
              onClick={openAddQuestionDialog}
              disabled={actionLoading}
            >
              Add Question
            </Button>
        </Box>


        {!selectedAssignment.questions?.length && (
            <Typography color="text.secondary" sx={{ fontStyle: 'italic' }}>No questions added yet.</Typography>
        )}

        {selectedAssignment.questions?.length > 0 && (
          <DragDropContext onDragEnd={onDragEnd}>
            <Droppable droppableId="questions">
              {(provided) => (
                <List {...provided.droppableProps} ref={provided.innerRef}>
                  {selectedAssignment.questions.map((question, index) => (
                    <Draggable
                        key={`${selectedAssignment.assignment_id}-${question.question_index}`} // Use a more stable key if index changes
                        draggableId={`${selectedAssignment.assignment_id}-${question.question_index}`}
                        index={index}
                        isDragDisabled={actionLoading} // Disable drag during actions
                    >
                      {(providedDraggable, snapshot) => (
                        <QuestionItem
                          ref={providedDraggable.innerRef}
                          {...providedDraggable.draggableProps}
                          isDragging={snapshot.isDragging}
                          secondaryAction={
                            <Box sx={{ display: 'flex', alignItems: 'center' }}>
                              <IconButton edge="end" title="Edit Question" aria-label="edit" sx={{ mr: 0.5 }} onClick={() => openEditQuestionDialog(question)} disabled={actionLoading}>
                                <EditIcon fontSize="small"/>
                              </IconButton>
                              <IconButton edge="end" title="Delete Question" aria-label="delete" onClick={() => openDeleteQuestionDialog(question.question_index)} disabled={actionLoading}>
                                <DeleteIcon fontSize="small"/>
                              </IconButton>
                              <Box {...providedDraggable.dragHandleProps} sx={{ display: 'inline-flex', alignItems: 'center', ml: 1, cursor: actionLoading? 'not-allowed' : 'grab', color: actionLoading? 'text.disabled' : 'inherit' }}>
                                  <DragIndicatorIcon />
                              </Box>
                            </Box>
                          }
                        >
                          <ListItemIcon sx={{ minWidth: 'auto', mr: 1.5 }}>
                            <QuestionIcon fontSize="small"/>
                          </ListItemIcon>
                          <ListItemText
                            primary={`Q${index + 1}: ${question.question_text}`}
                            primaryTypographyProps={{ sx: { wordBreak: 'break-word' } }}
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
      </Paper>
    );
  };

  // --- Main Return ---
  return (
    <Box sx={{ p: { xs: 1, sm: 2, md: 3 } }}> {/* Responsive padding */}
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 1 }}>
        <IconButton
          title="Back to Course"
          aria-label="back to course"
          onClick={() => router.push(`/course/${courseId}?semester=${semester}`)}
          sx={{ mr: 1 }}
        >
          <ArrowBackIcon />
        </IconButton>
        <Typography variant="h4" component="h1" sx={{ flexGrow: 1 }}>
          Course Assignments
        </Typography>
         <Button
          variant="contained"
          color="primary"
          size="small"
          startIcon={<AddIcon />}
          onClick={() => setCreateDialogOpen(true)}
          disabled={actionLoading}
        >
          Create Assignment
        </Button>
      </Box>

      {/* Render Assignment List Section */}
      <Typography variant="h5" sx={{ mb: 2 }}>Assignments List</Typography>
      {renderAssignmentList()}

      <Divider sx={{ my: 4 }} />

      {/* Render Details of Selected Assignment Section */}
       <Typography variant="h5" sx={{ mb: 2 }}>Selected Assignment Details</Typography>
      {renderAssignmentDetails()}


      {/* --- DIALOGS --- */}
      {/* Note: Moved dialog implementations outside render functions for clarity */}
      {/* Create Assignment Dialog */}
      <Dialog open={createDialogOpen} onClose={() => !actionLoading && setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Assignment</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            id="new-assignment-title" // Added id
            name="assignment_title"
            label="Assignment Title"
            fullWidth
            value={newAssignmentData.assignment_title}
            onChange={(e) => handleInputChange(e, setNewAssignmentData)}
            margin="dense" // Use dense margin
            required
            error={!newAssignmentData.assignment_title?.trim()} // Validate on trimmed value
            helperText={!newAssignmentData.assignment_title?.trim() ? "Title is required" : ""}
          />
          <TextField
             id="new-assignment-guidelines" // Added id
            name="assignment_guidelines"
            label="Assignment Guidelines"
            fullWidth
            multiline
            rows={4}
            value={newAssignmentData.assignment_guidelines}
            onChange={(e) => handleInputChange(e, setNewAssignmentData)}
            margin="dense" // Use dense margin
            helperText="General instructions or requirements (optional)"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)} disabled={actionLoading}>Cancel</Button>
          <Button onClick={handleCreateAssignment} variant="contained" color="primary" disabled={actionLoading || !newAssignmentData.assignment_title?.trim()}>
            {actionLoading ? <CircularProgress size={24} /> : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Assignment Dialog */}
      <Dialog open={editAssignmentDialogOpen} onClose={() => !actionLoading && setEditAssignmentDialogOpen(false)} maxWidth="sm" fullWidth>
          <DialogTitle>Edit Assignment Info</DialogTitle>
          <DialogContent>
              <TextField
                  autoFocus
                  id="edit-assignment-title" // Added id
                  name="assignment_title"
                  label="Assignment Title"
                  fullWidth
                  value={editAssignmentFormData.assignment_title}
                  onChange={(e) => handleInputChange(e, setEditAssignmentFormData)}
                  margin="dense"
                  required
                  error={!editAssignmentFormData.assignment_title?.trim()}
                  helperText={!editAssignmentFormData.assignment_title?.trim() ? "Title is required" : ""}
              />
              <TextField
                  id="edit-assignment-guidelines" // Added id
                  name="assignment_guidelines"
                  label="Assignment Guidelines"
                  fullWidth
                  multiline
                  rows={4}
                  value={editAssignmentFormData.assignment_guidelines}
                  onChange={(e) => handleInputChange(e, setEditAssignmentFormData)}
                  margin="dense"
                  helperText="General instructions or requirements (optional)"
              />
          </DialogContent>
          <DialogActions>
              <Button onClick={() => setEditAssignmentDialogOpen(false)} disabled={actionLoading}>Cancel</Button>
              <Button onClick={handleUpdateAssignment} variant="contained" color="primary" disabled={actionLoading || !editAssignmentFormData.assignment_title?.trim()}>
                 {actionLoading ? <CircularProgress size={24} /> : 'Save Changes'}
              </Button>
          </DialogActions>
      </Dialog>

       {/* Add Question Dialog */}
        <Dialog open={addQuestionDialogOpen} onClose={() => !actionLoading && setAddQuestionDialogOpen(false)} maxWidth="md" fullWidth>
            <DialogTitle>Add New Question</DialogTitle>
            <DialogContent>
                <TextField
                    autoFocus
                    id="add-question-text" // Added id
                    name="question_text"
                    label="Question Text"
                    fullWidth
                    multiline
                    rows={6}
                    value={questionData.question_text}
                    onChange={(e) => handleInputChange(e, setQuestionData)}
                    margin="dense"
                    required
                    error={!questionData.question_text?.trim()}
                    helperText={!questionData.question_text?.trim() ? "Question text is required" : ""}
                />
                {/* TODO: Add input for question_graphics_figures (e.g., file upload) */}
                <Typography variant="caption" display="block" sx={{ mt: 1 }}>Graphics/Figures can be added later if needed.</Typography>
            </DialogContent>
            <DialogActions>
                <Button onClick={() => setAddQuestionDialogOpen(false)} disabled={actionLoading}>Cancel</Button>
                <Button onClick={handleAddQuestion} variant="contained" color="primary" disabled={actionLoading || !questionData.question_text?.trim()}>
                   {actionLoading ? <CircularProgress size={24} /> : 'Add Question'}
                </Button>
            </DialogActions>
        </Dialog>

        {/* Edit Question Dialog */}
        <Dialog open={editQuestionDialogOpen} onClose={() => !actionLoading && setEditQuestionDialogOpen(false)} maxWidth="md" fullWidth>
            <DialogTitle>Edit Question {questionData.question_index !== null ? `(Q${questionData.question_index + 1})` : ''}</DialogTitle>
            <DialogContent>
                 <TextField
                    autoFocus
                    id="edit-question-text" // Added id
                    name="question_text"
                    label="Question Text"
                    fullWidth
                    multiline
                    rows={6}
                    value={questionData.question_text}
                    onChange={(e) => handleInputChange(e, setQuestionData)}
                    margin="dense"
                    required
                    error={!questionData.question_text?.trim()}
                    helperText={!questionData.question_text?.trim() ? "Question text is required" : ""}
                />
                 {/* TODO: Add input for question_graphics_figures (e.g., file upload and preview) */}
                 <Typography variant="caption" display="block" sx={{ mt: 1 }}>Graphics/Figures can be added later if needed.</Typography>
            </DialogContent>
            <DialogActions>
                <Button onClick={() => setEditQuestionDialogOpen(false)} disabled={actionLoading}>Cancel</Button>
                <Button onClick={handleEditQuestion} variant="contained" color="primary" disabled={actionLoading || !questionData.question_text?.trim()}>
                    {actionLoading ? <CircularProgress size={24} /> : 'Save Changes'}
                </Button>
            </DialogActions>
        </Dialog>

      {/* Delete Assignment Confirmation */}
      <ConfirmationDialog
          open={deleteAssignmentDialogOpen}
          onClose={() => !actionLoading && setDeleteAssignmentDialogOpen(false)}
          onConfirm={handleDeleteAssignment}
          title="Delete Assignment?"
          description={`Are you sure you want to delete the assignment "${selectedAssignment?.assignment_title || 'this assignment'}"? This action will delete the assignment, all its questions, rubrics, and submitted responses. This cannot be undone.`}
          confirmText="Delete"
          cancelText="Cancel"
          confirmColor="error"
          loading={actionLoading}
      />

      {/* Delete Question Confirmation */}
       <ConfirmationDialog
          open={deleteQuestionDialogOpen}
          onClose={() => !actionLoading && setDeleteQuestionDialogOpen(false)}
          onConfirm={handleDeleteQuestion}
          title="Delete Question?"
          description={`Are you sure you want to delete question ${questionToDeleteIndex !== null ? questionToDeleteIndex + 1 : ''}? This will remove the question and may affect associated rubrics or responses. This cannot be undone.`}
          confirmText="Delete"
          cancelText="Cancel"
          confirmColor="error"
          loading={actionLoading}
      />

      {/* Snackbar for Alerts */}
      <Snackbar
          open={alertOpen}
          autoHideDuration={6000}
          onClose={() => setAlertOpen(false)}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        >
          {/* Ensure Alert component is correctly imported from @mui/material */}
          <Alert onClose={() => setAlertOpen(false)} severity={alertSeverity} variant="filled" sx={{ width: '100%' }}>
            {alertMessage}
          </Alert>
      </Snackbar>
    </Box>
  );
}