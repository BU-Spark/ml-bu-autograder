/**
 * API service layer for interacting with the BU MET Autograder backend
 * Provides functions for making API calls and custom SWR hooks
 */

import axios from 'axios';
import useSWR from 'swr';
// Assuming config.js is in the same directory or adjusted path
import { BACKEND_URL, API_PREFIX, LIMITS, ERROR_MESSAGES } from './config';
import { signOut } from 'next-auth/react'; // Assuming next-auth is used

// Create an Axios instance with default config
const api = axios.create({
  baseURL: `${BACKEND_URL}${API_PREFIX}`, // e.g., http://localhost:8000/api/v1/
  timeout: LIMITS?.apiTimeout || 30000, // Use config timeout or default 30s
  headers: {
    'Content-Type': 'application/json',
  },
});

// --- Request Interceptor (Add Auth Token) ---
api.interceptors.request.use(
  (config) => {
    // --- Replace with your ACTUAL token retrieval logic ---
   // const token = typeof window !== 'undefined' ? localStorage.getItem('authToken') : null; // Example using localStorage
    // --- End Token Retrieval ---
   const token = "123bob"
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    } else {
      const isAuthEndpoint = config.url?.includes('/auth/');
      if (!isAuthEndpoint) {
        console.warn(`No auth token found for request to ${config.url}.`);
      }
    }
    return config;
  },
  (error) => {
    console.error("Axios request setup error:", error);
    return Promise.reject(error);
  }
);

// --- Response Interceptor (Error Handling) ---
api.interceptors.response.use(
  (response) => response, // Pass through successful responses
  (error) => {
    let userFriendlyError = new Error(ERROR_MESSAGES?.general || "An unexpected error occurred.");
    userFriendlyError.isNotFoundError = false; // Flag for 404s

    if (error.response) {
      // Server responded with a non-2xx status code
      const { status, data } = error.response;
      console.error(`API Response Error Status: ${status}`, data);

      const detailErrorMessage = Array.isArray(data?.detail)
        ? data.detail.map(err => `${err.loc?.slice(1).join('.') || 'field'} - ${err.msg}`).join('; ')
        : typeof data?.detail === 'string' ? data.detail : null;

      let specificMessage = detailErrorMessage;

      switch (status) {
        case 401:
          specificMessage = ERROR_MESSAGES?.auth?.unauthorized || "Authentication failed.";
          if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/auth')) {
            signOut({ callbackUrl: '/login?error=unauthorized' });
          }
          userFriendlyError = new Error(specificMessage);
          break;
        case 403:
          specificMessage = specificMessage || ERROR_MESSAGES?.auth?.forbidden || "Permission denied.";
          userFriendlyError = new Error(specificMessage);
          break;
        case 404:
          specificMessage = specificMessage || ERROR_MESSAGES?.api?.notFound || "Resource not found.";
          userFriendlyError = new Error(specificMessage);
          userFriendlyError.isNotFoundError = true; // Set 404 flag
          break;
        case 400: case 409: case 422:
          specificMessage = specificMessage || `Invalid request (${status}). Check input.`;
          userFriendlyError = new Error(specificMessage);
          break;
        case 500: case 502: case 503:
          specificMessage = specificMessage || ERROR_MESSAGES?.api?.serverError || "Server error occurred.";
          userFriendlyError = new Error(specificMessage);
          break;
        default:
          specificMessage = specificMessage || `API error (${status}).`;
          userFriendlyError = new Error(specificMessage);
      }
    } else if (error.request) {
      // Network error (no response received)
      console.error('Network error:', error.request);
      userFriendlyError = new Error(ERROR_MESSAGES?.network || "Network error. Check connection.");
    } else {
      // Request setup error
      console.error('Request configuration error:', error.message);
      userFriendlyError = new Error(ERROR_MESSAGES?.general || "Error setting up request.");
    }

    userFriendlyError.originalError = error; // Attach original error if needed
    return Promise.reject(userFriendlyError); // Reject with the formatted error
  }
);

// --- SWR Fetcher Function ---
// Uses the configured Axios instance for GET requests with SWR
const fetcher = async (url) => {
  // Interceptor handles error formatting. SWR catches the rejected promise.
  const response = await api.get(url);
  return response.data;
};

// --- API Service Methods ---

