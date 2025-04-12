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
import { courseService, assignmentService } from '../../../api';
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
        console.log('Fetching assignments for course:', courseId, 'semester:', semester); // Debugging log
        const assignmentsData = await assignmentService.getAssignments(courseId, semester);
        console.log('Fetched assignments:', assignmentsData); // Debugging log
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
        questions: [], // Initialize with an empty question list
      });

      setAssignments([...assignments, newAssignment]);
      setNewAssignmentData({
        assignment_title: '',
        assignment_guidelines: '',
      });
      setCreateDialogOpen(false);

      // Select the newly created assignment and update URL only if it's not the same URL
      setSelectedAssignment(newAssignment);

      const newRoute = `/course/${courseId}/assignments?semester=${semester}&assignmentId=${newAssignment.assignment_id}`;
      if (router.asPath !== newRoute) {
        router.push(newRoute, undefined, { shallow: true });
      }

      setAlertMessage('Assignment created successfully');
      setAlertSeverity('success');
      setAlertOpen(true);
    } catch (error) {
      console.error('Error creating assignment:', error);
      setAlertMessage(error.message || 'Failed to create assignment');
      setAlertSeverity('error');
      setAlertOpen(true);
    }
  };
/*
  // Handle updating an assignment
  const handleUpdateAssignment = async () => {
    if (!selectedAssignment) return;

    try {
      const updatedAssignment = {
        ...selectedAssignment,
        assignment_title: editAssignmentData.assignment_title,
        assignment_guidelines: editAssignmentData.assignment_guidelines,
      };

      await assignmentService.updateAssignment(courseId, semester, selectedAssignment.assignment_id, updatedAssignment);

      const updatedAssignments = assignments.map((assignment) =>
        assignment.assignment_id === selectedAssignment.assignment_id ? updatedAssignment : assignment
      );

      setAssignments(updatedAssignments);
      setSelectedAssignment(updatedAssignment);
      setEditAssignmentDialogOpen(false);

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
*/
  // Handle deleting an assignment
  const handleDeleteAssignment = async () => {
    if (!selectedAssignment) return;

    try {
      await assignmentService.deleteAssignment(courseId, semester, selectedAssignment.assignment_id);

      const updatedAssignments = assignments.filter(
        (assignment) => assignment.assignment_id !== selectedAssignment.assignment_id
      );
      setAssignments(updatedAssignments);
      setSelectedAssignment(null);
      setDeleteAssignmentDialogOpen(false);

      setAlertMessage('Assignment deleted successfully');
      setAlertSeverity('success');
      setAlertOpen(true);

      const newRoute = `/course/${courseId}/assignments?semester=${semester}`;
      if (router.asPath !== newRoute) {
        router.push(newRoute, undefined, { shallow: true });
      }
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
      const nextIndex = selectedAssignment.questions.length;

      const newQuestion = {
        ...questionData,
        question_index: nextIndex,
      };

      await assignmentService.addQuestion(courseId, semester, selectedAssignment.assignment_id, newQuestion);

      const updatedQuestions = [...selectedAssignment.questions, newQuestion];
      const updatedAssignment = {
        ...selectedAssignment,
        questions: updatedQuestions,
      };

      setAssignments(assignments.map((assignment) =>
        assignment.assignment_id === selectedAssignment.assignment_id ? updatedAssignment : assignment
      ));
      setSelectedAssignment(updatedAssignment);

      setQuestionData({
        question_text: '',
        question_index: 0,
        question_graphics_figures: null,
      });
      setAddQuestionDialogOpen(false);

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
      await assignmentService.editQuestion(courseId, semester, selectedAssignment.assignment_id, questionData.question_index, questionData);

      const updatedQuestions = selectedAssignment.questions.map((q) =>
        q.question_index === questionData.question_index ? questionData : q
      );

      const updatedAssignment = {
        ...selectedAssignment,
        questions: updatedQuestions,
      };

      setAssignments(assignments.map((assignment) =>
        assignment.assignment_id === selectedAssignment.assignment_id ? updatedAssignment : assignment
      ));
      setSelectedAssignment(updatedAssignment);

      setQuestionData({
        question_text: '',
        question_index: 0,
        question_graphics_figures: null,
      });
      setEditQuestionDialogOpen(false);

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
      await assignmentService.removeQuestion(courseId, semester, selectedAssignment.assignment_id, questionToDelete);

      const updatedQuestions = selectedAssignment.questions.filter(
        (q) => q.question_index !== questionToDelete
      );

      const reindexedQuestions = updatedQuestions.map((q, index) => ({
        ...q,
        question_index: index,
      }));

      const updatedAssignment = {
        ...selectedAssignment,
        questions: reindexedQuestions,
      };

      setAssignments(assignments.map((assignment) =>
        assignment.assignment_id === selectedAssignment.assignment_id ? updatedAssignment : assignment
      ));
      setSelectedAssignment(updatedAssignment);

      setDeleteQuestionDialogOpen(false);
      setQuestionToDelete(null);

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

      {/* Dialogs for Create, Edit, Delete Assignment & Questions */}
      {/* Create Assignment Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
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
          <Button onClick={handleCreateAssignment} variant="contained" color="primary" disabled={!newAssignmentData.assignment_title}>
            Create
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* Additional Dialogs */}
      {/* You can implement the other dialogs here */}
    </Box>
  );
}
