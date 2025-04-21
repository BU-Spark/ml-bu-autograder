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
    const token = "123bob"; // Example static token (remove in production)
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    } else {
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
      const errorMessage = data?.detail || error.message;
      switch (status) {
        case 401:
          console.error('Authentication error (401):', errorMessage);
          if (typeof window !== 'undefined' && window.location.pathname !== '/login' && !window.location.pathname.startsWith('/auth')) {
             signOut({ callbackUrl: '/login' });
          }
          return Promise.reject(new Error(ERROR_MESSAGES.auth.unauthorized));
        case 403:
          console.error('Forbidden error (403):', errorMessage);
          return Promise.reject(new Error(errorMessage || ERROR_MESSAGES.auth.forbidden));
        case 404:
          console.error('Not found error (404):', errorMessage);
          return Promise.reject(new Error(errorMessage || ERROR_MESSAGES.api.notFound));
        case 400: case 409: case 422:
          console.error(`Client error (${status}):`, errorMessage);
          let clientErrorMsg = errorMessage;
          if (Array.isArray(data?.detail)) {
             clientErrorMsg = data.detail.map(err => `${err.loc?.join('.')} - ${err.msg}`).join('; ');
          } else if (typeof data?.detail === 'string') {
             clientErrorMsg = data.detail;
          } else {
             clientErrorMsg = `Invalid request (${status}).`;
          }
          return Promise.reject(new Error(clientErrorMsg));
        case 500: case 502: case 503:
          console.error(`Server error (${status}):`, errorMessage);
          return Promise.reject(new Error(errorMessage || ERROR_MESSAGES.api.serverError));
        default:
          console.error(`API error (${status}):`, errorMessage);
          return Promise.reject(new Error(errorMessage || ERROR_MESSAGES.general));
      }
    } else if (error.request) {
      console.error('Network error:', error.request);
      return Promise.reject(new Error(ERROR_MESSAGES.network));
    } else {
      console.error('Request configuration error:', error.message);
      return Promise.reject(new Error(ERROR_MESSAGES.general));
    }
  }
);

