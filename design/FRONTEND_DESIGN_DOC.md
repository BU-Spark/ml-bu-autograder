# Frontend Design Document for BU MET Autograder (Next.js)

## 1. Overview

This Next.js + Material UI application is an instructor-focused frontend for the BU MET Autograder API. It provides a comprehensive and modular interface for managing courses, assignments, rubrics, materials, and instructor collaboration while supporting a robust grading workflow. Key features include:

- **Course Management:** Create, edit, delete, and manually transfer course details and materials.
- **Assignment & Question Management:** Easily create assignments, add/edit/delete questions, and reorder them using intuitive drag-and-drop.
- **Rubric Management:** Define detailed, per-question sub-rubrics—including points, guidelines, and leniency—with optional AI-generated suggestions that instructors can review and customize.
- **Grading:** Support flexible grading modes (grade ungraded responses, regrade all, or grade specific students/questions) through a clear selection interface, with visual cues and multi-selection capabilities.
- **Material Management:** Upload and manage course files using an interactive, drag-and-drop interface.
- **Instructor Collaboration:** Add or remove co-instructors, with safeguards to prevent self-removal.
- **User Authentication & Settings:** Secure login via NextAuth with Google/Microsoft OAuth, along with a settings page for profile management and access token control.
- **Responsive & Themed UI:** A fully responsive layout with adaptive grids and centralized theming (light/dark modes) ensures a consistent, accessible, and user-friendly experience across all devices.

This design emphasizes a clean, modular architecture and an intuitive user experience, enabling instructors to efficiently manage all aspects of their courses and grading processes.

## **2. High-Level User Flow**

1. **Login**  
   - Handled by **NextAuth** using Google/Microsoft OAuth.  
   - On successful authentication, the user is directed to a **Dashboard** that summarizes key course metrics (e.g., number of ungraded submissions, assignments overview) before listing individual courses.

2. **Dashboard**  
   - Displays a **brief summary** of:
     - Pending grading tasks (e.g., count of ungraded responses)
     - Recently updated courses or assignments
   - Provides **quick links** to detailed course pages and other settings.
   - (Note: All course transfer actions remain manual and are only accessible within the course detail view.)

3. **Courses Page (`/courses`)**  
   - Lists all courses accessible to the instructor.  
   - Allows instructors to **create** or **delete** courses via dedicated UI actions.  
   - Clicking a course navigates to the detailed view at `/course/[id]`.

4. **Course Detail (`/course/[id]`)**  
   Organized into sub-routes or tabs for each major feature:
   - **Overview** (`index.js`):  
     - Displays course information (name, semester, instructor list) along with a summary of course metrics (e.g., number of assignments, ungraded submissions).  
     - Provides a **manual "Transfer Course" button** (which opens a modal to select a past course/semester for transferring rubrics/materials).
     - Includes a link to **"Edit Course Details"** if course information needs updating.
   - **Assignments** (`assignments.js`):  
     - Enables instructors to **create, list, edit, delete, and reorder assignments** and questions.  
     - Reordering is handled via **drag-and-drop**; adding, editing, and deletion actions are confirmed through modal dialogs.
   - **Materials** (`materials.js`):  
     - Allows uploading, editing, and deletion of course materials through a drag-and-drop interface or file picker.
   - **Rubrics** (`rubrics.js`):  
     - Lets instructors manage **sub-rubrics** for each assignment question (including points, guidelines, and leniency).  
     - Provides an option to **fetch AI suggestions** by opening a modal where instructors can input optional guidance.  
     - AI suggestions appear in a visually distinct style and can be accepted, edited, or rejected.
   - **Grading** (`grading.js`):  
     - Displays student submissions (retrieved via `GET /responses` from the external student app).  
     - Contains a **grading mode selector** (a dropdown offering "Grade Ungraded," "Regrade All," and "Grade Specific") for flexible grading workflows.  
     - When "Grade Specific" is chosen, a **multi-select UI** (using checkboxes with support for shift-click selection) allows instructors to select specific students or questions. Selected items are visually highlighted, and a "Grade Selected" button triggers the appropriate API call.
   - **Instructors** (`instructors.js`):  
     - Provides a UI to **add or remove co-instructors** (via `POST/DELETE /course/instructor`), ensuring that the active instructor cannot remove themselves.