// Authentication Service
export const authService = {
  googleOAuth: (code) => api.get('/auth/google_oauth', { params: { code } }),
  getGoogleOAuthUrl: () => api.get('/auth/google_oauth_url'),
  createToken: (tokenName, tokenExpiry = null) => api.post('/auth/token', null, { params: { token_name: tokenName, token_expiry: tokenExpiry } }),
  listTokens: () => api.get('/auth/tokens'),
  deleteToken: (tokenName) => api.delete('/auth/token', { params: { token_name: tokenName } }),
};

// Course Management Service
export const courseService = {
  getCourses: (semester = null) => api.get('/courses', { params: { semester } }),
  getCourse: (courseId, semester) => api.get('/course', { params: { course_id: courseId, semester } }),
  createCourse: (courseData) => api.post('/course', courseData),
  deleteCourse: (courseId, semester) => api.delete('/course', { params: { course_id: courseId, semester } }),
  transferCourse: (currentSemester, currentCourseId, copyFromSemester, copyFromCourseId) => api.patch('/course/transfer', null, { params: { current_semester: currentSemester, current_course_id: currentCourseId, copy_from_course_semester: copyFromSemester, copy_from_course_id: copyFromCourseId, } }),
  addInstructor: (semester, courseId, instructor) => api.post('/course/instructor', null, { params: { semester, course_id: courseId, instructor } }),
  removeInstructor: (semester, courseId, instructor) => api.delete('/course/instructor', { params: { semester, course_id: courseId, instructor } }),
};

// Assignment Management Service
export const assignmentService = {
  getAssignments: (courseId, semester, includeQuestions = false) =>
    api.get('/assignments', { params: { course_id: courseId, semester: semester, include_questions: includeQuestions } }),
  getAssignment: (courseId, semester, assignmentId, includeQuestions = true) =>
    api.get(`/assignments/${String(assignmentId)}`, { params: { course_id: courseId, semester: semester, include_questions: includeQuestions } }),
  createAssignment: (semester, courseId, assignmentData) =>
    api.post('/assignment', assignmentData, { params: { semester: semester, course_id: courseId } }),
  deleteAssignment: (courseId, semester, assignmentId) =>
    api.delete(`/assignments/${String(assignmentId)}`, { params: { course_id: courseId, semester: semester } }),
  updateAssignmentMetadata: (semester, courseId, assignmentId, updateData) =>
    api.patch(`/assignments/${String(assignmentId)}`, updateData, { params: { semester: semester, course_id: courseId } }),
  addQuestion: (semester, courseId, assignmentId, addQuestionPayload) =>
    api.post(`/assignments/${String(assignmentId)}/questions`, addQuestionPayload, { params: { semester: semester, course_id: courseId } }),
  removeQuestion: (semester, courseId, assignmentId, questionIndex) =>
    api.delete(`/assignments/${String(assignmentId)}/questions/${questionIndex}`, { params: { semester: semester, course_id: courseId } }),
  editQuestion: (semester, courseId, assignmentId, questionIndex, editQuestionPayload) =>
    api.put(`/assignments/${String(assignmentId)}/questions/${questionIndex}`, editQuestionPayload, { params: { semester: semester, course_id: courseId } }),
  modifyQuestionOrder: (semester, courseId, assignmentId, reorderPayload) =>
    api.patch(`/assignments/${String(assignmentId)}/questions/order`, reorderPayload, { params: { semester: semester, course_id: courseId } }),
};

// Student Response & Grading Service
export const responseService = {
  uploadResponse: (responseData) => api.post('/response', responseData),
  replaceResponse: (responseData) => api.put('/response', responseData),
  deleteResponse: (semester, courseId, assignmentId, studentId, questionIndex = null) =>
    api.delete('/response', { params: { semester, course_id: courseId, assignment_id: String(assignmentId), student_id: studentId, question_index: questionIndex } }),
  getResponses: (semester, courseId, assignmentId, questionIndex = null, studentId = null) =>
    api.get('/responses', { params: { semester, course_id: courseId, assignment_id: String(assignmentId), question_index: questionIndex, student_id: studentId } }),
  gradeSpecific: (semester, courseId, assignmentId, studentIds, questionIndex = null) =>
    api.post('/response/grade/specific', { student_ids: studentIds }, { params: { semester, course_id: courseId, assignment_id: String(assignmentId), question_index: questionIndex } }),
  gradeUngraded: (semester, courseId, assignmentId, questionIndex = null) =>
    api.post('/response/grade/ungraded', null, { params: { semester, course_id: courseId, assignment_id: String(assignmentId), question_index: questionIndex } }),
  gradeAll: (semester, courseId, assignmentId, questionIndex = null) =>
    api.post('/response/grade/all', null, { params: { semester, course_id: courseId, assignment_id: String(assignmentId), question_index: questionIndex } }),
};

