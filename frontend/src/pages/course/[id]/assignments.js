/**
 * Assignments Page for BU MET Autograder
 * Interface for creating, editing, and managing assignments and their questions.
 * Located at: pages/course/[id]/assignments.js
 */

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import {
  Alert,
  Box,
  Button,
  Card,
  CardActionArea,
  CardContent,
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
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';
import { assignmentService } from '../../../api'; // Assuming api/index.js exports this
import CardSkeleton from '../../../components/CardSkeleton'; // Assuming component path
import ConfirmationDialog from '../../../components/ConfirmationDialog'; // Assuming component path

// Styled components
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
});
const QuestionItem = styled(ListItem)(({ theme, isDragging }) => ({
  border: `1px solid ${theme.palette.divider}`,
  borderRadius: theme.shape.borderRadius,
  marginBottom: theme.spacing(1),
  backgroundColor: isDragging ? theme.palette.action.hover : theme.palette.background.paper,
  boxShadow: isDragging ? theme.shadows[3] : 'none',
  alignItems: 'flex-start',
  paddingRight: theme.spacing(12), // Ensure space for actions
}));
const NoAssignmentsBox = styled(Box)(({ theme }) => ({
  textAlign: 'center',
  padding: theme.spacing(4),
  backgroundColor: theme.palette.background.paper,
  borderRadius: theme.shape.borderRadius,
  marginTop: theme.spacing(4),
}));

