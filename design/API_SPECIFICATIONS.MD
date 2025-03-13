# BU MET Autograder API Design Specifications (V1)

## Table of Contents

1. [Objects](#objects)
   - [User (A Course Instructor)](#user)
   - [Personal Authentication Token](#personal-authentication-token)
   - [Access Token](#access-token)
   - [Rubric](#rubric)
   - [Course](#course)
   - [Assignment](#assignment)
   - [Course Material](#course-material)
   - [Student](#student)
   - [Student Response](#student-response)
   - [Grade](#grade)

2. [API Endpoints](#api-endpoints)
   - **User Authentication Endpoints**
     - [POST /auth/token](#post-authtoken)
     - [DELETE /auth/token](#delete-authtoken)
     - [GET /auth/tokens](#get-authtokens)
     - [GET /auth/google-oauth](#get-authgoogle-oauth)
   - **Course Endpoints**
     - [POST /course](#post-course)
     - [DELETE /course](#delete-course)
     - [PATCH /course/transfer](#patch-coursetransfer)
     - [GET /courses](#get-courses)
     - [POST/DELETE /course/instructor](#postdelete-courseinstructor)
   - **Assignments Endpoints**
     - [POST /assignment](#post-assignment)
     - [PATCH /assignment/<action>](#patch-assignmentaction)
     - [GET /assignment](#get-assignment)
     - [GET /assignments](#get-assignments)
     - [DELETE /assignment](#delete-assignment)
   - **Student Response Endpoints**
     - [POST /response](#post-response)
     - [PUT /response](#put-response)
     - [DELETE /response](#delete-response)
     - [GET /responses](#get-responses)
     - [POST /response/grade](#post-responsegrade)
   - **Course Material Endpoints**
     - [POST /course-material](#post-course-material)
     - [DELETE /course-material](#delete-course-material)
     - [PATCH /course-material](#patch-course-material)
   - **Rubrics Endpoints**
     - [POST /rubric](#post-rubric)
     - [PATCH /enhance-rubric](#patch-enhance-rubric)
     - [GET /rubric](#get-rubric)

---

## Objects

This section describes the composition and fields of the various objects used throughout the API.

### [User](#user)
- **User ID (Non-Null):** Internal unique identifier of the user.
- **First Name (Nullable):** The user’s first name.
- **Last Name (Nullable):** The user’s last name.
- **User Email (Non-Null):** The email address of the user.

### [Personal Authentication Token](#personal-authentication-token)
This JSON Web Token (JWT) is intended for interactive sessions on the official front end.
- **User ID (Non-Null):** The identifier of the user.
- **Authentication Token (Non-Null):** The JWT string.

### [Access Token](#access-token)
This token is used to access the API programmatically. It is functionally similar to the Personal Authentication Token except that it cannot be used to generate additional access tokens.
- **User ID (Non-Null):** The identifier of the token owner.
- **Token Name (Non-Null):** A friendly name for the token (must be unique per user).
- **Token ID (Non-Null):** The secret token string (displayed only once during creation).
- **Token Expiry (Nullable):** Expiration time of the token. If not provided, the token never expires.

### [Rubric](#rubric)
The Rubric object contains the grading instructions for the LLM regarding leniency, point allocations, and deductions.
- **Assignment ID (Non-Null):** The ID of the associated assignment.
- **Leniency (Non-Null, Integer 1–5):** How lenient the grading should be.
  - **5:** Grade based mostly on effort; points are deducted only if no work is shown or the work appears thoughtless.
  - **1:** Strict adherence to instructor guidelines is required; any deviation (including vocabulary) may result in lost points.
- **Overall Instructor Guidelines (Nullable):** General grading criteria applicable to all questions.
- **List (Non-Null):** A list of sub-rubrics for individual questions:
  - **Question Index (Non-Null):** The index of the question for this sub-rubric.
  - **Maximum Points (Non-Null):** Maximum points available for this question.
  - **Leniency (Non-Null, Integer 1–5, Defaults to 3):** Leniency for this specific question. If omitted, the global leniency is used.
  - **Instructor Guideline (Nullable):** Detailed grading criteria for this question.

### [Course](#course)
This object represents a course. The combination of Course Name and Semester must be unique.
- **Course ID (Non-Null):** Unique identifier for the course.
- **Course Owner ID (Non-Null):** The ID of the user who created the course.
- **Course Name (Non-Null):** The name of the course.
- **Semester (Non-Null):** The semester during which the course is offered.
- **Instructors (Non-Null):** A list of email addresses of authenticated instructors for the course.

### [Assignment](#assignment)
The Assignment object contains the questions and guidelines for an assignment or quiz.
- **Assignment ID (Non-Null):** Unique identifier for the assignment.
- **Course ID (Non-Null):** The course to which the assignment belongs.
- **Assignment Title (Nullable):** The title of the assignment.
- **Assignment Guidelines (Nullable):** Overall instructions or formatting requirements applicable to all questions.
- **Ordered List (Non-Null):** A list of questions for the assignment:
  - **Question Text (Non-Null):** The text of the question.
  - **Question Graphics/Figures (Nullable):** Associated images or figures for the question.

### [Course Material](#course-material)
This object contains the course material and its modality.
- **Course ID (Non-Null):** The associated course’s ID.
- **Material ID (Non-Null):** Unique identifier for the material.
- **Material Name (Non-Null):** The title or name of the material.
- **Additional Notes (Nullable):** Any supplementary instructor notes for the material.
- **Modality (Non-Null):** The type of material (Video, Audio, Image, Text, PowerPoint, PDF, Website).
- **Data (Non-Null):** The actual content or data of the material.

### [Student](#student)
This object contains basic information about a student.
- **Student Identifier (Non-Null):** A unique identifier for the student (e.g., their BU email).
- **First Name (Nullable):** The student’s first name.
- **Last Name (Nullable):** The student’s last name.

### [Student Response](#student-response)
This object represents a student’s response to a question.
- **Student Identifier (Non-Null):** The unique identifier of the student.
- **Assignment ID (Non-Null):** The ID of the assignment to which the response belongs.
- **Question Index (Non-Null):** The index of the question being answered.
- **Response Modality (Non-Null):** The type of response (Video, Audio, Image, Text, PowerPoint, PDF, Website).
- **Data (Non-Null):** The content of the response.

### [Grade](#grade)
This object contains the grading results for a student’s response.
- **Student Identifier (Non-Null):** The unique identifier of the student.
- **Assignment ID (Non-Null):** The assignment ID for which the grade is given.
- **Question Index (Non-Null):** The question index to which the grade applies.
- **Grade (Non-Null):** The grade awarded to the student.
- **Explanation (Nullable):** A detailed explanation of the grade based on the rubric.

---

## API Endpoints

**Base URL:** `https://{domain}/api/v1`

Authentication can be performed either using an OAuth-obtained authorization token or an API-generated access token.

---

### User Authentication Endpoints

#### POST `/auth/token`
**Description:** Creates a new [Access Token](#access-token) for programmatic API access.

- **Parameters:**
  - **Token Name (Optional):** A friendly name for the token.  
    *Default:* "Token 1", "Token 2", etc.

- **Returns:**  
  An [Access Token](#access-token) object containing:
  - Token ID
  - Token Name
  - Access Token Secret

- **Errors:**  
  - **400 Bad Request:** If parameters are invalid.  
  - **401 Unauthorized:** If the requester is not authenticated.
  - **403 Forbidden:** If the request is authenticated but access is not allowed.

---

#### DELETE `/auth/token`
**Description:** Deletes an existing access token.

- **Parameters:**
  - **Token ID (Required):** The unique identifier of the access token to be deleted.

- **Returns:**  
  A success message.

- **Errors:**  
  - **400 Bad Request:** If the token ID is missing or invalid.  
  - **404 Not Found:** If the token does not exist.
  - **403 Forbidden:** If the request is authenticated but access is not allowed.

---

#### GET `/auth/tokens`
**Description:** Retrieves a list of all active access tokens for the authenticated user.

- **Returns:**  
  - A list of [Access Token](#access-token) objects

- **Errors:**  
  - **401 Unauthorized:** If the requester is not authenticated.
  - **403 Forbidden:** If the request is authenticated but access is not allowed.

---

#### GET `/auth/google-oauth`
**Description:** Callback endpoint for processing Google OAuth. When a user authorizes Google OAuth, they are redirected here so that the server can extract their authentication token.

- **Parameters:**
  - **access_token (Required)**
  - **expires_in (Required)**
  - **refresh_token (Required)**
  - **scope (Required)**
  - **token_type (Required)**
  - **id_token (Required)**

- **Returns:**  
  A [Personal Authentication Token](#personal-authentication-token) object required to access most endpoints.

- **Errors:**  
  - **400 Bad Request:** If required OAuth parameters are missing.
  - **401 Unauthorized:** If the OAuth parameters are invalid/not authorized to access Google's authentication endpoints.

---

### Course Endpoints

#### POST `/course`
**Description:** Creates a new [Course](#course).

- **Parameters:**
  - **Course Name (Required):** The name of the course.
  - **Course ID (Required):** The unique course identifier (e.g., "CS 132").
  - **Semester (Required):** The semester during which the course is offered.
  - **Instructors (Required):** A list of emails for authenticated instructors.

- **Returns:**  
  The created [Course](#course) object.

- **Errors:**  
  - **400 Bad Request:** If required parameters are missing or invalid.
  - **409 Conflict:** If a course with the same name and semester already exists.

---

#### DELETE `/course`
**Description:** Deletes an existing course.

- **Parameters:**
  - **Course ID (Required):** The unique identifier of the course.
  - **Semester (Required):** The semester of the course.

- **Returns:**  
  A success message.

- **Errors:**  
  - **404 Not Found:** If the course does not exist.
  - **401 Unauthorized:** If the requester is not authenticated.
  - **403 Forbidden:** If the request is authenticated but access is not allowed.

---

#### PATCH `/course/transfer`
**Description:** Transfers course materials and rubric data from a previous semester to a new one.

- **Parameters:**
  - **Current Course ID (Required):** The ID of the course being updated.
  - **Current Semester (Required):** The current semester of the course.
  - **Copy From Course ID (Required):** The ID of the course from which to transfer data.
  - **Copy From Course Semester (Required):** The semester of the course to copy from.

- **Returns:**  
  A success message and/or the updated [Course](#course) object.

- **Errors:**  
  - **404 Not Found:** If the source or destination course cannot be found.
  - **400 Bad Request:** If parameters are invalid.
  - **401 Unauthorized:** If the requester is not authenticated.
  - **403 Forbidden:** If the request is authenticated but access is not allowed.

---

#### GET `/courses`
**Description:** Retrieves a list of all courses to which the authenticated user has access.

- **Returns:**  
  - A list of [Course](#course) objects.

- **Errors:**  
  - **401 Unauthorized:** If the requester is not authenticated.

---

### **POST `/course/instructor`**
**Description:**  
Adds an instructor to a course.

- **Parameters:**
  - **Course ID (Required):** The unique identifier of the course.
  - **Semester (Required):** The semester of the course.
  - **Instructor (Required):** The email of the instructor to add.

- **Returns:**  
  - A success message.

- **Errors:**  
  - **400 Bad Request:** If parameters are missing or invalid.
  - **404 Not Found:** If the course is not found.
  - **401 Unauthorized:** If the requester is not authenticated.
  - **403 Forbidden:** If the request is authenticated but access is not allowed.
  - **409 Conflict:** If the instructor is already assigned to the course.

---

### **DELETE `/course/instructor`**
**Description:**  
Removes an instructor from a course.

- **Parameters:**
  - **Course ID (Required):** The unique identifier of the course.
  - **Semester (Required):** The semester of the course.
  - **Instructor (Required):** The email of the instructor to remove.

- **Returns:**  
  - A success message.

- **Errors:**  
  - **400 Bad Request:** If parameters are missing or invalid.
  - **404 Not Found:** If the course is not found or the instructor is not assigned to the course.
  - **401 Unauthorized:** If the requester is not authenticated.
  - **403 Forbidden:** If the request is authenticated but access is not allowed.

---

### Assignments Endpoints

#### POST `/assignment`
**Description:** Creates a new [Assignment](#assignment) with the provided questions and guidelines.

- **Parameters:**
  - **Course ID (Required):** The course identifier.
  - **Semester (Required):** The semester of the course.
  - **Assignment Guidelines (Required):** General instructions or formatting requirements for the assignment.
  - **Ordered List (Required):** A list of questions, where each item includes:
    - **Question Text (Required)**
    - **Question Graphics/Figures (Optional)**

- **Returns:**  
  - The created [Assignment](#assignment) object (including the Assignment ID).

- **Errors:**  
  - **400 Bad Request:** If parameters are missing or invalid.
  - **404 Not Found:** If the associated course does not exist.
  - **401 Unauthorized:** If the requester is not authenticated.
  - **403 Forbidden:** If the request is authenticated but access is not allowed.

---

#### PATCH `/assignment/<action>`
**Description:** Modifies an existing assignment. The `<action>` parameter specifies the type of update.

- **Actions and Parameters:**
  - **add-question:** Adds a new question to the assignment.
    - **Parameters:**
      - **Question Text (Required)**
      - **Question Graphics/Figures (Optional)**
    - **Returns:**  
      The new Question Index.
  - **remove-question:** Removes a question from the assignment.
    - **Parameters:**
      - **Question Index (Required):** The index of the question to remove.
  - **edit-question:** Edits a question.
    - **Parameters:**
      - **Question Index (Required)**
      - **New Question Text (Required)**
      - **New Question Graphics/Figures (Optional)**
  - **modify-order:** Modifies the order of the questions.
    - **Parameters:**
      - **List of Question Indexes (Required):** The new order for the questions.

- **Returns:**  
  - The updated [Assignment](#assignment) object.

- **Errors:**  
  - **400 Bad Request:** If the action or parameters are invalid.
  - **404 Not Found:** If the assignment or question does not exist.
  - **401 Unauthorized:** If the requester is not authenticated.
  - **403 Forbidden:** If the request is authenticated but access is not allowed.

---

#### GET `/assignment`
**Description:** Retrieves a specific assignment.

- **Parameters:**
  - **Course ID (Required):** The course identifier this assignment belongs to.
  - **Assignment ID (Required):** The identifier of the assignment.

- **Returns:**  
  - The corresponding [Assignment](#assignment) object.

- **Errors:**  
  - **404 Not Found:** If the assignment is not found.
  - **401 Unauthorized:** If the requester is not authenticated.
  - **403 Forbidden:** If the request is authenticated but access is not allowed.

---

#### GET `/assignments`
**Description:** Retrieves all assignments associated with the provided course.

- **Parameters:**
  - **Course ID (Required):** The course identifier this assignment belongs to.

- **Returns:**  
  - A list of [Assignment](#assignment) objects.

- **Errors:**  
  - **401 Unauthorized:** If the requester is not authenticated.
  - **403 Forbidden:** If the request is authenticated but access is not allowed.

---

#### DELETE `/assignment`
**Description:** Deletes a specified assignment.

- **Parameters:**
  - **Assignment ID (Required):** The identifier of the assignment to delete.

- **Returns:**  
  - A success message.

- **Errors:**  
  - **404 Not Found:** If the assignment does not exist.
  - **401 Unauthorized:** If the requester is not authenticated.
  - **403 Forbidden:** If the request is authenticated but access is not allowed.

---

### Student Response Endpoints

#### POST `/response`
**Description:** Uploads a student response to a specific assignment question.

- **Parameters:**
  - **Student Identifier (Required):** Unique identifier for the student.
  - **Assignment ID (Required):** The assignment identifier.
  - **Question Index (Required):** The index of the question being answered.
  - **Response Modality (Required):** The format of the response (Video, Audio, Image, Text, PowerPoint, PDF, Website).
  - **Data (Required):** The binary content of the student’s response.

- **Returns:**  
  - A success message.

- **Errors:**  
  - **400 Bad Request:** If required parameters are missing or invalid.
  - **404 Not Found:** If the assignment or question is not found.
  - **401 Unauthorized:** If the requester is not authenticated.
  - **403 Forbidden:** If the request is authenticated but access is not allowed.

---

#### PUT `/response`
**Description:** Replaces an existing student response with an updated one.

- **Parameters:**
  - **Student Identifier (Required):** Unique identifier for the student.
  - **Assignment ID (Required):** The assignment identifier.
  - **Question Index (Required):** The index of the question being answered.
  - **Response Modality (Required):** The format of the response (Video, Audio, Image, Text, PowerPoint, PDF, Website).
  - **Data (Required):** The binary content of the student’s response.

- **Returns:**  
  - A success message.

- **Errors:**  
  - **400 Bad Request:** If parameters are missing or invalid.
  - **404 Not Found:** If the existing response is not found.
  - **401 Unauthorized:** If the requester is not authenticated.
  - **403 Forbidden:** If the request is authenticated but access is not allowed.

---

#### DELETE `/response`
**Description:** Deletes a submitted student response. If no Question Index is provided, all responses for the specified assignment and student are deleted.

- **Parameters:**
  - **Student Identifier (Required)**
  - **Assignment ID (Required)**
  - **Question Index (Optional)**

- **Returns:**  
  - A success message.

- **Errors:**  
  - **400 Bad Request:** If required parameters are missing.
  - **404 Not Found:** If the specified response is not found.
  - **401 Unauthorized:** If the requester is not authenticated.
  - **403 Forbidden:** If the request is authenticated but access is not allowed.

---

#### GET `/responses`
**Description:** Retrieves student responses (with optional grade information) based on provided criteria.

- **Parameters:**
  - **Assignment ID (Required):** The assignment identifier.
  - **Question Index (Optional):** Specific question index.
  - **Student Identifier (Optional):** The unique identifier of a student.

- **Returns:**  
  - Combined [Student Response](#student-response) and [Grade](#grade) objects (if the assignment is graded).

- **Errors:**  
  - **400 Bad Request:** If the assignment ID is missing.
  - **404 Not Found:** If no matching responses are found.
  - **401 Unauthorized:** If the requester is not authenticated.
  - **403 Forbidden:** If the request is authenticated but access is not allowed.

---

#### POST `/response/grade`
**Description:** Requests grading for student responses. Supports single or batch grading modes.

- **Parameters (depending on grading mode):**
  - **For Specific or Batch Grading:**
    - **Type (Required):** `SPECIFIC`
    - **Student Identifier(s) (Required):** A list of student identifiers whose responses should be graded or regraded.
    - **Assignment ID (Required)**
    - **Question Index (Optional):** If omitted, grades all questions.
  - **For Grading Ungraded Work:**
    - **Type (Required):** `UNGRADED`
    - **Assignment ID (Required)**
    - **Question Index (Optional)**
  - **For Grading/Regrading All Work:**
    - **Type (Required):** `ALL`
    - **Assignment ID (Required)**
    - **Question Index (Optional)**

- **Returns:**  
  - A list of [Grade](#grade) objects.

- **Errors:**  
  - **400 Bad Request:** If parameters are missing or invalid.
  - **502 Internal Server Error:** External API call to the LLM Failed (ran out of credits? down?).
  - **401 Unauthorized:** If the requester is not authenticated.
  - **403 Forbidden:** If the request is authenticated but access is not allowed.

---

### Course Material Endpoints

#### POST `/course-material`
**Description:** Uploads new course material.

- **Parameters:**
  - **Course ID (Required)**
  - **Semester (Required)**
  - **Material Name (Required):** The title of the material.
  - **Modality (Required):** The type of material (Video, Audio, Image, Text, PowerPoint, PDF, Website).
  - **Additional Notes (Optional):** Supplementary information about the material.
  - **Data (Required):** The actual binary content of the material.

- **Returns:**  
  - The created [Course Material](#course-material) object.

- **Errors:**  
  - **400 Bad Request:** If required parameters are missing or invalid.
  - **409 Conflict:** If a material with the same identifier already exists.
  - **401 Unauthorized:** If the requester is not authenticated.
  - **403 Forbidden:** If the request is authenticated but access is not allowed.

---

#### DELETE `/course-material`
**Description:** Deletes specified course material.

- **Parameters:**
  - **Course ID (Required)**
  - **Semester (Required)**
  - **Material ID (Required):** The unique identifier of the material.

- **Returns:**  
  A success message.

- **Errors:**  
  - **404 Not Found:** If the material is not found.
  - **401 Unauthorized:** If the requester is not authenticated.
  - **403 Forbidden:** If the request is authenticated but access is not allowed.

---

#### PATCH `/course-material`
**Description:** Updates existing course material.

- **Parameters:**
  - **Course ID (Required)**
  - **Semester (Required)**
  - **Material ID (Required)**
  - **Material Name (Optional):** Updated title.
  - **Additional Notes (Optional):** Updated supplementary information.
  - **Modality (Optional):** Updated material type.
  - **Data (Optional):** Updated binary content.

- **Returns:**  
  - The updated [Course Material](#course-material) object.

- **Errors:**  
  - **400 Bad Request:** If parameters are missing or invalid.
  - **404 Not Found:** If the material to update cannot be found.
  - **401 Unauthorized:** If the requester is not authenticated.
  - **403 Forbidden:** If the request is authenticated but access is not allowed.

---

### Rubrics Endpoints

#### POST `/rubric`
**Description:** Manually creates a new [Rubric](#rubric) for an assignment.

- **Parameters:**
  - **Assignment ID (Required)**
  - **Max Points (Required):** The total maximum points for the assignment (must be equal to or greater than the sum of individual question points).
  - **Overall Instructor Guidelines (Optional):** Grading criteria that apply to all questions.
  - **List (Required):** A list of sub-rubric objects, each including:
    - **Question Index (Required)**
    - **Maximum Points (Required)**
    - **Instructor Guideline (Required):** Detailed grading criteria for the question.

- **Returns:**  
  - The created [Rubric](#rubric) object.

- **Errors:**  
  - **400 Bad Request:** If required parameters are missing or invalid.
  - **404 Not Found:** If the specified assignment is not found.
  - **401 Unauthorized:** If the requester is not authenticated.
  - **403 Forbidden:** If the request is authenticated but access is not allowed.

---

#### PUT `/ai-rubric`
**Description:** Enhances an existing rubric using AI-based improvements. If a rubric doesn't already exist, it generates a brand-new rubric coming up with its own guidelines.

- **Parameters:**
  - **Assignment ID (Required):** The assignment id for which to enhance the rubric for.
  - **Instructions (Optional):** Specific instructions on which aspects of the rubric to improve. A default set of instructions is applied if not provided.

- **Returns:**  
  - The improved [Rubric](#rubric) object.

- **Errors:**  
  - **502 Internal Server Error:** External API call to the LLM Failed (ran out of credits? down?).
  - **401 Unauthorized:** If the requester is not authenticated.
  - **403 Forbidden:** If the request is authenticated but access is not allowed.

---

#### GET `/rubric`
**Description:** Retrieves the rubric for a specified assignment (optionally for a specific question).

- **Parameters:**
  - **Assignment ID (Required):** The identifier of the assignment.
  - **Question Index (Optional):** Retrieve the rubric for a specific question; if omitted, returns the full rubric.

- **Returns:**  
  - The [Rubric](#rubric) object

- **Errors:**  
  - **404 Not Found:** If the rubric or specified question is not found.
  - **401 Unauthorized:** If the requester is not authenticated.
  - **403 Forbidden:** If the request is authenticated but access is not allowed.

---