# Frontend Design Document for BU MET Autograder (Next.js)

## 1. Overview

This Next.js + Material UI application is an instructor-focused frontend for the BU MET Autograder API. It provides a comprehensive and modular interface for managing courses, assignments, rubrics, materials, and instructor collaboration while supporting a robust grading workflow.

### API Integration and Key Interactions

The frontend interacts directly with the BU MET Autograder API. Key actions correspond to specific API endpoints; for example:
- **User Authentication:** Login is managed via NextAuth with Google/Microsoft OAuth using endpoints such as `/auth/google_oauth`.
- **Course and Assignment Management:** Creating or editing courses and assignments leverages endpoints like `/course`, `/courses`, `/assignment`, and related sub-endpoints.
- **Grading and Rubric Management:** The grading interface uses endpoints (e.g., `/response/grade/all`, `/ai_rubric`) to process student submissions and provide AI-generated rubric suggestions.
- **Material Management:** File uploads and updates are conducted through endpoints such as `/course_material`.

Robust error handling is built into these interactions—if API requests fail or experience delays, the UI displays clear notifications and fallback states.

### Third-Party Integration Dependencies

Certain features depend on external integrations:
- **OAuth Authentication:** The login process uses Google and Microsoft OAuth. In cases where these services are unavailable or encounter issues, the application provides appropriate error messages and prompts for retry.
- **AI Rubric Suggestions:** AI-generated rubric enhancements are accessed via the `/ai_rubric` endpoint. If the AI integration fails, the system gracefully falls back to manual rubric management.
- **File Uploads:** Material management supports drag-and-drop file uploads. Errors such as exceeding file size limits or unsupported formats trigger clear notifications.

### Key Features

- **Course Management:** Create, edit, delete, and manually transfer course details and materials.
- **Assignment & Question Management:** Easily create assignments, add/edit/delete questions, and reorder them using intuitive drag-and-drop.
- **Rubric Management:** Define detailed, per-question sub-rubrics—including points, guidelines, and leniency—with optional AI-generated suggestions that instructors can review and customize.
- **Grading:** Support flexible grading modes (grade ungraded responses, regrade all, or grade specific students/questions) through a clear selection interface with visual cues and multi-selection capabilities.
- **Manual Student Submissions (for testing):** Allows instructors to manually submit student responses on a per-question basis to mimic real student inputs.
- **Material Management:** Upload and manage course files using an interactive, drag-and-drop interface.
- **Instructor Collaboration:** Add or remove co-instructors, with safeguards to prevent self-removal.
- **User Authentication & Settings:** Secure login via NextAuth with robust profile management and access token control.
- **Responsive & Themed UI:** A fully responsive layout with adaptive grids and centralized theming (light/dark modes) ensures a consistent, accessible, and user-friendly experience across all devices.

This design emphasizes a clean, modular architecture and an intuitive user experience, ensuring that developers can implement the frontend with clear guidance on API integration, error handling, and third-party dependency management—all without needing external diagrams or additional context.

---

## **2. High-Level User Flow**

This section outlines the primary user journey within the application, describing how users navigate through the frontend interface and interact with various features. For specific **API details and backend integration**, see **Section 5 (Feature Highlights & API Integration).**

---

### **2.1 Login & Authentication**
- **User Action:**  
  - Instructors log in via **Google or Microsoft OAuth**.
  - Upon successful login, they are redirected to the **Dashboard**.
- **Error Handling & Edge Cases:**  
  - Failed authentication (e.g., expired token) displays a retry message.
  - Unauthorized users are shown an access restriction notice.

---

### **2.2 Dashboard (`/dashboard`)**
- **Purpose:**  
  - Displays an overview of **courses**, **pending grading tasks**, and key statistics.
  - Provides quick navigation to **courses**, **assignments**, and **grading**.
- **Navigation:**  
  - Clicking a course redirects to **Course Detail (`/course/[id]`)**.
  - Quick access buttons navigate to **Settings**, **Manual Submission**, and **Grading**.

---

### **2.3 Course Management (`/courses`)**
- **Purpose:**  
  - Lists all courses accessible to the instructor.
  - Allows creation, deletion, and course transfer.
