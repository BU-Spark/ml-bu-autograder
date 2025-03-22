/**
 * Manual Submission Page for BU MET Autograder
 * Allows instructors to simulate student responses for testing
 */

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import {
  Alert,
  AlertTitle,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Divider,
  FormControl,
  FormHelperText,
  Grid,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Snackbar,
  Step,
  StepLabel,
  Stepper,
  TextField,
  Typography,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  CloudUpload as UploadIcon,
  Send as SendIcon,
  CheckCircleOutline as SuccessIcon,
  ErrorOutline as ErrorIcon,
  ArrowBack as BackIcon,
  ArrowForward as ForwardIcon,
} from '@mui/icons-material';
import { courseService, assignmentService, responseService } from '../services/api';
import { APP_CONFIG } from '../config/config';
import CardSkeleton from '../components/CardSkeleton';

// Styled components
const SubmissionContainer = styled(Box)(({ theme }) => ({
  maxWidth: 1000,
  margin: '0 auto',
  padding: theme.spacing(3),
}));

const StepContent = styled(Box)(({ theme }) => ({
  marginTop: theme.spacing(3),
  marginBottom: theme.spacing(3),
  padding: theme.spacing(3),
  backgroundColor: theme.palette.background.paper,
  borderRadius: theme.shape.borderRadius,
  boxShadow: theme.shadows[1],
}));

const FileUploadBox = styled(Box)(({ theme }) => ({
  border: `2px dashed ${theme.palette.divider}`,
  borderRadius: theme.shape.borderRadius,
  padding: theme.spacing(3),
  textAlign: 'center',
  cursor: 'pointer',
  transition: 'border-color 0.2s ease-in-out',
  backgroundColor: theme.palette.background.default,
  '&:hover': {
    borderColor: theme.palette.primary.main,
  },
}));

// Steps for the submission process
const steps = ['Select Course', 'Select Assignment', 'Provide Response', 'Review & Submit'];

