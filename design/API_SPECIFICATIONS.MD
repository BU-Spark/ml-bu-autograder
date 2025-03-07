## API Endpoints

**Base:** https://{domain}/api/v1

**Authentication:** There are two methods of authentication. Providing an authorization token that is obtained from an OAuth authentication. Or providing a access token that each user can generate.

Questions: Do they want a UI for this, or do they think they have the technical knowledge to directly use the API?

### User Authentication Endpoint

This endpoint is related to authentication and security.

- POST /auth/token - Create a new access token.
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
        - Ordered List
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

### Grading Endpoint

Request related to student grades are directed here.

/grade

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

- POST /rubric
    - Assignment ID
    - 
- GET /make-rubric
    - Leniency