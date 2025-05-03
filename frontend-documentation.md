# 📄 BU MET Autograder - `fahim-iteration-two` Branch Documentation

## ✅ Overview

The `fahim-iteration-two` branch introduces a **centralized API service layer** for interacting with the BU MET Autograder backend. This implementation provides:

- 🚀 Configured **Axios instance** with interceptors for authentication and error handling
- 🔗 **API services** organized by domain (auth, course, assignment, material, response, rubric, user)
- 🧩 **SWR hooks** for frontend components to access data reactively and efficiently
- 📦 Modular export of services and hooks, aligning with backend API **endpoints and parameter naming**

---

## 🏗️ Key Features Implemented

| Feature                          | Status  |
|---------------------------------|---------|
| Axios instance with interceptors | ✅       |
| AuthService methods              | ✅       |
| CourseService methods            | ✅       |
| AssignmentService methods        | ✅       |
| MaterialService methods          | ✅       |
| RubricService methods            | ✅       |
| ResponseService methods          | ✅       |
| UserService methods              | ✅       |
| SWR hooks (user, courses, rubric, assignments, materials) | ✅ |

All API methods **follow the backend endpoints** as defined in the Python FastAPI backend (e.g., `/auth/google_oauth`, `/course_materials`, `/rubric`, etc.). Query params and request payloads are aligned to match **Pydantic schemas**.

---

## 📝 Required Additions

The following items still need to be implemented before merge:

1. ✅ **Unit tests using Jest**
   - Write Jest tests to cover:
     - Each API service method
     - Each SWR hook (basic hook call + error handling)
     - Error interceptor cases
2. ✅ **Google Analytics integration**
   - Add Google Analytics tracking script (manual or via Next.js plugin)
   - Ensure route changes are tracked (e.g., `pageview` events)
3. 🔍 **Validation against backend**
   - Confirm all service methods match latest backend endpoint specs (parameter names, HTTP verbs, query strings)
4. 📝 **Developer documentation for future contributors**
   - Example usage of each service
   - Example usage of SWR hooks in a Next.js page/component

---

## 🗂️ Follows These Backend Endpoints

The service layer is designed to **follow the exact backend endpoints** exposed by the Python FastAPI backend. Key endpoint groups:

| Service         | Example Endpoints                    |
|----------------|------------------------------------|
| AuthService     | `/auth/google_oauth`, `/auth/token` |
| CourseService   | `/courses`, `/course`               |
| AssignmentService | `/assignments`, `/assignment`     |
| MaterialService | `/course_materials`, `/course_material` |
| ResponseService | `/response`, `/responses`           |
| RubricService   | `/rubric`, `/ai_rubric`             |
| UserService     | `/user`                             |

All **query params, request bodies, and paths** should match the backend **OpenAPI schema** or documentation.

---

## 📌 Additional Notes

- The current implementation uses a **placeholder token** (`const token = "123bob";`) in the Axios interceptor — this must be replaced with **dynamic token retrieval** (e.g., from `localStorage`, `next-auth`, or a secure context).
- Some API methods return **Axios responses directly** — consider wrapping with helper functions if transformation is needed.
- All interceptors and hooks are **frontend-compatible** and assume the code runs in a **Next.js environment**.

---

## 🚩 Next Steps

✅ Validate API endpoints  
✅ Replace placeholder auth token retrieval  
✅ Add Jest tests for API services and hooks  
✅ Integrate Google Analytics  
✅ Prepare dev usage examples

---

📝 Please ensure that **all endpoints are verified** against the backend API documentation.

