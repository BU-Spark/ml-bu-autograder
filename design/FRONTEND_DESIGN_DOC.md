# Frontend Design Document for BU MET Autograder (Next.js)

## 1. Overview

This Next.js + Material UI application is an instructor-focused frontend for the BU MET Autograder API. Designed to integrate seamlessly with the updated API endpoints, it offers a comprehensive and modular interface for managing courses, assignments, rubrics, materials, and student submissions—all while supporting a flexible, robust grading workflow.

### API Integration and Key Interactions

All API requests now use the `/api/v1/` prefix to ensure consistent routing, and the base backend URL is centrally defined in the configuration file (`/src/config/config.js`). This approach enables a single point of update for deployment across different environments. Key interactions include:

- **User Authentication & Token Management:**  
  - **Authentication:** Instructors sign in using NextAuth with Google or Microsoft OAuth via the `/api/v1/auth/google_oauth` endpoint.  
  - **Token Management:** Secure API access is maintained by creating tokens using POST `/api/v1/auth/token`, listing them via GET `/api/v1/auth/tokens`, and deleting tokens with DELETE `/api/v1/auth/token`. Token values are shown only once at creation for security.

- **Course Management:**  
  - Courses are created, edited, and deleted through endpoints like `/api/v1/course` and `/api/v1/courses`.  
  - Course transfer operations (moving materials and course details between semesters) are executed via PATCH `/api/v1/course/transfer`.

- **Assignment & Question Management:**  
  - Assignments are managed using endpoints such as POST `/api/v1/assignment` for creation, with editing and deletion supported by corresponding endpoints.  
  - The intuitive drag-and-drop interface for reordering questions sends a PATCH request to `/api/v1/assignment/modify_order` with a payload specifying the new question order.

- **Rubric Management:**  
  - The Rubrics Tab now features a dedicated panel for managing subrubrics and grading criteria. Instructors can add, edit, and delete subrubrics and their associated grading criteria through interactive UI elements.  
  - All rubric modifications are saved by sending a PUT request to `/api/v1/rubric`, which accepts the complete rubric payload (including subrubrics and grading criteria).  
  - Additionally, AI-assisted rubric enhancements are available via GET `/api/v1/ai_rubric`, with a fallback to manual entry if needed.

- **Material Management:**  
  - Course materials are handled consistently: fetching all materials via GET `/api/v1/course_materials` (plural) returns file references, while individual material operations (upload, update, delete) use `/api/v1/course_material` (singular).

- **Student Submission Management:**  
  - Beyond manual test submissions, the application now includes a dedicated dashboard for managing actual student responses.  
  - Instructors can view, filter, and review detailed submissions fetched from GET `/api/v1/responses`.  
  - Grading actions are integrated via endpoints such as POST `/api/v1/response/grade/ungraded` (for grading all ungraded responses), POST `/api/v1/response/grade/specific`, and POST `/api/v1/response/grade/all`.

- **Instructor Collaboration:**  
  - Managing co-instructors is facilitated via POST `/api/v1/course/instructor` (to add an instructor) and DELETE `/api/v1/course/instructor` (to remove an instructor), with built-in safeguards to prevent self-removal.

### Third-Party Dependencies and Error Handling

The application leverages external integrations for OAuth authentication and AI-generated rubric suggestions. Robust error handling is implemented across all interactions:
- **Authentication Failures:** Clear error messages and retry prompts guide users through any login issues.
- **API Errors:** Inline validation messages and notification alerts inform instructors of issues like invalid inputs or request failures.
- **File Upload Issues:** Drag-and-drop file uploads include checks for size and format, with UI retry options if uploads fail.
---

## 2. High-Level User Flow

This section outlines the primary user journey within the application, detailing how instructors navigate the interface and interact with its various features. Note that all API calls use the `/api/v1/` prefix and the base backend URL is defined in the centralized configuration file (`/src/config/config.js`), ensuring consistent routing across environments.