- **Navigation:**  
  - Clicking a course redirects to its **Course Detail Page**.
  - New courses can be created via a modal.

---

### **2.4 Course Detail (`/course/[id]`)**
The Course Detail page consists of multiple **sub-sections**, each accessible via tabs.

#### **a. Overview Tab**
- **Purpose:**  
  - Displays **course details, instructors, and key metrics**.
  - Provides a **"Transfer Course"** feature for moving materials from previous semesters.

#### **b. Assignments Tab**
- **Purpose:**  
  - Allows instructors to **create, edit, delete, and reorder assignments**.
  - Features a **drag-and-drop** interface for reordering questions.
- **Navigation:**  
  - Clicking an assignment opens a **detailed question view**.

#### **c. Materials Tab**
- **Purpose:**  
  - Provides an interface for **uploading, editing, and deleting** course materials.
  - Supports **drag-and-drop** file uploads.

#### **d. Rubrics Tab**
- **Purpose:**  
  - Enables **manual rubric creation** and **AI-assisted rubric suggestions**.
- **Navigation:**  
  - Rubrics are linked directly to assignments.

#### **e. Grading Tab**
- **Purpose:**  
  - Displays student submissions and allows grading via multiple modes.
  - Supports **batch grading**, **regrading**, and **grading specific students/questions**.
- **Navigation:**  
  - Selecting a response **opens a grading interface** for detailed review.

#### **f. Instructors Tab**
- **Purpose:**  
  - Enables **co-instructor management** (add/remove instructors).
- **Navigation:**  
  - Clicking an instructor profile provides role details.

---

### **2.5 Manual Student Submission (`/manual_submission`)**
- **Purpose:**  
  - Allows instructors to **simulate student responses** for testing purposes.
- **Navigation:**  
  - The UI provides **assignment and question selection** before submission.

---

### **2.6 Settings (`/settings`)**
- **Purpose:**  
  - Displays **user profile details** and allows **API token management**.
- **Navigation:**  
  - Includes logout functionality.

---

### **2.7 Error Handling & UI Resilience**
- **General Strategies:**  
  - **Network/API Failures:** Display retry prompts and meaningful error messages.  
  - **Access Restrictions:** Unauthorized users are redirected with a **403 notice**.  
  - **Empty States:** When no data exists (e.g., no assignments), the UI **shows clear guidance** instead of a blank screen.

## 3. Tech Stack

### 3.1 Core Frameworks & UI

| Technology            | Purpose                                                                 |
|-----------------------|-------------------------------------------------------------------------|
| **Next.js**           | Provides server-side rendering, static site generation, and file-based routing for enhanced performance and SEO. |
| **Material UI (MUI)** | Supplies a consistent UI framework with pre-built components, theming, and responsive design capabilities. |
| **NextAuth**          | Manages authentication using Google and Microsoft OAuth, ensuring secure user login. |

### 3.2 API Communication & State Management

| Technology         | Purpose                                                                 |
|--------------------|-------------------------------------------------------------------------|
| **Axios**          | Makes HTTP requests to communicate with the backend API for data fetching and submission. |
| **SWR**            | Provides caching, revalidation, and automatic data updates for API calls to improve performance. |
| **React Context**  | Offers lightweight global state management, such as for theme toggling. |
| **Zustand**        | Manages complex UI state (e.g., multi-selection in grading) in a scalable and maintainable way. |

### 3.3 UI Enhancements & Interactivity

| Technology             | Purpose                                                                 |
|------------------------|-------------------------------------------------------------------------|
| **react-beautiful-dnd**| Enables intuitive drag-and-drop functionality for reordering assignments and questions. |
| **React Hook Form**    | Streamlines form handling and validation, reducing re-renders and improving performance. |
| **Zod/Yup**            | Provides schema-based validation to ensure correct and robust form input handling. |

## 4. Project Files

### 4.1 Directory Hierarchy

