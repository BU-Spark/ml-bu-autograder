Below is the **updated Frontend Design Document**, incorporating best practices for responsiveness, minimizing empty pages, maintaining modularity, and optionally integrating additional UI libraries with Material UI.

---

# Frontend Design Document for BU MET Autograder (Next.js)

## 1. Overview

This document describes a consolidated and scalable **Next.js** frontend for the **BU MET Autograder API**. The application is:

- **Modern & Modular**: Organized by features (courses, assignments, rubrics, etc.)
- **Responsive & Beautiful**: Uses **Material UI** (MUI) for a consistent, accessible design
- **Dark/Light Theming**: Toggle via React Context & MUI’s `ThemeProvider`
- **Role-Based (optional)**: Primarily for instructors, but can accommodate student flows if needed
- **All-in-One Course Page**: Each course can have sub-routes for materials, rubrics, grading, and instructor management
- **Note on Student Submissions**: Student uploads of responses (`POST/PUT/DELETE /response`) are **handled by a separate application** (using an access token). This frontend focuses on instructor features but can display student submissions for grading.

## 2. High-Level User Flow

### 2.1. Main Page (Login)
- **Login with Google/Microsoft** (via NextAuth)
- On success, navigates to `/courses`

### 2.2. Course List Page (`/courses`)
- Displays all courses for the authenticated user (instructor)
- "Create New Course" + "Delete Course" actions
- Clicking a course navigates to its detail page (`/course/[id]`)
- **Top App Bar** includes:
  - User greeting
  - Dark/Light mode toggle
  - Link to **Account Settings** (`/settings`)

### 2.3. Course Detail Sub-Routes

Each course contains several feature-based sub-routes. They can be organized with MUI `Tabs` or a side navigation to avoid having each page feel sparse:

- **`/course/[id]/index.js`**: Overview  
  - Show basic info about the course (e.g., name, semester)
  - "Transfer Course" button to copy data from a previous semester
  - Links/tabs to Assignments, Materials, Rubrics, Grading, Instructors

