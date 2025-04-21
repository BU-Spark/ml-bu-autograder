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
// Request interceptor to add auth token
const token = "123bob"; // <<<--- Using sessionStorage below is better for real apps
api.interceptors.request.use(
  (config) => {
    // Get token from sessionStorage (preferred over hardcoding)
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    } else {
       // Log only if it's not an auth request itself to avoid noise during login
       if (!config.url?.includes('/auth/')) {
            console.warn(`No 'authToken' found in sessionStorage for request to ${config.url}. Request sent without Authorization header.`);
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
    // Handle specific error cases
    if (error.response) {
      const { status, data } = error.response;
      const errorMessage = data?.detail || error.message; // Prefer backend 'detail' message

      // Server responded with a status code outside of 2xx range
      switch (status) {
        case 401:
          console.error('Authentication error (401):', errorMessage);
          // Only sign out if not already on login page to avoid loops
          if (typeof window !== 'undefined' && window.location.pathname !== '/login' && !window.location.pathname.startsWith('/auth')) { // Avoid signout during auth flow
             signOut({ callbackUrl: '/login' }); // Redirect to login on 401
          }
          // Return a more specific error for UI handling
          return Promise.reject(new Error(ERROR_MESSAGES.auth.unauthorized));

        case 403:
          console.error('Forbidden error (403):', errorMessage);
          // Might indicate insufficient permissions
          return Promise.reject(new Error(errorMessage || ERROR_MESSAGES.auth.forbidden)); // Use backend message

        case 404:
          console.error('Not found error (404):', errorMessage);
          return Promise.reject(new Error(errorMessage || ERROR_MESSAGES.api.notFound));

        case 400: // Bad Request
        case 409: // Conflict
        case 422: // Unprocessable Entity (often used by FastAPI for validation errors)
          console.error(`Client error (${status}):`, errorMessage);
          // Return a more specific error, potentially the backend message
          // Check if detail is an array (FastAPI validation errors)
          let clientErrorMsg = errorMessage;
          if (Array.isArray(data?.detail)) {
             clientErrorMsg = data.detail.map(err => `${err.loc?.join('.')} - ${err.msg}`).join('; ');
          } else if (typeof data?.detail === 'string') {
             clientErrorMsg = data.detail;
          } else {
             clientErrorMsg = `Invalid request (${status}).`;
          }
          return Promise.reject(new Error(clientErrorMsg));

        case 500:
        case 502: // Often from external services like LLM
        case 503:
          console.error(`Server error (${status}):`, errorMessage);
          return Promise.reject(new Error(errorMessage || ERROR_MESSAGES.api.serverError));

        default:
          console.error(`API error (${status}):`, errorMessage);
          return Promise.reject(new Error(errorMessage || ERROR_MESSAGES.general));
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
  // No try-catch needed here, interceptor handles errors, SWR catches rejected promises
  const response = await api.get(url);
  return response.data;
};

// --- API Service Methods ---

// Authentication
export const authService = {
  // GET /auth/google_oauth?code=...
  googleOAuth: (code) => api.get('/auth/google_oauth', { params: { code } }),

  // GET /auth/google_oauth_url
  getGoogleOAuthUrl: () => api.get('/auth/google_oauth_url'),

  // POST /auth/token?token_name=...&token_expiry=...
  createToken: (tokenName, tokenExpiry = null) => api.post('/auth/token', null, {
      params: {
          token_name: tokenName,
          token_expiry: tokenExpiry
      }
  }),

  // GET /auth/tokens
  listTokens: () => api.get('/auth/tokens'),

  // DELETE /auth/token?token_name=...
  deleteToken: (tokenName) => api.delete('/auth/token', { params: { token_name: tokenName } }),
};

// Course management
export const courseService = {
  // GET /courses?semester=...
  getCourses: (semester = null) => api.get('/courses', { params: { semester } }),

  // GET /course?course_id=...&semester=...
  getCourse: (courseId, semester) =>
    api.get('/course', { params: { course_id: courseId, semester } }),

  // POST /course (Body: Course)
  createCourse: (courseData) => api.post('/course', courseData),

  // DELETE /course?course_id=...&semester=...
  deleteCourse: (courseId, semester) =>
    api.delete('/course', { params: { course_id: courseId, semester } }),

  // PATCH /course/transfer?current_course_id=... etc.
  transferCourse: (currentSemester, currentCourseId, copyFromSemester, copyFromCourseId) =>
    api.patch('/course/transfer', null, {
      params: {
        current_semester: currentSemester,
        current_course_id: currentCourseId,
        copy_from_course_semester: copyFromSemester,
        copy_from_course_id: copyFromCourseId,
      },
    }),

  // POST /course/instructor?course_id=...&semester=...&instructor=...
  addInstructor: (semester, courseId, instructor) =>
    api.post('/course/instructor', null, { params: { semester, course_id: courseId, instructor } }),

  // DELETE /course/instructor?course_id=...&semester=...&instructor=...
  removeInstructor: (semester, courseId, instructor) =>
    api.delete('/course/instructor', { params: { semester, course_id: courseId, instructor } }),
};

// Assignment management
export const assignmentService = {
  // GET /assignments?course_id=...&semester=...
  getAssignments: (courseId, semester) =>
    api.get('/assignments', { params: { course_id: courseId, semester: semester } }),

  // GET /assignment?course_id=...&semester=...&assignment_id=...&include_questions=...
  getAssignment: (courseId, semester, assignmentId, includeQuestions = false) =>
    api.get('/assignment', {
      params: {
        course_id: courseId,
        semester: semester,
        assignment_id: assignmentId,
        include_questions: includeQuestions
      }
    }),

  // POST /assignment (Body: Assignment)
  createAssignment: (assignmentData) => // Renamed param for clarity
    api.post('/assignment', assignmentData), // Expects full Assignment object

  // DELETE /assignment?course_id=...&semester=...&assignment_id=...
  deleteAssignment: (courseId, semester, assignmentId) =>
    api.delete('/assignment', { params: { course_id: courseId, semester: semester, assignment_id: assignmentId } }),

  // --- MODIFIED FUNCTION ---
  // PATCH /assignments/{assignment_id}?semester=...&course_id=... (Body: AssignmentMetadataUpdate)
  updateAssignmentMetadata: (semester, courseId, assignmentId, updateData) =>
    api.patch(`/assignments/${assignmentId}`, updateData, { // ID in path, updateData is body
      params: { // Semester and courseId are query params
        semester: semester,
        course_id: courseId
        // assignment_id is removed from params
      }
    }),
  // --- END MODIFIED FUNCTION ---

  // PATCH /assignment/add_question (Body: AddQuestionRequest)
  addQuestion: (semester, courseId, assignmentId, questionData) =>
    api.patch('/assignment/add_question', { // Body contains all needed info
      semester: semester,
      course_id: courseId,
      assignment_id: assignmentId,
      question: questionData // questionData should be { question_text: "...", question_graphics_figures: null }
    }),

  // PATCH /assignment/remove_question?semester=...&course_id=...&assignment_id=...&question_index=...
  removeQuestion: (semester, courseId, assignmentId, questionIndex) =>
    api.patch('/assignment/remove_question', null, { // No request body
       params: {
         semester: semester,
         course_id: courseId,
         assignment_id: assignmentId,
         question_index: questionIndex
       }
    }),

  // PATCH /assignment/edit_question (Body: EditQuestionRequest)
  editQuestion: (semester, courseId, assignmentId, questionIndex, questionData) =>
    api.patch('/assignment/edit_question', { // Body contains all needed info
      semester: semester,
      course_id: courseId,
      assignment_id: assignmentId,
      question_index: questionIndex,
      question: questionData // questionData should be { question_text: "...", question_graphics_figures: null }
    }),

  // PATCH /assignment/modify_order (Body: ModifyOrderRequest)
  modifyQuestionOrder: (semester, courseId, assignmentId, newIndexOrder) =>
    api.patch('/assignment/modify_order', { // Body contains all needed info
      semester: semester,
      course_id: courseId,
      assignment_id: assignmentId,
      list_of_question_indexes: newIndexOrder
    }),
};

// Student response and Grading management
export const responseService = {
  // POST /response (Body: StudentResponse)
  uploadResponse: (responseData) => api.post('/response', responseData),

  // PUT /response (Body: StudentResponse)
  replaceResponse: (responseData) => api.put('/response', responseData),

  // DELETE /response?student_id=...&semester=... etc.
  deleteResponse: (semester, courseId, assignmentId, studentId, questionIndex = null) =>
    api.delete('/response', {
      params: {
        semester: semester,
        course_id: courseId,
        assignment_id: assignmentId,
        student_id: studentId,
        question_index: questionIndex,
      }
    }),

  // GET /responses?semester=...&course_id=... etc.
  getResponses: (semester, courseId, assignmentId, questionIndex = null, studentId = null) =>
    api.get('/responses', {
      params: {
        semester: semester,
        course_id: courseId,
        assignment_id: assignmentId,
        question_index: questionIndex,
        student_id: studentId
      }
    }),

  // --- Grading ---

  // POST /response/grade/specific?semester=...&course_id=... etc.
  gradeSpecific: (semester, courseId, assignmentId, studentIds, questionIndex = null) =>
    api.post('/response/grade/specific', null, {
      params: {
        semester: semester,
        course_id: courseId,
        assignment_id: assignmentId,
        student_ids: studentIds, // Axios should handle array serialization
        question_index: questionIndex
      }
    }),

  // POST /response/grade/ungraded?semester=...&course_id=... etc.
  gradeUngraded: (semester, courseId, assignmentId, questionIndex = null) =>
    api.post('/response/grade/ungraded', null, {
      params: {
        semester: semester,
        course_id: courseId,
        assignment_id: assignmentId,
        question_index: questionIndex
      }
    }),

  // POST /response/grade/all?semester=...&course_id=... etc.
  gradeAll: (semester, courseId, assignmentId, questionIndex = null) =>
    api.post('/response/grade/all', null, {
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
  // GET /course_materials?semester=...&course_id=...
  getMaterials: (semester, courseId) =>
    api.get('/course_materials', { params: { semester: semester, course_id: courseId } }),

  // GET /course_material?semester=...&course_id=...&material_id=...
  getMaterial: (semester, courseId, materialId) =>
    api.get('/course_material', { params: { semester: semester, course_id: courseId, material_id: materialId } }),

  // POST /course_material (Body: CourseMaterial)
  uploadMaterial: (materialData) => api.post('/course_material', materialData),

  // PATCH /course_material (Body: CourseMaterial)
  updateMaterial: (materialData) => api.patch('/course_material', materialData),

  // DELETE /course_material?semester=...&course_id=...&material_id=...
  deleteMaterial: (semester, courseId, materialId) =>
    api.delete('/course_material', { params: { semester: semester, course_id: courseId, material_id: materialId } }),
};

// Rubric management
export const rubricService = {
  // GET /rubric?semester=...&course_id=... etc.
  getRubric: (semester, courseId, assignmentId, questionIndex = null) =>
    api.get('/rubric', {
      params: {
        semester: semester,
        course_id: courseId,
        assignment_id: assignmentId,
        question_index: questionIndex
      }
    }),

  // PUT /rubric (Body: Rubric)
  createRubric: (rubricData) =>
    api.put('/rubric', rubricData),

  // GET /ai_rubric?semester=...&course_id=... etc.
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
  // GET /user
  getUserData: () => api.get('/user'),

  // PATCH /user (Body: UserPreferencesUpdate)
  updateUserPreferences: (preferencesData) => api.patch('/user', preferencesData),
};

// --- SWR Hooks ---

export const useUser = () => {
  const { data, error, mutate } = useSWR('/user', fetcher);
  return {
    user: data,
    isLoading: !error && !data,
    isError: error,
    mutate,
  };
};

export const useCourses = (semester = null) => {
  const queryString = semester ? `?semester=${encodeURIComponent(semester)}` : '';
  const { data, error, mutate } = useSWR(`/courses${queryString}`, fetcher);
  return {
    courses: data,
    isLoading: !error && !data,
    isError: error,
    mutate,
  };
};

// Updated to match backend route '/assignments'
export const useAssignments = (courseId, semester, includeQuestions = false) => {
  const shouldFetch = semester && courseId;
  const params = new URLSearchParams();
  if (courseId) params.append('course_id', courseId); // Corrected param name
  if (semester) params.append('semester', semester);
  if (includeQuestions) params.append('include_questions', 'true');

  const { data, error, mutate } = useSWR(
    shouldFetch ? `/assignments?${params.toString()}` : null, // Use /assignments
    fetcher
  );
  return {
    assignments: data,
    isLoading: !error && !data && shouldFetch,
    isError: error,
    mutate,
  };
};


export const useRubric = (semester, courseId, assignmentId, questionIndex = null) => {
  const shouldFetch = semester && courseId && assignmentId;
  const params = new URLSearchParams();
   if (semester) params.append('semester', semester);
   if (courseId) params.append('course_id', courseId);
   if (assignmentId) params.append('assignment_id', String(assignmentId));
  if (questionIndex !== null) params.append('question_index', String(questionIndex));

  const { data, error, mutate } = useSWR(
    shouldFetch ? `/rubric?${params.toString()}` : null,
    fetcher
  );

  return {
    rubric: data,
    isLoading: !error && !data && shouldFetch,
    isError: error,
    mutate,
  };
};


export const useMaterials = (semester, courseId) => {
   const shouldFetch = semester && courseId;
   const params = new URLSearchParams();
   if (semester) params.append('semester', semester);
   if (courseId) params.append('course_id', courseId);

   const { data, error, mutate } = useSWR(
    shouldFetch ? `/course_materials?${params.toString()}` : null,
    fetcher
  );
  return {
    materials: data,
    isLoading: !error && !data && shouldFetch,
    isError: error,
    mutate,
  };
};