5. **Settings (`/settings`)**  
   - Displays the instructor's profile and allows updates to personal details and notification preferences.  
   - Provides **access token management** (list, create, delete tokens using the appropriate API endpoints).  
   - Includes a **logout** option.

## **3. Tech Stack**

### **3.1 Core Frameworks & UI**

| Technology            | Purpose                                                                 |
|-----------------------|-------------------------------------------------------------------------|
| **Next.js**           | Provides Server-Side Rendering (SSR), Static Site Generation (SSG), and file-based routing for enhanced performance and SEO. |
| **Material UI (MUI)** | Supplies a consistent UI framework with pre-built components, theming, and responsive design capabilities. |
| **NextAuth**          | Manages authentication using Google/Microsoft OAuth, ensuring secure user login. |


### **3.2 API Communication & State Management**

| Technology  | Purpose                                                                 |
|-------------|-------------------------------------------------------------------------|
| **Axios**   | Makes HTTP requests to communicate with the backend API for data fetching and submission. |
| **SWR**     | Provides caching, revalidation, and automatic data updates for API calls to improve performance. |
| **React Context** | Offers lightweight global state management (e.g., for theme toggles). |
| **Zustand (Optional)** | A lightweight state management library that can be used for more complex UI state, such as multi-selection in grading, if needed. |


### **3.3 UI Enhancements & Interactivity**

| Technology             | Purpose                                                                 |
|------------------------|-------------------------------------------------------------------------|
| **react-beautiful-dnd**| Enables intuitive drag-and-drop functionality for reordering assignments and questions. |
| **React Hook Form**    | Streamlines form handling and validation, reducing re-renders and improving performance. |
| **Zod/Yup**            | Provides schema-based validation to ensure correct and robust form input handling. |
| **react-toastify (Optional)** | Offers enhanced toast notifications for better user feedback beyond MUI Snackbar. |


### **3.4 Testing & Quality Assurance**

| Technology                    | Purpose                                                                 |
|-------------------------------|-------------------------------------------------------------------------|
| **Jest + React Testing Library** | Used for unit testing React components to ensure reliability and maintainability. |
| **Cypress (Optional)**        | Facilitates end-to-end (E2E) testing to simulate real user interactions across the app. |


## 4. Project Files

### 4.1 Directory Hierarchy

```plaintext
frontend/
├── package.json
├── next.config.js
├── public/
│   ├── images/
│   │   └── example.png      # Example static asset
│   ├── icons/
│   │   └── favicon.ico      # Favicon
│   └── robots.txt           # SEO/crawler instructions
└── src/
    ├── config/
    │   └── config.js        # e.g., BACKEND_URL, other constants
    ├── components/
    │   ├── Layout.js        # Shared layout (header/footer wrapper)
    │   ├── Header.js
    │   ├── Footer.js
    │   ├── ThemeToggle.js
    │   ├── CardSkeleton.js  # Reusable loading placeholder
    │   ├── AISuggestionCard.js # Clearly styled AI suggestion display
    │   ├── ConfirmationDialog.js # General-purpose confirmation dialog
    │   ├── SelectableList.js # UI supporting shift-click and multi-selection
    │   └── GradingModeSelect.js # Dropdown for choosing grading mode
    ├── context/
    │   └── ThemeContext.js  # Provides context for theme toggling
    ├── pages/
    │   ├── _app.js
    │   ├── login.js
    │   ├── courses.js
    │   ├── course/
    │   │   └── [id]/
    │   │       ├── index.js         # Overview + transfer course
    │   │       ├── assignments.js   # Assignment & question management
    │   │       ├── materials.js     # Material management UI
    │   │       ├── rubrics.js       # Rubric management with AI integration
    │   │       ├── grading.js       # Grading modes & submission review
    │   │       └── instructors.js   # Manage instructors
    │   └── settings.js        # Access token management, logout
    ├── services/
    │   └── api.js            # Encapsulates Axios API calls & SWR hooks
    ├── theme/
    │   └── theme.js          # Material UI theme (colors, typography)
    ├── styles/
    │   ├── globals.css       # Global styling overrides
    │   └── variables.css     # CSS Variables (if used)
```

### **4.2 File Explanations**  

Each file in the project serves a specific purpose. Below is a breakdown of **what each file does** and how it contributes to the overall application.



#### **Top-Level Files & Directories**  