// Course Material Service
export const materialService = {
  getMaterials: (semester, courseId) => api.get('/course_materials', { params: { semester, course_id: courseId } }),
  getMaterial: (semester, courseId, materialId) => api.get('/course_material', { params: { semester, course_id: courseId, material_id: materialId } }), // Assuming materialId is int/string
  uploadMaterial: (materialData) => api.post('/course_material', materialData), // Often FormData
  updateMaterial: (materialData) => api.patch('/course_material', materialData),
  deleteMaterial: (semester, courseId, materialId) => api.delete('/course_material', { params: { semester, course_id: courseId, material_id: materialId } }),
};

// ============================================
// Rubric Management Service - ALIGNED WITH PYTHON CODE
// ============================================
export const rubricService = {
  /**
   * Retrieves the rubric for a specified assignment.
   * Corresponds to: GET /rubric (Query Parameters)
   * @param {string} semester - Semester of the course.
   * @param {string} courseId - Identifier of the course.
   * @param {string | number} assignmentId - Identifier of the assignment.
   * @param {number | null} [questionIndex=null] - Optional question index to retrieve a specific sub-rubric.
   * @returns {Promise<AxiosResponse<any>>} - The Axios response containing the Rubric object.
   */
  getRubric: (semester, courseId, assignmentId, questionIndex = null) => {
    // Construct query parameters object
    const params = {
        semester: semester,
        course_id: courseId,
        assignment_id: String(assignmentId), // Ensure assignment ID is a string
    };
    // Add question_index only if it's a valid number
    if (questionIndex !== null && typeof questionIndex === 'number' && !isNaN(questionIndex)) {
        params.question_index = questionIndex;
    }
    // Make GET request with parameters
    return api.get('/rubric', { params });
  },

  /**
   * Creates or updates (upserts) a rubric for an assignment.
   * Corresponds to: PUT /rubric (Request Body)
   * @param {object} rubricData - The full Rubric object matching the backend Pydantic model.
   *                              Must include semester, course_id, and assignment_id (as string).
   * @returns {Promise<AxiosResponse<any>>} - The Axios response containing the saved Rubric object.
   */
  createRubric: (rubricData) => {
    // The rubricData object passed from the component should already match the Pydantic structure.
    // Add a safety check for assignment_id type just in case.
    const payload = { ...rubricData };
    if (payload.assignment_id !== undefined && typeof payload.assignment_id !== 'string') {
        console.warn("rubricService.createRubric: assignment_id was not a string, converting.");
        payload.assignment_id = String(payload.assignment_id);
    }
    // Make PUT request, sending the payload as the request body
    return api.put('/rubric', payload);
  },

  /**
   * Requests AI-generated suggestions for enhancing or creating a rubric.
   * Corresponds to: GET /ai_rubric (Query Parameters)
   * @param {string} semester - Semester of the course.
   * @param {string} courseId - Identifier of the course.
   * @param {string | number} assignmentId - Identifier of the assignment.
   * @param {string | null} [instructions=null] - Optional specific instructions for the AI.
   * @returns {Promise<AxiosResponse<any>>} - The Axios response containing the AI-suggested Rubric object.
   */
  getAIRubric: (semester, courseId, assignmentId, instructions = null) => {
    // Construct query parameters object
    const params = {
        semester: semester,
        course_id: courseId,
        assignment_id: String(assignmentId), // Ensure assignment ID is a string
    };
    // Add instructions only if it's a non-empty string
    if (instructions && typeof instructions === 'string' && instructions.trim()) {
        params.instructions = instructions.trim();
    }
    // Make GET request with parameters
    return api.get('/ai_rubric', { params });
  }
};
// ============================================
// End Rubric Management Service
// ============================================

// User Management Service
export const userService = {
  // Corresponds to GET /user (or similar endpoint defined in your backend)
  getUserData: () => api.get('/user'),
  // Corresponds to PATCH /user (or similar)
  updateUserPreferences: (preferencesData) => api.patch('/user', preferencesData),
};

// --- SWR Hooks ---

// Helper function to create stable SWR keys from query parameters
const createSwrKey = (basePath, params) => {
  if (!params || Object.keys(params).length === 0) return basePath;
  // Filter out null/undefined, sort keys, convert values to string
  const sortedParams = Object.entries(params)
    .filter(([, value]) => value !== null && value !== undefined)
    .sort(([keyA], [keyB]) => keyA.localeCompare(keyB))
    .map(([key, value]) => [key, String(value)]); // Ensure string values

  if (sortedParams.length === 0) return basePath;
  const queryString = new URLSearchParams(sortedParams).toString();
  return `${basePath}?${queryString}`;
};