### 2.1 Login & Authentication
- **User Action:**  
  - Instructors log in using NextAuth with Google or Microsoft OAuth.
  - Upon successful authentication via the `/api/v1/auth/google_oauth` endpoint, they are redirected to the Dashboard.
- **Error Handling:**  
  - Failed logins (e.g., expired tokens) trigger clear error messages with retry prompts.
  - Unauthorized access results in a notice and redirection.

### 2.2 Dashboard (`/dashboard`)
- **Purpose:**  
  - Provides an overview of courses, pending grading tasks, and key statistics.
  - Offers quick navigation to Course Management, Assignments, Rubric Updates, and the Student Submission Dashboard.
- **Navigation:**  
  - Clicking a course takes users to the Course Detail page.
  - Quick access buttons direct users to Settings, Manual Test Submissions, and grading modules.

### 2.3 Course Management (`/courses`)
- **Purpose:**  
  - Lists all courses available to the instructor.
  - Facilitates course creation, deletion, and transfer between semesters.
- **Navigation:**  
  - Selecting a course redirects to its detailed view.
  - New courses can be added via a modal interface.

### 2.4 Course Detail (`/course/[id]`)
The Course Detail page is organized into several tabs:
- **Overview Tab:**  
  - Displays course details, instructor lists, and key metrics.
  - Includes a “Transfer Course” feature to migrate materials from previous semesters.
- **Assignments Tab:**  
  - Enables creation, editing, deletion, and reordering of assignments.
  - Reordering is handled through a drag-and-drop interface that sends a PATCH request to `/api/v1/assignment/modify_order`.
- **Materials Tab:**  
  - Provides an interface for uploading, editing, and deleting course materials via drag-and-drop.
- **Rubrics Tab:**  
  - Contains a dedicated panel for managing subrubrics and grading criteria.
  - Instructors can manually create or edit rubric details, with changes submitted via a PUT request to `/api/v1/rubric`.
- **Grading Tab:**  
  - Displays student submissions and supports various grading modes including batch grading, regrading, and targeted grading via endpoints like `/api/v1/response/grade/ungraded`, `/api/v1/response/grade/specific`, and `/api/v1/response/grade/all`.
- **Instructors Tab:**  
  - Allows for co-instructor management using add/remove features with safeguards to prevent self-removal.

### 2.5 Student Submission Management Dashboard
- **Purpose:**  
  - Provides a dedicated interface for managing actual student responses beyond test submissions.
  - Instructors can view, filter, and sort submissions by assignment, student, or question.
  - Detailed views allow for in-depth review of each submission, along with integrated grading actions.
- **Navigation & Integration:**  
  - Submissions are fetched using GET `/api/v1/responses`.
  - Grading and regrading actions are linked to the respective grading endpoints.
- **Error Handling:**  
  - API errors trigger inline notifications and retry options, ensuring a smooth user experience.

### 2.6 Manual Student Submission (`/manual_submission`)
- **Purpose:**  
  - Facilitates test submissions by instructors to simulate student responses.
- **Navigation:**  
  - Users select the target assignment and question before submitting test data.
- **Note:**  
  - This feature is separate from the main submission management dashboard, which handles live student data.

### 2.7 Settings (`/settings`)
- **Purpose:**  
  - Displays user profile details and manages API tokens.
  - Provides options for token creation (via POST `/api/v1/auth/token`), listing (GET `/api/v1/auth/tokens`), and deletion (DELETE `/api/v1/auth/token`).
- **Navigation:**  
  - Includes logout functionality and access to other profile settings.

### 2.8 Error Handling & UI Resilience
- **Strategies:**  
  - **Network/API Failures:** Display clear, actionable retry prompts.
  - **Access Restrictions:** Unauthorized access is managed with a 403 notice and appropriate redirections.
  - **Empty States:** In cases of missing data (e.g., no assignments or submissions), the UI presents guided messaging to help users navigate next steps.


## 3. Tech Stack

The BU MET Autograder frontend leverages a modern, scalable tech stack designed for efficiency, responsiveness, and seamless API integration. The base backend URL is centrally defined in `/src/config/config.js`, ensuring consistent routing across environments.

