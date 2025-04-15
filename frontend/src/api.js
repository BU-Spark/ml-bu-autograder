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
const token = "123bob";
api.interceptors.request.use(
  (config) => {
   // const token = typeof window !== 'undefined' ? sessionStorage.getItem('authToken') : null;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    } else {
       // <<< --- ADDED WARNING --- >>>
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
          if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
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
          return Promise.reject(new Error(errorMessage || `Invalid request (${status}).`));

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
  // --- Corrected: Expects 'code' from Google Redirect ---
  // GET /auth/google_oauth?code=...
  googleOAuth: (code) => api.get('/auth/google_oauth', { params: { code } }), // Send 'code' as query param

  // Get URL for redirecting user to Google
  // GET /auth/google_oauth_url
  getGoogleOAuthUrl: () => api.get('/auth/google_oauth_url'), // Backend needs to implement this

  // --- Correct ---
  // POST /auth/token?token_name=...&token_expiry=...
  createToken: (tokenName, tokenExpiry = null) => api.post('/auth/token', null, { // No body needed
      params: { // Send as query parameters
          token_name: tokenName,
          token_expiry: tokenExpiry // Send null or ISO date string if needed
      }
  }),

  // --- Correct ---
  // GET /auth/tokens
  listTokens: () => api.get('/auth/tokens'),

  // --- Corrected: Parameter name ---
  // DELETE /auth/token?token_name=...
  deleteToken: (tokenName) => api.delete('/auth/token', { params: { token_name: tokenName } }), // Use token_name

  // --- Removed: No corresponding backend endpoint ---
  // signOut: () => api.post('/auth/signout')
};

// Course management
export const courseService = {
  // --- Correct ---
  // GET /courses?semester=...
  getCourses: (semester = null) => api.get('/courses', { params: { semester } }), // Pass null if no semester filter

  // --- Correct ---
  // GET /course?course_id=...&semester=...
  getCourse: (courseId, semester) =>
    api.get('/course', { params: { course_id: courseId, semester } }),

  // --- Corrected: semester is part of the body model ---
  // POST /course (Body: Course)
  createCourse: (courseData) => // courseData must include semester
    api.post('/course', courseData), // Remove semester from params

  // --- Correct ---
  // DELETE /course?course_id=...&semester=...
  deleteCourse: (courseId, semester) =>
    api.delete('/course', { params: { course_id: courseId, semester } }),

  // --- Correct (but backend non-functional) ---
  // PATCH /course/transfer?current_course_id=... etc.
  transferCourse: (currentSemester, currentCourseId, copyFromSemester, copyFromCourseId) =>
    api.patch('/course/transfer', null, { // No request body needed
      params: {
        current_semester: currentSemester,
        current_course_id: currentCourseId,
        copy_from_course_semester: copyFromSemester, // Updated param name
        copy_from_course_id: copyFromCourseId,
      },
    }),

  // --- Correct ---
  // POST /course/instructor?course_id=...&semester=...&instructor=...
  addInstructor: (semester, courseId, instructor) => // Changed order for consistency
    api.post('/course/instructor', null, { params: { semester, course_id: courseId, instructor } }), // No body

  // --- Correct ---
  // DELETE /course/instructor?course_id=...&semester=...&instructor=...
  removeInstructor: (semester, courseId, instructor) => // Changed order for consistency
    api.delete('/course/instructor', { params: { semester, course_id: courseId, instructor } }),
};

// Assignment management (Incorporates previous corrections)
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
  createAssignment: (assignmentData) =>
    api.post('/assignment', assignmentData),

  // DELETE /assignment?course_id=...&semester=...&assignment_id=...
  deleteAssignment: (courseId, semester, assignmentId) =>
    api.delete('/assignment', { params: { course_id: courseId, semester: semester, assignment_id: assignmentId } }),

  // PATCH /assignment?course_id=...&semester=...&assignment_id=... (Body: AssignmentUpdateRequest)
  updateAssignmentMetadata: (semester, courseId, assignmentId, updateData) =>
    api.patch('/assignment', updateData, {
      params: {
        semester: semester,
        course_id: courseId,
        assignment_id: assignmentId
      }
    }),

  // PATCH /assignment/add_question (Body: AddQuestionRequest)
  addQuestion: (semester, courseId, assignmentId, questionData) =>
    api.patch('/assignment/add_question', {
      semester: semester,
      course_id: courseId,
      assignment_id: assignmentId,
      question: questionData
    }),

  // PATCH /assignment/remove_question?semester=...&course_id=...&assignment_id=...&question_index=...
  removeQuestion: (semester, courseId, assignmentId, questionIndex) =>
    api.patch('/assignment/remove_question', null, {
       params: {
         semester: semester,
         course_id: courseId,
         assignment_id: assignmentId,
         question_index: questionIndex
       }
    }),

  // PATCH /assignment/edit_question (Body: EditQuestionRequest)
  editQuestion: (semester, courseId, assignmentId, questionIndex, questionData) =>
    api.patch('/assignment/edit_question', {
      semester: semester,
      course_id: courseId,
      assignment_id: assignmentId,
      question_index: questionIndex,
      question: questionData
    }),

  // PATCH /assignment/modify_order (Body: ModifyOrderRequest)
  modifyQuestionOrder: (semester, courseId, assignmentId, newIndexOrder) =>
    api.patch('/assignment/modify_order', {
      semester: semester,
      course_id: courseId,
      assignment_id: assignmentId,
      list_of_question_indexes: newIndexOrder
    }),
};

