# BU MET Autograder API Design Specifications (V1)

## Table of Contents

1. [Objects](#objects)
   - [user](#user)
   - [personal_authentication_token](#personal_authentication_token)
   - [access_token](#access_token)
   - [rubric](#rubric)
   - [course](#course)
   - [assignment](#assignment)
   - [course_material](#course_material)
   - [student](#student)
   - [student_response](#student_response)
   - [grade](#grade)

2. [API Endpoints](#api-endpoints)
   - **User Authentication Endpoints**
     - [POST /auth/token](#post-auth-token)
     - [DELETE /auth/token](#delete-auth-token)
     - [GET /auth/tokens](#get-auth-tokens)
     - [GET /auth/google_oauth](#get-auth-google-oauth)
   - **Course Endpoints**
     - [POST /course](#post-course)
     - [DELETE /course](#delete-course)
     - [PATCH /course/transfer](#patch-course-transfer)
     - [GET /courses](#get-courses)
     - [POST /course/instructor](#post-course-instructor)
     - [DELETE /course/instructor](#delete-course-instructor)
   - **Assignment Endpoints**
     - [POST /assignment](#post-assignment)
     - [PATCH /assignment/add_question](#patch-assignment-add-question)
     - [PATCH /assignment/remove_question](#patch-assignment-remove-question)
     - [PATCH /assignment/edit_question](#patch-assignment-edit-question)
     - [PATCH /assignment/modify_order](#patch-assignment-modify-order)
     - [GET /assignment](#get-assignment)
     - [GET /assignments](#get-assignments)
     - [DELETE /assignment](#delete-assignment)
   - **Student Response Endpoints**
     - [POST /response](#post-response)
     - [PUT /response](#put-response)
     - [DELETE /response](#delete-response)
     - [GET /responses](#get-responses)
   - **Grading Endpoints**
     - [POST /response/grade/specific](#post-response-grade-specific)
     - [POST /response/grade/ungraded](#post-response-grade-ungraded)
     - [POST /response/grade/all](#post-response-grade-all)
   - **Course Material Endpoints**
     - [POST /course_material](#post-course-material)
     - [DELETE /course_material](#delete-course-material)
     - [PATCH /course_material](#patch-course-material)
   - **Rubric Endpoints**
     - [POST /rubric](#post-rubric)
     - [GET /ai_rubric](#get-ai-rubric)
     - [GET /rubric](#get-rubric)

---

## Objects

### [user](#user)
The user object (i.e. the instructor) who is signed in.
- **user_id** (Non-Null): Internal unique identifier.
- **first_name** (Nullable): The user's first name.
- **last_name** (Nullable): The user's last name.
- **user_email** (Non-Null): The user's email address.

### [personal_authentication_token](#personal_authentication_token)
A JSON Web Token (JWT) for interactive sessions on the official front end.
- **user_id** (Non-Null): The identifier of the user.
- **authentication_token** (Non-Null): The JWT string.

### [access_token](#access_token)
Used for programmatic API access; it cannot generate additional access tokens.
- **user_id** (Non-Null): The token owner's identifier.
- **token_name** (Non-Null): A friendly name for the token (must be unique per user).
- **token_id** (Non-Null): The secret token string (displayed only once during creation).
- **token_expiry** (Nullable): Expiration time. If omitted, the token never expires.

### [rubric](#rubric)
Contains grading instructions for the LLM regarding leniency, point allocations, and deductions.
- **assignment_id** (Non-Null): The associated assignment's ID.
- **grading_flags** (Nullable): A list of grading flags to apply on this rubric.
    - IGNORE_SPELLINGS: Don't penalize for minor spelling mistakes.
    - IGNORE_GRAMMAR: Don't penalize for minor grammar issues.
    - ORIGINALITY: Award points for originality and creativity while deducting for unoriginal ideas.
    - IGNORE_FORMATTING: Don't penalize for formatting issues.
- **leniency** (Non-Null, Integer 1–5): A number between 1-5 where 1 is very strict and 5 is very forgiving.
  - Leniency 1 – Very Strict: Grading is based solely on strict adherence to the provided guidelines. Any deviation—even minor—is penalized heavily. The focus is on precision, with little to no credit given for effort or creative approaches if they do not exactly match the expected answer.
  - Leniency 2 – Strict: Grading emphasizes correctness and complete adherence to instructions, but allows for minimal deviations. Minor errors or slight departures from the expected format result in significant point deductions, though there may be some recognition for effort if the overall structure is maintained.
  - Leniency 3 – Moderate: A balanced approach that weighs both correctness and the demonstration of understanding. Minor errors or unconventional approaches that still convey the correct reasoning are penalized moderately. This level offers a fair compromise between strict correctness and effort acknowledgment.
  - Leniency 4 – Lenient: The focus is on recognizing the student’s effort and overall understanding, even if the final answer isn’t perfect. Minor errors are tolerated with minimal deductions, and creative or partially correct solutions receive substantial credit, emphasizing improvement and learning over perfection.
  - Leniency 5 – Very Lenient: Grading is highly forgiving, prioritizing the student’s effort and thought process. Even if the answer is not completely correct, significant credit is given for demonstrating a clear understanding or a novel approach. Deductions are minimal for minor mistakes, and the overall goal is to encourage risk-taking and learning.
- **overall_instructor_guidelines** (Nullable): General grading criteria for all questions.
- **sub_rubrics** (Non-Null): A list of objects, each containing:
  - **question_index** (Non-Null): The question index.
  - **maximum_points** (Non-Null): Maximum points available.
  - **leniency** (Non-Null, Integer 1–5, Defaults to 3): Specific leniency for the question.
  - **instructor_guideline** (Nullable): Detailed grading criteria.

### [course](#course)
Represents a course; the combination of course_name and semester must be unique.
- **course_id** (Non-Null): Unique identifier.
- **course_name** (Non-Null): Name of the course.
- **semester** (Non-Null): Semester during which the course is offered.
- **instructors** (Non-Null): List of instructor emails.

### [assignment](#assignment)
Contains questions and guidelines for an assignment or quiz.
- **assignment_id** (Non-Null): The unique title or ID the assignment is known by.
- **course_id** (Non-Null): The course to which it belongs.
- **semester** (Non-Null): Semester during which the course is offered.
- **assignment_guidelines** (Nullable): General instructions or formatting requirements.
- **ordered_list** (Non-Null): A list of questions, each containing:
  - **question_text** (Non-Null): The question content.
  - **question_graphics_figures** (Nullable): Associated images/figures.

### [course_material](#course_material)
Contains the course material and its data_type.
- **course_id** (Non-Null): Associated course ID.
- **semester** (Non-Null): Semester during which the course is offered.
- **material_id** (Non-Null): Unique identifier.
- **material_name** (Non-Null): Title or name of the material.
- **additional_notes** (Nullable): Supplementary instructor notes.
- **data** (Non-Null):
  - **data_type** (Non-Null): (.png, .jpeg, .pdf, .mp3, .mp4, .html, .ppt, .doc, URL)
  - **metadata** (Nullable): Any associated metadata with the file.
  - **content** (Non-Null): Binary content encoded in Base64.

### [student](#student)
Contains basic student information.
- **student_identifier** (Non-Null): Unique identifier (e.g., BU email).
- **first_name** (Nullable): Student's first name.
- **last_name** (Nullable): Student's last name.

### [student_response](#student_response)
Represents a student’s answer to a question.
- **student_identifier** (Non-Null): Student's unique identifier.
- **assignment_id** (Non-Null): The unique title or ID the assignment is known by.
- **question_index** (Non-Null): The question being answered.
- **data** (Non-Null):
  - **data_type** (Non-Null): (.png, .jpeg, .pdf, .mp3, .mp4, .html, .ppt, .doc, URL)
  - **metadata** (Nullable): Any associated metadata with the file.
  - **content** (Non-Null): Binary content encoded in Base64.

### [grade](#grade)
Contains grading results for a student’s response.
- **student_identifier** (Non-Null): Student's unique identifier.
- **assignment_id** (Non-Null): The unique title or ID the assignment is known by.
- **question_index** (Non-Null): The question's index.
- **grade** (Non-Null): Awarded grade.
- **explanation** (Nullable): Explanation based on the rubric.

---

## API Endpoints

**Base URL:** `https://{domain}/api/v1`

Authentication can be performed using either an OAuth-obtained [personal_authentication_token](#personal_authentication_token) or an API-generated [access_token](#access_token).

---

### User Authentication Endpoints

<a id="post-auth-token"></a>
#### POST `/auth/token`
**Description:** Creates a new [access_token](#access_token) for programmatic API access.

- **JSON Body:**
  - **token_name** (Optional): Friendly name for the token.  
    *Default:* "token_1", "token_2", etc.

- **Returns:**  
  - An [access_token](#access_token) object

- **Errors:**
  - **400 Bad Request:** Invalid parameters.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

<a id="delete-auth-token"></a>
#### DELETE `/auth/token`
**Description:** Deletes an existing [access_token](#access_token).

- **JSON Body:**
  - **token_id** (Required): Unique identifier of the access token to delete.

- **Returns:**  
  - A success message.

- **Errors:**
  - **400 Bad Request:** token_id is missing or invalid.
  - **404 Not Found:** Token not found.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

<a id="get-auth-tokens"></a>
#### GET `/auth/tokens`
**Description:** Retrieves a list of active [access_token](#access_token) objects for the authenticated user.

- **Returns:**  
  - A list of [access_token](#access_token) objects.

- **Errors:**
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

<a id="get-auth-google-oauth"></a>
#### GET `/auth/google_oauth`
**Description:** Callback endpoint for processing Google OAuth. When a user authorizes via Google, they are redirected here to extract their authentication token.

- **Query Parameters:**
  - **access_token** (Required)
  - **expires_in** (Required)
  - **refresh_token** (Required)
  - **scope** (Required)
  - **token_type** (Required)
  - **id_token** (Required)

- **Returns:**  
  - The created or retrieved [user](#user) object.
  - A [personal_authentication_token](#personal_authentication_token) object required to access most endpoints.

- **Errors:**
  - **400 Bad Request:** Missing required OAuth parameters.
  - **401 Unauthorized:** Invalid OAuth parameters or unauthorized access to Google authentication endpoints.

---

### Course Endpoints

<a id="post-course"></a>
#### POST `/course`
**Description:** Creates a new [course](#course).

- **JSON Body:**
  - **course_name** (Required): Name of the course.
  - **course_id** (Required): Unique course identifier (e.g., "cs_132").
  - **semester** (Required): Semester during which the course is offered.
  - **instructors** (Required): List of instructor emails.

- **Returns:**  
  - The created [course](#course) object.

- **Errors:**
  - **400 Bad Request:** Missing or invalid parameters.
  - **409 Conflict:** A course with the same name and semester already exists.

---

<a id="delete-course"></a>
#### DELETE `/course`
**Description:** Deletes an existing [course](#course).

- **JSON Body:**
  - **course_id** (Required): Unique identifier.
  - **semester** (Required): Course semester.

- **Returns:**  
  - A success message.

- **Errors:**
  - **404 Not Found:** Course does not exist.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

<a id="patch-course-transfer"></a>
#### PATCH `/course/transfer`
**Description:** Transfers course materials and rubric data from a previous semester to a new one.

- **JSON Body:**
  - **current_course_id** (Required): ID of the course being updated.
  - **current_semester** (Required): Current semester.
  - **copy_from_course_id** (Required): ID of the course to copy from.
  - **copy_from_course_semester** (Required): Semester of the source course.

- **Returns:**  
  - A success message and/or the updated [course](#course) object.

- **Errors:**
  - **404 Not Found:** Source or destination course not found.
  - **400 Bad Request:** Invalid parameters.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

<a id="get-courses"></a>
#### GET `/courses`
**Description:** Retrieves all [course](#course) objects accessible by the authenticated user.

- **Returns:**  
  - A list of [course](#course) objects.

- **Errors:**
  - **401 Unauthorized:** Requester is not authenticated.

---

<a id="post-course-instructor"></a>
#### POST `/course/instructor`
**Description:** Adds an instructor to a [course](#course).

- **JSON Body:**
  - **course_id** (Required)
  - **semester** (Required)
  - **instructor** (Required): Email of the instructor to add.

- **Returns:**  
  - A success message.

- **Errors:**
  - **400 Bad Request:** Missing or invalid parameters.
  - **404 Not Found:** Course not found.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.
  - **409 Conflict:** Instructor is already assigned to the course.

---

<a id="delete-course-instructor"></a>
#### DELETE `/course/instructor`
**Description:** Removes an instructor from a [course](#course).

- **JSON Body:**
  - **course_id** (Required)
  - **semester** (Required)
  - **instructor** (Required): Email of the instructor to remove.

- **Returns:**  
  - A success message.

- **Errors:**
  - **400 Bad Request:** Missing or invalid parameters (i.e. can't remove yourself).
  - **404 Not Found:** Course or instructor assignment not found.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

### Assignment Endpoints

<a id="post-assignment"></a>
#### POST `/assignment`
**Description:** Creates a new [assignment](#assignment) with questions and guidelines.

- **JSON Body:**
  - **course_id** (Required)
  - **semester** (Required)
  // todo: maybe optional?
  - **assignment_id** (Required): The unique title or ID the assignment is known by.
  - **assignment_guidelines** (Required): General instructions.
  - **ordered_list** (Required): List of questions. Each item includes:
    - **question_text** (Required)
    - **question_graphics_figures** (Optional)

- **Returns:**  
  - The created [assignment](#assignment) object.

- **Errors:**
  - **400 Bad Request:** Missing or invalid parameters.
  - **404 Not Found:** Associated course not found.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

<a id="patch-assignment-add-question"></a>
#### PATCH `/assignment/add_question`
**Description:** Adds a new question to an [assignment](#assignment).

- **JSON Body:**
  - **assignment_id** (Required)
  - **question_text** (Required)
  - **question_graphics_figures** (Optional)

- **Returns:**  
  - The new question_index.

- **Errors:**
  - **400 Bad Request:** Missing or invalid parameters.
  - **404 Not Found:** Assignment not found.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

<a id="patch-assignment-remove-question"></a>
#### PATCH `/assignment/remove_question`
**Description:** Removes a question from an [assignment](#assignment).

- **JSON Body:**
  - **assignment_id** (Required)
  - **question_index** (Required)

- **Returns:**  
  - A success message.

- **Errors:**
  - **400 Bad Request:** Missing or invalid parameters.
  - **404 Not Found:** Assignment or question not found.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

<a id="patch-assignment-edit-question"></a>
#### PATCH `/assignment/edit_question`
**Description:** Edits an existing question in an [assignment](#assignment).

- **JSON Body:**
  - **assignment_id** (Required)
  - **question_index** (Required)
  - **new_question_text** (Required)
  - **new_question_graphics_figures** (Optional)

- **Returns:**  
  - A success message.

- **Errors:**
  - **400 Bad Request:** Missing or invalid parameters.
  - **404 Not Found:** Assignment or question not found.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

<a id="patch-assignment-modify-order"></a>
#### PATCH `/assignment/modify_order`
**Description:** Modifies the order of questions in an [assignment](#assignment).

- **JSON Body:**
  - **assignment_id** (Required)
  - **list_of_question_indexes** (Required): The new order for questions.

- **Returns:**  
  - The updated [assignment](#assignment) object.

- **Errors:**
  - **400 Bad Request:** Missing or invalid parameters.
  - **404 Not Found:** Assignment not found.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

<a id="get-assignment"></a>
#### GET `/assignment`
**Description:** Retrieves a specific [assignment](#assignment).

- **Query Parameters:**
  - **course_id** (Required)
  - **semester** (Non-Null): Semester during which the course is offered.
  - **assignment_id** (Required)

- **Returns:**  
  - The corresponding [assignment](#assignment) object.

- **Errors:**
  - **404 Not Found:** Assignment not found.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

<a id="get-assignments"></a>
#### GET `/assignments`
**Description:** Retrieves all [assignment](#assignment) objects associated with a course.

- **Query Parameters:**
  - **course_id** (Required)
  - **semester** (Non-Null): Semester during which the course is offered.

- **Returns:**  
  - A list of [assignment](#assignment) objects.

- **Errors:**
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

<a id="delete-assignment"></a>
#### DELETE `/assignment`
**Description:** Deletes a specified [assignment](#assignment).

- **JSON Body:**
  - **assignment_id** (Required)

- **Returns:**  
  - A success message.

- **Errors:**
  - **404 Not Found:** Assignment not found.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

### Student Response Endpoints

<a id="post-response"></a>
#### POST `/response`
**Description:** Uploads a [student_response](#student_response) to a specific assignment question.  The size of the data must be below a certain threshold or this endpoint will result in an error 400.

- **JSON Body:**
  - **student_identifier** (Required)
  - **assignment_id** (Required)
  - **question_index** (Required)
  - **data** (Required):
    - **data_type** (Required): (.png, .jpeg, .pdf, .mp3, .mp4, .html, .ppt, .doc, URL)
    - **metadata** (Optional): Any associated metadata with the file.
    - **content** (Required): Binary content encoded in Base64.

- **Returns:**  
  - A success message.

- **Errors:**
  - **400 Bad Request:** Missing or invalid parameters.
  - **404 Not Found:** Assignment or question not found.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

<a id="put response"></a>
#### PUT `/response`
**Description:** Replaces an existing [student_response](#student_response).  The size of the data must be below a certain threshold or this endpoint will result in an error 400.

- **JSON Body:**
  - **student_identifier** (Required)
  - **assignment_id** (Required)
  - **question_index** (Required)
  - **data** (Required):
    - **data_type** (Required): (.png, .jpeg, .pdf, .mp3, .mp4, .html, .ppt, .doc, URL)
    - **metadata** (Optional): Any associated metadata with the file.
    - **content** (Required): Binary content encoded in Base64.

- **Returns:**  
  - A success message.

- **Errors:**
  - **400 Bad Request:** Missing or invalid parameters.
  - **404 Not Found:** Existing response not found.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

<a id="delete-response"></a>
#### DELETE `/response`
**Description:** Deletes a [student_response](#student_response). If question_index is omitted, all responses for that assignment and student are deleted.

- **JSON Body:**
  - **student_identifier** (Required)
  - **assignment_id** (Required)
  - **question_index** (Optional)

- **Returns:**  
  - A success message.

- **Errors:**
  - **400 Bad Request:** Missing required parameters.
  - **404 Not Found:** Specified response not found.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

<a id="get-responses"></a>
#### GET `/responses`
**Description:** Retrieves [student_response](#student_response) objects (optionally including [grade](#grade) information) based on criteria.

- **Query Parameters:**
  - **assignment_id** (Required)
  - **question_index** (Optional)
  - **student_identifier** (Optional)

- **Returns:**  
  - Combined [student_response](#student_response) and [grade](#grade) objects (if graded).

- **Errors:**
  - **400 Bad Request:** Missing assignment_id.
  - **404 Not Found:** No matching responses found.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

<a id="post-response-grade-specific"></a>
### **POST `/response/grade/specific`**  
**Description:** Grades or regrades a specific student responses for an assignment.

- **JSON Body:**
  - **student_identifiers** (Required): List of student identifiers whom to grade.
  - **assignment_id** (Required)
  - **question_index** (Optional): Grades all questions for given assignment_id if omitted.

- **Returns:**  
  - A list of [grade](#grade) objects.

- **Errors:**
  - **400 Bad Request:** Missing or invalid parameters.
  - **502 Internal Server Error:** External LLM API call failure.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

<a id="post-response-grade-ungraded"></a>
### **POST `/response/grade/ungraded`**  
**Description:** Grades all ungraded responses for a specific assignment (optionally for a specific question).

- **JSON Body:**
  - **assignment_id** (Required)
  - **question_index** (Optional): Grades all ungraded questions for the assignment if omitted.

- **Returns:**  
  - A list of newly graded [grade](#grade) objects.

- **Errors:**
  - **400 Bad Request:** Missing or invalid parameters.
  - **502 Internal Server Error:** External LLM API call failure.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

<a id="post-response-grade-all"></a>
### **POST `/response/grade/all`**  
**Description:** Grades or regrades all student responses for a specific assignment (optionally for a specific question).  

- **JSON Body:**
  - **assignment_id** (Required)
  - **question_index** (Optional): Grades or Regrades all questions for the assignment if omitted.

- **Returns:**  
  - A list of all newly graded or regraded [grade](#grade) objects.

- **Errors:**
  - **400 Bad Request:** Missing or invalid parameters.
  - **502 Internal Server Error:** External LLM API call failure.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

### Course Material Endpoints

<a id="post-course-material"></a>
#### POST `/course_material`
**Description:** Uploads new [course_material](#course_material). The size of the data must be below a certain threshold or this endpoint will result in an error 400.

- **Parameters:**
  - **course_id** (Required)
  - **semester** (Required)
  - **material_name** (Optional): The friendly string name of the material.
  *Default: When not supplied defaults to Material 1, Material 2, etc...*
  - **additional_notes** (Optional)
  - **data** (Required):
    - **data_type** (Required): (.png, .jpeg, .pdf, .mp3, .mp4, .html, .ppt, .doc, URL)
    - **metadata** (Optional): Any associated metadata with the file.
    - **content** (Required): Binary content encoded in Base64.

- **Returns:**  
  - The created [course_material](#course_material) object.

- **Errors:**
  - **400 Bad Request:** Missing or invalid parameters.
  - **409 Conflict:** Material with the same identifier already exists.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

<a id="delete-course-material"></a>
#### DELETE `/course_material`
**Description:** Deletes specified [course_material](#course_material).

- **JSON Body:**
  - **course_id** (Required)
  - **semester** (Required)
  - **material_id** (Required)

- **Returns:**  
  - A success message.

- **Errors:**
  - **404 Not Found:** Material not found.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

<a id="patch-course-material"></a>
#### PATCH `/course_material`
**Description:** Updates existing [course_material](#course_material). The size of the data must be below a certain threshold or this endpoint will result in an error 400.

- **JSON Body:**
  - **course_id** (Required)
  - **semester** (Required)
  - **material_id** (Required): ID of the material we are updated.
  - **material_name** (Optional): The friendly string name of the material.
  - **additional_notes** (Optional)
  - **data** (Optional):
    - **data_type** (Required): (.png, .jpeg, .pdf, .mp3, .mp4, .html, .ppt, .doc, URL)
    - **metadata** (Optional): Any associated metadata with the file.
    - **content** (Required): Binary content encoded in Base64.

- **Returns:**  
  - The updated [course_material](#course_material) object.

- **Errors:**
  - **400 Bad Request:** Missing or invalid parameters.
  - **404 Not Found:** Material to update not found.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

### Rubric Endpoints

<a id="put-rubric"></a>
#### PUT `/rubric`
**Description:** Manually creates a new [rubric](#rubric) for an assignment.

- **JSON Body:**
  - **assignment_id** (Required)
  - **max_points** (Required): Total maximum points (must be ≥ sum of individual question points).
  - **overall_instructor_guidelines** (Optional)
  - **grading_flags**: A list of grading flags.
    - IGNORE_SPELLINGS: Don't penalize for minor spelling mistakes.
    - IGNORE_GRAMMAR: Don't penalize for minor grammar issues.
    - ORIGINALITY: Award points for originality and creativity while deducting for unoriginal ideas.
    - IGNORE_FORMATTING: Don't penalize for formatting issues.
  - **leniency** (Optional; defaults to 3): A number between 1-5 where 1 is very strict and 5 is very lenient.
  - **sub_rubrics** (Required): A list of sub-rubric objects, each including:
    - **question_index** (Required)
    - **maximum_points** (Required)
    - **instructor_guideline** (Required)

- **Returns:**  
  - The created [rubric](#rubric) object.

- **Errors:**
  - **400 Bad Request:** Missing or invalid parameters.
  - **404 Not Found:** Assignment not found.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

<a id="get-ai-rubric"></a>
#### GET `/ai_rubric`
**Description:** Enhances an existing [rubric](#rubric) using AI-based improvements.  
If a [rubric](#rubric) does not exist for the given assignment, a new one is generated with its own guidelines.  
*Note: This only proposes a new rubric and does not modify or create an existing rubric.*

- **JSON Body:**
  - **assignment_id** (Required)
  - **instructions** (Optional): Specific improvement instructions. If omitted, default instructions are applied.

- **Returns:**  
  - The improved [rubric](#rubric) object.

- **Errors:**
  - **502 Internal Server Error:** External LLM API call failure.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

<a id="get-rubric"></a>
#### GET `/rubric`
**Description:** Retrieves the [rubric](#rubric) for a specified assignment (or for a specific question).

- **Query Parameters:**
  - **assignment_id** (Required)
  - **question_index** (Optional): If omitted, returns the full [rubric](#rubric).

- **Returns:**  
  - The [rubric](#rubric) object.

- **Errors:**
  - **404 Not Found:** [Rubric](#rubric) or specified question not found.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---