// SWR fetcher function using our API instance
const fetcher = async (url) => {
  const response = await api.get(url);
  return response.data;
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

// Assignment management
export const assignmentService = {
  // GET /assignments (Backend expects strings)
  getAssignments: (courseId, semester, includeQuestions = false) => // Added includeQuestions consistency
    api.get('/assignments', { params: { course_id: courseId, semester: semester, include_questions: includeQuestions } }), // Pass include_questions

  // GET /assignment (Backend expects strings/bool)
  getAssignment: (courseId, semester, assignmentId, includeQuestions = false) =>
    api.get('/assignment', {
      params: {
        course_id: courseId,
        semester: semester,
        assignment_id: String(assignmentId), // Ensure string
        include_questions: includeQuestions
      }
    }),

  // POST /assignment (Backend generates string ID or expects string if provided)
  createAssignment: (assignmentData) =>
    api.post('/assignment', assignmentData),

  // DELETE /assignment (Backend expects strings)
  deleteAssignment: (courseId, semester, assignmentId) =>
    api.delete('/assignment', { params: { course_id: courseId, semester: semester, assignment_id: String(assignmentId) } }), // Ensure string

  // PATCH /assignments/{assignment_id} (Backend expects strings)
  updateAssignmentMetadata: (semester, courseId, assignmentId, updateData) =>
    api.patch(`/assignments/${String(assignmentId)}`, updateData, { // Ensure string ID in path
      params: {
        semester: semester,
        course_id: courseId
      }
    }),

  // PATCH /assignment/add_question (Backend expects strings in body)
  addQuestion: (semester, courseId, assignmentId, questionData) =>
    api.patch('/assignment/add_question', {
      semester: semester,
      course_id: courseId,
      assignment_id: String(assignmentId), // Ensure string
      question: questionData
    }),

  // PATCH /assignment/remove_question (Backend expects strings/int in query)
  removeQuestion: (semester, courseId, assignmentId, questionIndex) =>
    api.patch('/assignment/remove_question', null, {
       params: {
         semester: semester,
         course_id: courseId,
         assignment_id: String(assignmentId), // Ensure string
         question_index: questionIndex
       }
    }),

  // PATCH /assignment/edit_question (Backend expects strings in body)
  editQuestion: (semester, courseId, assignmentId, questionIndex, questionData) =>
    api.patch('/assignment/edit_question', {
      semester: semester,
      course_id: courseId,
      assignment_id: String(assignmentId), // Ensure string
      question_index: questionIndex,
      question: questionData
    }),

  // PATCH /assignment/modify_order (Backend expects strings in body)
  modifyQuestionOrder: (semester, courseId, assignmentId, newIndexOrder) =>
    api.patch('/assignment/modify_order', {
      semester: semester,
      course_id: courseId,
      assignment_id: String(assignmentId), // Ensure string
      list_of_question_indexes: newIndexOrder
    }),
};

// Student response and Grading management
export const responseService = {
  uploadResponse: (responseData) => api.post('/response', responseData),
  replaceResponse: (responseData) => api.put('/response', responseData),
  deleteResponse: (semester, courseId, assignmentId, studentId, questionIndex = null) => api.delete('/response', { params: { semester: semester, course_id: courseId, assignment_id: String(assignmentId), student_id: studentId, question_index: questionIndex, } }), // Ensure string ID
  getResponses: (semester, courseId, assignmentId, questionIndex = null, studentId = null) => api.get('/responses', { params: { semester: semester, course_id: courseId, assignment_id: String(assignmentId), question_index: questionIndex, student_id: studentId } }), // Ensure string ID
  gradeSpecific: (semester, courseId, assignmentId, studentIds, questionIndex = null) => api.post('/response/grade/specific', null, { params: { semester: semester, course_id: courseId, assignment_id: String(assignmentId), student_ids: studentIds, question_index: questionIndex } }), // Ensure string ID
  gradeUngraded: (semester, courseId, assignmentId, questionIndex = null) => api.post('/response/grade/ungraded', null, { params: { semester: semester, course_id: courseId, assignment_id: String(assignmentId), question_index: questionIndex } }), // Ensure string ID
  gradeAll: (semester, courseId, assignmentId, questionIndex = null) => api.post('/response/grade/all', null, { params: { semester: semester, course_id: courseId, assignment_id: String(assignmentId), question_index: questionIndex } }), // Ensure string ID
};

// Course material management
export const materialService = {
  getMaterials: (semester, courseId) => api.get('/course_materials', { params: { semester: semester, course_id: courseId } }),
  // Backend expects int ID for material
  getMaterial: (semester, courseId, materialId) => api.get('/course_material', { params: { semester: semester, course_id: courseId, material_id: materialId } }),
  // Backend generates int ID
  uploadMaterial: (materialData) => api.post('/course_material', materialData),
  // Backend expects full object with int ID
  updateMaterial: (materialData) => api.patch('/course_material', materialData),
   // Backend expects int ID for material
  deleteMaterial: (semester, courseId, materialId) => api.delete('/course_material', { params: { semester: semester, course_id: courseId, material_id: materialId } }),
};

// Rubric management
export const rubricService = {
  // GET /rubric (Backend expects assignment_id: str query param)
  getRubric: (semester, courseId, assignmentId, questionIndex = null) =>
    api.get('/rubric', {
      params: {
        semester: semester,
        course_id: courseId,
        assignment_id: String(assignmentId), // <<< CHANGED: Ensure string
        question_index: questionIndex
      }
    }),

  // PUT /rubric (Body: Rubric - assignment_id: str)
  createRubric: (rubricData) => // Ensure rubricData.assignment_id is string
    api.put('/rubric', rubricData),

  // GET /ai_rubric (Backend expects assignment_id: str query param)
  getAIRubric: (semester, courseId, assignmentId, instructions = null) =>
    api.get('/ai_rubric', {
      params: {
        semester: semester,
        course_id: courseId,
        assignment_id: String(assignmentId), // <<< CHANGED: Ensure string
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

export const useUser = () => {
  const { data, error, mutate } = useSWR('/user', fetcher);
  return { user: data, isLoading: !error && !data, isError: error, mutate, };
};

export const useCourses = (semester = null) => {
  const queryString = semester ? `?semester=${encodeURIComponent(semester)}` : '';
  const { data, error, mutate } = useSWR(`/courses${queryString}`, fetcher);
  return { courses: data, isLoading: !error && !data, isError: error, mutate, };
};

export const useAssignments = (courseId, semester, includeQuestions = false) => {
  const shouldFetch = semester && courseId;
  const params = new URLSearchParams();
  if (courseId) params.append('course_id', courseId);
  if (semester) params.append('semester', semester);
  if (includeQuestions) params.append('include_questions', 'true');
  const { data, error, mutate } = useSWR( shouldFetch ? `/assignments?${params.toString()}` : null, fetcher );
  return { assignments: data, isLoading: !error && !data && shouldFetch, isError: error, mutate, };
};


export const useRubric = (semester, courseId, assignmentId, questionIndex = null) => {
  // Ensure assignmentId is treated as string for the key and fetch check
  const assignmentIdStr = assignmentId !== null && typeof assignmentId !== 'undefined' ? String(assignmentId) : null;
  const shouldFetch = semester && courseId && assignmentIdStr; // Check string version

  const params = new URLSearchParams();
   if (semester) params.append('semester', semester);
   if (courseId) params.append('course_id', courseId);
   // --- CHANGED: Append assignmentIdStr ---
   if (assignmentIdStr) params.append('assignment_id', assignmentIdStr);
  if (questionIndex !== null) params.append('question_index', String(questionIndex));

  const { data, error, mutate } = useSWR(
    shouldFetch ? `/rubric?${params.toString()}` : null,
    fetcher
  );

  return { rubric: data, isLoading: !error && !data && shouldFetch, isError: error, mutate, };
};


export const useMaterials = (semester, courseId) => {
   const shouldFetch = semester && courseId;
   const params = new URLSearchParams();
   if (semester) params.append('semester', semester);
   if (courseId) params.append('course_id', courseId);
   const { data, error, mutate } = useSWR( shouldFetch ? `/course_materials?${params.toString()}` : null, fetcher );
  return { materials: data, isLoading: !error && !data && shouldFetch, isError: error, mutate, };
};