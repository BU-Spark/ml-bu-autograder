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
  baseURL: `${BACKEND_URL}${API_PREFIX}`, // Ensure API_PREFIX includes trailing / if needed
  timeout: LIMITS.apiTimeout,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    // Use sessionStorage or a more robust state management solution
    // IMPORTANT: Replace this static token with dynamic token retrieval
    //const token = typeof window !== 'undefined' ? sessionStorage.getItem('authToken') : null; // Example: Get from sessionStorage
    const token = "123bob"; // Example static token (REMOVE IN PRODUCTION)

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    } else {
       // Log warning only if it's not an auth-related endpoint itself
       if (!config.url?.includes('/auth/')) {
            console.warn(`No 'authToken' found for request to ${config.url}. Request sent without Authorization header.`);
       }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const { status, data } = error.response;
      // Use data?.detail first, then error.message as fallback
      const detailErrorMessage = Array.isArray(data?.detail)
                                 ? data.detail.map(err => `${err.loc?.join('.')} - ${err.msg}`).join('; ')
                                 : typeof data?.detail === 'string' ? data.detail : null;
      const errorMessage = detailErrorMessage || error.message || `Request failed with status code ${status}`;

      switch (status) {
        case 401:
          console.error('Authentication error (401):', errorMessage);
          // Redirect to login only on the client-side and if not already on auth pages
          if (typeof window !== 'undefined' && window.location.pathname !== '/login' && !window.location.pathname.startsWith('/auth')) {
             // Consider delaying signout slightly to allow error message display if needed
             signOut({ callbackUrl: '/login' });
          }
          // Reject with a user-friendly message
          return Promise.reject(new Error(ERROR_MESSAGES.auth.unauthorized));
        case 403:
          console.error('Forbidden error (403):', errorMessage);
          return Promise.reject(new Error(errorMessage || ERROR_MESSAGES.auth.forbidden));
        case 404:
          console.error('Not found error (404):', errorMessage);
          return Promise.reject(new Error(errorMessage || ERROR_MESSAGES.api.notFound));
        case 400: case 409: case 422: // Client-side validation/logic errors
          console.error(`Client error (${status}):`, errorMessage);
          // Use the detailed message if available, otherwise provide a generic one
          return Promise.reject(new Error(errorMessage || `Invalid request (${status}).`));
        case 500: case 501: case 502: case 503: // Server-side errors
          console.error(`Server error (${status}):`, errorMessage);
          return Promise.reject(new Error(errorMessage || ERROR_MESSAGES.api.serverError));
        default:
          console.error(`API error (${status}):`, errorMessage);
          return Promise.reject(new Error(errorMessage || ERROR_MESSAGES.general));
      }
    } else if (error.request) {
      // Network error (no response received)
      console.error('Network error:', error.request);
      return Promise.reject(new Error(ERROR_MESSAGES.network));
    } else {
      // Error setting up the request
      console.error('Request configuration error:', error.message);
      return Promise.reject(new Error(ERROR_MESSAGES.general));
    }
  }
);

// SWR fetcher function using our API instance
const fetcher = async (url) => {
  const response = await api.get(url);
  return response.data; // Axios automatically handles JSON parsing
};

// --- API Service Methods ---

// Authentication
export const authService = {
  googleOAuth: (code) => api.get('/auth/google_oauth', { params: { code } }),
  getGoogleOAuthUrl: () => api.get('/auth/google_oauth_url'),
  createToken: (tokenName, tokenExpiry = null) => api.post('/auth/token', null, { params: { token_name: tokenName, token_expiry: tokenExpiry } }),
  listTokens: () => api.get('/auth/tokens'),
  deleteToken: (tokenName) => api.delete('/auth/token', { params: { token_name: tokenName } }),
};

// Course management
export const courseService = {
  getCourses: (semester = null) => api.get('/courses', { params: { semester } }),
  getCourse: (courseId, semester) => api.get('/course', { params: { course_id: courseId, semester } }),
  createCourse: (courseData) => api.post('/course', courseData),
  deleteCourse: (courseId, semester) => api.delete('/course', { params: { course_id: courseId, semester } }),
  transferCourse: (currentSemester, currentCourseId, copyFromSemester, copyFromCourseId) => api.patch('/course/transfer', null, { params: { current_semester: currentSemester, current_course_id: currentCourseId, copy_from_course_semester: copyFromSemester, copy_from_course_id: copyFromCourseId, } }),
  addInstructor: (semester, courseId, instructor) => api.post('/course/instructor', null, { params: { semester, course_id: courseId, instructor } }),
  removeInstructor: (semester, courseId, instructor) => api.delete('/course/instructor', { params: { semester, course_id: courseId, instructor } }),
};