### 3.1 Core Frameworks & UI
- **Next.js:** Provides server-side rendering, static site generation, and file-based routing to enhance performance, SEO, and maintainability.
- **Material UI (MUI):** Supplies a comprehensive UI framework with pre-built components, centralized theming (including light/dark modes), and responsive design capabilities.
- **NextAuth:** Facilitates secure authentication via Google and Microsoft OAuth, integrating seamlessly with the API endpoints.

### 3.2 API Communication & State Management
- **Axios:** Handles HTTP requests to the backend API, automatically using the base URL from the configuration file for consistency.
- **SWR:** Implements efficient data fetching with built-in caching, revalidation, and automatic updates to keep the UI responsive.
- **React Context:** Manages lightweight global state, such as theme settings and user preferences.
- **Zustand:** Supports more complex UI state management, such as multi-selection in grading interfaces, in a scalable and maintainable way.

### 3.3 UI Enhancements & Interactivity
- **react-beautiful-dnd:** Enables intuitive drag-and-drop functionality for reordering assignments and questions.
- **React Hook Form:** Streamlines form handling and validation, reducing unnecessary re-renders and improving performance.
- **Zod/Yup:** Provides schema-based validation to ensure that all form inputs meet the required standards and reduce errors.

## 4. Project Files

This section details the organization of the project’s source code and assets, ensuring that developers can quickly locate and understand each component. The structure is designed for clarity, scalability, and ease of maintenance. Note that the base backend URL is centrally defined in `/src/config/config.js`.

### 4.1 Directory Structure

```
frontend/
├── package.json                  # Project metadata and dependencies.
├── next.config.js                # Next.js configuration settings.
├── public/                       # Static assets accessible by the client.
│   ├── images/                   # Example images and other static graphics.
│   ├── icons/                    # Favicon and other icon assets.
│   └── robots.txt                # SEO and crawler instructions.
└── src/
    ├── config/
    │   └── config.js             # Central configuration file (includes BACKEND_URL, OAuth keys, etc.).
    ├── components/               # Reusable UI components.
    │   ├── Layout.js             # Shared layout that wraps pages with header and footer.
    │   ├── Header.js             # Top navigation bar with logout, theme toggle, and settings links.
    │   ├── Footer.js             # Displays branding and useful links at the bottom of the app.
    │   ├── ThemeToggle.js        # Allows users to switch between light and dark modes.
    │   ├── CardSkeleton.js       # Provides placeholder skeletons for loading states.
    │   ├── AISuggestionCard.js   # Displays AI-generated rubric suggestions for instructors.
    │   ├── ConfirmationDialog.js # Modal dialog for confirming irreversible actions (e.g., deletions).
    │   ├── SelectableList.js     # Implements a multi-selection list with shift-click support.
    │   └── GradingModeSelect.js  # Dropdown component for selecting grading modes.
    ├── context/
    │   └── ThemeContext.js       # Global state management for theming and layout preferences.
    ├── pages/                    # Application pages using Next.js file-based routing.
    │   ├── _app.js               # Global wrapper for all pages; initializes providers, layouts, and global styles.
    │   ├── login.js              # Handles user authentication via NextAuth (Google/Microsoft OAuth).
    │   ├── courses.js            # Displays the list of courses; includes options for course creation and deletion.
    │   ├── manual_submission.js  # Provides an interface for instructors to simulate student submissions.
    │   ├── course/               # Dynamic course-related pages.
    │   │   └── [id]/
    │   │       ├── index.js          # Course overview page; displays key details and supports course transfer.
    │   │       ├── assignments.js    # Manages assignments and questions, including creation, editing, and reordering.
    │   │       ├── materials.js      # Interface for uploading, editing, and deleting course materials.
    │   │       ├── rubrics.js        # Rubric management page; enables manual rubric creation and AI suggestions.
    │   │       ├── grading.js        # Provides various grading modes and detailed views for student submissions.
    │   │       └── instructors.js    # Manages co-instructor assignments with safeguards (e.g., preventing self-removal).
    │   └── settings.js           # User profile management page; includes API token creation, listing, and deletion.
    ├── services/
    │   └── api.js                # Encapsulates Axios API calls and SWR hooks for interacting with the backend.
    ├── theme/
    │   └── theme.js              # Configures Material UI theme settings (colors, typography, breakpoints).
    └── styles/
        ├── globals.css           # Global CSS overrides that apply throughout the application.
        └── variables.css         # Defines CSS variables for consistent theming and styling across components.
```