| File/Directory  | Purpose |
|----------------|---------|
| `package.json` | Defines project dependencies, scripts, and metadata for the Next.js frontend. |
| `next.config.js` | Configures Next.js settings, such as API rewrites, image optimization, or custom headers. |
| `public/` | Stores static assets (images, icons, SEO files) that do not require processing by Webpack. |
| `robots.txt` | SEO-related file that controls search engine indexing behavior. |

---

#### **4.2.1 `/src/config/` - Configuration Files**  

| File | Purpose |
|------|---------|
| `config.js` | Stores constants such as `BACKEND_URL`, API versioning, and other global app settings. |

---

#### **4.2.2 `/src/components/` - Reusable UI Components**  

| File | Purpose |
|------|---------|
| `Layout.js` | Wraps all pages, providing a common **header, footer, and sidebar**. |
| `Header.js` | Contains **top navigation**, user greeting, dark mode toggle, and account settings link. |
| `Footer.js` | Static footer with branding and useful links. |
| `ThemeToggle.js` | Handles **light/dark mode** switching and persists user preference. |
| `CardSkeleton.js` | Displays **loading placeholders** (used in course list, assignments, and materials pages). |
| `AISuggestionCard.js` | Shows **AI-generated rubric suggestions** in a visually distinct style, allowing acceptance or editing. |
| `ConfirmationDialog.js` | Generic **confirmation modal** for irreversible actions (e.g., deleting assignments, materials). |
| `SelectableList.js` | Provides a **multi-selectable list** (for choosing students/questions in grading). Supports shift-click selection. |
| `GradingModeSelect.js` | Dropdown menu for selecting **grading modes** (grade ungraded, regrade all, grade specific). |

---

#### **4.2.3 `/src/context/` - Global Context Management**  

| File | Purpose |
|------|---------|
| `ThemeContext.js` | Stores and manages **light/dark mode** state globally. |

---

#### **4.2.4 `/src/pages/` - Application Routes**  

| File | Purpose |
|------|---------|
| `_app.js` | **Global wrapper** for all pages. Loads styles, context providers, and layout. |
| `login.js` | Implements **NextAuth login** (Google/Microsoft OAuth). |
| `courses.js` | Displays the **list of courses** an instructor has access to. |
| `/course/[id]/index.js` | Shows **course overview** and course transfer feature. |
| `/course/[id]/assignments.js` | **Manage assignments and questions** (add, edit, delete, reorder). |
| `/course/[id]/materials.js` | Upload, edit, and delete **course materials**. |
| `/course/[id]/rubrics.js` | **Manage sub-rubrics** (question-wise grading criteria) with optional **AI assistance**. |
| `/course/[id]/grading.js` | Displays **student submissions** and allows grading with **selectable grading modes**. |
| `/course/[id]/instructors.js` | Add/remove **co-instructors** for a course. |
| `settings.js` | Manage **access tokens** and logout functionality. |

---

#### **4.2.5 `/src/services/` - API Layer**  

| File | Purpose |
|------|---------|
| `api.js` | Encapsulates **API calls using Axios** (CRUD for assignments, grading, materials, etc.). |

---

#### **4.2.6 `/src/theme/` - Theming & Styling**  

| File | Purpose |
|------|---------|
| `theme.js` | Defines **global Material UI theme settings** (colors, typography, breakpoints). |

---

#### **4.2.7 `/src/styles/` - Global Stylesheets**  

| File | Purpose |
|------|---------|
| `globals.css` | Global **CSS overrides** for Material UI components and layout refinements. |
| `variables.css` | Defines **CSS variables** (if applicable) for easy theming adjustments. |

---

## 5. Feature Highlights

### **1. Instructor Management (`/course/[id]/instructors.js`)**  
- **Add/remove instructors** (`POST/DELETE /course/instructor`).  
- Prevent removal of the active user.  
- **Related files:**
  - **`/pages/course/[id]/instructors.js`** – Implements instructor UI.
  - **`/components/ConfirmationDialog.js`** – Used when confirming instructor removal.
  - **`/services/api.js`** – Handles API calls for adding/removing instructors.

### **5.2. Course Transfer (`/course/[id]/index.js`)**  
- "Transfer Course" button triggers a **modal selection** of past courses.  
- Instructor selects **source course/semester**, confirming via "Transfer" button, which calls `PATCH /course/transfer`.  
- Snackbar feedback for **success/error**.  
- **Related files:**
  - **`/pages/course/[id]/index.js`** – Course overview UI with transfer option.
  - **`/components/ConfirmationDialog.js`** – Ensures instructors confirm the action.
  - **`/services/api.js`** – Handles course transfer API request.