```plaintext
frontend/
├── package.json
├── next.config.js
├── public/
│   ├── images/
│   │   └── example.png          # Example static asset
│   ├── icons/
│   │   └── favicon.ico          # Favicon
│   └── robots.txt               # SEO and crawler instructions
└── src/
    ├── config/
    │   └── config.js            # Global configuration including BACKEND_URL, OAuth keys, and app key for generating OAuth URLs for Google and Microsoft
    ├── components/
    │   ├── Layout.js            # Shared layout wrapping header and footer
    │   ├── Header.js            # Top navigation bar with integrated logout functionality, theme toggle, and account settings link
    │   ├── Footer.js            # Static footer with branding and useful links
    │   ├── ThemeToggle.js       # Light/dark mode toggle control
    │   ├── CardSkeleton.js      # Reusable loading placeholder
    │   ├── AISuggestionCard.js  # Displays AI-generated rubric suggestions
    │   ├── ConfirmationDialog.js# General-purpose confirmation dialog
    │   ├── SelectableList.js    # UI component supporting shift-click multi-selection
    │   └── GradingModeSelect.js # Dropdown for choosing grading mode
    ├── context/
    │   └── ThemeContext.js      # Provides global theme management
    ├── pages/
    │   ├── _app.js              # Global wrapper for pages, loading styles and context providers
    │   ├── login.js             # Implements user authentication via NextAuth (Google/Microsoft OAuth)
    │   ├── courses.js           # Displays list of accessible courses with options for creation and deletion
    │   ├── manual_submission.js # Dedicated interface for manual student submissions
    │   ├── course/
    │   │   └── [id]/
    │   │       ├── index.js         # Course overview and course transfer functionality
    │   │       ├── assignments.js   # Assignment and question management interface
    │   │       ├── materials.js     # Course material management UI
    │   │       ├── rubrics.js       # Rubric management with AI integration
    │   │       ├── grading.js       # Grading interface with multiple grading modes
    │   │       └── instructors.js   # Co-instructor management interface
    │   └── settings.js          # User profile and access token management
    ├── services/
    │   └── api.js               # Encapsulates Axios API calls and SWR hooks for backend communication
    ├── theme/
    │   └── theme.js             # Material UI theme configuration (colors, typography, breakpoints)
    ├── styles/
    │   ├── globals.css          # Global styling overrides
    │   └── variables.css        # CSS variables for consistent theming
```

### 4.2 File Explanations

- **`/src/config/config.js`**  
  Stores global configuration constants, including the BACKEND_URL, OAuth keys, and the app key required to generate OAuth URLs for Google and Microsoft authentication.

- **`/src/components/Layout.js`**  
  Provides a consistent page layout with a header (including logout functionality), footer, and main content area.

- **`/src/components/Header.js`**  
  Contains the top navigation bar with integrated logout, a theme toggle, and quick links to account settings.

- **`/src/components/Footer.js`**  
  Displays branding information and useful links at the bottom of the application.

- **`/src/components/ThemeToggle.js`**  
  Manages switching between light and dark modes and persists the user's theme preference.

- **`/src/components/CardSkeleton.js`**  
  Serves as a loading placeholder for lists and dynamic content areas.

- **`/src/components/AISuggestionCard.js`**  
  Presents AI-generated suggestions for rubric improvements in an interactive format.

- **`/src/components/ConfirmationDialog.js`**  
  A generic modal dialog used to confirm irreversible actions such as deletions.

- **`/src/components/SelectableList.js`**  
  Implements a multi-select list with shift-click support, utilized in the grading interface for selecting students or questions.

- **`/src/components/GradingModeSelect.js`**  
  Provides a dropdown for selecting various grading modes.

- **`/src/context/ThemeContext.js`**  
  Manages global theme state across the application.

- **`/src/pages/_app.js`**  
  The global wrapper that initializes context providers, applies global styles, and sets up the layout for all pages.

- **`/src/pages/login.js`**  
  Handles user authentication via NextAuth with Google and Microsoft OAuth.

- **`/src/pages/courses.js`**  
  Lists all courses available to the instructor and provides UI actions for course creation and deletion.

- **`/src/pages/manual_submission.js`**  
  Offers a dedicated interface for manually submitting student responses. Instructors can select the target assignment and question, enter the response data, and submit it through the API.