### 4.2 File Explanations

- **Configuration (`/src/config/config.js`):**  
  Centralizes key settings such as the backend URL, OAuth keys, and other environment-specific variables. This file is the single source of truth for configuring API endpoints and external services.

- **Components (`/src/components/`):**  
  Contains reusable UI components used throughout the application:
  - **Layout.js:** Provides a consistent page layout including header, footer, and main content area.
  - **Header.js & Footer.js:** Manage the top navigation bar and bottom branding/information respectively.
  - **ThemeToggle.js:** Enables users to switch between light and dark modes.
  - **CardSkeleton.js:** Used as a loading placeholder for list views and data-driven components.
  - **AISuggestionCard.js:** Displays AI-generated rubric suggestions to aid instructors in refining grading rubrics.
  - **ConfirmationDialog.js:** A modal dialog for confirming irreversible actions such as deletions.
  - **SelectableList.js:** Supports multi-selection features, particularly useful in the grading interface.
  - **GradingModeSelect.js:** Offers a dropdown menu to select different grading modes.

- **Context (`/src/context/ThemeContext.js`):**  
  Provides global state management for theme-related settings, ensuring a consistent user experience across all pages.

- **Pages (`/src/pages/`):**  
  Implements the different views of the application using Next.js routing:
  - **_app.js:** Wraps all pages with global providers (e.g., ThemeContext), applies global styles, and integrates the common layout.
  - **login.js:** Manages user authentication via NextAuth, handling OAuth flows for Google and Microsoft.
  - **courses.js:** Displays a list of courses, offering functionality to create or delete courses.
  - **manual_submission.js:** Allows instructors to simulate student submissions for testing purposes.
  - **course/[id]/:**
    - **index.js:** Serves as the course overview page, showing course details and providing a feature to transfer course data from previous semesters.
    - **assignments.js:** Manages assignment and question operations, including creation, editing, deletion, and drag-and-drop reordering (integrated with `/api/v1/assignment/modify_order`).
    - **materials.js:** Provides an interface for managing course materials through file uploads, updates, and deletions.
    - **rubrics.js:** Focuses on rubric management, allowing manual editing and AI-assisted suggestions (with changes submitted via `/api/v1/rubric`).
    - **grading.js:** Displays student submissions and supports various grading workflows, connecting to endpoints for grading responses.
    - **instructors.js:** Handles the management of co-instructors, using endpoints for adding and removing instructors while preventing self-removal.
  - **settings.js:** Facilitates user profile management, including the creation, display, and deletion of API tokens via dedicated endpoints.

- **Services (`/src/services/api.js`):**  
  Contains functions for API interactions using Axios and SWR. This abstraction layer automatically uses the base URL from the config file and simplifies data fetching and error handling across the app.

- **Theme (`/src/theme/theme.js`):**  
  Defines the Material UI theme for the application. It sets up color palettes, typography, and breakpoints to ensure a consistent look and feel.

- **Styles (`/src/styles/`):**  
  Includes:
  - **globals.css:** Provides global CSS rules and resets to maintain design consistency.
  - **variables.css:** Defines CSS variables for colors, fonts, and spacing that are used throughout the project.

## 5. Feature Highlights & API Integration

This section maps key features of the frontend to their corresponding API endpoints and explains how the UI integrates with the backend. All API calls use the `/api/v1/` prefix, with the base backend URL defined in `/src/config/config.js`. Robust error handling and fallback mechanisms are incorporated to ensure a seamless user experience.