// --- Standard SWR Hook Options ---
const swrOptions = {
    revalidateOnFocus: true,
    revalidateOnReconnect: true,
    shouldRetryOnError: true, // Default retry logic
    dedupingInterval: 2000, // Avoid rapid refetching
};

// --- SWR Hook Options Specific to Rubric ---
const swrRubricOptions = {
    ...swrOptions,
    revalidateOnFocus: false, // Less aggressive revalidation for rubric editor
    revalidateOnReconnect: false,
    shouldRetryOnError: (error) => {
        // Do NOT retry on 404 errors for rubrics
        if (error?.isNotFoundError) return false;
        return true; // Retry other errors
    },
};

// --- SWR Hooks Definitions ---

// Hook for fetching user data
export const useUser = () => {
  const swrKey = '/user'; // The API endpoint for user data
  const { data, error, mutate, isLoading, isValidating } = useSWR(swrKey, fetcher, swrOptions);
  return {
    user: data, // The user object or undefined
    isLoading: isLoading, // True during initial fetch
    isValidating: isValidating, // True during revalidation
    isError: !!error, // Boolean indicating if an error occurred
    error: error, // The actual error object
    mutate, // Function to trigger revalidation
  };
};

// Hook for fetching courses
export const useCourses = (semester = null) => {
  const swrKey = createSwrKey('/courses', semester ? { semester } : {});
  const { data, error, mutate, isLoading, isValidating } = useSWR(swrKey, fetcher, swrOptions);
  return {
      courses: data,
      isLoading,
      isValidating,
      isError: !!error,
      error,
      mutate
  };
};

// Hook for fetching assignments
export const useAssignments = (courseId, semester, includeQuestions = false) => {
  const shouldFetch = !!(semester && courseId);
  const swrKey = shouldFetch
    ? createSwrKey('/assignments', { course_id: courseId, semester: semester, include_questions: includeQuestions })
    : null;
  const { data, error, mutate, isLoading, isValidating } = useSWR(swrKey, fetcher, swrOptions);
  return {
    assignments: data,
    isLoading: isLoading && shouldFetch,
    isValidating: isValidating && shouldFetch,
    isError: !!error,
    error: error,
    mutate,
  };
};

// Hook for fetching a specific rubric
export const useRubric = (semester, courseId, assignmentId) => {
  const assignmentIdStr = (assignmentId !== null && assignmentId !== undefined) ? String(assignmentId) : null;
  const shouldFetch = !!(semester && courseId && assignmentIdStr);
  // API parameters for the GET /rubric call
  const apiParams = { semester, course_id: courseId, assignment_id: assignmentIdStr };
  // SWR key based on the API parameters
  const swrKey = shouldFetch ? createSwrKey('/rubric', apiParams) : null;

  const { data, error, mutate, isLoading, isValidating } = useSWR(
      swrKey,
      fetcher,
      swrRubricOptions // Use specific options for rubric fetching
  );

  // Determine if the error is specifically a 404
  const isNotFoundError = !!error?.isNotFoundError;

  // Return null for data if 404, otherwise the data
  const rubricData = isNotFoundError ? null : data;
  // Return null for error if 404, otherwise the error object
  const finalError = isNotFoundError ? null : error;

  return {
    rubric: rubricData, // Rubric data or null
    isLoading: isLoading && shouldFetch && !error, // Loading state
    isValidating: isValidating && shouldFetch, // Revalidating state
    isError: !!finalError, // True if error other than 404
    error: finalError, // Error object (excluding 404)
    isNotFound: isNotFoundError, // Explicit flag for 404
    mutate, // SWR mutate function
  };
};

// Hook for fetching course materials
export const useMaterials = (semester, courseId) => {
   const shouldFetch = !!(semester && courseId);
   const swrKey = shouldFetch ? createSwrKey('/course_materials', { semester, course_id: courseId }) : null;
   const { data, error, mutate, isLoading, isValidating } = useSWR(swrKey, fetcher, swrOptions);
   return {
       materials: data,
       isLoading: isLoading && shouldFetch,
       isValidating: isValidating && shouldFetch,
       isError: !!error,
       error: error,
       mutate
    };
};

// IMPORTANT: NO final `export { ... }` block needed here.
// Each service and hook is exported individually using `export const`.