// Main component
export default function AssignmentsPage() {
  const router = useRouter();
  // Correctly extracts params from /course/[id]/assignments?semester=...&assignmentId=...
  const { id: courseId = '', semester = '', assignmentId: selectedAssignmentIdFromUrl = '' } = router.query;

  // State
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedAssignment, setSelectedAssignment] = useState(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editAssignmentDialogOpen, setEditAssignmentDialogOpen] = useState(false);
  const [addQuestionDialogOpen, setAddQuestionDialogOpen] = useState(false);
  const [editQuestionDialogOpen, setEditQuestionDialogOpen] = useState(false);
  const [deleteAssignmentDialogOpen, setDeleteAssignmentDialogOpen] = useState(false);
  const [deleteQuestionDialogOpen, setDeleteQuestionDialogOpen] = useState(false);
  const [newAssignmentData, setNewAssignmentData] = useState({ assignment_id: '', assignment_guidelines: '' });
  const [editAssignmentData, setEditAssignmentData] = useState({ assignment_id: '', assignment_guidelines: '' });
  const [questionData, setQuestionData] = useState({ question_text: '', question_index: -1 });
  const [questionToDeleteIndex, setQuestionToDeleteIndex] = useState(null);
  const [alertOpen, setAlertOpen] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [alertSeverity, setAlertSeverity] = useState('success');

  // Fetch assignments effect
  useEffect(() => {
    if (!router.isReady) return;

    if (!courseId || !semester) {
      setError("Course ID or Semester is missing from URL.");
      setLoading(false);
      return;
    }

    let isMounted = true;
    const fetchAssignments = async () => {
      setLoading(true);
      setError(null);
      try {
        // This fetches ALL assignments for the given courseId and semester
        const assignmentsData = await assignmentService.getAssignments({
          course_id: courseId,
          semester: semester,
          include_questions: true, // Fetch questions for detail view
        });

        if (isMounted) {
          const validAssignments = (Array.isArray(assignmentsData) ? assignmentsData : []).map(a => ({
              ...a,
              questions: Array.isArray(a?.questions) ? a.questions : []
          }));
          setAssignments(validAssignments); // State now holds all assignments
          console.log("Fetched assignments:", validAssignments);

          // If URL has a specific assignmentId, find it in the fetched list and select it
          if (selectedAssignmentIdFromUrl) {
            const assignment = validAssignments.find((a) => a && a.assignment_id === selectedAssignmentIdFromUrl);
            if (assignment) {
                setSelectedAssignment({ ...assignment, questions: assignment.questions || [] });
            } else {
                setSelectedAssignment(null);
                console.warn(`Assignment with ID ${selectedAssignmentIdFromUrl} not found in fetched list.`);
            }
          } else {
            // No specific assignment ID in URL, so no assignment is initially selected
            setSelectedAssignment(null);
          }
        }
      } catch (err) {
        console.error('Error fetching assignments:', err);
        if (isMounted) {
          setError(err.message || 'Failed to load assignments');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchAssignments();
    return () => { isMounted = false; };
  }, [router.isReady, courseId, semester, selectedAssignmentIdFromUrl]);

  // Helper to show alerts
  const showAlert = (message, severity = 'success') => {
    setAlertMessage(message);
    setAlertSeverity(severity);
    setAlertOpen(true);
  };

  // Helper to refetch a specific assignment's details
  const refetchSelectedAssignment = async (assignmentId) => {
      if (!assignmentId || !courseId || !semester) return null;
      try {
          const updatedData = await assignmentService.getAssignment({
              course_id: courseId,
              semester: semester,
              assignment_id: assignmentId,
              include_questions: true
          });
          return { ...updatedData, questions: Array.isArray(updatedData?.questions) ? updatedData.questions : [] };
      } catch (fetchError) {
          console.error("Error refetching assignment details:", fetchError);
          showAlert(`Could not refresh assignment details: ${fetchError.message}`, 'error');
          return null;
      }
  };

  // Helper to update assignment state locally and globally
  const updateAssignmentState = (updatedAssignment) => {
      if (!updatedAssignment || !updatedAssignment.assignment_id) return;
      const assignmentWithQuestions = { ...updatedAssignment, questions: updatedAssignment.questions || [] };
      setSelectedAssignment(assignmentWithQuestions);
      setAssignments(prevAssignments => prevAssignments.map(a =>
          a.assignment_id === assignmentWithQuestions.assignment_id ? assignmentWithQuestions : a
      ));
  };

  // Select assignment when card is clicked
  const handleSelectAssignment = (assignment) => {
    if (!assignment || typeof assignment.assignment_id === 'undefined' || assignment.assignment_id === null || assignment.assignment_id === '') {
        console.error("Attempted to select an assignment with invalid ID:", assignment);
        showAlert("Cannot select assignment: Invalid assignment data.", "error");
        return;
    }
    const assignmentWithQuestions = {...assignment, questions: assignment.questions || []};
    setSelectedAssignment(assignmentWithQuestions);
    router.push(`/course/${courseId}/assignments?semester=${semester}&assignmentId=${assignment.assignment_id}`, undefined, { shallow: true });
  };

  // --- CRUD Handlers (Implementation details remain the same as previous correct version) ---

  const handleCreateAssignment = async () => {
    if (!courseId || !semester || !newAssignmentData.assignment_id) {
      showAlert("Course context or Assignment ID (Title) is missing.", 'error');
      return;
    }
    try {
      const userProvidedAssignmentId = newAssignmentData.assignment_id;
      const payload = { course_id: courseId, semester: semester, assignment_id: userProvidedAssignmentId, assignment_guidelines: newAssignmentData.assignment_guidelines, questions: [] };
      const newAssignmentFromApi = await assignmentService.createAssignment(payload);
      const finalNewAssignment = { ...newAssignmentFromApi, assignment_id: userProvidedAssignmentId, questions: newAssignmentFromApi?.questions || [], };
      setAssignments(prev => [...prev, finalNewAssignment]);
      setNewAssignmentData({ assignment_id: '', assignment_guidelines: '' });
      setCreateDialogOpen(false);
      handleSelectAssignment(finalNewAssignment);
      showAlert('Assignment created successfully');
    } catch (error) {
      console.error('Error creating assignment:', error);
      let errorMsg = 'Failed to create assignment';
       if (error.response && error.response.data && error.response.data.detail) { if (typeof error.response.data.detail === 'string') { errorMsg = error.response.data.detail; } else if (Array.isArray(error.response.data.detail)) { errorMsg = error.response.data.detail.map(err => `${err.loc.join('->')}: ${err.msg}`).join('; '); } else { errorMsg = JSON.stringify(error.response.data.detail); } } else if (error.message) { errorMsg = error.message; }
      showAlert(errorMsg, 'error');
    }
  };

  const handleUpdateAssignment = async () => {
    if (!selectedAssignment) return;
    const updatedAssignmentLocally = { ...selectedAssignment, assignment_id: editAssignmentData.assignment_id, assignment_guidelines: editAssignmentData.assignment_guidelines };
    updateAssignmentState(updatedAssignmentLocally);
    setEditAssignmentDialogOpen(false);
    showAlert('Assignment updated locally (Note: API endpoint for title/guideline update may be missing)', 'warning');
    if (selectedAssignment.assignment_id !== updatedAssignmentLocally.assignment_id) {
      router.push(`/course/${courseId}/assignments?semester=${semester}&assignmentId=${updatedAssignmentLocally.assignment_id}`, undefined, { shallow: true });
    }
  };

  const handleDeleteAssignment = async () => {
    if (!selectedAssignment || !courseId || !semester) return;
    try {
      await assignmentService.deleteAssignment({ semester: semester, course_id: courseId, assignment_id: selectedAssignment.assignment_id });
      setAssignments(prev => prev.filter(a => a.assignment_id !== selectedAssignment.assignment_id));
      setSelectedAssignment(null);
      setDeleteAssignmentDialogOpen(false);
      showAlert('Assignment deleted successfully');
      router.push(`/course/${courseId}/assignments?semester=${semester}`, undefined, { shallow: true });
    } catch (error) {
      console.error('Error deleting assignment:', error);
      showAlert(error.message || 'Failed to delete assignment', 'error');
    }
  };

  const handleAddQuestion = async () => {
    if (!selectedAssignment || !questionData.question_text || !courseId || !semester) return;
    try {
      const payload = { semester: semester, course_id: courseId, assignment_id: selectedAssignment.assignment_id, question: { question_text: questionData.question_text }};
      await assignmentService.addQuestion(payload);
      const updatedAssignment = await refetchSelectedAssignment(selectedAssignment.assignment_id);
      if (updatedAssignment) updateAssignmentState(updatedAssignment);
      setQuestionData({ question_text: '', question_index: -1 });
      setAddQuestionDialogOpen(false);
      showAlert('Question added successfully');
    } catch (error) {
      console.error('Error adding question:', error);
      showAlert(error.message || 'Failed to add question', 'error');
    }
  };

  const handleEditQuestion = async () => {
    if (!selectedAssignment || !questionData.question_text || questionData.question_index < 0 || !courseId || !semester) return;
    try {
      const payload = { semester: semester, course_id: courseId, assignment_id: selectedAssignment.assignment_id, question_index: questionData.question_index, question: { question_text: questionData.question_text } };
      await assignmentService.editQuestion(payload);
      const updatedAssignment = await refetchSelectedAssignment(selectedAssignment.assignment_id);
      if (updatedAssignment) updateAssignmentState(updatedAssignment);
      setQuestionData({ question_text: '', question_index: -1 });
      setEditQuestionDialogOpen(false);
      showAlert('Question updated successfully');
    } catch (error) {
      console.error('Error editing question:', error);
      showAlert(error.message || 'Failed to edit question', 'error');
    }
  };

  const handleDeleteQuestion = async () => {
    if (!selectedAssignment || questionToDeleteIndex === null || !courseId || !semester) return;
    try {
      await assignmentService.removeQuestion({ semester: semester, course_id: courseId, assignment_id: selectedAssignment.assignment_id, question_index: questionToDeleteIndex });
      const updatedAssignment = await refetchSelectedAssignment(selectedAssignment.assignment_id);
      if (updatedAssignment) updateAssignmentState(updatedAssignment);
      setDeleteQuestionDialogOpen(false);
      setQuestionToDeleteIndex(null);
      showAlert('Question deleted successfully');
    } catch (error) {
      console.error('Error deleting question:', error);
      showAlert(error.message || 'Failed to delete question', 'error');
    }
  };

  const handleDragEnd = async (result) => {
    if (!result.destination || !selectedAssignment || !courseId || !semester) return;
    const { source, destination } = result;
    if (source.index === destination.index) return;

    const currentQuestions = selectedAssignment.questions || [];
    const orderedQuestions = Array.from(currentQuestions);
    const [movedQuestion] = orderedQuestions.splice(source.index, 1);
    orderedQuestions.splice(destination.index, 0, movedQuestion);

    const reindexedOptimistic = orderedQuestions.map((q, index) => ({ ...q, question_index: index }));
    const optimisticAssignment = { ...selectedAssignment, questions: reindexedOptimistic };
    updateAssignmentState(optimisticAssignment);

    try {
      const payload = { semester: semester, course_id: courseId, assignment_id: selectedAssignment.assignment_id, list_of_question_indexes: reindexedOptimistic.map((_, index) => index) };
      await assignmentService.modifyQuestionOrder(payload);
      const updatedAssignment = await refetchSelectedAssignment(selectedAssignment.assignment_id);
      if (updatedAssignment) updateAssignmentState(updatedAssignment);
      showAlert('Question order updated successfully');
    } catch (error) {
      console.error('Error updating question order:', error);
      showAlert(error.message || 'Failed to update question order. Reverting local changes.', 'error');
      const revertedAssignment = await refetchSelectedAssignment(selectedAssignment.assignment_id);
      if(revertedAssignment) { updateAssignmentState(revertedAssignment); }
      else {
          const originalAssignmentState = assignments.find(a => a.assignment_id === selectedAssignment.assignment_id);
          if (originalAssignmentState) setSelectedAssignment({...originalAssignmentState});
      }
    }
  };

  // --- Dialog Openers ---
  const handleOpenEditAssignmentDialog = () => {
    if (!selectedAssignment) return;
    setEditAssignmentData({ assignment_id: selectedAssignment.assignment_id || '', assignment_guidelines: selectedAssignment.assignment_guidelines || '' });
    setEditAssignmentDialogOpen(true);
  };

  const handleOpenEditQuestionDialog = (question) => {
    setQuestionData({ question_text: question.question_text || '', question_index: question.question_index });
    setEditQuestionDialogOpen(true);
  };

  // --- Input Change Handler ---
  const handleInputChange = (event, formSetter) => {
    const { name, value } = event.target;
    formSetter((prev) => ({ ...prev, [name]: value }));
  };

  // --- Render Functions (Implementation details remain the same) ---
  const renderAssignmentList = () => {
    if (loading && assignments.length === 0) { return <Grid container spacing={3}>{[1, 2, 3].map((i) => <Grid item xs={12} sm={6} md={4} key={i}><CardSkeleton height={150} /></Grid>)}</Grid>; }
    if (!loading && assignments.length === 0 && !error) { return ( <NoAssignmentsBox><AssignmentIcon sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} /><Typography variant="h6" gutterBottom>No Assignments Found</Typography><Typography variant="body2" color="text.secondary" paragraph>This course doesn't have any assignments yet.</Typography><Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={() => setCreateDialogOpen(true)}>Create First Assignment</Button></NoAssignmentsBox> ); }
    if (assignments.length > 0) {
      return (
        <Grid container spacing={3}>
          {assignments.map((assignment) => (
            assignment && assignment.assignment_id ? (
              <Grid item xs={12} sm={6} md={4} key={assignment.assignment_id}>
                <AssignmentCard raised={selectedAssignment?.assignment_id === assignment.assignment_id}>
                  <CardActionArea onClick={() => handleSelectAssignment(assignment)}>
                    <AssignmentCardContent>
                      <Typography variant="h6" component="h2" noWrap>{assignment.assignment_id}</Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>{(assignment.questions?.length || 0)} {(assignment.questions?.length || 0) === 1 ? 'question' : 'questions'}</Typography>
                      {assignment.assignment_guidelines && (<Typography variant="body2" color="text.secondary" sx={{ overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>{assignment.assignment_guidelines}</Typography>)}
                    </AssignmentCardContent>
                  </CardActionArea>
                </AssignmentCard>
              </Grid>
            ) : null
          ))}
        </Grid>
      );
    }
    return null;
  };

  const renderAssignmentDetails = () => {
    if (!selectedAssignment) return null;
    const currentQuestions = selectedAssignment.questions || [];

    return (
      <Box sx={{ mt: 4 }}>
        <Paper sx={{ p: 3, mb: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
            <Box sx={{ flexGrow: 1, mr: 2 }}><Typography variant="h5" gutterBottom>{selectedAssignment.assignment_id}</Typography><Typography variant="body2" color="text.secondary">{currentQuestions.length} {currentQuestions.length === 1 ? 'question' : 'questions'}</Typography></Box>
            <Box sx={{ flexShrink: 0 }}><IconButton color="primary" aria-label="edit assignment" onClick={handleOpenEditAssignmentDialog}><EditIcon /></IconButton><IconButton color="error" aria-label="delete assignment" onClick={() => setDeleteAssignmentDialogOpen(true)}><DeleteIcon /></IconButton></Box>
          </Box>
          {selectedAssignment.assignment_guidelines && (<><Divider sx={{ my: 2 }} /><Typography variant="subtitle1" gutterBottom>Guidelines:</Typography><Typography variant="body2" paragraph sx={{ whiteSpace: 'pre-wrap' }}>{selectedAssignment.assignment_guidelines}</Typography></>)}
        </Paper>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}><Typography variant="h6">Questions</Typography><Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={() => setAddQuestionDialogOpen(true)}>Add Question</Button></Box>
        {currentQuestions.length === 0 ? (
          <Paper sx={{ p: 3, textAlign: 'center' }}><QuestionIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} /><Typography variant="h6" gutterBottom>No Questions Yet</Typography><Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={() => setAddQuestionDialogOpen(true)}>Add First Question</Button></Paper>
        ) : (
          <DragDropContext onDragEnd={handleDragEnd}>
            <Droppable droppableId="questions-list">
              {(provided) => (
                <List {...provided.droppableProps} ref={provided.innerRef}>
                  {currentQuestions.map((question, index) => (
                    question && typeof question.question_index === 'number' ? (
                      <Draggable key={`q-${selectedAssignment.assignment_id}-${question.question_index}`} draggableId={`q-${selectedAssignment.assignment_id}-${question.question_index}`} index={index}>
                        {(provided, snapshot) => (
                          <QuestionItem ref={provided.innerRef} {...provided.draggableProps} isDragging={snapshot.isDragging}>
                            <ListItemIcon {...provided.dragHandleProps} sx={{ cursor: 'grab', alignSelf: 'center', mr: -1 }}><DragIndicatorIcon /></ListItemIcon>
                            <ListItemText primary={`Question ${index + 1}`} secondary={<Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-wrap' }}>{question.question_text}</Typography>} sx={{ pr: '96px' }}/>
                            <ListItemSecondaryAction sx={{ right: 16 }}>
                              <IconButton edge="end" aria-label="edit" onClick={() => handleOpenEditQuestionDialog(question)} sx={{ mr: 0.5 }}><EditIcon /></IconButton>
                              <IconButton edge="end" aria-label="delete" onClick={() => { setQuestionToDeleteIndex(question.question_index); setDeleteQuestionDialogOpen(true); }}><DeleteIcon /></IconButton>
                            </ListItemSecondaryAction>
                          </QuestionItem>
                        )}
                      </Draggable>
                    ) : null
                  ))}
                  {provided.placeholder}
                </List>
              )}
            </Droppable>
          </DragDropContext>
        )}
      </Box>
    );
  };

  // --- Main Return ---
  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <IconButton edge="start" aria-label="back to course" onClick={() => (courseId && semester) ? router.push(`/course/${courseId}?semester=${semester}`) : router.push('/courses')} sx={{ mr: 1 }}>
          <ArrowBackIcon />
        </IconButton>
        <Typography variant="h4" component="h1">Assignments {courseId ? `for ${courseId}`: ''} {semester ? `(${semester})` : ''}</Typography>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5">{selectedAssignment ? `Selected: ${selectedAssignment.assignment_id}` : 'Course Assignments'}</Typography>
        <Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={() => setCreateDialogOpen(true)}>Create Assignment</Button>
      </Box>

      {renderAssignmentList()}
      {selectedAssignment && <Divider sx={{ my: 4 }} />}
      {renderAssignmentDetails()}

      {/* Dialogs and Snackbar (Implementations remain the same) */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Assignment</DialogTitle>
        <DialogContent><TextField autoFocus name="assignment_id" label="Assignment ID / Title" fullWidth value={newAssignmentData.assignment_id} onChange={(e) => handleInputChange(e, setNewAssignmentData)} margin="normal" required helperText="Unique identifier (e.g., Homework 1)"/><TextField name="assignment_guidelines" label="Assignment Guidelines" fullWidth multiline rows={4} value={newAssignmentData.assignment_guidelines} onChange={(e) => handleInputChange(e, setNewAssignmentData)} margin="normal" helperText="General instructions"/></DialogContent>
        <DialogActions><Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button><Button onClick={handleCreateAssignment} variant="contained" color="primary" disabled={!newAssignmentData.assignment_id}>Create</Button></DialogActions>
      </Dialog>
      <Dialog open={editAssignmentDialogOpen} onClose={() => setEditAssignmentDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Edit Assignment</DialogTitle>
        <DialogContent><TextField autoFocus name="assignment_id" label="Assignment ID / Title" fullWidth value={editAssignmentData.assignment_id} onChange={(e) => handleInputChange(e, setEditAssignmentData)} margin="normal" required helperText="Unique identifier"/><TextField name="assignment_guidelines" label="Assignment Guidelines" fullWidth multiline rows={4} value={editAssignmentData.assignment_guidelines} onChange={(e) => handleInputChange(e, setEditAssignmentData)} margin="normal" helperText="General instructions"/></DialogContent>
        <DialogActions><Button onClick={() => setEditAssignmentDialogOpen(false)}>Cancel</Button><Button onClick={handleUpdateAssignment} variant="contained" color="primary" disabled={!editAssignmentData.assignment_id}>Update (Local Only)</Button></DialogActions>
      </Dialog>
      <Dialog open={addQuestionDialogOpen} onClose={() => setAddQuestionDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add New Question</DialogTitle>
        <DialogContent><TextField autoFocus name="question_text" label="Question Text" fullWidth multiline rows={6} value={questionData.question_text} onChange={(e) => handleInputChange(e, setQuestionData)} margin="normal" required helperText="Enter the full text"/></DialogContent>
        <DialogActions><Button onClick={() => setAddQuestionDialogOpen(false)}>Cancel</Button><Button onClick={handleAddQuestion} variant="contained" color="primary" disabled={!questionData.question_text}>Add Question</Button></DialogActions>
      </Dialog>
      <Dialog open={editQuestionDialogOpen} onClose={() => setEditQuestionDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Edit Question {typeof questionData.question_index === 'number' && questionData.question_index >= 0 ? questionData.question_index + 1 : ''}</DialogTitle>
        <DialogContent><TextField autoFocus name="question_text" label="Question Text" fullWidth multiline rows={6} value={questionData.question_text} onChange={(e) => handleInputChange(e, setQuestionData)} margin="normal" required helperText="Update the text"/></DialogContent>
        <DialogActions><Button onClick={() => setEditQuestionDialogOpen(false)}>Cancel</Button><Button onClick={handleEditQuestion} variant="contained" color="primary" disabled={!questionData.question_text}>Update Question</Button></DialogActions>
      </Dialog>
      <ConfirmationDialog open={deleteAssignmentDialogOpen} title="Delete Assignment" message={`Delete assignment "${selectedAssignment?.assignment_id || ''}"? This removes all questions and cannot be undone.`} confirmText="Delete" cancelText="Cancel" confirmButtonProps={{ color: 'error' }} onConfirm={handleDeleteAssignment} onCancel={() => setDeleteAssignmentDialogOpen(false)}/>
      <ConfirmationDialog open={deleteQuestionDialogOpen} title="Delete Question" message={`Delete Question ${questionToDeleteIndex !== null ? questionToDeleteIndex + 1 : ''}? Cannot be undone.`} confirmText="Delete" cancelText="Cancel" confirmButtonProps={{ color: 'error' }} onConfirm={handleDeleteQuestion} onCancel={() => { setDeleteQuestionDialogOpen(false); setQuestionToDeleteIndex(null); }}/>
      <Snackbar open={alertOpen} autoHideDuration={6000} onClose={() => setAlertOpen(false)} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert onClose={() => setAlertOpen(false)} severity={alertSeverity} variant="filled" sx={{ width: '100%' }}>{alertMessage}</Alert>
      </Snackbar>
    </Box>
  );
}