### 5.1 User Authentication & Token Management
- **Features:**
  - **User Login:** Instructors authenticate via Google or Microsoft OAuth using NextAuth.
  - **API Token Handling:** Create, list, and delete access tokens for secure API interactions.
- **API Endpoints:**
  - **OAuth Callback:** GET `/api/v1/auth/google_oauth`
  - **Create Token:** POST `/api/v1/auth/token`
  - **List Tokens:** GET `/api/v1/auth/tokens`
  - **Delete Token:** DELETE `/api/v1/auth/token`
- **Error Handling:**
  - Display clear messages for authentication failures and invalid token operations.
  - Token values are shown only once during creation for security.

### 5.2 Course Management & Transfer
- **Features:**
  - **Course Operations:** Create, view, and delete courses.
  - **Course Transfer:** Migrate course materials and details between semesters.
- **API Endpoints:**
  - **Create Course:** POST `/api/v1/course`
  - **Delete Course:** DELETE `/api/v1/course`
  - **List Courses:** GET `/api/v1/courses`
  - **Transfer Course:** PATCH `/api/v1/course/transfer`
- **Error Handling:**
  - Handle 403 (unauthorized) and 404 (course not found) errors with appropriate UI notifications.

### 5.3 Assignment & Question Management
- **Features:**
  - **Assignment Creation & Editing:** Manage assignments and associated questions.
  - **Question Reordering:** Use an intuitive drag-and-drop interface to reorder questions.
- **API Endpoints:**
  - **Create Assignment:** POST `/api/v1/assignment`
  - **Edit/Delete Assignment:** (Corresponding endpoints for updating and deleting)
  - **Reorder Questions:** PATCH `/api/v1/assignment/modify_order`  
    - **Payload Example:** Includes `semester`, `course_id`, `assignment_id`, and an ordered list of question indexes.
- **Error Handling:**
  - Inline validation for editing errors and alerts for failures in reordering requests.

### 5.4 Rubric Management & Subrubric/Grading Criteria UI
- **Features:**
  - **Rubric Creation:** Define overall grading guidelines and per-question subrubrics.
  - **Subrubric and Grading Criteria Management:** Add, edit, and delete subrubrics along with associated grading criteria.
  - **AI-Enhanced Rubric Suggestions:** Option to retrieve AI-generated enhancements.
- **API Endpoints:**
  - **Create/Update Rubric:** PUT `/api/v1/rubric`
  - **Fetch Rubric:** GET `/api/v1/rubric`
  - **AI Rubric Suggestions:** GET `/api/v1/ai_rubric`
- **Error Handling:**
  - Validate inputs for grading criteria and display inline error messages.
  - Provide fallback to manual entry if the AI service fails.

### 5.5 Material Management
- **Features:**
  - **File Operations:** Upload, edit, and delete course materials.
  - **Data Handling:** Fetch all course materials as file references.
- **API Endpoints:**
  - **Fetch Materials:** GET `/api/v1/course_materials` (returns a list of file references)
  - **Single Material Operations:**  
    - **Upload Material:** POST `/api/v1/course_material`
    - **Update Material:** PATCH `/api/v1/course_material`
    - **Delete Material:** DELETE `/api/v1/course_material`
- **Error Handling:**
  - Manage errors like unsupported file formats or size limits with clear UI prompts and retry options.

### 5.6 Student Submission Management
- **Features:**
  - **Dashboard View:** A dedicated interface for managing live student submissions.
  - **Detailed Submission Review:** View, filter, and sort submissions by assignment, student, or question.
  - **Grading Actions:** Grade ungraded responses, or regrade specific or all responses.
- **API Endpoints:**
  - **Fetch Submissions:** GET `/api/v1/responses`
  - **Grade Specific Submissions:** POST `/api/v1/response/grade/specific`
  - **Grade All or Ungraded Submissions:**  
    - POST `/api/v1/response/grade/all`  
    - POST `/api/v1/response/grade/ungraded`
- **Error Handling:**
  - Use inline notifications and retry options for API failures.
  - Display empty states with guidance when no submissions are available.

