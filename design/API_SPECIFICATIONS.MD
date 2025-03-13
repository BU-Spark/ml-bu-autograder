## Objects
This section of the specifications detail the composition and fields of the various objects involved.

### User (A Course Instructor)
- User ID: An internal ID of the user.
- First Name: User's first name.
- Last Name: User's last name.
- User Email: The email of the user.

### Personal Authentication Token
This JWT access token is intended for interactive user sessions on the official front end.
- User ID: The ID of the user.
- Authentication Token: The string token

### Access Token
This access token is used to access the API programmatically. It is functionally equivalent to the Personal Authentication Token except that it cannot be used to create another access token.
- User ID: The ID of the user owning this authentication token.
- Token Name: The friendly string token name. Must be unique per user.
- Token ID: The string of the secret token. This is only shown to the user once.
- Token Expiry: When does this access token expire. If not specified, it never expires.

### Rubric
The Rubric object contains instructions for the LLM how to grade in terms of leniency, point allotments, and what things to deduct points for.
- Assignment ID: the id of the assignment this rubric is associated with.
- Leniency (1-5): How lenient should the grader be?
  - 5: Only grade based on effort. Points only deducted if either there is no work shown or the work shown indicates student didn't really think through the solution.
  - ...
  - 1: Any deviation from instructor guidelines results in lost points. Even the specific vocabulary is important.
- Overall Instructor Guidelines (nullable): Grading criteria that applies to all questions.
- List:
  - Question Index: The question for which this sub-rubric is for
  - Maximum Points: The max points student can get for this question
  - Leniency (1-5): How lenient should the grader be on this SPECIFIC question. If not specified, global leniency is used. (nullable).
  - Instructor Guideline: Grading criteria for this specific question breaking down the grading categories.

### Course
Holds the overall course object. Course Name and Semester are unique together.
- Course ID: The ID of the course.
- Course Owner ID: The ID of the user who created this course.
- Course Name: The name of the course.
- Semester: The semester of the course.
- Instructors: A list of emails consisting of authenticated instructors for this course.

### Assignment
The assignment object contains the question sub-objects and the guidelines for the assignment.
- Assignment ID: The ID of the assignment.
- Course ID: The ID of the course this assignment is associated with.
- Assignment Title: The title of the assignment.
- Assignment Guidelines: Guidelines that apply to all questions (i.e. requirements for what format your answer should be such as whether you are required to show your work)
- Ordered List: A list of questions in this assignment
  - Question Text
  - Question Graphics/Figures

### Course Material
The course material object contains the course material and the modality of the material.
- Course ID: The ID of the course.
- Material ID: The ID of the material.
- Material Name: The name of the material.
- Additional Notes: Any additional notes about the material that you want the LLM to know. (Optional)
- Modality: The modality of the material (Video, Audio, Image, Text, PowerPoint, PDF, Website)
- Data: The actual data of the material.

### Student
The student object contains the student's information.
- Student Identifier: Some unique identifier that should be used to identify this student. (i.e. their BU email)
- First Name: Student's first name.
- Last Name: Student's last name.

### Student Response
The student response object contains the student's response to a question.
- Student Identifier: Some unique identifier that should be used to identify this student.
- Assignment ID: The ID of the assignment student is responding to.
- Question Index: The index of the question student is responding to.
- Response Modality: The modality of the response (Video, Audio, Image, Text, PowerPoint, PDF, Website)
- Data: The actual data of the response.

### Grade
The grade object contains the graded information for a student's response.
- Student Identifier: Some unique identifier that should be used to identify this student.
- Assignment ID: The ID of the assignment this grade is for.
- Question Index: The index of the question this grade is for.
- Grade: The grade the student received.
- Explanation: The explanation of the grade and its correspondence to the rubric.


## API Endpoints

**Base:** https://{domain}/api/v1

**Authentication:** There are two methods of authentication. Providing an authorization token that is obtained from an OAuth authentication. Or providing a access token that each user can generate.

### User Authentication Endpoint

This endpoint is related to authentication and security.

- POST /auth/token - Create a new access token for accessing the API.
    - Parameters
        - Token Name: The friendly name of the token (optional)
            - Default: Token 1, Token 2, …
    - Returns:
        - Token ID
        - Token Name
        - Access Token Secret
- DELETE  /auth/token - Create an access token
    - Parameters:
        - Token ID
- GET /auth/tokens - Get list of all active access tokens
    - Returns:
        - List
            - Token ID
            - Token Name
- GET /auth/google-oauth - When a user authorizes Google OAuth, google redirects them to this endpoint where we can extract their authentication token.
    - Parameters:
        - access_token
        - expires_in
        - refresh_token
        - scope
        - token_type
        - id_token
    - Returns
        - Authorization Token (this token would be required to access most endpoints)

### Course Endpoint

Requests related to the course itself and managing who has access to this course.

- POST /course
    - Parameters:
        - Course Name: The name of the course.
        - Course ID: The ID of the course (i.e. CS 132)
        - Semester: The semester of the course.
        - Instructors: A list of emails consisting of authenticated instructors for this course.
- DELETE /course
    - Course ID: The ID of the course
    - Semester: The semester of the course.
- PATCH /course/transfer - used to transfer course materials and rubric from a previous semester to a new one.
    - Current Course ID: The ID of the course.
    - Current Semester: The semester of the course.
    - Copy From Course ID: The ID of the course you want to transfer data from.
    - Copy From Course Semester: The semester of the course you want to transfer data from.