### **5.3. Assignments (`/course/[id]/assignments.js`)**  
- **Create new assignments** (`POST /assignment`).  
- Manage **assignment questions**:
  - **Added**: "Add Question" button opens a modal.
  - **Edited**: Inline text fields with a save button.
  - **Removed**: Trash icon triggers a confirmation dialog.
  - **Reordered**: **Drag-and-drop** (MUI `DragDropContext`).  
- **Related files:**
  - **`/pages/course/[id]/assignments.js`** – UI for managing assignments.
  - **`/components/ConfirmationDialog.js`** – Used when confirming deletions.
  - **`/services/api.js`** – Manages API calls for assignments.
  - **`/components/SelectableList.js`** – Enables **multi-selection** of questions.

### **5.4. Materials (`/course/[id]/materials.js`)**  
- **Upload materials** via drag-and-drop or file picker (`POST /course_material`).  
- **Edit/delete** files (`PATCH/DELETE /course_material`).  
- **Related files:**
  - **`/pages/course/[id]/materials.js`** – UI for managing course materials.
  - **`/components/ConfirmationDialog.js`** – Ensures deletion confirmation.
  - **`/components/CardSkeleton.js`** – Provides a loading placeholder when fetching materials.
  - **`/services/api.js`** – Handles material upload, update, and deletion.

### **5.5. Rubrics (`/course/[id]/rubrics.js`)**  
- Manage **sub-rubrics** for each question (points, guidelines, leniency).  
- AI-generated rubric improvements via `"Suggest Rubric Improvements"` (`GET /ai_rubric`).  
  - Instructors can provide **optional AI guidance** in a text field.  
  - AI suggestions appear **visually distinct** and can be **accepted/rejected individually**.  
- **Related files:**
  - **`/pages/course/[id]/rubrics.js`** – UI for rubric management.
  - **`/components/AISuggestionCard.js`** – Displays AI-generated suggestions.
  - **`/services/api.js`** – Calls AI rubric suggestion API.

### **5.6. Grading (`/course/[id]/grading.js`)**  
- **List student submissions** (`GET /responses`).  
- Provides a **grading mode selection UI**:
  - **Dropdown menu** for selecting grading mode:
    - `"Grade Ungraded"` (`POST /response/grade/ungraded`)
    - `"Regrade All"` (`POST /response/grade/all`)
    - `"Grade Specific"` (`POST /response/grade/specific`)  
  - Selecting **specific students/questions**:
    - **Multi-selection UI** (checkbox-based, shift-click support).  
    - **Selected items get highlighted** for clarity.  
    - Clicking `"Grade Selected"` triggers grading.  
- **Related files:**
  - **`/pages/course/[id]/grading.js`** – UI for grading interface.
  - **`/components/GradingModeSelect.js`** – Dropdown for grading mode selection.
  - **`/components/SelectableList.js`** – Enables **multi-selection of students/questions**.
  - **`/services/api.js`** – Handles grading API calls.

### **5.7. Access Token Management (`/settings.js`)**  
- **List tokens** (`GET /auth/tokens`).  
- **Create new token** (`POST /auth/token`).  
- **Delete token** (`DELETE /auth/token`) with a confirmation dialog.  
- **Related files:**
  - **`/pages/settings.js`** – UI for managing access tokens.
  - **`/components/ConfirmationDialog.js`** – Ensures deletion confirmation.
  - **`/services/api.js`** – Handles API calls for token creation/deletion.

## **6. Responsiveness & Theming**  

The frontend will be **fully responsive** and support **theme customizability** using **Material UI’s Grid system, ThemeProvider, and breakpoints**.  
All theming settings are **centralized** in theme/theme.js, making it **easy to adjust styles, colors, and layouts** without modifying individual components.

---

### **6.1 Responsive Layouts with MUI Grid**  

MUI’s **Grid** system will be used to create a flexible, **adaptive layout** across different screen sizes. 
Key Strategies for this are:

#### **Adaptive Column Layouts**  
- Course cards, assignments, and lists will be displayed in a **grid format** that adjusts dynamically:
  - **Desktop:** 3 columns (md={4})
  - **Tablet:** 2 columns (sm={6})
  - **Mobile:** 1 column (xs={12})
  
