# BU MET Autograder

A comprehensive Python application for AI-powered rubric refinement and automated grading of student quiz answers. This application orchestrates the complete workflow from rubric improvement to batch grading of student submissions.

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Installation](#installation)
   - [Prerequisites](#prerequisites)
   - [Setup](#setup)
4. [Usage](#usage)
   - [Complete Grading Pipeline](#complete-grading-pipeline)
   - [Rubric Refinement Only](#rubric-refinement-only)
   - [Programmatic Usage](#programmatic-usage)
5. [Application Structure](#application-structure)
6. [Configuration](#configuration)
7. [How It Works](#how-it-works)
   - [Rubric Refinement Process](#rubric-refinement-process)
   - [Grading Process](#grading-process)
   - [CSV Loading Intelligence](#csv-loading-intelligence)
   - [Grading Principles](#grading-principles)
8. [Output Files](#output-files)
   - [Refined Rubric Files](#refined-rubric-files)
   - [Grading Results](#grading-results)
9. [Error Handling](#error-handling)
10. [Logging](#logging)
11. [Troubleshooting](#troubleshooting)
    - [Common Issues](#common-issues)
    - [Debug Mode](#debug-mode)
12. [Testing](#testing)
13. [Limitations & Future Work](#limitations--future-work)
14. [Dependencies](#dependencies)
15. [Contributing](#contributing)
16. [Team](#team)
17. [License](#license)

## Overview

The BU MET Autograder provides an end-to-end solution for:

1. **Rubric Refinement**: Uses LLM-powered iterative refinement to improve grading rubrics until they meet quality targets
2. **Automated Grading**: Grades student answers from CSV files using refined rubrics
3. **Result Export**: Saves graded results back to CSV with scores and feedback

## Features

- **Iterative Rubric Refinement**: Automatically improves rubrics through multiple iterations until reaching a target quality score
- **LLM-Powered Grading**: Uses Azure OpenAI to grade student answers with consistent, fair scoring
- **Flexible CSV Support**: Automatically detects and handles various CSV column name formats
- **Configurable Targets**: Customizable target scores and iteration limits
- **Automatic Storage**: Saves refined rubrics and grading results automatically
- **Comprehensive Logging**: Detailed logging for debugging and monitoring
- **Python 3.10+ Compatible**: Works with Python 3.10 and later versions

## Installation

### Prerequisites

- Python 3.10+ (tested with Python 3.10)
- Azure OpenAI API access with appropriate credentials
- Required Python packages (see dependencies below)

### Setup

1. **Install dependencies** (if not already installed):
   ```bash
   pip install openai python-dotenv
   ```

2. **Configure environment variables**:
   
   Create a `.env` file in the project root with the following variables:
   ```env
   AZURE_LLM_DEPLOYMENT_URL=https://your-resource.openai.azure.com/
   AZURE_LLM_DEPLOYMENT_KEY=your-api-key
   AZURE_OPENAI_API_VERSION=your-llm-api-version
   AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name
   ```

   **Note**: The `AZURE_LLM_DEPLOYMENT_URL` can be in various formats:
   - Base URL: `https://your-resource.openai.azure.com/`
   - Full deployment URL: `https://your-resource.openai.azure.com/openai/deployments/your-deployment`
   
   The system will automatically extract and configure the deployment name.

## Usage

### Complete Grading Pipeline

The main entry point (`main.py`) runs the complete workflow:

1. Refines the rubric (if not already refined)
2. Loads the refined rubric
3. Grades all student answers from CSV
4. Saves results to CSV

**Run the complete pipeline:**
```bash
cd ai-baseline/app
python main.py --quiz-id quiz_1
```

**Required Arguments:**
- `--quiz-id`: Quiz identifier (e.g., `quiz_1`, `quiz_2`). This parameter is required and determines which quiz's rubric and student answers to process.

**Optional Arguments:**
- `--target-score`: Target critique score for rubric refinement (default: 95)
- `--max-iterations`: Maximum iterations for rubric refinement (default: 5)
- `--skip-refinement`: Skip rubric refinement step (use existing refined rubric if available)

**Expected file structure:**
```
ai-baseline/
├── data/
│   ├── quiz_1/
│   │   ├── rubric.txt                    # Original rubric
│   │   ├── quiz_1_results.csv            # Input: Student answers
│   │   └── quiz_1_graded.csv            # Output: Graded results
│   ├── quiz_2/
│   │   ├── rubric.txt
│   │   ├── quiz_2_results.csv
│   │   └── quiz_2_graded.csv
│   └── rubric-refined/
│       ├── quiz_1/
│       │   ├── rubric_refined.txt        # Refined rubric (auto-generated)
│       │   └── quiz_1.json               # Refined rubric JSON
│       └── quiz_2/
│           ├── rubric_refined.txt
│           └── quiz_2.json
```

**CSV Input Format Support:**

The pipeline automatically detects and supports multiple CSV column name formats:

**Format 1** (Numeric student IDs):
```csv
Student Number,student answer
26,"Student's answer text here..."
27,"Another student's answer..."
```

**Format 2** (Text-based student identifiers):
```csv
Student username,AI Score,AI Feedback,student answer
student 1,10,"Feedback...","Student's answer text here..."
student 2,12,"Feedback...","Another student's answer..."
```

**Supported Column Name Variations:**
- Student identifier: `Student Number`, `Student username`, `Student Username`, `student_number`, `student_username`
- Student answer: `student answer`, `Student Answer`, `student_answer`, `answer`

The pipeline will automatically:
- Detect the appropriate columns from your CSV
- Normalize student identifiers to `Student Number` for consistency
- Skip rows with missing data
- Log which columns are being used

**CSV Output Format** (`{quiz_id}_graded.csv`):
```csv
Student Number,student answer,AI Score (New),AI Comment (New)
26,"Student's answer...",14,16,"Great explanation of the concept..."
student 1,"Another answer...",12,12,"Good understanding, but could expand on..."
```

The output preserves all original columns and adds:
- `AI Score (New)`: Numerical score assigned by the AI grader
- `AI Comment (New)`: Constructive feedback text

### Rubric Refinement Only

For testing and refining rubrics without grading:

**Using the CLI:**
```bash
cd ai-baseline/app
python -m app.cli --quiz-id quiz_1
```

Or if running from the project root:
```bash
python -m ai-baseline.app.cli --quiz-id quiz_1
```

**CLI Options:**
```bash
python -m app.cli --help

Required Arguments:
  --quiz-id ID                Quiz identifier (e.g., 'quiz_1', 'quiz_2')

Optional Arguments:
  --rubric-file PATH          Path to rubric file (default: derived from --quiz-id)
  --no-iterative              Disable iterative refinement (single-pass only)
  --target-score SCORE        Target critique score (default: 95)
  --max-iterations N          Maximum refinement iterations (default: 5)
```

**Examples:**
```bash
# Refine quiz_1 with default settings
cd ai-baseline/app
python -m app.cli --quiz-id quiz_1

# Refine quiz_2 with custom target score
python -m app.cli --quiz-id quiz_2 --target-score 90 --max-iterations 10

# Single-pass refinement (no iteration)
python -m app.cli --quiz-id quiz_1 --no-iterative

# Use custom rubric file path
python -m app.cli --quiz-id quiz_1 --rubric-file data/custom/rubric.txt
```

### Programmatic Usage

**Import and use the package:**

When running from the `ai-baseline/app` directory:
```python
from app import (
    RubricTestRunner,
    initialize_llm_service,
    create_rubric_refinement_service,
    get_rubric_file_path,
    DEFAULT_TARGET_SCORE,
    DEFAULT_MAX_ITERATIONS
)

# Initialize services
if not initialize_llm_service():
    raise RuntimeError("Failed to initialize LLM service")

# Specify quiz ID
quiz_id = "quiz_1"
rubric_file = get_rubric_file_path(quiz_id)

# Create runner
runner = RubricTestRunner(rubric_file)
if not runner.initialize_service():
    raise RuntimeError("Failed to initialize rubric refinement service")

# Load rubric
assignment, rubric = runner.load_rubric()

# Run iterative refinement
response = runner.iterative_refinement(
    assignment, rubric,
    target_score=DEFAULT_TARGET_SCORE,
    max_iterations=DEFAULT_MAX_ITERATIONS
)

if response:
    print(f"Final score: {response.critique.overall_score}/100")
    print(f"Refined rubric saved!")
```

**Note**: When importing from outside the `ai-baseline/app` directory, you may need to adjust the import path or add the parent directory to `sys.path`.

## Application Structure

```
ai-baseline/app/
├── __init__.py              # Package exports
├── main.py                  # Complete grading pipeline entry point
├── cli.py                   # Command-line interface
├── config.py                # Configuration constants
├── core/                    # Core business logic
│   ├── __init__.py
│   ├── models.py            # Data models
│   ├── parser.py            # Rubric file parser
│   └── runner.py            # Test runner and refinement logic
├── services/                # Service layer
│   ├── __init__.py
│   └── initialization.py    # LLM and service initialization
├── utils/                   # Utility functions
│   ├── __init__.py
│   ├── csv_parser.py        # CSV parsing utilities
│   ├── formatter.py         # Rubric formatting
│   ├── path_utils.py        # Path resolution utilities
│   └── storage.py           # File I/O operations
└── test/                    # Tests
    └── test_rubric_review.py
```

## Configuration

Default configuration values (in `config.py`):

```python
DEFAULT_SEMESTER = "spring2025"
DEFAULT_TARGET_SCORE = 95
DEFAULT_MAX_ITERATIONS = 5

# Helper function to get rubric file path
def get_rubric_file_path(quiz_id: str) -> str:
    return f"data/{quiz_id}/rubric.txt"
```

**Note**: The `quiz_id` parameter is required for all operations. Course ID and assignment ID are automatically derived from the quiz_id when parsing rubrics.

## How It Works

### Rubric Refinement Process

1. **Load Original Rubric**: Parses the rubric file using LLM to extract structured data
2. **Generate Critique**: LLM analyzes the rubric for weaknesses, missing criteria, and scoring issues
3. **Refine Rubric**: LLM generates an improved version addressing identified issues
4. **Iterate**: Repeats critique and refinement until target score is reached or max iterations exceeded
5. **Save Results**: Stores refined rubric in both text and JSON formats

### Grading Process

1. **Load Refined Rubric**: Uses refined rubric if available, otherwise falls back to original
2. **Build System Prompt**: Combines grading instructions with rubric content
3. **Load Student Answers**: Automatically detects CSV column names and loads student data
4. **Grade Each Answer**: Sends student answer to LLM with system prompt
5. **Extract Results**: Parses JSON response containing score and feedback
6. **Save to CSV**: Writes graded results with new columns for AI scores and comments

### CSV Loading Intelligence

The pipeline includes intelligent CSV parsing that:

- **Auto-detects column names**: Tries multiple variations of common column names
- **Handles different formats**: Supports both numeric and text-based student identifiers
- **Validates data**: Skips rows with missing answers or identifiers
- **Preserves original data**: Maintains all original columns in the output
- **Provides logging**: Reports which columns are detected and how many rows are processed

### Grading Principles

The system follows these principles (embedded in the grading prompt):

- **Conceptual Understanding First**: High-level understanding is the primary scoring factor
- **Fair Partial Credit**: Rewards partial understanding appropriately
- **No Length Bias**: Sentence/word count is NOT a scoring criterion
- **Consistency**: Similar answers receive similar scores (within ±1 point)
- **Supportive Feedback**: Provides constructive, specific feedback referencing rubric elements

## Output Files

### Refined Rubric Files

- **Text Format**: `data/rubric-refined/{quiz_id}/rubric_refined.txt`
  - Human-readable format matching original rubric structure
  
- **JSON Format**: `data/rubric-refined/{quiz_id}/{quiz_id}.json`
  - Structured data for programmatic use

### Grading Results

- **Graded CSV**: `data/{quiz_id}/{quiz_id}_graded.csv`
  - Original columns plus:
    - `AI Score (New)`: Numerical score
    - `AI Comment (New)`: Feedback text

## Error Handling

The pipeline includes robust error handling:

- **Missing Files**: Clear error messages with file paths searched
- **API Failures**: Logs warnings and continues with available data
- **Invalid Responses**: Attempts to extract JSON from various response formats
- **Missing Environment Variables**: Detailed error messages listing required variables
- **CSV Format Issues**: Automatic column detection with fallback options and clear error messages

## Logging

The pipeline uses Python's `logging` module with INFO level by default. Logs include:

- Pipeline progress (steps 1-6)
- Rubric refinement iterations
- CSV column detection and usage
- Individual student grading progress
- Errors and warnings
- File save locations
- Rows skipped due to missing data

## Troubleshooting

### Common Issues

**1. "Missing required environment variables"**
- Ensure `.env` file exists in project root
- Verify all Azure OpenAI variables are set correctly

**2. "Rubric file not found"**
- Check that `data/{quiz_id}/rubric.txt` exists
- Verify the quiz_id matches your directory structure

**3. "Student answers CSV not found"**
- Ensure `data/{quiz_id}/{quiz_id}_results.csv` exists
- Verify the file name matches the pattern `{quiz_id}_results.csv`

**4. "Could not find student answer column"**
- Check that your CSV has a column with one of these names:
  - `student answer`, `Student Answer`, `student_answer`, or `answer`
- The pipeline will show available columns in the error message

**5. "No student answers found to grade"**
- Verify your CSV has data rows (not just headers)
- Check that the student answer column contains non-empty values
- Review logs for information about skipped rows
- Ensure student identifier column exists (supports multiple name variations)

**6. "Failed to parse grade from response"**
- LLM response may not be in expected JSON format
- Check logs for the actual response content
- The system will continue grading other students

**7. "Deployment name not found"**
- Verify `AZURE_OPENAI_DEPLOYMENT_NAME` is set in `.env`
- Or ensure deployment name is in the URL path

**8. "cannot import name 'UTC' from 'datetime'"**
- This error indicates Python 3.10 compatibility issue
- The codebase has been updated to use `timezone.utc` instead
- Ensure you have the latest version of the code

### Debug Mode

Enable more verbose logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or set environment variable:
```bash
export PYTHONPATH=/path/to/project
python main.py --quiz-id quiz_1
```

## Testing

Run tests:
```bash
cd ai-baseline/app
python -m pytest test/
```

## Limitations & Future Work

**Planned improvements:**
- [ ] Refactor the code to make it easier to maintain
- [ ] Support multiple quiz grading in single run
- [ ] Add progress bars for long-running operations
- [ ] Support custom grading prompts per quiz
- [ ] Add retry logic for API failures
- [ ] Batch processing for large student datasets
- [ ] Add interactivity with LLM while refining rubric
- [ ] Add a frontend to work with interactivity with LLM
- [ ] Incorporate emailing the professor with the rubric and graded results

## Dependencies

Core dependencies:
- `openai` - Azure OpenAI client
- `python-dotenv` - Environment variable management

Internal dependencies (from parent project):
- `app.models.*` - Data models for assignments, rubrics, etc.
- `app.services.rubric_refinement_service` - Rubric refinement logic
- `app.utils.*` - Utility functions

## Contributing

When modifying the pipeline:

1. Update this README if adding new features
2. Maintain backward compatibility with existing CSV formats
3. Add appropriate error handling and logging
4. Test with sample data before production use
5. Ensure Python 3.10+ compatibility

## Team

| 👤 **First Name**  | **Last Name**  | ✉️ **Email Address**  |
|:------------------|:--------------|:----------------------|
| Edaad            | Azman         | edaad@bu.edu     |
| Jonathan             | Wu       | jcwu@bu.edu      |
| Sadid-E-alam              | Ethun           | sethun@bu.edu      |
| Kwabena    | Ampomah         | kwabamp@bu.edu         |

## License

This project is licensed under the **GNU General Public License (GPL)**. See the [LICENSE](LICENSE) file for more details.
