# Unified Pipeline

A comprehensive Python package for AI-powered rubric refinement and automated grading of student quiz answers. This pipeline orchestrates the complete workflow from rubric improvement to batch grading of student submissions.

## Overview

The Unified Pipeline provides an end-to-end solution for:

1. **Rubric Refinement**: Uses LLM-powered iterative refinement to improve grading rubrics until they meet quality targets
2. **Automated Grading**: Grades student answers from CSV files using refined rubrics
3. **Result Export**: Saves graded results back to CSV with scores and feedback

## Features

- **Iterative Rubric Refinement**: Automatically improves rubrics through multiple iterations until reaching a target quality score
- **LLM-Powered Grading**: Uses Azure OpenAI to grade student answers with consistent, fair scoring
- **CSV-Based Workflow**: Simple input/output using CSV files for student data
- **Configurable Targets**: Customizable target scores and iteration limits
- **Automatic Storage**: Saves refined rubrics and grading results automatically
- **Comprehensive Logging**: Detailed logging for debugging and monitoring

## Installation

### Prerequisites

- Python 3.8+
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
   AZURE_OPENAI_API_VERSION=2024-02-15-preview
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
cd ai-baseline/unified_pipeline
python main.py
```

**Expected file structure:**
```
ai-baseline/
├── data/
│   ├── quiz_1/
│   │   ├── rubric.txt                    # Original rubric
│   │   ├── quiz_1_results.csv            # Input: Student answers
│   │   └── quiz_1_graded.csv            # Output: Graded results
│   └── rubric-refined/
│       └── quiz_1/
│           ├── rubric_refined.txt        # Refined rubric (auto-generated)
│           └── quiz_1.json               # Refined rubric JSON
```

**CSV Input Format** (`quiz_1_results.csv`):
```csv
Student Number,student answer
12345,"Student's answer text here..."
67890,"Another student's answer..."
```

**CSV Output Format** (`quiz_1_graded.csv`):
```csv
Student Number,student answer,AI Score (New),AI Comment (New)
12345,"Student's answer...",14,16,"Great explanation of the concept..."
67890,"Another answer...",12,16,"Good understanding, but could expand on..."
```

### Rubric Refinement Only

For testing and refining rubrics without grading:

**Using the CLI:**
```bash
python -m unified_pipeline.cli
```

**CLI Options:**
```bash
python -m unified_pipeline.cli --help

Options:
  --rubric-file PATH          Path to rubric file (default: data/quiz_1/rubric.txt)
  --no-iterative              Disable iterative refinement (single-pass only)
  --target-score SCORE        Target critique score (default: 95)
  --max-iterations N          Maximum refinement iterations (default: 5)
```

**Example:**
```bash
# Refine with custom target score
python -m unified_pipeline.cli --target-score 90 --max-iterations 10

# Single-pass refinement (no iteration)
python -m unified_pipeline.cli --no-iterative

# Custom rubric file
python -m unified_pipeline.cli --rubric-file data/quiz_2/rubric.txt
```

### Programmatic Usage

**Import and use the package:**
```python
from unified_pipeline import (
    RubricTestRunner,
    initialize_llm_service,
    create_rubric_refinement_service,
    DEFAULT_RUBRIC_FILE,
    DEFAULT_TARGET_SCORE,
    DEFAULT_MAX_ITERATIONS
)

# Initialize services
if not initialize_llm_service():
    raise RuntimeError("Failed to initialize LLM service")

# Create runner
runner = RubricTestRunner(DEFAULT_RUBRIC_FILE)
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

## Package Structure

```
unified_pipeline/
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
DEFAULT_RUBRIC_FILE = "data/quiz_1/rubric.txt"
DEFAULT_SEMESTER = "spring2025"
DEFAULT_COURSE_ID = "quiz_1"
DEFAULT_ASSIGNMENT_ID = "quiz_1"
DEFAULT_TARGET_SCORE = 95
DEFAULT_MAX_ITERATIONS = 5
```

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
3. **Grade Each Answer**: Sends student answer to LLM with system prompt
4. **Extract Results**: Parses JSON response containing score and feedback
5. **Save to CSV**: Writes graded results with new columns for AI scores and comments

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

## Logging

The pipeline uses Python's `logging` module with INFO level by default. Logs include:

- Pipeline progress (steps 1-5)
- Rubric refinement iterations
- Individual student grading progress
- Errors and warnings
- File save locations

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
- Verify CSV has `Student Number` and `student answer` columns

**4. "Failed to parse grade from response"**
- LLM response may not be in expected JSON format
- Check logs for the actual response content
- The system will continue grading other students

**5. "Deployment name not found"**
- Verify `AZURE_OPENAI_DEPLOYMENT_NAME` is set in `.env`
- Or ensure deployment name is in the URL path

### Debug Mode

Enable more verbose logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Testing

Run tests:
```bash
cd ai-baseline/unified_pipeline
python -m pytest test/
```

## Limitations & Future Work

Current limitations (as noted in `main.py`):

- Hardcoded `quiz_id = "quiz_1"` in main pipeline
- Not yet scalable to other quizzes without code modification

**Planned improvements:**
- [ ] Add `--quiz-id` argument to CLI and main pipeline
- [ ] Support multiple quiz grading in single run
- [ ] Add progress bars for long-running operations
- [ ] Support custom grading prompts per quiz
- [ ] Add retry logic for API failures

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

## License

Part of the ML BU Autograder project.

