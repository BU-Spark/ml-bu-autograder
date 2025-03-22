/**
 * Global configuration file for the BU MET Autograder frontend
 * Contains environment variables, API endpoints, and other global settings
 */

// Base API URL - can be overridden by environment variables
export const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://api.autograder.bu.edu';

// API version prefix used for all endpoints
export const API_PREFIX = '/api/v1';

// Authentication settings
export const AUTH_CONFIG = {
  // OAuth providers
  providers: {
    google: {
      clientId: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET,
    },
    microsoft: {
      clientId: process.env.NEXT_PUBLIC_MICROSOFT_CLIENT_ID,
      clientSecret: process.env.MICROSOFT_CLIENT_SECRET,
    },
  },
  // JWT settings
  jwt: {
    secret: process.env.JWT_SECRET,
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
};

// Application settings
export const APP_CONFIG = {
  appName: 'BU MET Autograder',
  defaultTheme: 'light',
  supportEmail: 'support@autograder.bu.edu',
  maxUploadSize: 10 * 1024 * 1024, // 10MB in bytes
  acceptedFileTypes: {
    materials: ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.txt', '.zip'],
    submissions: ['.pdf', '.txt', '.md', '.py', '.java', '.js', '.html', '.css'],
  },
};

// Feature flags
export const FEATURES = {
  enableAIRubrics: true,
  enableBatchGrading: true,
  enableCourseTransfer: true,
};

// Timeouts and limits
export const LIMITS = {
  apiTimeout: 30000, // 30 seconds
  maxItemsPerPage: 50,
  tokenNameMaxLength: 50,
};

// Error messages
export const ERROR_MESSAGES = {
  general: 'An unexpected error occurred. Please try again.',
  network: 'Network error. Please check your connection and try again.',
  auth: {
    loginFailed: 'Authentication failed. Please try again.',
    sessionExpired: 'Your session has expired. Please log in again.',
    unauthorized: 'You are not authorized to access this resource.',
  },
  api: {
    timeout: 'The request timed out. Please try again.',
    notFound: 'The requested resource was not found.',
    badRequest: 'Invalid request. Please check your inputs and try again.',
    serverError: 'Server error. Our team has been notified.',
  },
  upload: {
    sizeExceeded: `File size exceeds the maximum limit of ${APP_CONFIG.maxUploadSize / (1024 * 1024)}MB.`,
    typeNotSupported: 'File type not supported.',
    failed: 'File upload failed. Please try again.',
  },
};