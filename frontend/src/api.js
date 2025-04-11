/**
 * API service layer for interacting with the BU MET Autograder backend
 * Provides functions for making API calls and custom SWR hooks
 */

import axios from 'axios';
import useSWR from 'swr';
import { BACKEND_URL, API_PREFIX, LIMITS, ERROR_MESSAGES } from './config';
import { signOut } from 'next-auth/react';

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
          // Unauthorized - could trigger logout or refresh token (if implemented)
          console.error('Authentication error:', error.response);
          signOut({ callbackUrl: '/login' }); // Redirect to login on 401
          return Promise.reject(new Error(ERROR_MESSAGES.auth.unauthorized));

        case 403:
          console.error('Forbidden error:', error.response);
          return Promise.reject(new Error(ERROR_MESSAGES.auth.unauthorized));
        case 404:
          console.error('Not found error:', error.response);
          return Promise.reject(new Error(ERROR_MESSAGES.api.notFound));
        case 400:
          console.error('Bad request error:', error.response);
          // Returning the original error response to provide details.
          return Promise.reject(error.response); // Reject with the full response
        case 500:
          console.error('Server error:', error.response);
          return Promise.reject(new Error(ERROR_MESSAGES.api.serverError));
        default:
          console.error('API error:', error.response);
          return Promise.reject(new Error(ERROR_MESSAGES.general));
      }
    } else if (error.request) {
      // Request was made but no response received
      console.error('Network error:', error.request);
      return Promise.reject(new Error(ERROR_MESSAGES.network));
    } else {
      // Something else happened while setting up the request
      console.error('Request configuration error:', error.message);
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
    throw error; // SWR handles the error
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
  //Sign out
  signOut: () => api.post('/auth/signout')
};

