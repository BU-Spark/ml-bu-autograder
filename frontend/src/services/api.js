/**
 * API service layer for interacting with the BU MET Autograder backend
 * Provides functions for making API calls and custom SWR hooks
 */

import axios from 'axios';
import useSWR from 'swr';
import { BACKEND_URL, API_PREFIX, LIMITS, ERROR_MESSAGES } from '../config/config';

// Create an Axios instance with default config
const api = axios.create({
  baseURL: `${BACKEND_URL}${API_PREFIX}`,
  timeout: LIMITS.apiTimeout,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle specific error cases
    if (error.response) {
      // Server responded with a status code outside of 2xx range
      switch (error.response.status) {
        case 401:
          // Unauthorized - could trigger logout or refresh token
          console.error('Authentication error:', error);
          return Promise.reject(new Error(ERROR_MESSAGES.auth.unauthorized));
        case 403:
          console.error('Forbidden error:', error);
          return Promise.reject(new Error(ERROR_MESSAGES.auth.unauthorized));
        case 404:
          console.error('Not found error:', error);
          return Promise.reject(new Error(ERROR_MESSAGES.api.notFound));
        case 400:
          console.error('Bad request error:', error);
          return Promise.reject(new Error(ERROR_MESSAGES.api.badRequest));
        case 500:
          console.error('Server error:', error);
          return Promise.reject(new Error(ERROR_MESSAGES.api.serverError));
        default:
          console.error('API error:', error);
          return Promise.reject(new Error(ERROR_MESSAGES.general));
      }
    } else if (error.request) {
      // Request was made but no response received
      console.error('Network error:', error);
      return Promise.reject(new Error(ERROR_MESSAGES.network));
    } else {
      // Something else happened while setting up the request
      console.error('Request configuration error:', error);
      return Promise.reject(new Error(ERROR_MESSAGES.general));
    }
  }
);

// SWR fetcher function using our API instance
const fetcher = async (url) => {
  try {
    const response = await api.get(url);
    return response.data;
  } catch (error) {
    throw error;
  }
};

// API service methods

// Authentication
export const authService = {
  // Get token using Google OAuth
  googleOAuth: (params) => api.get('/auth/google_oauth', { params }),

  // Token management
  createToken: (tokenName) => api.post('/auth/token', null, { params: { token_name: tokenName } }),
  listTokens: () => api.get('/auth/tokens'),
  deleteToken: (tokenId) => api.delete('/auth/token', { params: { token_id: tokenId } }),
};

// Course management
export const courseService = {
  // Course CRUD operations
  getCourses: () => api.get('/courses'),
  getCourse: (courseId, semester) => api.get('/course', { params: { course_id: courseId, semester } }),
  createCourse: (semester, courseData) => api.post('/course', courseData, { params: { semester } }),
  deleteCourse: (courseId, semester) => api.delete('/course', { params: { course_id: courseId, semester } }),

  // Course transfer
  transferCourse: (currentCourseId, currentSemester, copyFromCourseId, copyFromCourseSemester) =>
    api.patch('/course/transfer', null, {
      params: {
        current_course_id: currentCourseId,
        current_semester: currentSemester,
        copy_from_course_id: copyFromCourseId,
        copy_from_course_semester: copyFromCourseSemester
      }
    }),

  // Instructor management
  addInstructor: (courseId, semester, instructor) =>
    api.post('/course/instructor', null, { params: { course_id: courseId, semester, instructor } }),
  removeInstructor: (courseId, semester, instructor) =>
    api.delete('/course/instructor', { params: { course_id: courseId, semester, instructor } }),
};

// Assignment management
export const assignmentService = {
  // Assignment CRUD operations
  getAssignments: (courseId, semester) =>
    api.get('/assignments', { params: { course_id: courseId, semester } }),
  getAssignment: (courseId, semester, assignmentId) =>
    api.get('/assignment', { params: { course_id: courseId, semester, assignment_id: assignmentId } }),
  createAssignment: (assignmentData) => api.post('/assignment', assignmentData),
  deleteAssignment: (assignmentId) => api.delete('/assignment', { params: { assignment_id: assignmentId } }),

  // Question management
  addQuestion: (questionData) => api.patch('/assignment/add_question', questionData),
  removeQuestion: (assignmentId, questionIndex) =>
    api.patch('/assignment/remove_question', null, { params: { assignment_id: assignmentId, question_index: questionIndex } }),
  editQuestion: (questionData) => api.patch('/assignment/edit_question', questionData),
  modifyQuestionOrder: (orderData) => api.patch('/assignment/modify_order', orderData),
};

