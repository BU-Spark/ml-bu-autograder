/**
 * API service layer for interacting with the BU MET Autograder backend
 * Provides functions for making API calls and custom SWR hooks
 */

import axios from 'axios';
import useSWR from 'swr';
// Assuming these are correctly defined in your project's ./config.js
import { BACKEND_URL, API_PREFIX, LIMITS, ERROR_MESSAGES } from './config';
import { signOut } from 'next-auth/react';

// Create an Axios instance with default config
const api = axios.create({
  baseURL: `${BACKEND_URL}${API_PREFIX}`,
  timeout: LIMITS.apiTimeout,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    // TODO: Replace with your actual token retrieval logic
    const token = "i_testify_cats_are_better"; // Placeholder token
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response, // Pass successful responses along
  (error) => {
    // Initialize custom error object if response exists
    let customError = new Error(ERROR_MESSAGES.general);
    if (error.response) {
        const { status, data } = error.response;
        let errorMessage = ERROR_MESSAGES.general;

        switch (status) {
            case 400:
                console.error('Bad request error:', error.response);
                if (data?.detail && Array.isArray(data.detail)) {
                    errorMessage = data.detail.map(err => `${err.loc.join('->')}: ${err.msg}`).join('; ');
                } else if (data?.detail && typeof data.detail === 'string') {
                    errorMessage = data.detail;
                } else {
                    errorMessage = ERROR_MESSAGES.api?.badRequest || "Bad Request";
                }
                customError = new Error(errorMessage);
                break; // Break after setting message
            case 401:
                console.error('Authentication error:', error.response);
                signOut({ callbackUrl: '/login' }); // Trigger sign out
                errorMessage = data?.detail || ERROR_MESSAGES.auth?.unauthorized || "Authentication failed.";
                customError = new Error(errorMessage);
                break;
            case 403:
                console.error('Forbidden error:', error.response);
                errorMessage = data?.detail || ERROR_MESSAGES.auth?.forbidden || "Permission denied.";
                customError = new Error(errorMessage);
                break;
            case 404:
                console.error('Not found error:', error.response);
                errorMessage = data?.detail || ERROR_MESSAGES.api?.notFound || "Resource not found.";
                customError = new Error(errorMessage);
                break;
            case 409:
                console.error('Conflict error:', error.response);
                errorMessage = data?.detail || "Resource conflict.";
                customError = new Error(errorMessage);
                break;
             case 422: // Unprocessable Entity (Validation Errors)
                console.error('Validation error:', error.response);
                 if (data?.detail && Array.isArray(data.detail)) {
                    // Format validation errors nicely
                    errorMessage = "Validation Failed: " + data.detail.map(err => `${err.loc.join('.')} - ${err.msg}`).slice(0, 3).join('; ');
                    if (data.detail.length > 3) errorMessage += '...';
                } else if (data?.detail && typeof data.detail === 'string') {
                    errorMessage = data.detail; // Handle simple string detail
                } else {
                     errorMessage = ERROR_MESSAGES.api?.validationError || "Validation failed.";
                }
                customError = new Error(errorMessage);
                break;
            case 500:
            case 502:
                console.error('Server error:', error.response);
                errorMessage = data?.detail || ERROR_MESSAGES.api?.serverError || "Server error.";
                customError = new Error(errorMessage);
                break;
            default:
                console.error('API error:', error.response);
                errorMessage = data?.detail || ERROR_MESSAGES.general;
                customError = new Error(errorMessage);
                break;
        }
        // Attach the original response to the custom error object
        customError.response = error.response;

    } else if (error.request) {
        // Network error
        console.error('Network error:', error.request);
        customError = new Error(ERROR_MESSAGES.network || "Network error. Check connection.");
        // Add a property to distinguish network errors if needed
        customError.isNetworkError = true;
    } else {
        // Other errors (e.g., request setup)
        console.error('Request configuration error:', error.message);
        customError = new Error(error.message || ERROR_MESSAGES.general);
    }

    return Promise.reject(customError); // Reject with the processed error
  }
);


// SWR fetcher function using our API instance
const fetcher = async (url) => {
  // SWR key is the URL. Axios instance has baseURL configured.
  const response = await api.get(url);
  return response.data; // Return only the data for SWR
};

// API service methods definitions remain largely the same,
// but ensure they return response.data if not using a helper that already does.

// Helper function for consistent data extraction (optional but recommended)
const handleResponse = (axiosPromise) => {
    return axiosPromise.then(response => response.data)
                       .catch(error => { throw error; }); // Let interceptor handle error formatting
}

// --- AUTH SERVICE ---
export const authService = {
  getGoogleOAuthUrl: () => handleResponse(api.get('/auth/google_oauth_url')),
  googleOAuth: (params) => handleResponse(api.get('/auth/google_oauth', { params })),
  createToken: (params) => handleResponse(api.post('/auth/token', null, { params })),
  listTokens: () => handleResponse(api.get('/auth/tokens')),
  deleteToken: (params) => handleResponse(api.delete('/auth/token', { params })),
};

// --- COURSE SERVICE ---
export const courseService = {
  getCourses: (params) => handleResponse(api.get('/courses', { params })),
  getCourse: (params) => handleResponse(api.get('/course', { params })),
  createCourse: (courseData) => handleResponse(api.post('/course', courseData)),
  deleteCourse: (params) => handleResponse(api.delete('/course', { params })),
  transferCourse: (params) => handleResponse(api.patch('/course/transfer', null, { params })),
  addInstructor: (params) => handleResponse(api.post('/course/instructor', null, { params })),
  removeInstructor: (params) => handleResponse(api.delete('/course/instructor', { params })),
};

// --- ASSIGNMENT SERVICE ---
export const assignmentService = {
  /**
   * List assignments for a course.
   * @param {object} params
   * @param {string} params.course_id
   * @param {string} params.semester
   * @param {boolean} [params.include_questions=true]
   * @returns {Promise<AssignmentDef[]>}
   */
  // *** CORRECTED IMPLEMENTATION ***
  getAssignments: async (params) => {
    const response = await api.get('/assignments', { params });
    return response.data; // Directly return the data property
  },

  /**
   * Get a specific assignment.
   * @param {object} params
   * @param {string} params.course_id
   * @param {string} params.semester
   * @param {string} params.assignment_id
   * @param {boolean} [params.include_questions=true]
   * @returns {Promise<AssignmentDef>}
   */
  // *** CORRECTED IMPLEMENTATION ***
   getAssignment: async (params) => {
    const response = await api.get('/assignment', { params });
    return response.data; // Directly return the data property
  },

  /**
   * Create a new assignment.
   * @param {AssignmentDef} assignmentData - The assignment to create (request body).
   * @returns {Promise<AssignmentDef>}
   */
   // *** CORRECTED IMPLEMENTATION ***
   createAssignment: async (assignmentData) => {
       // POST request sends data as the second argument
      const response = await api.post('/assignment', assignmentData);
      return response.data; // Return the created assignment data
  },

  /**
   * Delete an assignment.
   * @param {object} params
   * @param {string} params.semester
   * @param {string} params.course_id
   * @param {string} params.assignment_id
   * @returns {Promise<object>} - Empty object on success.
   */
   // *** CORRECTED IMPLEMENTATION ***
   deleteAssignment: async (params) => {
       // DELETE requests usually don't have a body, params are query params
      const response = await api.delete('/assignment', { params });
      return response.data; // Often empty {}
  },

  /**
   * Add a question to an assignment.
   * @param {AddQuestionRequestDef} questionData - Data for the new question (request body).
   * @returns {Promise<object>} - Empty object on success.
   */
   // *** CORRECTED IMPLEMENTATION ***
   addQuestion: async (questionData) => {
       // PATCH request sends data as the second argument
      const response = await api.patch('/assignment/add_question', questionData);
      return response.data; // Often empty {}
  },

  /**
   * Remove a question from an assignment.
   * @param {object} params
   * @param {string} params.semester
   * @param {string} params.course_id
   * @param {string} params.assignment_id
   * @param {number} params.question_index
   * @returns {Promise<object>} - Empty object on success.
   */
   // *** CORRECTED IMPLEMENTATION ***
   removeQuestion: async (params) => {
      // PATCH request, but no body specified in spec, only query params
      const response = await api.patch('/assignment/remove_question', null, { params });
      return response.data; // Often empty {}
  },

  /**
   * Edit an existing question in an assignment.
   * @param {EditQuestionRequestDef} questionData - Data for editing the question (request body).
   * @returns {Promise<object>} - Empty object on success.
   */
   // *** CORRECTED IMPLEMENTATION ***
   editQuestion: async (questionData) => {
       // PATCH request sends data as the second argument
      const response = await api.patch('/assignment/edit_question', questionData);
      return response.data; // Often empty {}
  },

  /**
   * Modify the order of questions in an assignment.
   * @param {ModifyOrderRequestDef} orderData - New order of question indexes (request body).
   * @returns {Promise<object>} - Empty object on success.
   */
   // *** CORRECTED IMPLEMENTATION ***
   modifyQuestionOrder: async (orderData) => {
       // PATCH request sends data as the second argument
      const response = await api.patch('/assignment/modify_order', orderData);
      return response.data; // Often empty {}
  },
};

// --- RESPONSE SERVICE --- (Assuming these are okay, apply similar fix if needed)
export const responseService = {
  uploadResponse: (responseData) => handleResponse(api.post('/response', responseData)),
  replaceResponse: (responseData) => handleResponse(api.put('/response', responseData)),
  deleteResponse: (params) => handleResponse(api.delete('/response', { params })),
  getSingleResponse: (params) => handleResponse(api.get('/response', { params })),
  getResponses: (params) => handleResponse(api.get('/responses', { params })),
  gradeSpecific: (params) => handleResponse(api.post('/response/grade/specific', null, { params })),
  gradeUngraded: (params) => handleResponse(api.post('/response/grade/ungraded', null, { params })),
  gradeAll: (params) => handleResponse(api.post('/response/grade/all', null, { params })),
};

// --- MATERIAL SERVICE --- (Assuming these are okay)
export const materialService = {
  getMaterials: (params) => handleResponse(api.get('/course_materials', { params })),
  getMaterial: (params) => handleResponse(api.get('/course_material', { params })),
  uploadMaterial: (materialData) => handleResponse(api.post('/course_material', materialData)),
  updateMaterial: (materialData) => handleResponse(api.patch('/course_material', materialData)),
  deleteMaterial: (params) => handleResponse(api.delete('/course_material', { params })),
};

// --- RUBRIC SERVICE --- (Assuming these are okay)
export const rubricService = {
  getRubric: (params) => handleResponse(api.get('/rubric', { params })),
  createOrUpdateRubric: (rubricData) => handleResponse(api.put('/rubric', rubricData)),
  getAIRubric: (params) => handleResponse(api.get('/ai_rubric', { params })),
};

// --- USER SERVICE --- (Assuming these are okay)
export const userService = {
  getUserData: () => handleResponse(api.get('/user')),
  updateUserPreferences: (preferencesData) => handleResponse(api.patch('/user', preferencesData)),
};


// --- SWR Hooks --- (Ensure they use the corrected service methods or the fetcher)

export const useUser = () => {
  // Use the fetcher which correctly returns response.data
  const { data, error, mutate, isLoading } = useSWR('/user', fetcher);
  return { user: data, isLoading, isError: error, mutate };
};

export const useCourses = (semester) => {
  const url = semester ? `/courses?semester=${encodeURIComponent(semester)}` : '/courses';
   // Use the fetcher which correctly returns response.data
  const { data, error, mutate, isLoading } = useSWR(url, fetcher);
  return { courses: data, isLoading, isError: error, mutate };
};

// Note: The useAssignments hook might become less necessary if the page
// always fetches the list in useEffect, but it can be kept for other uses
// or adapted if needed. Ensure the key matches what fetcher expects.
export const useAssignments = (courseId, semester, includeQuestions = true) => {
  const key = (courseId && semester)
    ? `/assignments?course_id=${encodeURIComponent(courseId)}&semester=${encodeURIComponent(semester)}&include_questions=${includeQuestions}`
    : null;
   // Use the fetcher which correctly returns response.data
  const { data, error, mutate, isLoading } = useSWR(key, fetcher);
  return { assignments: data, isLoading, isError: error, mutate };
};

export const useRubric = (semester, courseId, assignmentId, questionIndex = null) => {
  let key = null;
  if (semester && courseId && assignmentId) {
    const params = new URLSearchParams({ semester: semester, course_id: courseId, assignment_id: assignmentId });
    if (questionIndex !== null && questionIndex !== undefined) { params.append('question_index', String(questionIndex)); }
    key = `/rubric?${params.toString()}`;
  }
   // Use the fetcher which correctly returns response.data
  const { data, error, mutate, isLoading } = useSWR(key, fetcher);
  return { rubric: data, isLoading, isError: error, mutate };
};

export const useMaterials = (courseId, semester) => {
  const key = (courseId && semester) ? `/course_materials?course_id=${encodeURIComponent(courseId)}&semester=${encodeURIComponent(semester)}` : null;
   // Use the fetcher which correctly returns response.data
  const { data, error, mutate, isLoading } = useSWR(key, fetcher);
  return { materials: data, isLoading, isError: error, mutate };
};

// Exporting the raw instance might still be needed for specific cases like file uploads
// export { api as rawAxiosInstance };
export default api; // Default export might not be used if named exports are preferred