// ============================================
// Assignment management - CORRECTED
// ============================================
export const assignmentService = {
  // GET /assignments - Looks OK
  getAssignments: (courseId, semester, includeQuestions = false) =>
    api.get('/assignments', { params: { course_id: courseId, semester: semester, include_questions: includeQuestions } }),

  // GET /assignments/{assignment_id} - Looks OK
  getAssignment: (courseId, semester, assignmentId, includeQuestions = true) =>
    api.get(`/assignments/${String(assignmentId)}`, { // Ensure string ID in path
      params: {
        course_id: courseId,
        semester: semester,
        include_questions: includeQuestions
      }
    }),

  // *** CORRECTED: POST /assignment ***
  // Pass semester & courseId for query params, assignmentData for the body
  createAssignment: (semester, courseId, assignmentData) => {
    // assignmentData should contain the full Assignment structure expected by the backend Body,
    // including the placeholder question_index values if needed for validation.
    return api.post(
      '/assignment', // Keep path (or change if backend router uses /assignments)
      assignmentData, // This is the Request Body
      { // This object contains config, including 'params' for Query Parameters
        params: {
          semester: semester,
          course_id: courseId
        }
      }
    );
  },

  // DELETE /assignments/{assignment_id} - Looks OK
  deleteAssignment: (courseId, semester, assignmentId) =>
    api.delete(`/assignments/${String(assignmentId)}`, { // Ensure string ID in path
       params: { course_id: courseId, semester: semester }
    }),

  // PATCH /assignments/{assignment_id} - Looks OK
  updateAssignmentMetadata: (semester, courseId, assignmentId, updateData) =>
    api.patch(`/assignments/${String(assignmentId)}`, updateData, { // Ensure string ID in path
      params: {
        semester: semester,
        course_id: courseId
      }
    }),

  // *** CORRECTED: POST /assignments/{assignment_id}/questions ***
  // Ensure payload structure matches backend's AddQuestionRequest { "question": Question }
  // where Question requires question_index (using placeholder from frontend)
  addQuestion: (semester, courseId, assignmentId, addQuestionPayload) => {
    // addQuestionPayload received from frontend should already be:
    // { question: { question_index: 0, question_text: "...", ... } }
    // If not, construct it here:
    /* const payload = {
        question: {
            question_index: addQuestionPayload.question_index ?? 0, // Placeholder needed for validation
            question_text: addQuestionPayload.question_text,
            question_graphics_figures: addQuestionPayload.question_graphics_figures ?? null
        }
    }; */
    return api.post(
      `/assignments/${String(assignmentId)}/questions`,
      addQuestionPayload, // Send the structured payload as Body
      { // Config object for query parameters
        params: {
          semester: semester,
          course_id: courseId,
        }
      }
    );
  },

  // DELETE /assignments/{assignment_id}/questions/{question_index} - Looks OK
  removeQuestion: (semester, courseId, assignmentId, questionIndex) =>
    api.delete(`/assignments/${String(assignmentId)}/questions/${questionIndex}`, { // Ensure string ID in path
       params: {
         semester: semester,
         course_id: courseId,
       }
    }),

  // *** CORRECTED: PUT /assignments/{assignment_id}/questions/{question_index} ***
  // Ensure payload structure matches backend's EditQuestionRequest { "question": Question }
  // where Question requires the correct question_index
  editQuestion: (semester, courseId, assignmentId, questionIndex, editQuestionPayload) => {
    // editQuestionPayload received from frontend should already be:
    // { question: { question_index: N, question_text: "...", ... } }
    // If not, construct it here:
    /* const payload = {
        question: {
            ...editQuestionPayload, // Contains text, graphics etc.
            question_index: questionIndex // Ensure correct index is in payload
        }
    }; */
    return api.put(
      `/assignments/${String(assignmentId)}/questions/${questionIndex}`,
      editQuestionPayload, // Send the structured payload as Body
      { // Config object for query parameters
        params: {
          semester: semester,
          course_id: courseId,
        }
      }
    );
  },

  // *** CORRECTED: PATCH /assignments/{assignment_id}/questions/order ***
  // Pass reorderPayload directly (should be { questions: [...] } from frontend)
  modifyQuestionOrder: (semester, courseId, assignmentId, reorderPayload) => {
    // reorderPayload received from frontend should be:
    // { questions: [{ question_index: N }, { question_index: M }, ...] }
    // This structure must match the backend's ModifyOrderRequest model
    return api.patch(
        `/assignments/${String(assignmentId)}/questions/order`,
        reorderPayload, // Send the received object directly as Request Body
        { // Config object for query parameters
            params: {
                semester: semester,
                course_id: courseId,
            }
        }
    );
  }
};
// ============================================
// End Assignment Management Corrections
// ============================================


// Student response and Grading management
export const responseService = {
  // Assuming these paths are correct per backend
  uploadResponse: (responseData) => api.post('/response', responseData),
  replaceResponse: (responseData) => api.put('/response', responseData),
  deleteResponse: (semester, courseId, assignmentId, studentId, questionIndex = null) =>
    api.delete('/response', { params: { semester: semester, course_id: courseId, assignment_id: String(assignmentId), student_id: studentId, question_index: questionIndex } }), // Ensure string ID
  getResponses: (semester, courseId, assignmentId, questionIndex = null, studentId = null) =>
    api.get('/responses', { params: { semester: semester, course_id: courseId, assignment_id: String(assignmentId), question_index: questionIndex, student_id: studentId } }), // Ensure string ID
  gradeSpecific: (semester, courseId, assignmentId, studentIds, questionIndex = null) =>
    api.post('/response/grade/specific', { student_ids: studentIds } , { // Send student IDs in body now if needed
        params: { semester: semester, course_id: courseId, assignment_id: String(assignmentId), question_index: questionIndex } // Keep others in params
    }),
  gradeUngraded: (semester, courseId, assignmentId, questionIndex = null) =>
    api.post('/response/grade/ungraded', null, { params: { semester: semester, course_id: courseId, assignment_id: String(assignmentId), question_index: questionIndex } }), // Ensure string ID
  gradeAll: (semester, courseId, assignmentId, questionIndex = null) =>
    api.post('/response/grade/all', null, { params: { semester: semester, course_id: courseId, assignment_id: String(assignmentId), question_index: questionIndex } }), // Ensure string ID
};