// Student response management
export const responseService = {
  // Response CRUD operations
  uploadResponse: (responseData) => api.post('/response', responseData),
  replaceResponse: (responseData) => api.put('/response', responseData),
  deleteResponse: (studentIdentifier, assignmentId, questionIndex = null) =>
    api.delete('/response', {
      params: {
        student_identifier: studentIdentifier,
        assignment_id: assignmentId,
        question_index: questionIndex
      }
    }),

  // Get responses
  getResponses: (assignmentId, questionIndex = null, studentIdentifier = null) =>
    api.get('/responses', {
      params: {
        assignment_id: assignmentId,
        question_index: questionIndex,
        student_identifier: studentIdentifier
      }
    }),

  // Grading
  gradeSpecific: (studentIdentifiers, assignmentId, questionIndex = null) =>
    api.post('/response/grade/specific', null, {
      params: {
        student_identifiers: studentIdentifiers,
        assignment_id: assignmentId,
        question_index: questionIndex
      }
    }),
  gradeUngraded: (assignmentId, questionIndex = null) =>
    api.post('/response/grade/ungraded', null, {
      params: {
        assignment_id: assignmentId,
        question_index: questionIndex
      }
    }),
  gradeAll: (assignmentId, questionIndex = null) =>
    api.post('/response/grade/all', null, {
      params: {
        assignment_id: assignmentId,
        question_index: questionIndex
      }
    }),
};

// Course material management
export const materialService = {
  // Get all materials for a course
  getMaterials: (courseId, semester) =>
    api.get('/course_materials', { params: { course_id: courseId, semester } }),

  // Material CRUD operations
  getMaterial: (courseId, semester, materialId) =>
    api.get('/course_material', { params: { course_id: courseId, semester, material_id: materialId } }),
  uploadMaterial: (materialData) => api.post('/course_material', materialData),
  updateMaterial: (materialData) => api.patch('/course_material', materialData),
  deleteMaterial: (courseId, semester, materialId) =>
    api.delete('/course_material', { params: { course_id: courseId, semester, material_id: materialId } }),
};

// Rubric management
export const rubricService = {
  // Rubric CRUD operations
  getRubric: (assignmentId, questionIndex = null) =>
    api.get('/rubric', { params: { assignment_id: assignmentId, question_index: questionIndex } }),
  createRubric: (rubricData) => api.put('/rubric', rubricData),

  // AI rubric enhancement
  getAIRubric: (assignmentId, instructions = null) =>
    api.get('/ai_rubric', { params: { assignment_id: assignmentId, instructions } }),
};

// User management
export const userService = {
  // User data and preferences
  getUserData: () => api.get('/user'),
  updateUserPreferences: (preferencesData) => api.patch('/user', preferencesData),
};

// Custom SWR hooks for data fetching
export const useUser = () => {
  const { data, error, mutate } = useSWR('/user', fetcher);
  return {
    user: data,
    isLoading: !error && !data,
    isError: error,
    mutate,
  };
};

export const useCourses = () => {
  const { data, error, mutate } = useSWR('/courses', fetcher);
  return {
    courses: data,
    isLoading: !error && !data,
    isError: error,
    mutate,
  };
};

export const useAssignments = (courseId, semester) => {
  const { data, error, mutate } = useSWR(
    courseId && semester ? `/assignments?course_id=${courseId}&semester=${semester}` : null,
    fetcher
  );
  return {
    assignments: data,
    isLoading: !error && !data,
    isError: error,
    mutate,
  };
};

export const useRubric = (assignmentId, questionIndex = null) => {
  const params = new URLSearchParams({ assignment_id: assignmentId });
  if (questionIndex !== null) params.append('question_index', questionIndex);

  const { data, error, mutate } = useSWR(
    assignmentId ? `/rubric?${params.toString()}` : null,
    fetcher
  );

  return {
    rubric: data,
    isLoading: !error && !data,
    isError: error,
    mutate,
  };
};

export const useMaterials = (courseId, semester) => {
  const { data, error, mutate } = useSWR(
    courseId && semester ? `/course_materials?course_id=${courseId}&semester=${semester}` : null,
    fetcher
  );
  return {
    materials: data,
    isLoading: !error && !data,
    isError: error,
    mutate,
  };
};

export default api;