- **`/src/pages/course/[id]/index.js`**  
  Displays a course overview, including key course details and a feature for transferring course information and materials from a previous semester.

- **`/src/pages/course/[id]/assignments.js`**  
  Provides tools to create, edit, delete, and reorder assignments and questions via an intuitive UI.

- **`/src/pages/course/[id]/materials.js`**  
  Enables uploading, editing, and deleting course materials through an interactive interface.

- **`/src/pages/course/[id]/rubrics.js`**  
  Offers comprehensive management of per-question sub-rubrics, including point allocation, detailed guidelines, and integrated AI-generated suggestions.

- **`/src/pages/course/[id]/grading.js`**  
  Displays student submissions and supports multiple grading modes, including grading ungraded responses, regrading all submissions, and grading specific students or questions through a multi-select interface.

- **`/src/pages/course/[id]/instructors.js`**  
  Provides functionality for managing co-instructors, including adding or removing instructors with built-in safeguards.

- **`/src/pages/settings.js`**  
  Manages the user's profile details and access tokens, facilitating secure account management.

- **`/src/services/api.js`**  
  Contains functions for making API calls using Axios, as well as SWR hooks for efficient data fetching and updating.

- **`/src/theme/theme.js`**  
  Defines the Material UI theme, including color palettes, typography, and responsive breakpoints to ensure a consistent look and feel.

- **`/src/styles/globals.css`** and **`/src/styles/variables.css`**  
  Provide global style overrides and CSS variables to support consistent theming and layout adjustments throughout the application.

---



## **5. Feature Highlights & API Integration**

This section serves as a quick reference for frontend developers, mapping **key features** to their **corresponding API endpoints** and detailing error-handling strategies.

For an overview of the user experience and navigation, see **Section 2 (High-Level User Flow)**.

---

### **5.1 Instructor Management**
- **Feature:** Manage co-instructors (add or remove).
- **API Endpoints:**
  - `POST /course/instructor` (Add instructor)
  - `DELETE /course/instructor` (Remove instructor)
- **Error Handling:**
  - ❌ `403 Forbidden`: Unauthorized request.
  - ❌ `400 Bad Request`: Invalid instructor details.
  - ❌ Prevents self-removal (handled in UI).

---

### **5.2 Course Management & Transfer**
- **Feature:** Create, delete, and transfer courses across semesters.
- **API Endpoints:**
  - `POST /course` (Create course)
  - `DELETE /course` (Delete course)
  - `PATCH /course/transfer` (Transfer course details & materials)
- **Error Handling:**
  - ❌ `403 Forbidden`: Unauthorized instructor.
  - ❌ `404 Not Found`: Course does not exist.
  - ❌ `400 Bad Request`: Missing or invalid parameters.

---

### **5.3 Assignment Management**
- **Feature:** Create, edit, delete, and reorder assignments.
- **API Endpoints:**
  - `GET /assignments` (Fetch assignments)
  - `POST /assignment` (Create assignment)
  - `PATCH /assignment` (Modify assignment)
  - `DELETE /assignment` (Delete assignment)
- **Error Handling:**
  - ❌ `404 Not Found`: Assignment or course missing.
  - ❌ `403 Forbidden`: Unauthorized instructor.
  - ❌ **Cannot delete assignments with graded responses** (handled in UI).

---

### **5.4 Material Management**
- **Feature:** Upload, edit, and delete course materials.
- **API Endpoints:**
  - `GET /course_material` (Fetch materials)
  - `POST /course_material` (Upload material)
  - `DELETE /course_material` (Delete material)
- **Error Handling:**
  - ❌ `400 Bad Request`: Unsupported file format or size exceeded.
  - ❌ `404 Not Found`: Material does not exist.
  - ❌ **File upload failures trigger UI retry mechanisms**.

---

### **5.5 Rubric Management**
- **Feature:** Create/edit grading rubrics with optional AI suggestions.
- **API Endpoints:**
  - `GET /rubric` (Fetch rubric)
  - `PUT /rubric` (Create/update rubric)
  - `GET /ai_rubric` (AI-generated rubric suggestions)
