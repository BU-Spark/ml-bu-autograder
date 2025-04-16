/**
 * Course Assignments Page for BU MET Autograder
 * This page allows instructors to manage assignments and their questions.
 * The component expects the backend to return an object like:
 *
 * {
 *   "semester": "spring2025",
 *   "course_id": "met505",
 *   "assignment_id": "ab6ebdae-1caa-4daa-9c56-7e9048b0f30f",
 *   "assignment_guidelines": null,
 *   "questions": []
 * }
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
} from '@mui/icons-material';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';
import { assignmentService } from '../../../api';
import CardSkeleton from '../../../components/CardSkeleton';
import ConfirmationDialog from '../../../components/ConfirmationDialog';

// Styled Components
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
  paddingRight: theme.spacing(16),
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

export default function Assignments() {
  const router = useRouter();
  const { id: courseIdParam, semester: semesterParam, assignment_id: assignmentId } = router.query;
  const courseId = typeof courseIdParam === 'string' ? courseIdParam : null;
  const semester = typeof semesterParam === 'string' ? semesterParam : null;


  // States for assignments and UI state management
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

  // New assignments only have guidelines (no separate title)
  const [newAssignmentData, setNewAssignmentData] = useState({ assignment_guidelines: '' });
  const [editAssignmentFormData, setEditAssignmentFormData] = useState({ assignment_guidelines: '' });
  const [questionData, setQuestionData] = useState({ question_text: '', question_index: null, question_graphics_figures: null });
  const [questionToDeleteIndex, setQuestionToDeleteIndex] = useState(null);
  const [alertOpen, setAlertOpen] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [alertSeverity, setAlertSeverity] = useState('success');

  // Helper function to update input state
  const handleInputChange = useCallback((event, setter) => {
    const { name, value } = event.target;
    setter(prev => ({ ...prev, [name]: value }));
  }, []);

  // Helper function to show alerts
  const showAlert = useCallback((message, severity = 'success') => {
    setAlertMessage(message);
    setAlertSeverity(severity);
    setAlertOpen(true);
  }, []);

  // Data fetching: load assignment details based on assignment_id
  const fetchAssignmentDetails = useCallback(async (idToFetch) => {
    if (!courseId || !semester || !idToFetch) return;
    setLoadingDetails(true);
    setDetailsError(null);
    try {
      const assignmentWithQuestions = await assignmentService.getAssignment(courseId, semester, idToFetch, true);
      // Sort questions by their index if needed
      if (Array.isArray(assignmentWithQuestions.questions)) {
        assignmentWithQuestions.questions.sort((a, b) => a.question_index - b.question_index);
      } else {
        assignmentWithQuestions.questions = [];
      }
      // Capture the complete response from the backend (including assignment_id)
      setSelectedAssignment(assignmentWithQuestions);
    } catch (err) {
      setDetailsError(err.message || 'Failed to load details.');
      setSelectedAssignment(null);
    } finally {
      setLoadingDetails(false);
    }
  }, [courseId, semester]);

  // Fetch all assignments when courseId and semester are available
  useEffect(() => {
    if (courseId && semester) {
      const fetchAssignments = async () => {
        setLoadingAssignments(true);
        setListError(null);
        try {
          const assignmentsData = await assignmentService.getAssignments(courseId, semester);
          if (Array.isArray(assignmentsData)) {
            setAssignments(assignmentsData);
          } else {
            setAssignments([]);
          }
        } catch (err) {
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

  // Event handler: selecting an assignment updates the URL and local state.
  const handleSelectAssignment = (assignment) => {
    if (!courseId || !semester || !assignment?.assignment_id) return;
    const newRoute = `/course/${courseId}/assignments?semester=${semester}&assignmentId=${assignment.assignment_id}`;
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

  // Open the Create Assignment dialog
  const openCreateDialog = () => {
    setNewAssignmentData({ assignment_guidelines: '' });
    setCreateDialogOpen(true);
  };

  // Create Assignment: note that assignment_id is omitted so the backend generates it.
  const handleCreateAssignment = async () => {
    if (!courseId || !semester) {
      showAlert('Course context missing.', 'warning');
      return;
    }
    setActionLoading(true);
    try {
      const assignmentPayload = {
        assignment_id: assignmentId, // Backend should generate this
        course_id: courseId,
        semester: semester,
        assignment_guidelines: newAssignmentData.assignment_guidelines || null,
        questions: [],
      };
      const newAssignment = await assignmentService.createAssignment(assignmentPayload);
      // The newAssignment response should include assignment_id, as in your JSON example.
      setAssignments(prev => [...prev, newAssignment]);
      setNewAssignmentData({ assignment_guidelines: '' });
      setCreateDialogOpen(false);
      showAlert(`Assignment created (ID: ${newAssignment.assignment_id}).`);
      handleSelectAssignment(newAssignment);
    } catch (error) {
      showAlert(error.response?.data?.detail || error.message || 'Failed to create assignment.', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  // Open Edit Assignment dialog
  const openEditAssignmentDialog = (assignmentToEdit) => {
    if (!assignmentToEdit || !assignmentToEdit.assignment_id) return;
    setSelectedAssignment(assignmentToEdit);
    setEditAssignmentFormData({
      assignment_guidelines: assignmentToEdit.assignment_guidelines || '',
    });
    setEditAssignmentDialogOpen(true);
  };

  // Update Assignment metadata
  const handleUpdateAssignment = async () => {
    if (!selectedAssignment || !selectedAssignment.assignment_id || !semester || !courseId) return;
    const { assignment_guidelines } = editAssignmentFormData;
    const updatePayload = { assignment_guidelines: assignment_guidelines || null };
    setActionLoading(true);
    try {
      const updatedAssignment = await assignmentService.updateAssignmentMetadata(
        semester,
        courseId,
        selectedAssignment.assignment_id,
        updatePayload
      );
      setAssignments(prev =>
        prev.map(a =>
          a.assignment_id === selectedAssignment.assignment_id ? { ...a, ...updatedAssignment } : a
        )
      );
      setSelectedAssignment(prev => ({ ...prev, ...updatedAssignment }));
      setEditAssignmentDialogOpen(false);
      showAlert('Assignment updated.');
    } catch (error) {
      showAlert(error.message || 'Failed to update assignment.', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  // Delete Assignment
  const handleDeleteAssignment = async () => {
    if (!selectedAssignment || !semester || !courseId) {
      showAlert('Cannot delete: context is missing.', 'error');
      setDeleteAssignmentDialogOpen(false);
      return;
    }
    setActionLoading(true);
    setDeleteAssignmentDialogOpen(false);
    try {
      await assignmentService.deleteAssignment(courseId, semester, selectedAssignment.assignment_id);
      setAssignments(prev => prev.filter(a => a.assignment_id !== selectedAssignment.assignment_id));
      showAlert(`Assignment (ID: ${selectedAssignment.assignment_id}) deleted successfully.`);
      handleClearSelection();
    } catch (error) {
      const displayError = error.response?.data?.detail || error.message || 'Failed to delete assignment.';
      showAlert(displayError, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  // --- Question CRUD ---

  const openAddQuestionDialog = () => {
    if (!selectedAssignment || !selectedAssignment.assignment_id) {
      showAlert('Select a valid assignment first.', 'warning');
      return;
    }
    setQuestionData({ question_text: '', question_index: null, question_graphics_figures: null });
    setAddQuestionDialogOpen(true);
  };

  const handleAddQuestion = async () => {
    if (!selectedAssignment || !selectedAssignment.assignment_id || !semester || !courseId || !questionData.question_text?.trim()) {
      showAlert(!selectedAssignment ? 'No assignment selected.' : 'Question text required.', 'warning');
      return;
    }
    const questionPayload = { question_text: questionData.question_text.trim(), question_graphics_figures: null };
    setActionLoading(true);
    try {
      const response = await assignmentService.addQuestion(semester, courseId, selectedAssignment.assignment_id, questionPayload);
      // Expecting response to include a question_index for the new question.
      const newQuestion = { ...questionPayload, question_index: response.question_index };
      setSelectedAssignment(prev => {
        const updatedQuestions = [...(prev?.questions || []), newQuestion].sort((a, b) => a.question_index - b.question_index);
        return { ...prev, questions: updatedQuestions };
      });
      setAddQuestionDialogOpen(false);
      showAlert('Question added.');
      setQuestionData({ question_text: '', question_index: null, question_graphics_figures: null });
    } catch (error) {
      showAlert(error.message || 'Failed to add question.', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const openEditQuestionDialog = (question) => {
    if (!question || question.question_index === null) return;
    setQuestionData({
      question_text: question.question_text || '',
      question_index: question.question_index,
      question_graphics_figures: question.question_graphics_figures || null,
    });
    setEditQuestionDialogOpen(true);
  };

  const handleEditQuestion = async () => {
    if (!selectedAssignment || !selectedAssignment.assignment_id || questionData.question_index === null || !semester || !courseId || !questionData.question_text?.trim()) {
      showAlert('Invalid data or context for editing question.', 'warning');
      return;
    }
    const questionPayload = { question_text: questionData.question_text.trim(), question_graphics_figures: null };
    setActionLoading(true);
    try {
      const updatedQuestion = await assignmentService.editQuestion(
        semester,
        courseId,
        selectedAssignment.assignment_id,
        questionData.question_index,
        questionPayload
      );
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
      showAlert(error.message || 'Failed to edit question.', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const onDragEnd = useCallback(async (result) => {
    const { source, destination } = result;
    if (!destination || !selectedAssignment || !selectedAssignment.assignment_id || !selectedAssignment.questions || selectedAssignment.questions.length < 2 || !semester || !courseId) return;
    if (destination.droppableId === source.droppableId && destination.index === source.index) return;
    const currentQuestions = Array.from(selectedAssignment.questions).sort((a, b) => a.question_index - b.question_index);
    const [reorderedItem] = currentQuestions.splice(source.index, 1);
    currentQuestions.splice(destination.index, 0, reorderedItem);
    setSelectedAssignment(prev => ({ ...prev, questions: currentQuestions }));
    const newIndexOrder = currentQuestions.map(q => q.question_index);
    setActionLoading(true);
    try {
      await assignmentService.modifyQuestionOrder(semester, courseId, selectedAssignment.assignment_id, newIndexOrder);
      showAlert('Order updated. Refreshing details...');
      await fetchAssignmentDetails(selectedAssignment.assignment_id);
    } catch (error) {
      showAlert(error.message || 'Failed to update order.', 'error');
      await fetchAssignmentDetails(selectedAssignment.assignment_id);
    } finally {
      setActionLoading(false);
    }
  }, [selectedAssignment, semester, courseId, fetchAssignmentDetails]);

  const openDeleteQuestionDialog = (index) => {
    if (typeof index !== 'number') return;
    setQuestionToDeleteIndex(index);
    setDeleteQuestionDialogOpen(true);
  };

  const handleDeleteQuestion = async () => {
    if (!selectedAssignment || !selectedAssignment.assignment_id || questionToDeleteIndex === null || typeof questionToDeleteIndex !== 'number' || !semester || !courseId) return;
    setActionLoading(true);
    try {
      await assignmentService.removeQuestion(semester, courseId, selectedAssignment.assignment_id, questionToDeleteIndex);
      showAlert('Question deleted. Refreshing details...');
      await fetchAssignmentDetails(selectedAssignment.assignment_id);
    } catch (error) {
      showAlert(error.message || 'Failed to delete question.', 'error');
    } finally {
      setDeleteQuestionDialogOpen(false);
      setQuestionToDeleteIndex(null);
      setActionLoading(false);
    }
  };

  // Render function for the assignment list
  const renderAssignmentList = () => {
    if (loadingAssignments) {
      return (
        <Grid container spacing={3} sx={{ mb: 4 }}>
          {[1, 2, 3].map(n => (
            <Grid item xs={12} sm={6} md={4} key={n}>
              <CardSkeleton />
            </Grid>
          ))}
        </Grid>
      );
    }
    if (listError) return <Alert severity="error" sx={{ mb: 3 }}>{listError}</Alert>;
    if (!assignments.length) {
      return (
        <NoAssignmentsBox>
          <AssignmentIcon sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6">No assignments found.</Typography>
          <Typography color="text.secondary" sx={{ mb: 2 }}>Create one to get started.</Typography>
          <Button variant="contained" startIcon={<AddIcon />} onClick={openCreateDialog}>Create Assignment</Button>
        </NoAssignmentsBox>
      );
    }
    return (
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {assignments.map(assignment => (
          <Grid item xs={12} sm={6} md={4} key={assignment.assignment_id}>
            <AssignmentCard variant="outlined" sx={{ borderColor: selectedAssignment?.assignment_id === assignment.assignment_id ? 'primary.main' : 'divider' }}>
              <CardActionArea onClick={() => handleSelectAssignment(assignment)} sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                <AssignmentCardContent>
                  <Typography gutterBottom variant="h6" noWrap title={`Assignment ${assignment.assignment_id}`}>
                    {`Assignment ${assignment.assignment_id}`}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    ID: {assignment.assignment_id}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    display: '-webkit-box',
                    WebkitLineClamp: 3,
                    WebkitBoxOrient: 'vertical',
                    flexGrow: 1,
                  }}>
                    {assignment.assignment_guidelines || 'No guidelines.'}
                  </Typography>
                </AssignmentCardContent>
              </CardActionArea>
              <CardActions sx={{ justifyContent: 'flex-end', pt: 0, pb: 1, px: 1 }}>
                <IconButton title="Edit Assignment Info" size="small" onClick={(e) => { e.stopPropagation(); openEditAssignmentDialog(assignment); }} disabled={actionLoading}>
                  <EditIcon fontSize="small" />
                </IconButton>
                <IconButton title="Delete Assignment" size="small" onClick={(e) => { e.stopPropagation(); setSelectedAssignment(assignment); setDeleteAssignmentDialogOpen(true); }} disabled={actionLoading} color="error">
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </CardActions>
            </AssignmentCard>
          </Grid>
        ))}
      </Grid>
    );
  };

  // Render function for assignment details
  const renderAssignmentDetails = () => {
    if (loadingDetails) {
      return (
        <Paper elevation={0} sx={{ mt: 4, p: 3, textAlign: 'center' }}>
          <CircularProgress />
          <Typography sx={{ mt: 1 }}>Loading details...</Typography>
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
    if (!selectedAssignment || !selectedAssignment.assignment_id) {
      if (!loadingAssignments && assignments.length > 0) {
        return (
          <Paper elevation={0} variant="outlined" sx={{ mt: 4, p: 3, textAlign: 'center' }}>
            <Typography color="text.secondary">Select an assignment to view details.</Typography>
          </Paper>
        );
      }
      return null;
    }
    return (
      <Paper elevation={3} sx={{ mt: 4, p: { xs: 1, sm: 2, md: 3 } }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 1 }}>
          <Typography variant="h5" component="h2">{`Assignment ${selectedAssignment.assignment_id}`}</Typography>
          <Box>
            <Button variant="outlined" size="small" startIcon={<EditIcon />} onClick={() => openEditAssignmentDialog(selectedAssignment)} sx={{ mr: 1 }} disabled={actionLoading}>
              Edit Info
            </Button>
            <Button variant="outlined" size="small" color="error" startIcon={<DeleteIcon />} onClick={() => setDeleteAssignmentDialogOpen(true)} disabled={actionLoading}>
              Delete Assignment
            </Button>
          </Box>
        </Box>
        <Typography variant="body2" color="text.secondary" paragraph sx={{
          whiteSpace: 'pre-wrap',
          maxHeight: '150px',
          overflowY: 'auto',
          border: '1px solid #eee',
          p: 1,
          borderRadius: 1,
          background: '#f9f9f9',
        }}>
          {selectedAssignment.assignment_guidelines || 'No guidelines.'}
        </Typography>
        <Divider sx={{ my: 3 }} />
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Questions</Typography>
          <Button variant="contained" size="small" startIcon={<AddIcon />} onClick={openAddQuestionDialog} disabled={actionLoading}>
            Add Question
          </Button>
        </Box>
        {(!selectedAssignment.questions || !selectedAssignment.questions.length) && (
          <Typography color="text.secondary" sx={{ fontStyle: 'italic', textAlign: 'center', py: 2 }}>
            No questions added yet.
          </Typography>
        )}
        {selectedAssignment.questions && selectedAssignment.questions.length > 0 && (
          <DragDropContext onDragEnd={onDragEnd}>
            <Droppable droppableId="questions">
              {(provided) => (
                <List {...provided.droppableProps} ref={provided.innerRef}>
                  {selectedAssignment.questions.map((question, index) => (
                    <Draggable key={`${selectedAssignment.assignment_id}-${question.question_index}`} draggableId={`${selectedAssignment.assignment_id}-${question.question_index}`} index={index} isDragDisabled={actionLoading}>
                      {(providedDraggable, snapshot) => (
                        <QuestionItem ref={providedDraggable.innerRef} {...providedDraggable.draggableProps} isDragging={snapshot.isDragging}
                          secondaryAction={
                            <Box sx={{ display: 'flex', alignItems: 'center' }}>
                              <IconButton edge="end" title="Edit Question" sx={{ mr: 0.5 }} onClick={() => openEditQuestionDialog(question)} disabled={actionLoading}>
                                <EditIcon fontSize="small"/>
                              </IconButton>
                              <IconButton edge="end" title="Delete Question" onClick={() => openDeleteQuestionDialog(question.question_index)} disabled={actionLoading}>
                                <DeleteIcon fontSize="small"/>
                              </IconButton>
                              <Box {...providedDraggable.dragHandleProps} sx={{ display: 'inline-flex', alignItems: 'center', ml: 1, cursor: actionLoading ? 'not-allowed' : 'grab' }} title="Drag to reorder">
                                <DragIndicatorIcon />
                              </Box>
                            </Box>
                          }>
                          <ListItemIcon sx={{ minWidth: 'auto', mr: 1.5 }}>
                            <Typography variant="body2" sx={{ fontWeight: 'bold' }}>{`Q${index + 1}:`}</Typography>
                          </ListItemIcon>
                          <ListItemText primary={`${question.question_text}`} primaryTypographyProps={{ sx: { wordBreak: 'break-word' } }}/>
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

  return (
    <Box sx={{ p: { xs: 1, sm: 2, md: 3 } }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 1 }}>
        <IconButton title="Back" aria-label="back" onClick={() => (courseId && semester) && router.push(`/course/${courseId}?semester=${semester}`)} disabled={!courseId || !semester} sx={{ mr: 1 }}>
          <ArrowBackIcon />
        </IconButton>
        <Typography variant="h4" component="h1" sx={{ flexGrow: 1 }}>Course Assignments</Typography>
        <Button variant="contained" color="primary" size="small" startIcon={<AddIcon />} onClick={openCreateDialog} disabled={actionLoading || !courseId || !semester}>
          Create Assignment
        </Button>
      </Box>

      <Typography variant="h5" sx={{ mb: 2 }}>Assignments List</Typography>
      {renderAssignmentList()}

      <Divider sx={{ my: 4 }} />

      <Typography variant="h5" sx={{ mb: 2 }}>Selected Assignment Details</Typography>
      {renderAssignmentDetails()}

      {/* Create Assignment Dialog */}
      <Dialog open={createDialogOpen} onClose={() => !actionLoading && setCreateDialogOpen(false)} maxWidth="sm" fullWidth aria-labelledby="create-assignment-dialog-title">
        <DialogTitle id="create-assignment-dialog-title">Create New Assignment</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            id="new-assignment-guidelines"
            name="assignment_guidelines"
            label="Assignment Guidelines (Optional)"
            fullWidth
            multiline
            rows={4}
            value={newAssignmentData.assignment_guidelines}
            onChange={(e) => handleInputChange(e, setNewAssignmentData)}
            margin="dense"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)} disabled={actionLoading}>Cancel</Button>
          <Button onClick={handleCreateAssignment} variant="contained" color="primary" disabled={actionLoading}>
            {actionLoading ? <CircularProgress size={24}/> : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Assignment Dialog */}
      <Dialog open={editAssignmentDialogOpen} onClose={() => !actionLoading && setEditAssignmentDialogOpen(false)} maxWidth="sm" fullWidth aria-labelledby="edit-assignment-dialog-title">
        <DialogTitle id="edit-assignment-dialog-title">Edit Assignment Info</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            id="edit-assignment-guidelines"
            name="assignment_guidelines"
            label="Assignment Guidelines (Optional)"
            fullWidth
            multiline
            rows={4}
            value={editAssignmentFormData.assignment_guidelines}
            onChange={(e) => handleInputChange(e, setEditAssignmentFormData)}
            margin="dense"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditAssignmentDialogOpen(false)} disabled={actionLoading}>Cancel</Button>
          <Button onClick={handleUpdateAssignment} variant="contained" color="primary" disabled={actionLoading}>
            {actionLoading ? <CircularProgress size={24}/> : 'Save Changes'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Add Question Dialog */}
      <Dialog open={addQuestionDialogOpen} onClose={() => !actionLoading && setAddQuestionDialogOpen(false)} maxWidth="md" fullWidth aria-labelledby="add-question-dialog-title">
        <DialogTitle id="add-question-dialog-title">Add New Question</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            id="add-question-text"
            name="question_text"
            label="Question Text"
            fullWidth
            multiline
            rows={6}
            value={questionData.question_text}
            onChange={(e) => handleInputChange(e, setQuestionData)}
            margin="dense"
            required
            error={!questionData.question_text?.trim() && questionData.question_text !== ''}
            helperText={!questionData.question_text?.trim() && questionData.question_text !== '' ? "Question text is required" : ""}
          />
          <Typography variant="caption" display="block" sx={{ mt: 1 }}>Graphics/Figures not yet supported.</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddQuestionDialogOpen(false)} disabled={actionLoading}>Cancel</Button>
          <Button onClick={handleAddQuestion} variant="contained" color="primary" disabled={actionLoading || !questionData.question_text?.trim()}>
            {actionLoading ? <CircularProgress size={24}/> : 'Add Question'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Question Dialog */}
      <Dialog open={editQuestionDialogOpen} onClose={() => !actionLoading && setEditQuestionDialogOpen(false)} maxWidth="md" fullWidth aria-labelledby="edit-question-dialog-title">
        <DialogTitle id="edit-question-dialog-title">Edit Question {questionData.question_index !== null ? `(Original Index ${questionData.question_index})` : ''}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            id="edit-question-text"
            name="question_text"
            label="Question Text"
            fullWidth
            multiline
            rows={6}
            value={questionData.question_text}
            onChange={(e) => handleInputChange(e, setQuestionData)}
            margin="dense"
            required
            error={!questionData.question_text?.trim() && questionData.question_text !== ''}
            helperText={!questionData.question_text?.trim() && questionData.question_text !== '' ? "Question text is required" : ""}
          />
          <Typography variant="caption" display="block" sx={{ mt: 1 }}>Graphics/Figures not yet supported.</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditQuestionDialogOpen(false)} disabled={actionLoading}>Cancel</Button>
          <Button onClick={handleEditQuestion} variant="contained" color="primary" disabled={actionLoading || !questionData.question_text?.trim()}>
            {actionLoading ? <CircularProgress size={24}/> : 'Save Changes'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Assignment Confirmation Dialog */}
      <ConfirmationDialog
        open={deleteAssignmentDialogOpen}
        onClose={() => !actionLoading && setDeleteAssignmentDialogOpen(false)}
        onConfirm={handleDeleteAssignment}
        title="Delete Assignment?"
        description={`Delete assignment (ID: ${selectedAssignment?.assignment_id}) and all its questions/data? Cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        confirmColor="error"
        loading={actionLoading}
      />

      {/* Delete Question Confirmation Dialog */}
      <ConfirmationDialog
        open={deleteQuestionDialogOpen}
        onClose={() => !actionLoading && setDeleteQuestionDialogOpen(false)}
        onConfirm={handleDeleteQuestion}
        title="Delete Question?"
        description={`Delete question (Original Index ${questionToDeleteIndex !== null ? questionToDeleteIndex : ''}) from assignment (ID: ${selectedAssignment?.assignment_id})? Cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        confirmColor="error"
        loading={actionLoading}
      />

      {/* Alert Snackbar */}
      <Snackbar open={alertOpen} autoHideDuration={6000} onClose={() => setAlertOpen(false)} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert onClose={() => setAlertOpen(false)} severity={alertSeverity} variant="filled" sx={{ width: '100%' }}>
          {alertMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
}