// Main component
export default function ManualSubmission() {
  const router = useRouter();

  // State for stepper
  const [activeStep, setActiveStep] = useState(0);

  // State for courses and assignments
  const [courses, setCourses] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [loadingCourses, setLoadingCourses] = useState(true);
  const [loadingAssignments, setLoadingAssignments] = useState(false);

  // State for selected items
  const [selectedCourse, setSelectedCourse] = useState({
    courseId: '',
    semester: '',
  });
  const [selectedAssignment, setSelectedAssignment] = useState('');
  const [selectedQuestion, setSelectedQuestion] = useState('');

  // State for response data
  const [studentIdentifier, setStudentIdentifier] = useState('');
  const [responseType, setResponseType] = useState('text');
  const [textResponse, setTextResponse] = useState('');
  const [fileResponse, setFileResponse] = useState(null);
  const [filePreview, setFilePreview] = useState('');

  // State for submission
  const [submitting, setSubmitting] = useState(false);
  const [submissionResult, setSubmissionResult] = useState(null);

  // State for alerts
  const [alertOpen, setAlertOpen] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [alertSeverity, setAlertSeverity] = useState('success');

  // Validation state
  const [errors, setErrors] = useState({});

  // Fetch courses on component mount
  useEffect(() => {
    const fetchCourses = async () => {
      try {
        const coursesData = await courseService.getCourses();
        setCourses(coursesData || []);
      } catch (error) {
        console.error('Error fetching courses:', error);
        setAlertMessage('Failed to load courses: ' + error.message);
        setAlertSeverity('error');
        setAlertOpen(true);
      } finally {
        setLoadingCourses(false);
      }
    };

    fetchCourses();
  }, []);

  // Fetch assignments when course is selected
  useEffect(() => {
    const fetchAssignments = async () => {
      if (!selectedCourse.courseId || !selectedCourse.semester) return;

      setLoadingAssignments(true);
      try {
        const assignmentsData = await assignmentService.getAssignments(
          selectedCourse.courseId,
          selectedCourse.semester
        );
        setAssignments(assignmentsData || []);
      } catch (error) {
        console.error('Error fetching assignments:', error);
        setAlertMessage('Failed to load assignments: ' + error.message);
        setAlertSeverity('error');
        setAlertOpen(true);
      } finally {
        setLoadingAssignments(false);
      }
    };

    if (selectedCourse.courseId && selectedCourse.semester) {
      fetchAssignments();
    }
  }, [selectedCourse]);

  // Update questions when assignment is selected
  useEffect(() => {
    if (!selectedAssignment) {
      setQuestions([]);
      return;
    }

    const assignment = assignments.find((a) => a.assignment_id === selectedAssignment);
    if (assignment) {
      setQuestions(assignment.questions || []);
    } else {
      setQuestions([]);
    }
  }, [selectedAssignment, assignments]);

  // Handle course selection
  const handleCourseSelect = (courseId, semester) => {
    setSelectedCourse({ courseId, semester });
    setSelectedAssignment('');
    setSelectedQuestion('');
  };

  // Handle file selection
  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Check file size
    if (file.size > APP_CONFIG.maxUploadSize) {
      setErrors({
        ...errors,
        file: `File size exceeds the maximum limit of ${APP_CONFIG.maxUploadSize / (1024 * 1024)}MB.`,
      });
      return;
    }

    // Check file type
    const fileExtension = `.${file.name.split('.').pop().toLowerCase()}`;
    if (!APP_CONFIG.acceptedFileTypes.submissions.includes(fileExtension)) {
      setErrors({
        ...errors,
        file: `File type not supported. Accepted types: ${APP_CONFIG.acceptedFileTypes.submissions.join(', ')}`,
      });
      return;
    }

    setFileResponse(file);
    setErrors({ ...errors, file: null });

    // Create file preview
    const reader = new FileReader();
    reader.onload = (e) => {
      setFilePreview(e.target.result);
    };
    reader.readAsDataURL(file);
  };

  // Handle file drop
  const handleFileDrop = (event) => {
    event.preventDefault();
    event.stopPropagation();

    if (event.dataTransfer.files && event.dataTransfer.files.length > 0) {
      const file = event.dataTransfer.files[0];

      // Check file size
      if (file.size > APP_CONFIG.maxUploadSize) {
        setErrors({
          ...errors,
          file: `File size exceeds the maximum limit of ${APP_CONFIG.maxUploadSize / (1024 * 1024)}MB.`,
        });
        return;
      }

      // Check file type
      const fileExtension = `.${file.name.split('.').pop().toLowerCase()}`;
      if (!APP_CONFIG.acceptedFileTypes.submissions.includes(fileExtension)) {
        setErrors({
          ...errors,
          file: `File type not supported. Accepted types: ${APP_CONFIG.acceptedFileTypes.submissions.join(', ')}`,
        });
        return;
      }

      setFileResponse(file);
      setErrors({ ...errors, file: null });

      // Create file preview
      const reader = new FileReader();
      reader.onload = (e) => {
        setFilePreview(e.target.result);
      };
      reader.readAsDataURL(file);
    }
  };

  // Prevent default drag behavior
  const handleDragOver = (event) => {
    event.preventDefault();
    event.stopPropagation();
  };

  // Handle step navigation
  const handleNext = () => {
    // Validate current step
    if (!validateCurrentStep()) return;

    setActiveStep((prevStep) => prevStep + 1);
  };

  const handleBack = () => {
    setActiveStep((prevStep) => prevStep - 1);
  };

  const handleReset = () => {
    setActiveStep(0);
    setSelectedCourse({ courseId: '', semester: '' });
    setSelectedAssignment('');
    setSelectedQuestion('');
    setStudentIdentifier('');
    setResponseType('text');
    setTextResponse('');
    setFileResponse(null);
    setFilePreview('');
    setSubmissionResult(null);
    setErrors({});
  };

  // Validate current step
  const validateCurrentStep = () => {
    let isValid = true;
    const newErrors = {};

    switch (activeStep) {
      case 0: // Course selection
        if (!selectedCourse.courseId || !selectedCourse.semester) {
          newErrors.course = 'Please select a course';
          isValid = false;
        }
        break;

      case 1: // Assignment selection
        if (!selectedAssignment) {
          newErrors.assignment = 'Please select an assignment';
          isValid = false;
        }
        if (!selectedQuestion) {
          newErrors.question = 'Please select a question';
          isValid = false;
        }
        break;

      case 2: // Response data
        if (!studentIdentifier) {
          newErrors.studentIdentifier = 'Please enter a student identifier';
          isValid = false;
        }

        if (responseType === 'text' && !textResponse.trim()) {
          newErrors.textResponse = 'Please enter a response';
          isValid = false;
        }

        if (responseType === 'file' && !fileResponse) {
          newErrors.file = 'Please upload a file';
          isValid = false;
        }
        break;

      default:
        break;
    }

    setErrors(newErrors);
    return isValid;
  };

  // Handle submission
  const handleSubmit = async () => {
    if (!validateCurrentStep()) return;

    setSubmitting(true);

    try {
      // Prepare response data
      let responseData;

      if (responseType === 'text') {
        responseData = {
          student_identifier: studentIdentifier,
          assignment_id: selectedAssignment,
          question_index: parseInt(selectedQuestion),
          data: {
            data_type: '.txt',
            content: btoa(textResponse), // Base64 encode the text
          },
        };
      } else {
        // Read file as base64
        const fileContent = await readFileAsBase64(fileResponse);

        responseData = {
          student_identifier: studentIdentifier,
          assignment_id: selectedAssignment,
          question_index: parseInt(selectedQuestion),
          data: {
            data_type: `.${fileResponse.name.split('.').pop().toLowerCase()}`,
            content: fileContent,
            metadata: {
              filename: fileResponse.name,
              size: `${(fileResponse.size / 1024).toFixed(2)}KB`,
              type: fileResponse.type,
            },
          },
        };
      }

      // Submit response
      await responseService.uploadResponse(responseData);

      setSubmissionResult({
        success: true,
        message: 'Response submitted successfully!',
      });

      setAlertMessage('Response submitted successfully!');
      setAlertSeverity('success');
      setAlertOpen(true);
    } catch (error) {
      console.error('Error submitting response:', error);

      setSubmissionResult({
        success: false,
        message: `Submission failed: ${error.message}`,
      });

      setAlertMessage(`Submission failed: ${error.message}`);
      setAlertSeverity('error');
      setAlertOpen(true);
    } finally {
      setSubmitting(false);
    }
  };

  // Helper function to read file as base64
  const readFileAsBase64 = (file) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        // Extract the base64 content from the data URL
        const base64Content = reader.result.split(',')[1];
        resolve(base64Content);
      };
      reader.onerror = (error) => reject(error);
      reader.readAsDataURL(file);
    });
  };

  // Render step content
  const getStepContent = (step) => {
    switch (step) {
      case 0: // Course selection
        return (
          <StepContent>
            <Typography variant="h6" gutterBottom>
              Select a Course
            </Typography>

            {loadingCourses ? (
              <Box sx={{ mt: 3 }}>
                <CardSkeleton height={100} />
                <CardSkeleton height={100} />
              </Box>
            ) : courses.length === 0 ? (
              <Alert severity="info" sx={{ mt: 2 }}>
                No courses available. Please create a course first.
              </Alert>
            ) : (
              <Grid container spacing={3} sx={{ mt: 1 }}>
                {courses.map((course) => (
                  <Grid item xs={12} sm={6} md={4} key={`${course.course_id}-${course.semester}`}>
                    <Card
                      raised={
                        selectedCourse.courseId === course.course_id &&
                        selectedCourse.semester === course.semester
                      }
                      sx={{
                        cursor: 'pointer',
                        transition: 'transform 0.2s',
                        '&:hover': {
                          transform: 'translateY(-4px)',
                        },
                      }}
                      onClick={() => handleCourseSelect(course.course_id, course.semester)}
                    >
                      <CardContent>
                        <Typography variant="h6" noWrap>
                          {course.course_id}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {course.semester}
                        </Typography>
                        <Typography variant="body2" sx={{ mt: 1 }}>
                          {course.instructors?.length} {course.instructors?.length === 1 ? 'instructor' : 'instructors'}
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            )}

            {errors.course && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {errors.course}
              </Alert>
            )}
          </StepContent>
        );

      case 1: // Assignment selection
        return (
          <StepContent>
            <Typography variant="h6" gutterBottom>
              Select an Assignment and Question
            </Typography>

            {loadingAssignments ? (
              <Box sx={{ mt: 3 }}>
                <CardSkeleton height={100} />
              </Box>
            ) : assignments.length === 0 ? (
              <Alert severity="info" sx={{ mt: 2 }}>
                No assignments available for this course. Please create an assignment first.
              </Alert>
            ) : (
              <Box sx={{ mt: 3 }}>
                <FormControl fullWidth error={!!errors.assignment} sx={{ mb: 3 }}>
                  <InputLabel id="assignment-select-label">Assignment</InputLabel>
                  <Select
                    labelId="assignment-select-label"
                    value={selectedAssignment}
                    onChange={(e) => setSelectedAssignment(e.target.value)}
                    label="Assignment"
                  >
                    {assignments.map((assignment) => (
                      <MenuItem key={assignment.assignment_id} value={assignment.assignment_id}>
                        {assignment.assignment_title || `Assignment ${assignment.assignment_id}`}
                      </MenuItem>
                    ))}
                  </Select>
                  {errors.assignment && <FormHelperText>{errors.assignment}</FormHelperText>}
                </FormControl>

                <FormControl fullWidth error={!!errors.question} disabled={!selectedAssignment}>
                  <InputLabel id="question-select-label">Question</InputLabel>
                  <Select
                    labelId="question-select-label"
                    value={selectedQuestion}
                    onChange={(e) => setSelectedQuestion(e.target.value)}
                    label="Question"
                  >
                    {questions.map((question) => (
                      <MenuItem key={question.question_index} value={question.question_index}>
                        Question {question.question_index + 1}
                      </MenuItem>
                    ))}
                  </Select>
                  {errors.question && <FormHelperText>{errors.question}</FormHelperText>}
                </FormControl>

                {selectedAssignment && selectedQuestion !== '' && (
                  <Paper sx={{ p: 2, mt: 3, bgcolor: 'background.default' }}>
                    <Typography variant="subtitle1" gutterBottom>
                      Question Preview:
                    </Typography>
                    <Typography variant="body1">
                      {
                        questions.find(
                          (q) => q.question_index === parseInt(selectedQuestion)
                        )?.question_text
                      }
                    </Typography>
                  </Paper>
                )}
              </Box>
            )}
          </StepContent>
        );

      case 2: // Response data
        return (
          <StepContent>
            <Typography variant="h6" gutterBottom>
              Provide Response Data
            </Typography>

            <TextField
              label="Student Identifier"
              fullWidth
              margin="normal"
              value={studentIdentifier}
              onChange={(e) => setStudentIdentifier(e.target.value)}
              error={!!errors.studentIdentifier}
              helperText={
                errors.studentIdentifier ||
                "Enter a unique identifier for the student (e.g., email, ID number)"
              }
            />

            <FormControl fullWidth margin="normal">
              <InputLabel id="response-type-label">Response Type</InputLabel>
              <Select
                labelId="response-type-label"
                value={responseType}
                onChange={(e) => setResponseType(e.target.value)}
                label="Response Type"
              >
                <MenuItem value="text">Text Response</MenuItem>
                <MenuItem value="file">File Upload</MenuItem>
              </Select>
              <FormHelperText>
                Select how you want to provide the response
              </FormHelperText>
            </FormControl>

            {responseType === 'text' ? (
              <TextField
                label="Text Response"
                fullWidth
                multiline
                rows={6}
                margin="normal"
                value={textResponse}
                onChange={(e) => setTextResponse(e.target.value)}
                error={!!errors.textResponse}
                helperText={errors.textResponse}
                placeholder="Enter the student's response text here..."
              />
            ) : (
              <Box sx={{ mt: 3 }}>
                <input
                  type="file"
                  id="file-upload"
                  style={{ display: 'none' }}
                  onChange={handleFileSelect}
                  accept={APP_CONFIG.acceptedFileTypes.submissions.join(',')}
                />

                <FileUploadBox
                  component="label"
                  htmlFor="file-upload"
                  onDrop={handleFileDrop}
                  onDragOver={handleDragOver}
                  sx={{ borderColor: errors.file ? 'error.main' : 'divider' }}
                >
                  <UploadIcon fontSize="large" color="primary" />
                  <Typography variant="h6" sx={{ mt: 2 }}>
                    {fileResponse ? 'File Selected' : 'Drag & Drop or Click to Upload'}
                  </Typography>
                  {fileResponse ? (
                    <Typography variant="body2" color="text.secondary">
                      {fileResponse.name} ({(fileResponse.size / 1024).toFixed(2)} KB)
                    </Typography>
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      Accepted file types: {APP_CONFIG.acceptedFileTypes.submissions.join(', ')}
                    </Typography>
                  )}
                </FileUploadBox>

                {errors.file && (
                  <Typography color="error" variant="body2" sx={{ mt: 1 }}>
                    {errors.file}
                  </Typography>
                )}

                {fileResponse && filePreview && (
                  <Box sx={{ mt: 3 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      File Preview:
                    </Typography>
                    {fileResponse.type.startsWith('image/') ? (
                      <Box
                        component="img"
                        src={filePreview}
                        alt="File preview"
                        sx={{
                          maxWidth: '100%',
                          maxHeight: 200,
                          objectFit: 'contain',
                          border: (theme) => `1px solid ${theme.palette.divider}`,
                          borderRadius: 1,
                        }}
                      />
                    ) : (
                      <Paper sx={{ p: 2, bgcolor: 'background.default' }}>
                        <Typography variant="body2" color="text.secondary">
                          Preview not available for this file type.
                        </Typography>
                      </Paper>
                    )}
                  </Box>
                )}
              </Box>
            )}
          </StepContent>
        );

      case 3: // Review & Submit
        return (
          <StepContent>
            <Typography variant="h6" gutterBottom>
              Review & Submit
            </Typography>

            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                    Course Information
                  </Typography>
                  <Typography variant="body2">
                    <strong>Course ID:</strong> {selectedCourse.courseId}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Semester:</strong> {selectedCourse.semester}
                  </Typography>

                  <Divider sx={{ my: 2 }} />

                  <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                    Assignment & Question
                  </Typography>
                  <Typography variant="body2">
                    <strong>Assignment:</strong>{' '}
                    {
                      assignments.find((a) => a.assignment_id === selectedAssignment)
                        ?.assignment_title || selectedAssignment
                    }
                  </Typography>
                  <Typography variant="body2">
                    <strong>Question:</strong> Question {parseInt(selectedQuestion) + 1}
                  </Typography>

                  <Divider sx={{ my: 2 }} />

                  <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                    Student Information
                  </Typography>
                  <Typography variant="body2">
                    <strong>Student ID:</strong> {studentIdentifier}
                  </Typography>
                </Paper>
              </Grid>

              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
                    Response Content
                  </Typography>
                  <Typography variant="body2">
                    <strong>Response Type:</strong> {responseType === 'text' ? 'Text' : 'File'}
                  </Typography>

                  {responseType === 'text' ? (
                    <Paper
                      sx={{
                        p: 2,
                        mt: 2,
                        bgcolor: 'background.default',
                        whiteSpace: 'pre-wrap',
                        maxHeight: 200,
                        overflow: 'auto',
                      }}
                    >
                      {textResponse || <em>No text provided</em>}
                    </Paper>
                  ) : (
                    <Box sx={{ mt: 2 }}>
                      {fileResponse ? (
                        <>
                          <Typography variant="body2">
                            <strong>File Name:</strong> {fileResponse.name}
                          </Typography>
                          <Typography variant="body2">
                            <strong>File Size:</strong> {(fileResponse.size / 1024).toFixed(2)} KB
                          </Typography>
                          <Typography variant="body2">
                            <strong>File Type:</strong> {fileResponse.type}
                          </Typography>

                          {fileResponse.type.startsWith('image/') && filePreview && (
                            <Box
                              component="img"
                              src={filePreview}
                              alt="File preview"
                              sx={{
                                mt: 2,
                                maxWidth: '100%',
                                maxHeight: 100,
                                objectFit: 'contain',
                                border: (theme) => `1px solid ${theme.palette.divider}`,
                                borderRadius: 1,
                              }}
                            />
                          )}
                        </>
                      ) : (
                        <Typography variant="body2" color="error">
                          No file selected
                        </Typography>
                      )}
                    </Box>
                  )}
                </Paper>
              </Grid>
            </Grid>

            {submissionResult && (
              <Alert
                severity={submissionResult.success ? 'success' : 'error'}
                sx={{ mt: 3 }}
                icon={submissionResult.success ? <SuccessIcon /> : <ErrorIcon />}
              >
                <AlertTitle>{submissionResult.success ? 'Success' : 'Error'}</AlertTitle>
                {submissionResult.message}
              </Alert>
            )}
          </StepContent>
        );

      default:
        return 'Unknown step';
    }
  };

  // Render navigation buttons
  const renderNavButtons = () => {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 3 }}>
        <Button
          variant="outlined"
          disabled={activeStep === 0 || submitting}
          onClick={handleBack}
          startIcon={<BackIcon />}
        >
          Back
        </Button>

        <Box>
          {activeStep === steps.length - 1 ? (
            <Button
              variant="contained"
              color="primary"
              onClick={handleSubmit}
              disabled={submitting || submissionResult?.success}
              startIcon={submitting ? <CircularProgress size={24} /> : <SendIcon />}
            >
              {submitting ? 'Submitting...' : 'Submit Response'}
            </Button>
          ) : (
            <Button
              variant="contained"
              color="primary"
              onClick={handleNext}
              endIcon={<ForwardIcon />}
            >
              Next
            </Button>
          )}

          {submissionResult?.success && (
            <Button
              variant="outlined"
              color="primary"
              onClick={handleReset}
              sx={{ ml: 2 }}
            >
              Submit Another
            </Button>
          )}
        </Box>
      </Box>
    );
  };

  return (
    <SubmissionContainer>
      <Typography variant="h4" component="h1" gutterBottom>
        Manual Student Submission
      </Typography>

      <Typography variant="body1" color="text.secondary" paragraph>
        Use this tool to simulate student responses for testing the grading system.
      </Typography>

      <Stepper activeStep={activeStep} sx={{ my: 4 }}>
        {steps.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>

      {getStepContent(activeStep)}

      {renderNavButtons()}

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
    </SubmissionContainer>
  );
}