// Student response and Grading management
export const responseService = {
  // --- Correct ---
  // POST /response (Body: StudentResponse)
  uploadResponse: (responseData) => api.post('/response', responseData),

  // --- Correct ---
  // PUT /response (Body: StudentResponse)
  replaceResponse: (responseData) => api.put('/response', responseData),

  // --- Correct ---
  // DELETE /response?student_id=...&semester=... etc.
  deleteResponse: (semester, courseId, assignmentId, studentId, questionIndex = null) => // Consistent param order
    api.delete('/response', {
      params: {
        semester: semester,
        course_id: courseId,
        assignment_id: assignmentId,
        student_id: studentId, // Use student_id as expected by backend Query
        question_index: questionIndex, // Will be omitted if null
      }
    }),

  // --- Correct ---
  // GET /responses?semester=...&course_id=... etc.
  getResponses: (semester, courseId, assignmentId, questionIndex = null, studentId = null) => // Consistent param order
    api.get('/responses', {
      params: {
        semester: semester,
        course_id: courseId,
        assignment_id: assignmentId,
        question_index: questionIndex, // Will be omitted if null
        student_id: studentId // Will be omitted if null
      }
    }),

  // --- Grading ---

  // --- Correct ---
  // POST /response/grade/specific?semester=...&course_id=... etc. (Note: API path prefix adds /response)
  gradeSpecific: (semester, courseId, assignmentId, studentIds, questionIndex = null) => // studentIds is List[str]
    api.post('/response/grade/specific', null, { // No body
      params: {
        semester: semester,
        course_id: courseId,
        assignment_id: assignmentId,
        student_ids: studentIds, // Send array as query param (axios usually handles this correctly)
        question_index: questionIndex
      }
    }),

  // --- Correct ---
  // POST /response/grade/ungraded?semester=...&course_id=... etc.
  gradeUngraded: (semester, courseId, assignmentId, questionIndex = null) =>
    api.post('/response/grade/ungraded', null, { // No body
      params: {
        semester: semester,
        course_id: courseId,
        assignment_id: assignmentId,
        question_index: questionIndex
      }
    }),

  // --- Correct ---
  // POST /response/grade/all?semester=...&course_id=... etc.
  gradeAll: (semester, courseId, assignmentId, questionIndex = null) =>
    api.post('/response/grade/all', null, { // No body
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
  // --- Correct ---
  // GET /course_materials?semester=...&course_id=...
  getMaterials: (semester, courseId) =>
    api.get('/course_materials', { params: { semester: semester, course_id: courseId } }),

  // --- Correct ---
  // GET /course_material?semester=...&course_id=...&material_id=...
  getMaterial: (semester, courseId, materialId) =>
    api.get('/course_material', { params: { semester: semester, course_id: courseId, material_id: materialId } }),

  // --- Correct ---
  // POST /course_material (Body: CourseMaterial)
  uploadMaterial: (materialData) => api.post('/course_material', materialData),

  // --- Correct ---
  // PATCH /course_material (Body: CourseMaterial)
  updateMaterial: (materialData) => api.patch('/course_material', materialData),

  // --- Correct ---
  // DELETE /course_material?semester=...&course_id=...&material_id=...
  deleteMaterial: (semester, courseId, materialId) =>
    api.delete('/course_material', { params: { semester: semester, course_id: courseId, material_id: materialId } }),
};

// Rubric management
export const rubricService = {
  // --- Correct ---
  // GET /rubric?semester=...&course_id=... etc.
  getRubric: (semester, courseId, assignmentId, questionIndex = null) =>
    api.get('/rubric', {
      params: {
        semester: semester,
        course_id: courseId,
        assignment_id: assignmentId,
        question_index: questionIndex // Omitted if null
      }
    }),

  // --- Correct ---
  // PUT /rubric (Body: Rubric)
  createRubric: (rubricData) => // Expects full Rubric object
    api.put('/rubric', rubricData),

  // --- Correct ---
  // GET /ai_rubric?semester=...&course_id=... etc.
  getAIRubric: (semester, courseId, assignmentId, instructions = null) =>
    api.get('/ai_rubric', {
      params: {
        semester: semester,
        course_id: courseId,
        assignment_id: assignmentId,
        instructions: instructions // Omitted if null
      }
    }),
};

// User management
export const userService = {
  // --- Correct ---
  // GET /user
  getUserData: () => api.get('/user'),

  // --- Correct ---
  // PATCH /user (Body: UserPreferencesUpdate)
  updateUserPreferences: (preferencesData) => api.patch('/user', preferencesData),
};

// --- SWR Hooks (Generally look OK, relying on the service methods above) ---

export const useUser = () => {
  const { data, error, mutate } = useSWR('/user', fetcher);
  return {
    user: data,
    isLoading: !error && !data,
    isError: error,
    mutate,
  };
};

export const useCourses = (semester = null) => { // Allow optional semester filtering
  const queryString = semester ? `?semester=${encodeURIComponent(semester)}` : '';
  const { data, error, mutate } = useSWR(`/courses${queryString}`, fetcher);
  return {
    courses: data,
    isLoading: !error && !data,
    isError: error,
    mutate,
  };
};

export const useAssignments = (semester, courseId, includeQuestions = false) => { // Add includeQuestions hook option
  const shouldFetch = semester && courseId;
  const params = new URLSearchParams();
  if (semester) params.append('semester', semester);
  if (courseId) params.append('course_id', courseId);
  if (includeQuestions) params.append('include_questions', 'true'); // Add include_questions

  const { data, error, mutate } = useSWR(
    shouldFetch ? `/assignments?${params.toString()}` : null,
    fetcher
  );
  return {
    assignments: data,
    isLoading: !error && !data && shouldFetch, // Only loading if should fetch
    isError: error,
    mutate,
  };
};


export const useRubric = (semester, courseId, assignmentId, questionIndex = null) => {
  const shouldFetch = semester && courseId && assignmentId;
  const params = new URLSearchParams({
    semester: semester,
    course_id: courseId,
    assignment_id: String(assignmentId), // Ensure string
  });
  if (questionIndex !== null) params.append('question_index', String(questionIndex)); // Ensure string

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

// Note: Exporting the instance directly isn't common; exporting service objects is typical.
// If you need to export the configured axios instance:
// export default api;