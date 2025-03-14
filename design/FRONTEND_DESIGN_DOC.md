# Frontend Design Document for BU MET Autograder (Next.js)

## 1. Overview

This design document describes a consolidated and scalable **Next.js** frontend for the **BU MET Autograder API**. The application is:

- **Modern & Modular**: Organized by features (courses, assignments, rubrics, etc.)
- **Responsive & Beautiful**: Uses **Material UI** for a consistent, accessible design
- **Dark/Light Theming**: Toggle via React Context & MUI’s `ThemeProvider`
- **Role-Based (optional)**: Primarily for instructors, but can accommodate student flows if needed
- **All-in-One Course Page**: Each course can have sub-routes for materials, rubrics, and grading

## 2. High-Level User Flow

### 2.1. Main Page (Login)
- **Login with Google/Microsoft** (via NextAuth)
- On success, navigates to `/courses`

### 2.2. Course List Page (`/courses`)
- Displays all courses for the authenticated user (instructor)
- "Create New Course" + "Delete Course" actions
- **Instructor Management** (Add/Remove instructors for each course)
- Clicking a course navigates to its detail page (`/course/[id]`)
- **Top App Bar** includes:
  - User greeting
  - Dark/Light mode toggle
  - Link to **Account Settings** (`/settings`)

### 2.3. Course Detail Sub-Routes
Rather than a single giant page, we structure each feature as a sub-route for clarity:

- **`/course/[id]/index.js`**: Overview
  - Show basic info about the course (e.g., name, semester)
  - "Transfer Course" button to copy data from a previous semester
  - Links/tabs to Assignments, Materials, Rubrics, Grading

- **`/course/[id]/assignments.js`**
  - List all assignments
  - Create a new assignment (title, guidelines, etc.)
  - Add/remove/edit/reorder assignment questions
  - Possibly show partial data for student submissions or link to the grading page

- **`/course/[id]/materials.js`**
  - Upload course materials (docs, images, etc.)
  - Edit or replace materials
  - Delete materials
  - Drag-and-drop UI recommended
  - Error states for file size or format issues

- **`/course/[id]/rubrics.js`**
  - Manage rubric(s) for this course’s assignments
  - Create or edit rubrics (sub-rubrics, flags, leniency)
  - AI-based enhancements (`GET /ai_rubric`)
  - If question indexing is relevant, show how to retrieve or update only a specific question’s rubric

- **`/course/[id]/grading.js`**
  - View all student responses for the course or a specific assignment
  - Trigger grading (bulk or per-question) using AI or manual scoring
  - Show success/failure statuses and final grades/explanations

This sub-route approach ensures each feature is well-separated yet still under the relevant course.

### 2.4. Account Settings Page (`/settings`)
- **Access Token Management**
  - List existing tokens
  - Create new tokens
  - Delete tokens with confirmation
- Logout
- Return link to `/courses`

## 3. Tech Stack
- **Next.js** (enables SSR, SSG, easy page routing)
- **Material UI** (UI components, theming)
- **NextAuth** (OAuth for Google/Microsoft)
- **Axios + SWR** for data fetching and caching
- **React Context** for theme toggling
- **Vercel** for hosting

## 4. File Structure

```
frontend/
├── package.json
├── next.config.js
├── public/
│   └── ...
└── src/
    ├── config/
    │   └── config.js        # Contains BACKEND_URL
    ├── components/
    │   ├── Layout.js        # Shared layout w/ Header, Footer
    │   ├── Header.js
    │   ├── Footer.js
    │   ├── ThemeToggle.js
    ├── context/
    │   └── ThemeContext.js
    ├── pages/
    │   ├── _app.js          # Next.js root app wrapper
    │   ├── login.js         # Main login page
    │   ├── courses.js       # Lists user courses
    │   ├── course/
    │   │   └── [id]/
    │   │       ├── index.js       # Course overview + Transfer
    │   │       ├── assignments.js # Assignments Q&A mgmt
    │   │       ├── materials.js   # Course materials mgmt
    │   │       ├── rubrics.js     # Rubric mgmt
    │   │       └── grading.js     # Student responses & grading
    │   ├── settings.js      # Account tokens, logout
    ├── services/
    │   └── api.js           # Encapsulated API calls
    ├── theme/
    │   └── theme.js         # MUI theme config for light/dark
    ├── styles/
    │   └── globals.css      # Global CSS
    └── ...
```

## 5. Notable Features & Implementation Details

1. **Instructor Management**
   - In `/courses` or sub-page, a modal or inline form to add an instructor (`POST /course/instructor`) or remove one (`DELETE /course/instructor`).
   - Validation for duplicate or invalid emails.

2. **Course Transfer** (Under Course Overview)
   - "Transfer" button opens a modal to select old course/semester.
   - Calls `PATCH /course/transfer` on confirmation.
   - Updates local state with newly copied materials/rubrics.

3. **Assignments** (Under `/[id]/assignments.js`)
   - Provide CRUD for assignments & questions.
   - Show a list or table of questions; each row can be edited or reordered.

4. **Course Materials**
   - `/[id]/materials.js` for uploading, patching, and deleting (`POST`, `PATCH`, `DELETE /course_material`).
   - Drag-and-drop, progress bar, error handling.

5. **Rubrics**
   - `/[id]/rubrics.js` for creating or editing (`PUT /rubric`).
   - Show sub-rubrics in a table or list.
   - Provide AI enhancement (`GET /ai_rubric`) with optional instructor guidelines.

6. **Grading**
   - `/[id]/grading.js` for listing student responses (`GET /responses`) and triggering AI-based grading (`POST /response/grade/...`).
   - Possibly show partial or fully graded data.
   - Offer manual entry if AI not used.

7. **Access Token Management** (`/settings`)
   - List existing tokens, create new (`POST /auth/token`), delete (`DELETE /auth/token`).
   - Confirm actions with a dialog.

8. **Authentication Flow**
   - Using NextAuth, store user session, handle redirects after login.
   - Possibly map user roles (instructor/student) if needed.

9. **Error & Loading States**
   - Reusable loading spinners or skeletons.
   - Use MUI `Alert` or `Snackbar` for error messages.
   - Consistent approach across all pages.

## 6. Conclusion

By consolidating materials, rubrics, and grading into sub-routes of `/course/[id]`—and referencing them via dedicated `.js` files or a tabbed layout—the design avoids redundancy. Each feature is discoverable under its relevant course. For multi-role scenarios, we can expand similarly for students.

This refined design is **maintainable, intuitive, and thorough**, covering all major endpoints while providing a clear, modular user experience.