- **Error Handling:**
  - ❌ `404 Not Found`: Rubric or assignment missing.
  - ❌ **If AI service fails, UI falls back to manual rubric input**.

---

### **5.6 Grading Interface**
- **Feature:** Grade student responses (batch or individual).
- **API Endpoints:**
  - `GET /responses` (Fetch responses)
  - `POST /response/grade/all` (Grade all)
  - `POST /response/grade/specific` (Grade specific students/questions)
- **Error Handling:**
  - ❌ `400 Bad Request`: Invalid grading request.
  - ❌ `404 Not Found`: No responses found.
  - ❌ **If grading API fails, UI provides a retry option**.

---

### **5.7 Manual Student Submission**
- **Feature:** Instructors submit test responses.
- **API Endpoints:**
  - `POST /response` (Submit response)
- **Error Handling:**
  - ❌ `400 Bad Request`: Invalid input or missing fields.
  - ❌ **Submissions validate against API before sending**.

---

### **5.8 Access Token Management & Profile**
- **Feature:** Manage API access tokens.
- **API Endpoints:**
  - `GET /auth/tokens` (Fetch user tokens)
  - `POST /auth/token` (Create token)
  - `DELETE /auth/token` (Delete token)
- **Error Handling:**
  - ❌ `403 Forbidden`: Unauthorized token access.
  - ❌ `400 Bad Request`: Invalid token name or request.

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

## **7. Error & Loading States**  

To ensure a smooth user experience, the frontend will provide **clear visual indicators** for loading and error states.  

All error handling and loading feedback will be **standardized across the application** to ensure **consistency and usability**.

### **7.1 Loading States**  

#### **Skeleton Placeholders**  
- The `CardSkeleton.js` component will be used for **loading placeholders** where lists of data are expected (e.g., courses, assignments, materials).  
- This ensures that content areas never appear blank while waiting for API responses.  
- Used in:  
  - **Course List (`/courses`)** – Displays skeleton loaders while fetching courses.  
  - **Assignments (`/course/[id]/assignments.js`)** – Shows skeletons for assignments while loading.  
  - **Materials (`/course/[id]/materials.js`)** – Displays placeholders for file uploads.  

#### **Loading Spinners**  
- For **interactive actions** (e.g., submitting a form, grading responses), **MUI’s CircularProgress** will be used.  
- Spinners will appear inside buttons or sections while an API request is in progress.  

#### **Related Files:**  
- **`/components/CardSkeleton.js`** – Provides reusable skeleton loaders for list views.  
- **`/components/GradingModeSelect.js`** – Displays spinners while grading API calls are in progress.  
- **`/components/ConfirmationDialog.js`** – Displays spinners when confirming deletions.  

### **7.2 Error Handling**  

#### **Snackbar Alerts**  
- API failures (e.g., `500 Internal Server Error`, `403 Forbidden`) will trigger **MUI Snackbar** alerts.  
- These will provide **real-time feedback** and automatically disappear after a few seconds.  
- Error messages will be **context-aware**, displaying **specific reasons** (e.g., "Invalid file format" instead of a generic error).  

#### **"No Data" Placeholders**  
- If an API request returns **empty results**, the UI will display a friendly message instead of a blank screen:  
  - `"No assignments yet"` in `/course/[id]/assignments.js`  
  - `"No materials uploaded"` in `/course/[id]/materials.js`  
  - `"No rubrics defined"` in `/course/[id]/rubrics.js`  
- **Custom placeholder icons** will be used to provide **visual clarity**.  

#### **Related Files:**  
- **`/components/ErrorSnackbar.js`** – Reusable Snackbar component for displaying error messages.  
- **`/components/ConfirmationDialog.js`** – Displays confirmation modals with built-in error handling.  
- **`/components/CardSkeleton.js`** – Handles placeholder loading states to prevent blank screens.

## 8. Conclusion

This design ensures a **clean**, **responsive**, and **instructor-focused** Next.js app. It leverages Material UI for theming, layout, and a consistent UX. By separating each domain (assignments, rubrics, materials, grading, instructors) into clear sub-routes, the codebase remains modular and easy to maintain, while providing all the features required by the **BU MET Autograder**.