#### **Breakpoints for Page Sections**  
- Pages will be **split into sections** (main content + side panels).  
- On **large screens**, side panels (e.g., filters, rubrics, grading settings) will be displayed **beside the main content**.  
- On **mobile**, the UI will automatically switch to a **stacked layout**.

#### **Auto-Adjusting Dialogs & Forms**  
- MUI’s Dialog will dynamically **scale** based on screen size (maxWidth="sm" | "md" | "lg") to prevent oversized popups.

#### **Related Files:**  
- **/theme/theme.js** – Defines responsive breakpoints and grid spacing.  
- **/components/Layout.js** – Ensures consistent spacing and structure across all pages.  
- **/pages/course/[id]/grading.js** – Uses grid layout to **properly arrange grading controls**.  
- **/pages/course/[id]/assignments.js** – Uses grid to ensure **question lists** are responsive.  

### **6.2 Theming & Customization**  

The **entire theme** will be stored in theme/theme.js to ensure **consistent styling** and **easy updates**.  
Future branding adjustments can be made **by modifying a single file**.

#### **Global Theme System (theme/theme.js)**
- **All theme colors, typography, font sizes, and spacing values** are defined centrally.
- Uses **MUI’s responsiveFontSizes(createTheme(...))** to ensure dynamic text scaling.  
- Custom styles for **buttons, cards, and dialogs** ensure brand consistency.

#### **Light/Dark Mode**
- The application supports **dark mode**, with a toggle located in the **header**.  
- Theme switching is **context-based** and persists across sessions.  

##### **Related Files:**  
- **/theme/theme.js** – Stores color schemes, fonts, spacing, and overrides.  
- **/components/ThemeToggle.js** – Implements light/dark mode switching UI.  
- **/context/ThemeContext.js** – Manages the theme selection state.  
- **/pages/_app.js** – Wraps the application with ThemeProvider to apply the theme globally.

### **6.3 Fancy UI Enhancements & Effects**  

To **enhance user experience**, the UI will include **subtle design elements** for **better interaction feedback**.

#### **6.3.1. Hover Effects**  
- Buttons and cards will have a **soft shadow on hover** for visual feedback.  
- Navigation items will use **color transitions** (transition: all 0.3s ease-in-out).  

#### **6.3.2. Interactive Click Effects**  
- Buttons will have an **animated press-down effect** (scale(0.95)) for a **tactile feel**.

#### **6.3.3. Background Design**  
- **Default Background:** Uses **plain colors** (background.default) to maintain readability.  
- **Optional Image Backgrounds:**  
  - **Light Mode:** Subtle gradient (linear-gradient(to bottom, #f5f5f5, #e0e0e0)).  
  - **Dark Mode:** Abstract **geometric textures** for contrast.

#### **6.3.4. Custom Scrollbars**  
- **On desktop**, a **custom scrollbar** will match the theme colors.  
- **On mobile**, scrolling will **use native behavior** for smoother UX.

##### **Related Files:**  
- **/theme/theme.js** – Defines hover styles, transitions, and background preferences.  
- **/components/Layout.js** – Ensures background styles are applied consistently.  
- **/styles/globals.css** – Customizes **scrollbar styles and hover effects**.  



### **6.4 Theming Details**  

The color scheme follows **Material Design principles** to ensure **good contrast, readability, and accessibility**.

##### **Light Mode**  
| Element  | Color  |  
|----------|--------|  
| **Primary** | #1976d2 (Bright blue for buttons/links) |  
| **Secondary** | #ff6f00 (Orange for accents and highlights) |  
| **Background (default)** | #fafafa (Soft gray to avoid stark white) |  
| **Background (paper)** | #ffffff (Used for cards and containers) |  
| **Text (primary)** | #212121 (Dark gray for readability) |  

##### **Dark Mode**  
| Element  | Color  |  
|----------|--------|  
| **Primary** | #90caf9 (Lighter blue for better contrast) |  
| **Secondary** | #ffb74d (Soft orange for accessibility) |  
| **Background (default)** | #121212 (Deep gray-black to reduce eye strain) |  
| **Background (paper)** | #1e1e1e (Darker gray for contrast) |  
| **Text (primary)** | #ffffff (Pure white for strong readability) |  

##### **Related Files:**  
- **/theme/theme.js** – Defines color palettes and typography.  
- **/components/ThemeToggle.js** – Toggles between light/dark mode.  
- **/context/ThemeContext.js** – Stores the theme state persistently.  




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