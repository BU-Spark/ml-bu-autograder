/**
 * Assignments Page for BU MET Autograder
 * Interface for creating, editing, and managing assignments
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
import { courseService, assignmentService } from '../../../services/api';
import CardSkeleton from '../../../components/CardSkeleton';
import ConfirmationDialog from '../../../components/ConfirmationDialog';

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
}));

const NoAssignmentsBox = styled(Box)(({ theme }) => ({
  textAlign: 'center',
  padding: theme.spacing(4),
  backgroundColor: theme.palette.background.paper,
  borderRadius: theme.shape.borderRadius,
  marginTop: theme.spacing(4),
}));

// Main component
export default function Assignments() {
  const router = useRouter();
  const { id: courseId, semester, assignmentId: selectedAssignmentId } = router.query;

  // State for assignments
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // State for selected assignment
  const [selectedAssignment, setSelectedAssignment] = useState(null);

  // State for dialogs
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editAssignmentDialogOpen, setEditAssignmentDialogOpen] = useState(false);
  const [addQuestionDialogOpen, setAddQuestionDialogOpen] = useState(false);
  const [editQuestionDialogOpen, setEditQuestionDialogOpen] = useState(false);
  const [deleteAssignmentDialogOpen, setDeleteAssignmentDialogOpen] = useState(false);
  const [deleteQuestionDialogOpen, setDeleteQuestionDialogOpen] = useState(false);

  // State for form data
  const [newAssignmentData, setNewAssignmentData] = useState({
    assignment_title: '',
    assignment_guidelines: '',
  });

  const [editAssignmentData, setEditAssignmentData] = useState({
    assignment_title: '',
    assignment_guidelines: '',
  });

  const [questionData, setQuestionData] = useState({
    question_text: '',
    question_index: 0,
    question_graphics_figures: null,
  });

  const [questionToDelete, setQuestionToDelete] = useState(null);

  // State for alerts
  const [alertOpen, setAlertOpen] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [alertSeverity, setAlertSeverity] = useState('success');

  // Fetch assignments
  useEffect(() => {
    const fetchAssignments = async () => {
      if (!courseId || !semester) return;

      setLoading(true);
      try {
        const assignmentsData = await assignmentService.getAssignments(courseId, semester);
        setAssignments(assignmentsData || []);

        // If an assignment ID is provided in the URL, select it
        if (selectedAssignmentId) {
          const assignment = assignmentsData.find(
            (a) => a.assignment_id === selectedAssignmentId
          );
          if (assignment) {
            setSelectedAssignment(assignment);
          }
        }

        setError(null);
      } catch (err) {
        console.error('Error fetching assignments:', err);
        setError(err.message || 'Failed to load assignments');
      } finally {
        setLoading(false);
      }
    };

    fetchAssignments();
  }, [courseId, semester, selectedAssignmentId]);

  // Handle creating a new assignment
  const handleCreateAssignment = async () => {
    try {
      const newAssignment = await assignmentService.createAssignment({
        course_id: courseId,
        semester: semester,
        assignment_title: newAssignmentData.assignment_title,
        assignment_guidelines: newAssignmentData.assignment_guidelines,
        questions: [],
      });

      // Add to assignments list
      setAssignments([...assignments, newAssignment]);

      // Reset form and close dialog
      setNewAssignmentData({
        assignment_title: '',
        assignment_guidelines: '',
      });
      setCreateDialogOpen(false);

      // Select the new assignment
      setSelectedAssignment(newAssignment);

      // Show success alert
      setAlertMessage('Assignment created successfully');
      setAlertSeverity('success');
      setAlertOpen(true);

      // Update URL with new assignment ID
      router.push(`/course/${courseId}/assignments?semester=${semester}&assignmentId=${newAssignment.assignment_id}`, undefined, { shallow: true });
    } catch (error) {
      console.error('Error creating assignment:', error);
      setAlertMessage(error.message || 'Failed to create assignment');
      setAlertSeverity('error');
      setAlertOpen(true);
    }
  };

  // Handle updating an assignment
  const handleUpdateAssignment = async () => {
    if (!selectedAssignment) return;

    try {
      // Update assignment through the API
      // This is a simplified version - in a real app, you'd likely have a dedicated update endpoint
      const updatedAssignment = {
        ...selectedAssignment,
        assignment_title: editAssignmentData.assignment_title,
        assignment_guidelines: editAssignmentData.assignment_guidelines,
      };

      // Mock update - in a real implementation, call the API
      // await assignmentService.updateAssignment(updatedAssignment);

      // Update in local state
      const updatedAssignments = assignments.map((assignment) =>
        assignment.assignment_id === selectedAssignment.assignment_id
          ? updatedAssignment
          : assignment
      );

      setAssignments(updatedAssignments);
      setSelectedAssignment(updatedAssignment);

      // Close dialog
      setEditAssignmentDialogOpen(false);

      // Show success alert
      setAlertMessage('Assignment updated successfully');
      setAlertSeverity('success');
      setAlertOpen(true);
    } catch (error) {
      console.error('Error updating assignment:', error);
      setAlertMessage(error.message || 'Failed to update assignment');
      setAlertSeverity('error');
      setAlertOpen(true);
    }
  };

  // Handle deleting an assignment
  const handleDeleteAssignment = async () => {
    if (!selectedAssignment) return;

    try {
      await assignmentService.deleteAssignment(selectedAssignment.assignment_id);

      // Remove from assignments list
      const updatedAssignments = assignments.filter(
        (assignment) => assignment.assignment_id !== selectedAssignment.assignment_id
      );
      setAssignments(updatedAssignments);

      // Clear selected assignment
      setSelectedAssignment(null);

      // Close dialog
      setDeleteAssignmentDialogOpen(false);

      // Show success alert
      setAlertMessage('Assignment deleted successfully');
      setAlertSeverity('success');
      setAlertOpen(true);

      // Update URL to remove assignmentId
      router.push(`/course/${courseId}/assignments?semester=${semester}`, undefined, { shallow: true });
    } catch (error) {
      console.error('Error deleting assignment:', error);
      setAlertMessage(error.message || 'Failed to delete assignment');
      setAlertSeverity('error');
      setAlertOpen(true);
    }
  };

  // Handle adding a question
  const handleAddQuestion = async () => {
    if (!selectedAssignment) return;

    try {
      // Determine the next question index
      const nextIndex = selectedAssignment.questions.length;

      const newQuestion = {
        ...questionData,
        question_index: nextIndex,
      };

      await assignmentService.addQuestion({
        semester: semester,
        course_id: courseId,
        assignment_id: selectedAssignment.assignment_id,
        question: newQuestion,
      });

      // Update the selected assignment with the new question
      const updatedQuestions = [...selectedAssignment.questions, newQuestion];
      const updatedAssignment = {
        ...selectedAssignment,
        questions: updatedQuestions,
      };

      // Update in local state
      const updatedAssignments = assignments.map((assignment) =>
        assignment.assignment_id === selectedAssignment.assignment_id
          ? updatedAssignment
          : assignment
      );

      setAssignments(updatedAssignments);
      setSelectedAssignment(updatedAssignment);

      // Reset form and close dialog
      setQuestionData({
        question_text: '',
        question_index: 0,
        question_graphics_figures: null,
      });
      setAddQuestionDialogOpen(false);

      // Show success alert
      setAlertMessage('Question added successfully');
      setAlertSeverity('success');
      setAlertOpen(true);
    } catch (error) {
      console.error('Error adding question:', error);
      setAlertMessage(error.message || 'Failed to add question');
      setAlertSeverity('error');
      setAlertOpen(true);
    }
  };

  // Handle editing a question
  const handleEditQuestion = async () => {
    if (!selectedAssignment) return;

    try {
      await assignmentService.editQuestion({
        semester: semester,
        course_id: courseId,
        assignment_id: selectedAssignment.assignment_id,
        question: questionData,
      });

      // Update the selected assignment with the edited question
      const updatedQuestions = selectedAssignment.questions.map((q) =>
        q.question_index === questionData.question_index ? questionData : q
      );

      const updatedAssignment = {
        ...selectedAssignment,
        questions: updatedQuestions,
      };

      // Update in local state
      const updatedAssignments = assignments.map((assignment) =>
        assignment.assignment_id === selectedAssignment.assignment_id
          ? updatedAssignment
          : assignment
      );

      setAssignments(updatedAssignments);
      setSelectedAssignment(updatedAssignment);

      // Reset form and close dialog
      setQuestionData({
        question_text: '',
        question_index: 0,
        question_graphics_figures: null,
      });
      setEditQuestionDialogOpen(false);

      // Show success alert
      setAlertMessage('Question updated successfully');
      setAlertSeverity('success');
      setAlertOpen(true);
    } catch (error) {
      console.error('Error editing question:', error);
      setAlertMessage(error.message || 'Failed to edit question');
      setAlertSeverity('error');
      setAlertOpen(true);
    }
  };

  // Handle deleting a question
  const handleDeleteQuestion = async () => {
    if (!selectedAssignment || questionToDelete === null) return;

    try {
      await assignmentService.removeQuestion(
        selectedAssignment.assignment_id,
        questionToDelete
      );

      // Update the selected assignment by removing the deleted question
      const updatedQuestions = selectedAssignment.questions.filter(
        (q) => q.question_index !== questionToDelete
      );

      // Reindex remaining questions
      const reindexedQuestions = updatedQuestions.map((q, index) => ({
        ...q,
        question_index: index,
      }));

      const updatedAssignment = {
        ...selectedAssignment,
        questions: reindexedQuestions,
      };

      // Update in local state
      const updatedAssignments = assignments.map((assignment) =>
        assignment.assignment_id === selectedAssignment.assignment_id
          ? updatedAssignment
          : assignment
      );

      setAssignments(updatedAssignments);
      setSelectedAssignment(updatedAssignment);

      // Close dialog and reset
      setDeleteQuestionDialogOpen(false);
      setQuestionToDelete(null);

      // Show success alert
      setAlertMessage('Question deleted successfully');
      setAlertSeverity('success');
      setAlertOpen(true);
    } catch (error) {
      console.error('Error deleting question:', error);
      setAlertMessage(error.message || 'Failed to delete question');
      setAlertSeverity('error');
      setAlertOpen(true);
    }
  };

  // Handle opening edit assignment dialog
  const handleOpenEditAssignmentDialog = () => {
    if (!selectedAssignment) return;

    setEditAssignmentData({
      assignment_title: selectedAssignment.assignment_title || '',
      assignment_guidelines: selectedAssignment.assignment_guidelines || '',
    });

    setEditAssignmentDialogOpen(true);
  };

  // Handle opening edit question dialog
  const handleOpenEditQuestionDialog = (question) => {
    setQuestionData({
      question_text: question.question_text,
      question_index: question.question_index,
      question_graphics_figures: question.question_graphics_figures || null,
    });

    setEditQuestionDialogOpen(true);
  };

  // Handle selecting an assignment
  const handleSelectAssignment = (assignment) => {
    setSelectedAssignment(assignment);

    // Update URL with selected assignment ID
    router.push(`/course/${courseId}/assignments?semester=${semester}&assignmentId=${assignment.assignment_id}`, undefined, { shallow: true });
  };

  // Handle drag and drop reordering of questions
  const handleDragEnd = async (result) => {
    if (!result.destination || !selectedAssignment) return;

    const { source, destination } = result;

    // Don't do anything if dropped in the same position
    if (source.index === destination.index) return;

    // Reorder the questions array
    const questions = Array.from(selectedAssignment.questions);
    const [movedQuestion] = questions.splice(source.index, 1);
    questions.splice(destination.index, 0, movedQuestion);

    // Update question indexes to match their new positions
    const reindexedQuestions = questions.map((q, index) => ({
      ...q,
      question_index: index,
    }));

    try {
      // Update the question order via API
      await assignmentService.modifyQuestionOrder({
        semester: semester,
        course_id: courseId,
        assignment_id: selectedAssignment.assignment_id,
        list_of_question_indexes: reindexedQuestions.map((q) => q.question_index),
      });

      // Update local state
      const updatedAssignment = {
        ...selectedAssignment,
        questions: reindexedQuestions,
      };

      const updatedAssignments = assignments.map((assignment) =>
        assignment.assignment_id === selectedAssignment.assignment_id
          ? updatedAssignment
          : assignment
      );

      setAssignments(updatedAssignments);
      setSelectedAssignment(updatedAssignment);

      // Show success alert
      setAlertMessage('Question order updated successfully');
      setAlertSeverity('success');
      setAlertOpen(true);
    } catch (error) {
      console.error('Error updating question order:', error);
      setAlertMessage(error.message || 'Failed to update question order');
      setAlertSeverity('error');
      setAlertOpen(true);
    }
  };

  // Handle form input changes
  const handleInputChange = (event, formSetter) => {
    const { name, value } = event.target;
    formSetter((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  // Render the assignment list
  const renderAssignmentList = () => {
    if (loading) {
      return (
        <Grid container spacing={3}>
          {[1, 2, 3].map((item) => (
            <Grid item xs={12} sm={6} md={4} key={item}>
              <CardSkeleton height={150} />
            </Grid>
          ))}
        </Grid>
      );
    }

    if (assignments.length === 0) {
      return (
        <NoAssignmentsBox>
          <AssignmentIcon sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            No Assignments Found
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            You don't have any assignments yet. Create your first assignment to get started.
          </Typography>
          <Button
            variant="contained"
            color="primary"
            startIcon={<AddIcon />}
            onClick={() => setCreateDialogOpen(true)}
          >
            Create Assignment
          </Button>
        </NoAssignmentsBox>
      );
    }

    return (
      <Grid container spacing={3}>
        {assignments.map((assignment) => (
          <Grid item xs={12} sm={6} md={4} key={assignment.assignment_id}>
            <AssignmentCard
              raised={selectedAssignment?.assignment_id === assignment.assignment_id}
            >
              <CardActionArea onClick={() => handleSelectAssignment(assignment)}>
                <AssignmentCardContent>
                  <Typography variant="h6" component="h2" noWrap>
                    {assignment.assignment_title || 'Untitled Assignment'}
                  </Typography>

                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    {assignment.questions.length} {assignment.questions.length === 1 ? 'question' : 'questions'}
                  </Typography>

                  {assignment.assignment_guidelines && (
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                        mb: 1,
                      }}
                    >
                      {assignment.assignment_guidelines}
                    </Typography>
                  )}
                </AssignmentCardContent>
              </CardActionArea>
            </AssignmentCard>
          </Grid>
        ))}
      </Grid>
    );
  };

  // Render the selected assignment details
  const renderAssignmentDetails = () => {
    if (!selectedAssignment) return null;

    return (
      <Box sx={{ mt: 4 }}>
        <Paper sx={{ p: 3, mb: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <Box>
              <Typography variant="h5" gutterBottom>
                {selectedAssignment.assignment_title || 'Untitled Assignment'}
              </Typography>

              <Typography variant="body2" color="text.secondary">
                {selectedAssignment.questions.length} {selectedAssignment.questions.length === 1 ? 'question' : 'questions'}
              </Typography>
            </Box>

            <Box>
              <IconButton
                color="primary"
                aria-label="edit assignment"
                onClick={handleOpenEditAssignmentDialog}
              >
                <EditIcon />
              </IconButton>

              <IconButton
                color="error"
                aria-label="delete assignment"
                onClick={() => setDeleteAssignmentDialogOpen(true)}
              >
                <DeleteIcon />
              </IconButton>
            </Box>
          </Box>

          {selectedAssignment.assignment_guidelines && (
            <>
              <Divider sx={{ my: 2 }} />

              <Typography variant="subtitle1" gutterBottom>
                Guidelines:
              </Typography>

              <Typography variant="body2" paragraph>
                {selectedAssignment.assignment_guidelines}
              </Typography>
            </>
          )}
        </Paper>

        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Questions</Typography>

          <Button
            variant="contained"
            color="primary"
            startIcon={<AddIcon />}
            onClick={() => setAddQuestionDialogOpen(true)}
          >
            Add Question
          </Button>
        </Box>

        {selectedAssignment.questions.length === 0 ? (
          <Paper sx={{ p: 3, textAlign: 'center' }}>
            <QuestionIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              No Questions Yet
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Add questions to this assignment to get started.
            </Typography>
            <Button
              variant="contained"
              color="primary"
              startIcon={<AddIcon />}
              onClick={() => setAddQuestionDialogOpen(true)}
            >
              Add Question
            </Button>
          </Paper>
        ) : (
          <DragDropContext onDragEnd={handleDragEnd}>
            <Droppable droppableId="questions-list">
              {(provided) => (
                <List {...provided.droppableProps} ref={provided.innerRef}>
                  {selectedAssignment.questions.map((question, index) => (
                    <Draggable
                      key={`question-${question.question_index}`}
                      draggableId={`question-${question.question_index}`}
                      index={index}
                    >
                      {(provided, snapshot) => (
                        <QuestionItem
                          ref={provided.innerRef}
                          {...provided.draggableProps}
                          isDragging={snapshot.isDragging}
                        >
                          <ListItemIcon {...provided.dragHandleProps}>
                            <DragIndicatorIcon />
                          </ListItemIcon>

                          <ListItemText
                            primary={`Question ${index + 1}`}
                            secondary={
                              <Typography
                                variant="body2"
                                color="text.secondary"
                                sx={{
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  display: '-webkit-box',
                                  WebkitLineClamp: 2,
                                  WebkitBoxOrient: 'vertical',
                                }}
                              >
                                {question.question_text}
                              </Typography>
                            }
                          />

                          <ListItemSecondaryAction>
                            <IconButton
                              edge="end"
                              aria-label="edit"
                              onClick={() => handleOpenEditQuestionDialog(question)}
                              sx={{ mr: 1 }}
                            >
                              <EditIcon />
                            </IconButton>

                            <IconButton
                              edge="end"
                              aria-label="delete"
                              onClick={() => {
                                setQuestionToDelete(question.question_index);
                                setDeleteQuestionDialogOpen(true);
                              }}
                            >
                              <DeleteIcon />
                            </IconButton>
                          </ListItemSecondaryAction>
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
      </Box>
    );
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <IconButton
          edge="start"
          aria-label="back to course"
          onClick={() => router.push(`/course/${courseId}?semester=${semester}`)}
          sx={{ mr: 1 }}
        >
          <ArrowBackIcon />
        </IconButton>

        <Typography variant="h4" component="h1">
          Assignments
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5">
          {selectedAssignment ? 'All Assignments' : 'Course Assignments'}
        </Typography>

        <Button
          variant="contained"
          color="primary"
          startIcon={<AddIcon />}
          onClick={() => setCreateDialogOpen(true)}
        >
          Create Assignment
        </Button>
      </Box>

      {renderAssignmentList()}

      {renderAssignmentDetails()}

      {/* Create Assignment Dialog */}
      <Dialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Create New Assignment</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            name="assignment_title"
            label="Assignment Title"
            fullWidth
            value={newAssignmentData.assignment_title}
            onChange={(e) => handleInputChange(e, setNewAssignmentData)}
            margin="normal"
            required
          />

          <TextField
            name="assignment_guidelines"
            label="Assignment Guidelines"
            fullWidth
            multiline
            rows={4}
            value={newAssignmentData.assignment_guidelines}
            onChange={(e) => handleInputChange(e, setNewAssignmentData)}
            margin="normal"
            helperText="Include any general instructions or requirements for the assignment"
          />
        </DialogContent>

        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleCreateAssignment}
            variant="contained"
            color="primary"
            disabled={!newAssignmentData.assignment_title}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Assignment Dialog */}
      <Dialog
        open={editAssignmentDialogOpen}
        onClose={() => setEditAssignmentDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Edit Assignment</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            name="assignment_title"
            label="Assignment Title"
            fullWidth
            value={editAssignmentData.assignment_title}
            onChange={(e) => handleInputChange(e, setEditAssignmentData)}
            margin="normal"
            required
          />

          <TextField
            name="assignment_guidelines"
            label="Assignment Guidelines"
            fullWidth
            multiline
            rows={4}
            value={editAssignmentData.assignment_guidelines}
            onChange={(e) => handleInputChange(e, setEditAssignmentData)}
            margin="normal"
            helperText="Include any general instructions or requirements for the assignment"
          />
        </DialogContent>

        <DialogActions>
          <Button onClick={() => setEditAssignmentDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleUpdateAssignment}
            variant="contained"
            color="primary"
            disabled={!editAssignmentData.assignment_title}
          >
            Update
          </Button>
        </DialogActions>
      </Dialog>

      {/* Add Question Dialog */}
      <Dialog
        open={addQuestionDialogOpen}
        onClose={() => setAddQuestionDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Add Question</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            name="question_text"
            label="Question Text"
            fullWidth
            multiline
            rows={4}
            value={questionData.question_text}
            onChange={(e) => handleInputChange(e, setQuestionData)}
            margin="normal"
            required
            helperText="Enter the text of the question"
          />

          {/* In a real implementation, add graphics/figures upload here */}
        </DialogContent>

        <DialogActions>
          <Button onClick={() => setAddQuestionDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleAddQuestion}
            variant="contained"
            color="primary"
            disabled={!questionData.question_text}
          >
            Add Question
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Question Dialog */}
      <Dialog
        open={editQuestionDialogOpen}
        onClose={() => setEditQuestionDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Edit Question</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            name="question_text"
            label="Question Text"
            fullWidth
            multiline
            rows={4}
            value={questionData.question_text}
            onChange={(e) => handleInputChange(e, setQuestionData)}
            margin="normal"
            required
            helperText="Enter the text of the question"
          />

          {/* In a real implementation, add graphics/figures upload here */}
        </DialogContent>

        <DialogActions>
          <Button onClick={() => setEditQuestionDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleEditQuestion}
            variant="contained"
            color="primary"
            disabled={!questionData.question_text}
          >
            Update Question
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Assignment Confirmation Dialog */}
      <ConfirmationDialog
        open={deleteAssignmentDialogOpen}
        title="Delete Assignment"
        message={`Are you sure you want to delete "${selectedAssignment?.assignment_title || 'this assignment'}"? This action cannot be undone and will remove all associated questions and rubrics.`}
        confirmText="Delete"
        cancelText="Cancel"
        confirmButtonProps={{ color: 'error' }}
        onConfirm={handleDeleteAssignment}
        onCancel={() => setDeleteAssignmentDialogOpen(false)}
      />

      {/* Delete Question Confirmation Dialog */}
      <ConfirmationDialog
        open={deleteQuestionDialogOpen}
        title="Delete Question"
        message="Are you sure you want to delete this question? This action cannot be undone."
        confirmText="Delete"
        cancelText="Cancel"
        confirmButtonProps={{ color: 'error' }}
        onConfirm={handleDeleteQuestion}
        onCancel={() => {
          setDeleteQuestionDialogOpen(false);
          setQuestionToDelete(null);
        }}
      />

      {/* Alert Snackbar */}
      <Snackbar
        open={alertOpen}
        autoHideDuration={6000}
        onClose={() => setAlertOpen(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setAlertOpen(false)}
          severity={alertSeverity}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {alertMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
}