### 5.7 Instructor Collaboration
- **Features:**
  - **Co-Instructor Management:** Add or remove instructors from a course.
- **API Endpoints:**
  - **Add Instructor:** POST `/api/v1/course/instructor`
  - **Remove Instructor:** DELETE `/api/v1/course/instructor`
- **Error Handling:**
  - Prevent self-removal and provide error messages for unauthorized actions or missing parameters.

### 5.8 Error & Loading States
- **General Strategy:**
  - **Error Handling:** Uniform handling of API errors with contextual alerts (e.g., Snackbar notifications) and inline validation.
  - **Loading Feedback:** Use skeleton loaders (via `CardSkeleton.js`) and spinners (using MUI’s CircularProgress) to indicate active processes.

---

## **6. Responsiveness & Theming**  

This section details how the frontend ensures **responsiveness**, **consistent theming**, and **usability across different screen sizes and devices**. The application leverages **Material UI (MUI)’s** grid system, theme provider, and CSS utilities to maintain a **consistent user experience**.

### **6.1 Responsive Layouts with Material UI**  

The frontend dynamically adapts to different screen sizes using **MUI’s Grid system, breakpoints, and responsive components**. The goal is to **maintain usability across desktops, tablets, and mobile devices**.

#### **a. Adaptive Grid System**
The app follows a **column-based layout** that adjusts automatically:

| Screen Size | Layout Behavior |
|------------|----------------|
| **Desktop (≥960px)** | Multi-column layouts with full sidebar visibility. |
| **Tablet (600px – 960px)** | Two-column layouts; sidebars may collapse. |
| **Mobile (<600px)** | Single-column layouts; collapsible navigation. |

- **Assignments, courses, and grading views** display as a **grid-based list** that dynamically resizes based on screen width.
- **Side navigation panels (filters, grading settings)** automatically **collapse into drawers** on smaller screens.

#### **b. Component Resizing & Visibility Adjustments**
- **Forms & Dialogs:**  
  - Automatically **resize** (`maxWidth="sm" | "md" | "lg"`) for better readability.
  - Prevent overflow on smaller screens by ensuring modal content is scrollable.
  
- **Navigation Adjustments:**  
  - The main navigation **collapses into a drawer** on mobile.  
  - The grading interface **adapts dynamically**, ensuring all controls remain accessible.

- **Touch & Click Support:**  
  - **Drag-and-drop (react-beautiful-dnd)** is optimized for **both touch and mouse input**.
  - **Keyboard navigation is fully supported** for accessibility.

### **6.2 Theming & Customization**  

All styling is **centrally managed** in the **Material UI ThemeProvider** (`/theme/theme.js`), ensuring a **consistent look and feel**.

#### **a. Theme Customization**
- **Typography, colors, and spacing** are defined in a **single theme object**, ensuring all UI elements stay visually consistent.
- **Global overrides** allow seamless adjustments without modifying individual components.

#### **b. Light/Dark Mode Support**
- Users can switch between **Light Mode** and **Dark Mode** via a **persistent theme toggle**.
- The setting is stored in **local storage**, ensuring user preference is saved across sessions.

| Mode | Primary Colors | Background Colors |
|------|--------------|----------------|
| **Light Mode** | `#1976d2` (blue), `#ff6f00` (orange) | `#fafafa` (light gray) |
| **Dark Mode** | `#90caf9` (light blue), `#ffb74d` (soft orange) | `#121212` (deep gray-black) |

#### **c. CSS Variables for Theming**
- Key values (such as primary colors and font sizes) are defined using **CSS variables**, making them easy to modify in `/theme/theme.js`.
- This allows **brand customization without modifying individual components**.

### **6.3 Performance Optimizations**  

#### **a. Lazy Loading for Heavy Components**
- **Large lists (assignments, courses, responses)** use **virtualized rendering** to prevent unnecessary re-renders.
- **Dialogs, modals, and forms** load only when needed (`lazy()` imports in Next.js).

