# BU MET Autograder API Design Specifications (V2.1)

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

2. [API Endpoints](#api_endpoints)
   - **User Authentication Endpoints**
     - [POST /auth/token](#post_auth_token)
     - [DELETE /auth/token](#delete_auth_token)
     - [GET /auth/tokens](#get_auth_tokens)
     - [GET /auth/google_oauth](#get_auth_google_oauth)
   - **Course Endpoints**
     - [POST /course](#post_course)
     - [DELETE /course](#delete_course)
     - [PATCH /course/transfer](#patch_course_transfer)
     - [GET /courses](#get_courses)
     - [POST /course/instructor](#post_course_instructor)
     - [DELETE /course/instructor](#delete_course_instructor)
   - **Assignment Endpoints**
     - [POST /assignment](#post_assignment)
     - [PATCH /assignment/add_question](#patch_assignment_add_question)
     - [PATCH /assignment/remove_question](#patch_assignment_remove_question)
     - [PATCH /assignment/edit_question](#patch_assignment_edit_question)
     - [PATCH /assignment/modify_order](#patch_assignment_modify_order)
     - [GET /assignment](#get_assignment)
     - [GET /assignments](#get_assignments)
     - [DELETE /assignment](#delete_assignment)
   - **Student Response Endpoints**
     - [POST /response](#post_response)
     - [PUT /response](#put_response)
     - [DELETE /response](#delete_response)
     - [GET /responses](#get_responses)
     - [POST /response/grade](#post_response_grade)
   - **Course Material Endpoints**
     - [POST /course_material](#post_course_material)
     - [DELETE /course_material](#delete_course_material)
     - [PATCH /course_material](#patch_course_material)
   - **Rubric Endpoints**
     - [POST /rubric](#post_rubric)
     - [PUT /ai_rubric](#put_ai_rubric)
     - [GET /rubric](#get_rubric)

---

## Objects

### [user](#user)
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
- **leniency** (Non-Null, Integer 1–5): Overall leniency rating.
  - **5:** Grade mostly on effort; minor work shown means minimal point deductions.
  - **1:** Strict adherence to guidelines; deviations may lose points.
- **overall_instructor_guidelines** (Nullable): General grading criteria for all questions.
- **sub_rubrics** (Non-Null): A list of objects, each containing:
  - **question_index** (Non-Null): The question index.
  - **maximum_points** (Non-Null): Maximum points available.
  - **leniency** (Non-Null, Integer 1–5, Defaults to 3): Specific leniency for the question.
  - **instructor_guideline** (Nullable): Detailed grading criteria.

### [course](#course)
Represents a course; the combination of course_name and semester must be unique.
- **course_id** (Non-Null): Unique identifier.
- **course_owner_id** (Non-Null): The creator's user ID.
- **course_name** (Non-Null): Name of the course.
- **semester** (Non-Null): Semester during which the course is offered.
- **instructors** (Non-Null): List of instructor emails.

### [assignment](#assignment)
Contains questions and guidelines for an assignment or quiz.
- **assignment_id** (Non-Null): Unique identifier.
- **course_id** (Non-Null): The course to which it belongs.
- **assignment_title** (Nullable): Title of the assignment.
- **assignment_guidelines** (Nullable): General instructions or formatting requirements.
- **ordered_list** (Non-Null): A list of questions, each containing:
  - **question_text** (Non-Null): The question content.
  - **question_graphics_figures** (Nullable): Associated images/figures.

### [course_material](#course_material)
Contains the course material and its modality.
- **course_id** (Non-Null): Associated course ID.
- **material_id** (Non-Null): Unique identifier.
- **material_name** (Non-Null): Title or name of the material.
- **additional_notes** (Nullable): Supplementary instructor notes.
- **modality** (Non-Null): Type (video, audio, image, text, powerpoint, pdf, website).
- **data** (Non-Null): Binary content or data.

### [student](#student)
Contains basic student information.
- **student_identifier** (Non-Null): Unique identifier (e.g., BU email).
- **first_name** (Nullable): Student's first name.
- **last_name** (Nullable): Student's last name.

### [student_response](#student_response)
Represents a student’s answer to a question.
- **student_identifier** (Non-Null): Student's unique identifier.
- **assignment_id** (Non-Null): The assignment's ID.
- **question_index** (Non-Null): The question being answered.
- **response_modality** (Non-Null): Format (video, audio, image, text, powerpoint, pdf, website).
- **data** (Non-Null): Content of the response.

### [grade](#grade)
Contains grading results for a student’s response.
- **student_identifier** (Non-Null): Student's unique identifier.
- **assignment_id** (Non-Null): Assignment identifier.
- **question_index** (Non-Null): The question's index.
- **grade** (Non-Null): Awarded grade.
- **explanation** (Nullable): Explanation based on the rubric.

---

## API Endpoints

**Base URL:** `https://{domain}/api/v1`

Authentication can be performed using either an OAuth-obtained [personal_authentication_token](#personal_authentication_token) or an API-generated [access_token](#access_token).

---

### User Authentication Endpoints

#### POST `/auth/token`
**Description:** Creates a new [access_token](#access_token) for programmatic API access.

- **Parameters:**
  - **token_name** (Optional): Friendly name for the token.  
    *Default:* "token_1", "token_2", etc.

- **Returns:**  
  - An [access_token](#access_token) object

- **Errors:**
  - **400 Bad Request:** Invalid parameters.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

#### DELETE `/auth/token`
**Description:** Deletes an existing [access_token](#access_token).

- **Parameters:**
  - **token_id** (Required): Unique identifier of the access token to delete.

- **Returns:**  
  - A success message.

- **Errors:**
  - **400 Bad Request:** token_id is missing or invalid.
  - **404 Not Found:** Token not found.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

#### GET `/auth/tokens`
**Description:** Retrieves a list of active [access_token](#access_token) objects for the authenticated user.

- **Returns:**  
  - A list of [access_token](#access_token) objects.

- **Errors:**
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

#### GET `/auth/google_oauth`
**Description:** Callback endpoint for processing Google OAuth. When a user authorizes via Google, they are redirected here to extract their authentication token.

- **Parameters:**
  - **access_token** (Required)
  - **expires_in** (Required)
  - **refresh_token** (Required)
  - **scope** (Required)
  - **token_type** (Required)
  - **id_token** (Required)

- **Returns:**  
  - A [personal_authentication_token](#personal_authentication_token) object required to access most endpoints.

- **Errors:**
  - **400 Bad Request:** Missing required OAuth parameters.
  - **401 Unauthorized:** Invalid OAuth parameters or unauthorized access to Google authentication endpoints.

---

### Course Endpoints

#### POST `/course`
**Description:** Creates a new [course](#course).

- **Parameters:**
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

#### DELETE `/course`
**Description:** Deletes an existing [course](#course).

- **Parameters:**
  - **course_id** (Required): Unique identifier.
  - **semester** (Required): Course semester.

- **Returns:**  
  - A success message.

- **Errors:**
  - **404 Not Found:** Course does not exist.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

#### PATCH `/course/transfer`
**Description:** Transfers course materials and rubric data from a previous semester to a new one.

- **Parameters:**
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

#### GET `/courses`
**Description:** Retrieves all [course](#course) objects accessible by the authenticated user.

- **Returns:**  
  - A list of [course](#course) objects.

- **Errors:**
  - **401 Unauthorized:** Requester is not authenticated.

---

#### POST `/course/instructor`
**Description:** Adds an instructor to a [course](#course).

- **Parameters:**
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

#### DELETE `/course/instructor`
**Description:** Removes an instructor from a [course](#course).

- **Parameters:**
  - **course_id** (Required)
  - **semester** (Required)
  - **instructor** (Required): Email of the instructor to remove.

- **Returns:**  
  - A success message.

- **Errors:**
  - **400 Bad Request:** Missing or invalid parameters.
  - **404 Not Found:** Course or instructor assignment not found.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

### Assignment Endpoints

#### POST `/assignment`
**Description:** Creates a new [assignment](#assignment) with questions and guidelines.

- **Parameters:**
  - **course_id** (Required)
  - **semester** (Required)
  - **assignment_guidelines** (Required): General instructions.
  - **ordered_list** (Required): List of questions. Each item includes:
    - **question_text** (Required)
    - **question_graphics_figures** (Optional)

- **Returns:**  
  - The created [assignment](#assignment) object (including assignment_id).

- **Errors:**
  - **400 Bad Request:** Missing or invalid parameters.
  - **404 Not Found:** Associated course not found.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

#### PATCH `/assignment/add_question`
**Description:** Adds a new question to an [assignment](#assignment).

- **Parameters:**
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

#### PATCH `/assignment/remove_question`
**Description:** Removes a question from an [assignment](#assignment).

- **Parameters:**
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

#### PATCH `/assignment/edit_question`
**Description:** Edits an existing question in an [assignment](#assignment).

- **Parameters:**
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

#### PATCH `/assignment/modify_order`
**Description:** Modifies the order of questions in an [assignment](#assignment).

- **Parameters:**
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

#### GET `/assignment`
**Description:** Retrieves a specific [assignment](#assignment).

- **Parameters:**
  - **course_id** (Required)
  - **assignment_id** (Required)

- **Returns:**  
  - The corresponding [assignment](#assignment) object.

- **Errors:**
  - **404 Not Found:** Assignment not found.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

#### GET `/assignments`
**Description:** Retrieves all [assignment](#assignment) objects associated with a course.

- **Parameters:**
  - **course_id** (Required)

- **Returns:**  
  - A list of [assignment](#assignment) objects.

- **Errors:**
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

#### DELETE `/assignment`
**Description:** Deletes a specified [assignment](#assignment).

- **Parameters:**
  - **assignment_id** (Required)

- **Returns:**  
  - A success message.

- **Errors:**
  - **404 Not Found:** Assignment not found.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

### Student Response Endpoints

#### POST `/response`
**Description:** Uploads a [student_response](#student_response) to a specific assignment question.

- **Parameters:**
  - **student_identifier** (Required)
  - **assignment_id** (Required)
  - **question_index** (Required)
  - **response_modality** (Required): (video, audio, image, text, powerpoint, pdf, website)
  - **data** (Required): Binary content.

- **Returns:**  
  - A success message.

- **Errors:**
  - **400 Bad Request:** Missing or invalid parameters.
  - **404 Not Found:** Assignment or question not found.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

#### PUT `/response`
**Description:** Replaces an existing [student_response](#student_response).

- **Parameters:**
  - **student_identifier** (Required)
  - **assignment_id** (Required)
  - **question_index** (Required)
  - **response_modality** (Required)
  - **data** (Required): Updated binary content.

- **Returns:**  
  - A success message.

- **Errors:**
  - **400 Bad Request:** Missing or invalid parameters.
  - **404 Not Found:** Existing response not found.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

#### DELETE `/response`
**Description:** Deletes a [student_response](#student_response). If question_index is omitted, all responses for that assignment and student are deleted.

- **Parameters:**
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

#### GET `/responses`
**Description:** Retrieves [student_response](#student_response) objects (optionally including [grade](#grade) information) based on criteria.

- **Parameters:**
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

#### POST `/response/grade`
**Description:** Requests grading for [student_response](#student_response) objects. Supports multiple modes.

- **Parameters (Depending on Mode):**
  - **For Specific or Batch Grading:**
    - **type** (Required): `specific`
    - **student_identifiers** (Required): List of student identifiers.
    - **assignment_id** (Required)
    - **question_index** (Optional): Grades all questions if omitted.
  - **For Grading Ungraded Work:**
    - **type** (Required): `ungraded`
    - **assignment_id** (Required)
    - **question_index** (Optional)
  - **For Grading/Regrading All Work:**
    - **type** (Required): `all`
    - **assignment_id** (Required)
    - **question_index** (Optional)

- **Returns:**  
  - A list of [grade](#grade) objects.

- **Errors:**
  - **400 Bad Request:** Missing or invalid parameters.
  - **502 Internal Server Error:** External LLM API call failure.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

### Course Material Endpoints

#### POST `/course_material`
**Description:** Uploads new [course_material](#course_material).

- **Parameters:**
  - **course_id** (Required)
  - **semester** (Required)
  - **material_name** (Required)
  - **modality** (Required): (video, audio, image, text, powerpoint, pdf, website)
  - **additional_notes** (Optional)
  - **data** (Required): Binary content.

- **Returns:**  
  - The created [course_material](#course_material) object.

- **Errors:**
  - **400 Bad Request:** Missing or invalid parameters.
  - **409 Conflict:** Material with the same identifier already exists.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

#### DELETE `/course_material`
**Description:** Deletes specified [course_material](#course_material).

- **Parameters:**
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

#### PATCH `/course_material`
**Description:** Updates existing [course_material](#course_material).

- **Parameters:**
  - **course_id** (Required)
  - **semester** (Required)
  - **material_id** (Required)
  - **material_name** (Optional)
  - **additional_notes** (Optional)
  - **modality** (Optional)
  - **data** (Optional)

- **Returns:**  
  - The updated [course_material](#course_material) object.

- **Errors:**
  - **400 Bad Request:** Missing or invalid parameters.
  - **404 Not Found:** Material to update not found.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

### Rubric Endpoints

#### PUT `/rubric`
**Description:** Manually creates a new [rubric](#rubric) for an assignment.

- **Parameters:**
  - **assignment_id** (Required)
  - **max_points** (Required): Total maximum points (must be ≥ sum of individual question points).
  - **overall_instructor_guidelines** (Optional)
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

#### GET `/ai_rubric`
**Description:** Enhances an existing [rubric](#rubric) using AI-based improvements.  
If a [rubric](#rubric) does not exist for the given assignment, a new one is generated with its own guidelines.  
*Note: This only proposes a new rubric and does not modify or create an existing rubric.*

- **Parameters:**
  - **assignment_id** (Required)
  - **instructions** (Optional): Specific improvement instructions. If omitted, default instructions are applied.

- **Returns:**  
  - The improved [rubric](#rubric) object.

- **Errors:**
  - **502 Internal Server Error:** External LLM API call failure.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---

#### GET `/rubric`
**Description:** Retrieves the [rubric](#rubric) for a specified assignment (or for a specific question).

- **Parameters:**
  - **assignment_id** (Required)
  - **question_index** (Optional): If omitted, returns the full [rubric](#rubric).

- **Returns:**  
  - The [rubric](#rubric) object.

- **Errors:**
  - **404 Not Found:** [Rubric](#rubric) or specified question not found.
  - **401 Unauthorized:** Requester is not authenticated.
  - **403 Forbidden:** Authenticated but access is not allowed.

---