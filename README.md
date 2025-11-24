# MET BU Autograder 

**A Boston University SPARK Project**  
**For Boston University’s Metropolitan College Office of Education Technology and Innovation (MET ETI)**

---

## 📖 Table of Contents  
1. [Overview](#-overview)  
2. [✨ Key Features](#-key-features)  
3. [ Goals](#-goals)  
4. [ Tech Stack](#-tech-stack)
5. [📌 Development Roadmap](#-development-roadmap)  
6. [ Setup Instructions](#-setup-instructions)  
   - [📦 Prerequisites](#-prerequisites)  
   - [📥 Clone the Repository](#-clone-the-repository)  
   - [🐍 Create a Virtual Environment](#-create-a-virtual-environment)  
   - [📜 Install Dependencies](#-install-dependencies)  
   - [ Setup Environment Variables](#-setup-environment-variables)  
   - [ Start the Application](#-start-the-application)  
   - [📑 API Documentation](#-api-documentation)  
7. [📊 Workflow Diagram](#-workflow-diagram)  
8. [📂 Project Structure](#-project-structure)  
9. [ Azure Storage Format](#-azure-storage-format)
10. [👥 Team](#-team)  
11. [📜 License](#-license)  

---

## 🌍 Overview

**MET BU Autograder** is a web-based REST API for AI-Assisted Grading of written and “complex” assignments. It refines and optimizes grading capabilities using various Large Language Models (LLMs) and advanced context management.  

Developed as part of a **Boston University SPARK** project for **BU MET ETI**, this tool is designed to integrate seamlessly with multiple LLM backends and provide a robust, well-documented API for clients seeking to enhance their grading workflows.

---

## ✨ Key Features

 **Context Management Strategies** - Ensures the AI retains necessary context across requests over otherwise stateless APIs.

 **Retrieval-Augmented Generation** - Uses a vector database to store supplemental data like documents, videos, images, and graphs.

 **Web Crawling** - Gathers assignment-relevant information with optional automatic update checking.

 **Prompt Engineering** - Uses zero-shot, few-shot, self-consistency prompting, and instruction tuning.

 **File Conversion & Extraction** - Supports multiple formats (CSV, PDF, diagrams, PowerPoints) to feed into LLM APIs.

---

##  Goals

 **Future-Proof Design**: Integrate with multiple text-based or vision-based LLM backends.  
 **Consistent Grading**: Standardized grading approach for improved fairness and reliability.  
 **Well-Documented API**: Clear and accessible documentation for clients and contributors.  
 **Efficiency**: Minimize unnecessary external API calls to reduce costs while maintaining high accuracy.

---

##  Tech Stack

🟡 **Language**: Python 🐍  
 **Framework**: FastAPI   
🔵 **Others**:  
   - LLM integration (multiple providers)  
   - Vector databases (for retrieval-augmented generation)  
   - Web crawling utilities (Selenium, requests)

---

## 📌 Development Roadmap

 **Phase 0:** Project Vision & Goals ✅

 **Phase 1:** Project Setup & Initial API Development ✅

 **Phase 2:** LLM Integration & Context Management ⏳

 **Phase 3:** Web Crawling & Vector Database Implementation ⏳  

 **Phase 4:** Performance Optimization & API Documentation ⏳  

 **Phase 5:** Deployment & User Testing ⏳  

---

## 📊 Workflow Diagram

Below is a visual representation of our current workflow for the MET BU Autograder workflow:

![proposed-workflow](assets/proposed-workflow.png)

---

##  Setup Instructions

### 📦 Prerequisites
- Python 3.11 or higher installed on your system.
- Pip 24.0 or higher installed on your system.

*Older versions may work*

### 📥 Clone the Repository

Clone the project repository to your local machine:

```bash
git clone <repository_url>
cd <repository_folder>
```

*Replace `<repository_url>` with your repository URL and `<repository_folder>` with the cloned folder name.*

### 🐍 Create a Virtual Environment

It is recommended to use a virtual environment to manage project dependencies.

#### On Linux/macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

#### On Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

### 📜 Install Dependencies

Upgrade pip and install the project requirements using the provided `requirements.txt` file:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

###  Setup Environment Variables

Copy the sample `.env-example` file to `.env`. Then provide or modify all environment variables as needed.

To generate a secure JWT encryption secret, run the script located at the root of the repository:

```bash
python generate_jwt_secret.py
```

Then, set the `JWT_ENCRYPTION_SECRET_FILE` environment variable to the path of the generated secret file (output by the script).

###  Start the Application

Start the FastAPI application using Uvicorn with the auto-reload option for development:

```bash
uvicorn app.main:app --reload --port 8000
```

The server should start on [http://localhost:8000](http://localhost:8000).

To start the FastAPI application for production use, run the following instead:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Feel free to modify the port or host to your use case in either case.

### 📑 API Documentation

Once the application is running, you can view the interactive API documentation generated by FastAPI:

- **Swagger UI:** [{BASE_URL}/docs](http://localhost:8000/docs)
- **ReDoc:** [{BASE_URL}/redoc](http://localhost:8000/redoc)

## 📂 Project Structure

###  Backend
```
app
├── README.md
├── __init__.py
├── main.py
├── models
│ ├── __init__.py
│ ├── assignment.py
│ ├── course.py
│ ├── course_material.py
│ ├── grade.py
│ ├── rubric.py
│ ├── student.py
│ ├── student_response.py
│ ├── token.py
│ ├── uploaded_file.py
│ └── user.py
├── requirements.txt
├── routes
│ ├── __init__.py
│ ├── assignment.py
│ ├── auth.py
│ ├── course.py
│ ├── course_material.py
│ ├── grading.py
│ ├── rubric.py
│ ├── student_response.py
│ └── user.py
└── utils
    ├── __init__.py
    ├── azure_ai_service.py
    ├── azure_blob_uploader.py
    └── json_web_token.py

```

### 💻 Frontend
```
frontend
├── README.md
├── next.config.js
├── package-lock.json
├── package.json
├── public
│ ├── icons
│ │ └── favicon.ico
│ ├── images
│ │ ├── avatar-placeholder.png
│ │ ├── bu-logo.png
│ │ ├── bu-met-logo.png
│ │ ├── favicon.png
│ │ └── login-background.png
│ └── robots.txt
└── src
    ├── ThemeContext.js
    ├── api.js
    ├── components
    │ ├── AISuggestionCard.js
    │ ├── CardSkeleton.js
    │ ├── ConfirmationDialog.js
    │ ├── Footer.js
    │ ├── GradingModeSelect.js
    │ ├── Header.js
    │ ├── Layout.js
    │ ├── Navigation.js
    │ ├── SelectableList.js
    │ └── ThemeToggle.js
    ├── config.js
    ├── pages
    │ ├── _app.js
    │ ├── course
    │ │ └── [id]
    │ │     ├── assignments.js
    │ │     ├── grading.js
    │ │     ├── index.js
    │ │     ├── instructors.js
    │ │     ├── materials.js
    │ │     └── rubrics.js
    │ ├── courses.js
    │ ├── login.js
    │ ├── manual_submission.js
    │ └── settings.js
    ├── styles
    │ ├── globals.css
    │ ├── theme.js
    │ └── variables.css
    └── utils
        └── createEmotionCache.js

```

###  Azure Storage Format
This document outlines the directory and file structure used within the Azure Blob Storage container.

```
📂 `/`
├── 📂 `course/`
│   └── 📂 `{semester_key}/`                   *(e.g., "Fall2024")*
│       └── 📂 `{course_id}/`                   *(e.g., "CS101")*
│           ├── 📄 `course.json`                *(Course metadata - `Course` model)*
│           ├── 📂 `assignment/`
│           │   └── 📂 `{assignment_id}/`       *(Integer ID)*
│           │       ├── 📄 `assignment.json`    *(Assignment metadata - `Assignment` model)*
│           │       ├── 📂 `{question_index}/`  *(Integer index, 0-based)*
│           │       │   ├── 📄 `question.json`    *(Question metadata - `Question` model)*
│           │       │   └── 📂 `student_response/`
│           │       │       └── 📂 `{student_id}/`  *(Student identifier, often email)*
│           │       │           ├── 📄 `response.*`  *(Student's answer file - `StudentResponse` model, extension from `data.data_type`)*
│           │       │           └── 📄 `grade.json`   *(Grading details - `Grade` model, part of `GradedStudentResponse`)*
│           │       └── 📂 `rubrics/`
│           │           ├── 📄 `assignment.json` *(Overall assignment rubric - `Rubric` model)*
│           │           └── 📄 `{question_index}.json` *(Sub-rubric for a specific question - `SubRubric` model)*
│           └── 📂 `course_material/`
│               └── 📄 `{material_id}.*`         *(Course materials - `CourseMaterial` model, extension from `data.data_type`)*
│
└── 📂 `user/`
    └── 📂 `{user_email}/`
        ├── 📄 `user.json`               *(User metadata - `User` model)*
        └── 📂 `tokens/`
            └── 📄 `{token_name}.json`         *(Personal Access Token details - `PersonalAccessToken` model)*

```

---

## 👥 Team

| 👤 **First Name**  | **Last Name**  | ✉️ **Email Address**  |  **GitHub Username**  |
|:------------------|:--------------|:----------------------|:-----------------------|
| Fahim            | Uddin         | fahuddin@bu.edu      | [fahimuddin/fahimuddin1](https://github.com/fahimuddin/fahimuddin1) |
| Zach             | Gentile       | zgentile@bu.edu      | [zgentile](https://github.com/zgentile) |
| Josh             | Yip           | joshyjip@bu.edu      | [joshyipp](https://github.com/joshyipp) |
| Muhammad Aseef   | Imran         | aseef@bu.edu         | [Aseeef](https://github.com/Aseeef) |

---

## 📜 License

This project is licensed under the **GNU General Public License (GPL)**. See the [LICENSE](LICENSE) file for more details.

---

> ⚠️ **Note**: This project is in active development. For more details on installation, usage, or contributing, please refer to the project’s documentation and issue tracker.  

---

<sub>_If you have any questions or feedback, feel free to open an issue or reach out via email._</sub>