#### **b. Optimized CSS Rendering**
- **Material UI’s styling engine** ensures that only **critical styles are loaded per page**.
- **Global styles** are minimized to prevent layout shifts.

#### **c. Image Optimization**
- **Next.js Image Component (`next/image`)** handles:
  - **Automatic lazy loading** for improved performance.
  - **Format optimization** (WebP, AVIF) to reduce load times.

### **6.4 Accessibility Considerations**  

Ensuring an **inclusive user experience** by adhering to **WCAG standards**.

#### **a. Keyboard & Screen Reader Support**
- All **interactive elements** (buttons, forms, modals) include **ARIA labels** for accessibility.
- Full **keyboard navigation** is supported across the app.

#### **b. High-Contrast Mode & Color Accessibility**
- The color scheme ensures **sufficient contrast for readability**.
- **Form error messages and alerts** follow **accessibility best practices**.

---

## 7. Error & Loading States

This section defines the strategies for handling errors and indicating loading states throughout the application. It covers all aspects of the UI—from course and assignment operations to token management, rubric modifications (including subrubrics and grading criteria), and the student submission dashboard—ensuring a seamless user experience.

### 7.1 Loading States

- **Skeleton Placeholders:**  
  - The `CardSkeleton.js` component is used to display loading placeholders when fetching lists of courses, assignments, materials, or student submissions. This ensures that content areas are never blank while data is loading.
  - Specific pages like the student submission dashboard and the rubric management panel (especially when fetching AI-generated suggestions via `/api/v1/ai_rubric`) utilize these skeletons.

- **Loading Spinners:**  
  - For interactive actions—such as form submissions, grading requests, or token creation—the UI displays spinners using MUI’s CircularProgress.  
  - These spinners appear within buttons or specific sections to provide immediate feedback during network calls.

- **Additional Considerations:**  
  - Loading indicators are also applied during actions such as file uploads, token management operations, and API calls for rubric updates, ensuring users are informed of background processes.

### 7.2 Error Handling

- **Uniform Notification System:**  
  - All API failures trigger context-aware alerts, typically implemented using MUI Snackbar notifications. These alerts provide specific error messages (e.g., “Invalid file format” for material uploads, “Authentication failed” for login issues, or “Unable to retrieve AI rubric suggestions”) and often include actionable options such as retry buttons.
  
- **Inline Validation:**  
  - For operations like assignment editing, rubric updates, or token management, inline validation messages are shown to indicate errors such as missing required fields, invalid formats, or parameter mismatches.
  
- **Specific API Error Handling:**  
  - **User Authentication & Token Management:** Errors during token creation (POST `/api/v1/auth/token`) or deletion (DELETE `/api/v1/auth/token`) prompt clear error messages and guide the user on corrective steps.
  - **Rubric Management:** When updating rubrics via PUT `/api/v1/rubric` or fetching AI suggestions via GET `/api/v1/ai_rubric`, any errors trigger a fallback mechanism that allows the instructor to manually edit the rubric.  
  - **Student Submission Dashboard:** Errors from GET `/api/v1/responses` or grading endpoints (such as POST `/api/v1/response/grade/all` and POST `/api/v1/response/grade/ungraded`) display detailed error states with options to refresh or retry the operation.
  - **General Network/API Failures:** In all cases—whether for course operations, assignment reordering, material uploads, or instructor management—errors like 403 (unauthorized), 404 (not found), 400 (bad request), or 502 (external API failures) are handled uniformly with contextual alerts.

- **Empty States:**  
  - In scenarios where no data is available (e.g., no courses, no submissions, or no tokens), the UI presents informative messages with guidance on next steps, ensuring that users understand the context and know how to proceed.

## 8. Conclusion

This design ensures a **clean**, **responsive**, and **instructor-focused** Next.js app. It leverages Material UI for theming, layout, and a consistent UX. By separating each domain (assignments, rubrics, materials, grading, instructors) into clear sub-routes, the codebase remains modular and easy to maintain, while providing all the features required by the **BU MET Autograder**.