- GET /courses
    - Returns:
        - List of courses the authenticated user has access to.
- DELETE or POST /course/instructor
    - Course ID: The ID of the course.
    - Semester: The semester of the course.
    - Instructor: The email of the instructor to add or remove.

### Assignments Endpoint

This endpoint is related to managing the assignment or quiz which is to be graded.

- POST /assignment
    - Parameters:
        - Course ID: The ID of the course
        - Semester: The semester of the course
        - Assignment Guidelines: Guidelines that apply to all questions (i.e. requirements for what format your answer should be such as whether you are required to show your work)
        - Ordered List: A list of questions in this assignment
            - Question Text
            - Question Graphics/Figures
    - Returns:
        - Assignment ID
- PATCH /assignment/<action>
    - When <action> is add-question
        - Parameters:
            - Question Text
            - Question Graphics/Figures
        - Returns:
            - Question Index
    - When <action> is remove-question
        - Parameters:
            - Question Index (i.e. for question 1, this is 1)
    - When <action> is edit-question
        - Parameters:
            - Question Index
            - New Question Text
            - New Question Graphics/Figures
    - When <action> is modify-order
        - Parameters:
            - List of Question Indexes in the new order
- GET /assignment
    - Parameters:
        - Assignment ID
    - Returns:
        - Assignment Object
- GET /assignments
    - Returns:
        - List
            - Assignment Object
- DELETE /assignment
    - Parameters:
        - Assignment ID

### Student Response Endpoint

Request related to student response management, including the grading of those responses are here.
- POST /response - upload a student response
    - Parameters:
        - Student Identifier: Unique identifier for the student
        - Assignment ID: The ID of the assignment
        - Question Index: The index of the question being responded to
        - Response Modality: The modality of the response (Video, Audio, Image, Text, PowerPoint, PDF, Website)
        - Data: The actual content of the student's response
    - Returns:
        - Success message
- PUT /response - replace an existing student response with a new response
    - Parameters:
        - Student Identifier: Unique identifier for the student
        - Assignment ID: The ID of the assignment
        - Question Index: The index of the question being responded to
        - Response Modality: The new modality of the response
        - Data: The new content of the student's response
    - Returns:
        - Success message
- DELETE /response - delete a submitted student response
    - Parameters:
        - Student Identifier: Unique identifier for the student
        - Assignment ID: The ID of the assignment
        - Question Index: The index of the question (Optional)
    - Description: If no Question Index provided, deletes all responses for the specified assignment and student
    - Returns:
        - Success message
- GET /responses - get all submitted student responses that match specified criteria (including with grades with the responses have been graded)
    - Parameters:
        - Assignment ID: The ID of the assignment (Required)
        - Question Index: The index of the question (Optional)
        - Student Identifier: Unique identifier for the student (Optional)
    - Returns:
        - Student Response Object
        - Grade Object
- POST /response/grade - request student (a) response(s) to be graded. Support batch grading if the grading of multiple responses is specified.
    - Parameters:
        - For Single Grading OR Batch Grading:
          - Type: SPECIFIC (requests grading of specific responses)
          - Student Identifier(s): A list of unique identifier for the students whose responses to request to be graded (or regraded).
          - Assignment ID: The ID of the assignment
          - Question Index: The index of the question (Optional, if not specified will grade all questions for that assignment)
        - For Grading Just Ungraded Work:
          - Type: UNGRADED
          - Assignment ID: The ID of the assignment
          - Question Index: The index of the question (Optional, if not specified will grade all questions for that assignment)
        - For Grading or Regraded All Work:
          - Type: ALL
          - Assignment ID: The ID of the assignment
          - Question Index: The index of the question (Optional, if not specified will grade all questions for that assignment)
    - Returns:
        - List of Grade objects
### Course Material Endpoint

Requests related to course materials are directed here.

- POST /course-material
    - Course ID
    - Semester
    - Modality (Video, Audio, Image, Text, Powerpoint, PDF, Website)
- DELETE /course-material
- PATCH /course-material

### Rubrics Endpoint

This endpoint manages the rubrics. Rubrics can either be manually specified or AI generated or a combination of both.

- POST /rubric - manually specify a rubric
  - Assignment ID
  - Max Points
  - Overall Rubric Data (nullable)
  - List:
    - Question Index: The question for which this rubric is for
    - Maximum Points: The max points student can get for this question
    - Rubric Data: Grading criteria for this question further breaking down the grading categories.
- PATCH /enhance-rubric - uses AI to enhance specified rubric:
  - Parameters:
    - Instructions: The specific instructions about what aspects to enhance about the rubric. A default value is provided.
  - Returns:
    - Improved rubric
- GET /rubric
  - Parameters:
      - Assignment ID: The assignment for which to get the rubric for.
      - Question Index: The specific question for which to retrieve the rubric (Optional)
  - Returns:
    - Max Points: The max point points student can get for this assignment. Must be larger than or equal to the sum of the individual questions.
    - Overall Rubric Data (nullable): Rubric data that doesn't apply to a specific question
    - List:
      - Question Index: The question for which this rubric is for
      - Maximum Points: The max points student can get for this question
      - Rubric Data: Grading criteria for this question further breaking down the grading categories.