// Course material management
export const materialService = {
  // Assuming these paths and ID types (int) are correct per backend
  getMaterials: (semester, courseId) => api.get('/course_materials', { params: { semester: semester, course_id: courseId } }),
  getMaterial: (semester, courseId, materialId) => api.get('/course_material', { params: { semester: semester, course_id: courseId, material_id: materialId } }),
  uploadMaterial: (materialData) => api.post('/course_material', materialData), // Often uses FormData, check backend/axios config
  updateMaterial: (materialData) => api.patch('/course_material', materialData),
  deleteMaterial: (semester, courseId, materialId) => api.delete('/course_material', { params: { semester: semester, course_id: courseId, material_id: materialId } }),
};

// Rubric management
export const rubricService = {
  // GET /rubric (Backend expects assignment_id: str query param)
  getRubric: (semester, courseId, assignmentId, questionIndex) =>
    api.get('/rubric', {
      params: {
        semester: semester,
        course_id: courseId,
        assignment_id: String(assignmentId), // Ensure string
      }
    }),

  // PUT /rubric (Body: Rubric - ensure assignment_id: str)
  createRubric: (rubricData) => {
      // Ensure assignment_id within the rubricData object is a string if needed
      const payload = { ...rubricData };
      if (payload.assignment_id !== undefined) {
          payload.assignment_id = String(payload.assignment_id);
      }
      return api.put('/rubric', payload);
  },


  // GET /ai_rubric (Backend expects assignment_id: str query param)
  getAIRubric: (semester, courseId, assignmentId, instructions = null) =>
    api.get('/ai_rubric', {
      params: {
        semester: semester,
        course_id: courseId,
        assignment_id: String(assignmentId), // Ensure string
        instructions: instructions
      }
    }),
};

// User management
export const userService = {
  getUserData: () => api.get('/user'),
  updateUserPreferences: (preferencesData) => api.patch('/user', preferencesData),
};

// --- SWR Hooks ---

// Helper function to create stable SWR keys from params
const createSwrKey = (basePath, params) => {
  if (!params) return basePath;
  // Sort params for key stability
  const sortedParams = Object.entries(params)
    .filter(([key, value]) => value !== null && value !== undefined) // Filter out null/undefined
    .sort(([keyA], [keyB]) => keyA.localeCompare(keyB));
  const queryString = new URLSearchParams(sortedParams).toString();
  return queryString ? `${basePath}?${queryString}` : basePath;
};

export const useUser = () => {
  const { data, error, mutate, isLoading } = useSWR('/user', fetcher);
  return { user: data, isLoading, isError: error, mutate, };
};

export const useCourses = (semester = null) => {
  const swrKey = createSwrKey('/courses', { semester });
  const { data, error, mutate, isLoading } = useSWR(swrKey, fetcher);
  return { courses: data, isLoading, isError: error, mutate, };
};

export const useAssignments = (courseId, semester, includeQuestions = false) => {
  const shouldFetch = semester && courseId;
  const swrKey = shouldFetch
    ? createSwrKey('/assignments', { course_id: courseId, semester: semester, include_questions: includeQuestions })
    : null;
  const { data, error, mutate, isLoading } = useSWR(swrKey, fetcher);
  return { assignments: data, isLoading: isLoading && shouldFetch, isError: error, mutate, };
};


export const useRubric = (semester, courseId, assignmentId, questionIndex = null) => {
  const assignmentIdStr = assignmentId !== null && typeof assignmentId !== 'undefined' ? String(assignmentId) : null;
  const shouldFetch = semester && courseId && assignmentIdStr;
  const swrKey = shouldFetch
     ? createSwrKey('/rubric', { semester, course_id: courseId, assignment_id: assignmentIdStr, question_index: questionIndex })
     : null;
  const { data, error, mutate, isLoading } = useSWR(swrKey, fetcher);
  return { rubric: data, isLoading: isLoading && shouldFetch, isError: error, mutate, };
};


export const useMaterials = (semester, courseId) => {
   const shouldFetch = semester && courseId;
   const swrKey = shouldFetch ? createSwrKey('/course_materials', { semester, course_id: courseId }) : null;
   const { data, error, mutate, isLoading } = useSWR(swrKey, fetcher);
   return { materials: data, isLoading: isLoading && shouldFetch, isError: error, mutate, };
};

// Export the services
// (No changes needed here, already exported)