- **`/course/[id]/assignments.js`**
  - List all assignments
  - Create a new assignment (title, guidelines, etc.)
  - Add/remove/edit/reorder assignment questions
  - Consider using MUI’s [Skeleton](https://mui.com/material-ui/react-skeleton/) for loading states and “No assignments yet” placeholders if empty

- **`/course/[id]/materials.js`**
  - Upload course materials (docs, images, etc.)
  - Edit or replace materials
  - Delete materials
  - Handle empty or loading states gracefully with placeholders or illustrations

- **`/course/[id]/rubrics.js`**
  - Manage rubrics for this course’s assignments
  - AI-based enhancements (`GET /ai_rubric`)

- **`/course/[id]/grading.js`**
  - View all student responses (which are uploaded by a separate student-facing app)
  - Trigger grading using AI or manual scoring
  - Show partial or fully graded data
  - Use tabular views or card layouts to avoid an empty look

- **`/course/[id]/instructors.js`**
  - **Instructor Management (Add/Remove)**:  
    - Fetch list of current instructors (`GET /courses`)
    - Add an instructor (`POST /course/instructor`)
    - Remove an instructor (`DELETE /course/instructor`, with validation to prevent self-removal)

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
    │   └── config.js         # Contains BACKEND_URL
    ├── components/
    │   ├── Layout.js         # Shared layout w/ Header, Footer
    │   ├── Header.js
    │   ├── Footer.js
    │   ├── ThemeToggle.js
    ├── context/
    │   └── ThemeContext.js
    ├── pages/
    │   ├── _app.js           # Next.js root app wrapper
    │   ├── login.js          # Main login page
    │   ├── courses.js        # Lists user courses
    │   ├── course/
    │   │   └── [id]/
    │   │       ├── index.js        # Course overview + Transfer
    │   │       ├── assignments.js  # Assignments mgmt
    │   │       ├── materials.js    # Course materials mgmt
    │   │       ├── rubrics.js      # Rubric mgmt
    │   │       ├── grading.js      # Student responses & grading
    │   │       └── instructors.js  # Instructor management
    │   ├── settings.js       # Account tokens, logout
    ├── services/
    │   └── api.js            # Encapsulated API calls
    ├── theme/
    │   └── theme.js          # MUI theme config for light/dark
    ├── styles/
    │   └── globals.css       # Global CSS
    └── ...
```

## 5. Notable Features & Implementation Details

### 5.1. Instructor Management (`/course/[id]/instructors.js`)
- **Fetching Instructors**:
  - `GET /courses` to retrieve instructor emails for a specific course.
  
- **Adding an Instructor**:
  - `POST /course/instructor`
  - Input validation (email format)
  - Show errors for duplicate entries

- **Removing an Instructor**:
  - `DELETE /course/instructor`
  - Prevents removal of the logged-in instructor

### 5.2. Course Transfer (Under Course Overview)
- "Transfer" button opens a modal to select old course/semester.
- Calls `PATCH /course/transfer` on confirmation.

### 5.3. Assignments (`/course/[id]/assignments.js`)
- CRUD for assignments & questions.
- **Empty State**: If no assignments exist, provide a “No assignments yet” message plus an “Add Assignment” button.

### 5.4. Course Materials (`/course/[id]/materials.js`)
- Uploading, patching, and deleting course materials.
- **Drag-and-Drop** or file upload with a progress bar for better user experience.

### 5.5. Rubrics (`/course/[id]/rubrics.js`)
- Create or edit rubrics, including sub-rubrics and flags
- AI-based improvement with `GET /ai_rubric`

### 5.6. Grading (`/course/[id]/grading.js`)
- View student responses (uploaded by a separate student portal)
- Trigger AI grading or do manual scoring
- **Batch** or **per-question** grading endpoints

### 5.7. Access Token Management (`/settings`)
- Create/delete API tokens
- Confirm token removal with MUI `Dialog` or `AlertDialog`

### 5.8. Authentication Flow
- **NextAuth** for OAuth
- Ensures only instructors can access course-management endpoints

### 5.9. Error & Loading States
- Use MUI `Alert` or `Snackbar` for errors
- Use [Skeleton](https://mui.com/material-ui/react-skeleton/) or custom spinners for loading

## 6. Color Scheme
You can implement a simple light/dark palette in `theme.js`:

- **Light Mode**  
  - Primary: `#1976d2`  
  - Secondary: `#ff6f00`  
  - Background: `#fafafa`  
  - Paper: `#ffffff`  
  - Text (primary): `#212121`

- **Dark Mode**  
  - Primary: `#90caf9`  
  - Secondary: `#ffb74d`  
  - Background: `#121212`  
  - Paper: `#1e1e1e`  
  - Text (primary): `#ffffff`

Tailor these to BU or departmental branding as needed.

## 7. Additional Best Practices

### 7.1. Responsiveness
- **MUI Grid & Breakpoints**: Use responsive layout features (`xs`, `sm`, `md`, etc.) to ensure pages adapt to mobile, tablet, and desktop.  
- **Responsive Typography**: Enable fluid font sizing in the MUI theme or with [responsiveFontSizes](https://mui.com/material-ui/customization/typography/#responsive-font-sizes).

### 7.2. Minimizing Empty Pages
- **Tabs or Accordions**: Consolidate small features into tabbed sections instead of separate pages.  
- **Empty States**: Show placeholders when data is missing (“No assignments,” “No materials,” etc.) plus a clear call-to-action to create or upload.  
- **Skeleton Loading**: Prevent blank screens by showing skeletons while data is fetched.

### 7.3. Maintainability & Modularity
- **Feature-Based File Organization**: Keep code for each feature (Courses, Assignments, Instructors, etc.) grouped logically.  
- **Reusable Components**: Abstract repeated patterns into shared components (e.g., common forms, repetitive layouts).  
- **API Encapsulation**: Keep data-fetching in `services/api.js`, so changes to endpoints don’t ripple through the entire UI.

### 7.4. Pairing MUI with Other Libraries
- **Consistency**: If using a second UI library (e.g., a specialized design system), unify color palettes and spacing for consistency.  
- **Custom MUI Themes**: Often enough to achieve a unique look without mixing libraries.  
- **Performance**: Additional libraries can add overhead, so evaluate your performance budget.

---

## 8. Conclusion

This **Next.js + Material UI** design remains **modular**, **responsive**, and easily maintainable. It consolidates major instructor-facing features (Assignments, Rubrics, Materials, Grading, Instructor Management) into clear sub-routes or tabbed sections. We also handle empty states and loading states with MUI components to keep the app visually appealing. Student submissions remain in a **separate** application using the provided access tokens, ensuring a clear division of concerns.