// Course management
export const courseService = {
  // Course CRUD operations
  getCourses: (semester) => api.get('/courses', { params: { semester } }),
  getCourse: (courseId, semester) =>
    api.get('/course', { params: { course_id: courseId, semester } }),
  createCourse: (semester, courseData) =>
    api.post('/course', courseData, { params: { semester } }),
  deleteCourse: (courseId, semester) =>
    api.delete('/course', { params: { course_id: courseId, semester } }),

  // Course transfer
  transferCourse: (currentCourseId, currentSemester, copyFromCourseId, copyFromCourseSemester) =>
    api.patch('/course/transfer', null, {
      params: {
        current_course_id: currentCourseId,
        current_semester: currentSemester,
        copy_from_course_id: copyFromCourseId,
        copy_from_course_semester: copyFromCourseSemester,
      },
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
    api.get('/assignments', { params: { course_id: courseId, semester: semester } }),

  getAssignment: (courseId, semester, assignmentId) =>
    api.get('/assignment', { params: { course_id: courseId, semester: semester, assignment_id: assignmentId } }),

  createAssignment: (assignmentData) =>
    api.post('/assignment', assignmentData),

  deleteAssignment: (courseId, semester, assignmentId) =>
    api.delete('/assignment', { params: { course_id: courseId, semester: semester, assignment_id: assignmentId } }),

  // Question management
  addQuestion: (courseId, semester, assignmentId, questionData) =>
    api.patch('/assignment/add_question', questionData, { params: { course_id: courseId, semester: semester, assignment_id: assignmentId } }),

  removeQuestion: (courseId, semester, assignmentId, questionIndex) =>
    api.patch('/assignment/remove_question', null, { params: { course_id: courseId, semester: semester, assignment_id: assignmentId, question_index: questionIndex } }),

  editQuestion: (courseId, semester, assignmentId, questionIndex, questionData) =>
    api.patch('/assignment/edit_question', questionData, { params: { course_id: courseId, semester: semester, assignment_id: assignmentId, question_index: questionIndex } }),

  modifyQuestionOrder: (courseId, semester, assignmentId, orderData) =>
    api.patch('/assignment/modify_order', orderData, { params: { course_id: courseId, semester: semester, assignment_id: assignmentId } }),

  // Update assignment
  updateAssignment: (courseId, semester, assignmentId, assignmentData) =>
    api.put('/assignment', assignmentData, { params: { course_id: courseId, semester: semester, assignment_id: assignmentId } }),
};

// Student response management
export const responseService = {
  // Response CRUD operations
  uploadResponse: (responseData) => api.post('/response', responseData),
  
  replaceResponse: (responseData) => api.put('/response', responseData),
  
  deleteResponse: (studentIdentifier, semester, courseId, assignmentId, questionIndex = null) =>
    api.delete('/response', {
      params: {
        student_id: studentIdentifier,
        semester: semester,
        course_id: courseId,
        assignment_id: assignmentId,
        question_index: questionIndex,
      }
    }),

  // Get responses
  getResponses: (semester, courseId, assignmentId, questionIndex = null, studentIdentifier = null) =>
    api.get('/responses', {
      params: {
        semester: semester,
        course_id: courseId,
        assignment_id: assignmentId,
        question_index: questionIndex,
        student_id: studentIdentifier
      }
    }),

  // Grading
  gradeSpecific: (studentIdentifiers, semester, courseId, assignmentId, questionIndex = null) =>
    api.post('/grade/specific', null, {
      params: {
        student_ids: studentIdentifiers,
        semester: semester,
        course_id: courseId,
        assignment_id: assignmentId,
        question_index: questionIndex
      }
    }),
  
  gradeUngraded: (semester, courseId, assignmentId, questionIndex = null) =>
    api.post('/grade/ungraded', null, {
      params: {
        semester: semester,
        course_id: courseId,
        assignment_id: assignmentId,
        question_index: questionIndex
      }
    }),
  
  gradeAll: (semester, courseId, assignmentId, questionIndex = null) =>
    api.post('/grade/all', null, {
      params: {
        semester: semester,
        course_id: courseId,
        assignment_id: assignmentId,
        question_index: questionIndex
      }
    }),
};

// Course material management
export const materialService = {
  // Get all materials for a course
  getMaterials: (semester, courseId) =>
    api.get('/course_materials', { params: { semester: semester, course_id: courseId } }),

  // Material CRUD operations
  getMaterial: (semester, courseId, materialId) =>
    api.get('/course_material', { params: { semester: semester, course_id: courseId, material_id: materialId } }),
  
  uploadMaterial: (materialData) => api.post('/course_material', materialData),
  
  updateMaterial: (materialData) => api.patch('/course_material', materialData),
  
  deleteMaterial: (semester, courseId, materialId) =>
    api.delete('/course_material', { params: { semester: semester, course_id: courseId, material_id: materialId } }),
};


// Rubric management
export const rubricService = {
  // Rubric CRUD operations
  getRubric: (semester, courseId, assignmentId, questionIndex = null) =>
    api.get('/rubric', { 
      params: { 
        semester: semester, 
        course_id: courseId, 
        assignment_id: assignmentId, 
        question_index: questionIndex 
      } 
    }),

  createRubric: (rubricData) => 
    api.put('/rubric', rubricData), // Correctly uses PUT for creating a rubric

  // AI rubric enhancement
  getAIRubric: (semester, courseId, assignmentId, instructions = null) =>
    api.get('/ai_rubric', { 
      params: { 
        semester: semester, 
        course_id: courseId, 
        assignment_id: assignmentId, 
        instructions: instructions 
      } 
    }),
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

export const useAssignments = (semester, courseId) => {
  const { data, error, mutate } = useSWR(
    semester && courseId ? `/assignments?semester=${semester}&course_id=${courseId}` : null,
    fetcher
  );
  return {
    assignments: data,
    isLoading: !error && !data,
    isError: error,
    mutate,
  };
};


export const useRubric = (semester, courseId, assignmentId, questionIndex = null) => {
  const params = new URLSearchParams({
    assignment_id: assignmentId,
    semester: semester,
    course_id: courseId,
  });
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


export const useMaterials = (semester, courseId) => {
  const { data, error, mutate } = useSWR(
    semester && courseId ? `/course_materials?semester=${semester}&course_id=${courseId}` : null,
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