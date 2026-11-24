# SR1001: Job Summary Statistics and Monitoring

## Overview

SR1001 provides comprehensive job progress monitoring with real-time summary statistics and metrics. The module includes:

- **Job Summary Statistics**: Aggregated metrics for completed pages (avg/min/max/total times and character counts)
- **Page-by-Page Metrics**: Detailed metrics for each page
- **Web UI Dashboard**: Interactive monitoring dashboard with real-time updates
- **REST API**: Public API endpoints for programmatic access
- **Command-Line Interface**: CLI tools for batch operations

## Features

### Summary Statistics (For Completed Pages)

- **Timing Metrics**
  - Average elapsed time
  - Minimum elapsed time
  - Maximum elapsed time
  - Total elapsed time

- **Input Character Metrics**
  - Average input characters
  - Total input characters
  - Min/Max input characters

- **Output Character Metrics**
  - Average output characters
  - Total output characters
  - Min/Max output characters

- **Compression Analysis**
  - Output/Input compression ratio

- **Progress Tracking**
  - Overall progress percentage
  - Status breakdown (completed, failed, interrupted, running)

## Usage

### Web UI Dashboard

Access the job monitoring dashboard at:
```
http://localhost/sr1001/?job_id=<JOB_ID>
```

The dashboard displays:
- Overall job progress
- Real-time status updates (auto-refresh every 5 seconds)
- Page-by-page status visualization
- Summary statistics for completed pages
- Color-coded page status cells

### REST API Endpoints

#### Get Job Status
```bash
GET /sr1001/api/job/<job_id>
```
Returns basic job information and progress.

**Example:**
```bash
curl http://localhost/sr1001/api/job/7a424a0bed4a465986723929a93c48a0
```

**Response:**
```json
{
  "job_id": "7a424a0bed4a465986723929a93c48a0",
  "status": "running",
  "total_pages": 534,
  "completed": 6,
  "failed": 0,
  "running": 1,
  "progress_percent": 1.1,
  "elapsed_seconds": 210.87
}
```

#### Get Job Summary Statistics
```bash
GET /sr1001/api/job/<job_id>/summary
```
Returns comprehensive summary statistics for the job.

**Example:**
```bash
curl http://localhost/sr1001/api/job/7a424a0bed4a465986723929a93c48a0/summary
```

**Response:**
```json
{
  "job_id": "7a424a0bed4a465986723929a93c48a0",
  "total_pages": 534,
  "completed_pages": 6,
  "failed_pages": 0,
  "avg_elapsed_seconds": 35.14,
  "min_elapsed_seconds": 30.9,
  "max_elapsed_seconds": 50.99,
  "total_elapsed_seconds": 210.87,
  "avg_input_characters": 3998,
  "total_input_characters": 23988,
  "avg_output_characters": 855.67,
  "total_output_characters": 5134,
  "avg_compression_ratio": 0.31,
  "progress_percent": 1.1
}
```

#### Get Page-by-Page Metrics
```bash
GET /sr1001/api/job/<job_id>/metrics
```
Returns detailed metrics for each page.

**Example:**
```bash
curl http://localhost/sr1001/api/job/7a424a0bed4a465986723929a93c48a0/metrics
```

**Response:**
```json
{
  "job_id": "7a424a0bed4a465986723929a93c48a0",
  "metrics": [
    {
      "page_number": 1,
      "status": "completed",
      "input_characters": 82,
      "output_characters": 53,
      "elapsed_seconds": 50.992
    },
    ...
  ]
}
```

#### Get Job Pages
```bash
GET /sr1001/api/job/<job_id>/pages
```
Returns detailed page status information.

### Command-Line Interface

#### Display Summary Statistics
```bash
python -c "from impl_translator.src.features.SR1001.batch import main; import sys; sys.exit(main())" \
  summary \
  --working-dir /path/to/jobs \
  --job-id 7a424a0bed4a465986723929a93c48a0
```

**Output (Human-Readable):**
```
======================================================================
JOB SUMMARY STATISTICS
======================================================================

Progress: 1.1% (6/534 pages)

Status Breakdown:
  Completed:     6
  Failed:        0
  Interrupted:   0
  Running:       1
  Pending:       0

Timing Statistics (Completed Pages):
  Average:       35.14 sec
  Min:           30.90 sec
  Max:           50.99 sec
  Total:        210.87 sec

Input Characters (Completed Pages):
  Average:        3998 chars
  Min:              82 chars
  Max:            5772 chars
  Total:         23988 chars

Output Characters (Completed Pages):
  Average:         856 chars
  Min:              53 chars
  Max:            1229 chars
  Total:          5134 chars

Compression Ratio (Output/Input):
  Average:       0.310

======================================================================
```

**Output (JSON):**
```bash
python -c "from impl_translator.src.features.SR1001.batch import main; import sys; sys.exit(main())" \
  summary \
  --working-dir /path/to/jobs \
  --job-id 7a424a0bed4a465986723929a93c48a0 \
  --json
```

#### Display Page-by-Page Metrics
```bash
python -c "from impl_translator.src.features.SR1001.batch import main; import sys; sys.exit(main())" \
  metrics \
  --working-dir /path/to/jobs \
  --job-id 7a424a0bed4a465986723929a93c48a0
```

**Output (Human-Readable):**
```
Page-by-page metrics for job 7a424a0bed4a465986723929a93c48a0:
------------------------------------------------------------------------------------------
Page       Status      Input     Output   Time (s)
------------------------------------------------------------------------------------------
   1    completed         82         53      50.99
   2    completed       2362       1159      31.98
   3    completed       4960        595      32.51
   4    completed       5772       1087      32.33
   5    completed       5739       1229      32.16
   6    completed       5073       1011      30.90
   7      running       4726          -          -
```

**Output (JSON):**
```bash
python -c "from impl_translator.src.features.SR1001.batch import main; import sys; sys.exit(main())" \
  metrics \
  --working-dir /path/to/jobs \
  --job-id 7a424a0bed4a465986723929a93c48a0 \
  --json
```

## Public API (Python)

### Module: `impl_translator.src.features.SR1001.summary`

#### `calculate_summary(state: dict) -> SummaryMetrics`
Calculate summary statistics from job state.

**Parameters:**
- `state`: Job state dictionary loaded from job.yaml

**Returns:**
- `SummaryMetrics`: Dataclass containing all calculated statistics

**Example:**
```python
from impl_translator.src.features.SR1001 import summary
from impl_translator.src.libs import job
from pathlib import Path

working_dir = Path("_data/odbpp_translatol/output/job")
state = job.load(working_dir, "7a424a0bed4a465986723929a93c48a0")
metrics = summary.calculate_summary(state)

print(f"Completed: {metrics.completed_pages}")
print(f"Average time: {metrics.avg_elapsed_seconds:.2f}s")
print(f"Compression ratio: {metrics.avg_compression_ratio:.3f}")
```

#### `calculate_page_metrics(state: dict) -> list[PageMetrics]`
Extract page-by-page metrics from job state.

**Parameters:**
- `state`: Job state dictionary loaded from job.yaml

**Returns:**
- List of `PageMetrics` dataclass instances ordered by page number

**Example:**
```python
metrics = summary.calculate_page_metrics(state)
for page in metrics:
    if page.status == "completed":
        print(f"Page {page.page_number}: {page.elapsed_seconds:.2f}s")
```

#### `format_summary(summary: SummaryMetrics) -> str`
Format summary metrics as human-readable string.

**Parameters:**
- `summary`: SummaryMetrics object

**Returns:**
- Formatted summary string

#### `format_summary_json(summary: SummaryMetrics) -> dict`
Convert summary metrics to JSON-serializable dict.

**Parameters:**
- `summary`: SummaryMetrics object

**Returns:**
- Dictionary suitable for JSON serialization

#### `load_and_summarize(working_dir: Path, job_id: str) -> tuple[dict, SummaryMetrics]`
Load job state and calculate summary in one call.

**Parameters:**
- `working_dir`: Working directory containing jobs
- `job_id`: Job ID to load

**Returns:**
- Tuple of (job_state, summary_metrics)

**Example:**
```python
state, metrics = summary.load_and_summarize(working_dir, job_id)
print(summary.format_summary(metrics))
```

## Data Structures

### PageMetrics
```python
@dataclass
class PageMetrics:
    page_number: int              # 1-based page number
    status: str                   # "completed", "failed", "running", "interrupted"
    input_characters: int | None  # Number of input characters
    output_characters: int | None # Number of output characters
    elapsed_seconds: float | None # Time elapsed in seconds
```

### SummaryMetrics
```python
@dataclass
class SummaryMetrics:
    # Counts
    total_pages: int              # Total number of pages
    completed_pages: int          # Number of completed pages
    failed_pages: int             # Number of failed pages
    interrupted_pages: int        # Number of interrupted pages
    running_pages: int            # Number of currently running pages
    pending_pages: int            # Number of pending pages
    
    # Timing (for completed pages)
    avg_elapsed_seconds: float | None
    min_elapsed_seconds: float | None
    max_elapsed_seconds: float | None
    total_elapsed_seconds: float | None
    
    # Character counts (for completed pages)
    avg_input_characters: float | None
    min_input_characters: int | None
    max_input_characters: int | None
    total_input_characters: int | None
    
    avg_output_characters: float | None
    min_output_characters: int | None
    max_output_characters: int | None
    total_output_characters: int | None
    
    # Compression
    avg_compression_ratio: float | None
    
    # Progress
    progress_percent: float       # 0-100 percentage
```

## Configuration

### Environment Variables

- `IMPL_TRANSLATOR_WORKING_DIR`: Working directory containing job folders (default: `output/job`)

## Implementation Details

### File Structure

```
impl_translator/src/features/SR1001/
├── summary.py              # Core summary calculation logic
├── batch/
│   └── __init__.py        # CLI commands
├── app/
│   └── __init__.py        # Flask routes and API
├── html/
│   └── index.html         # Web dashboard UI
└── __init__.py
```

### Processing

1. **Load Job State**: Read job.yaml file
2. **Calculate Metrics**: Process page information to calculate statistics
3. **Format Output**: Convert to human-readable or JSON format
4. **Display/Return**: Output via API, CLI, or Web UI

### Real-Time Updates

The Web UI automatically refreshes every 5 seconds to show the latest statistics as pages complete.

## Performance Considerations

- **Summary calculations** are performed in-memory on the loaded job state
- **No heavy I/O** beyond reading the single job.yaml file
- **Efficient statistics** using Python's built-in `statistics` module
- **Suitable for jobs with hundreds or thousands of pages**

## Error Handling

- Invalid job IDs are validated before file access
- Missing job files return 404 responses
- Null/None values are handled gracefully in statistics calculation
- Division by zero is prevented with explicit checks

## Examples

### Monitor a job in real-time
```bash
# Terminal 1: Get the job ID
export JOB_ID="7a424a0bed4a465986723929a93c48a0"

# Terminal 2: Refresh summary every 10 seconds
watch -n 10 "python -c 'from impl_translator.src.features.SR1001.batch import main; import sys; sys.exit(main())' summary --working-dir _data/odbpp_translatol/output/job --job-id $JOB_ID"
```

### Process metrics in a script
```python
from impl_translator.src.features.SR1001 import summary
from pathlib import Path

working_dir = Path("_data/odbpp_translatol/output/job")
job_id = "7a424a0bed4a465986723929a93c48a0"

state, metrics = summary.load_and_summarize(working_dir, job_id)

# Custom processing
if metrics.completed_pages > 0:
    avg_time = metrics.avg_elapsed_seconds
    if avg_time > 60:
        print(f"⚠️  Slow pages detected: {avg_time:.1f}s average")
    
    # Export as JSON for integration
    import json
    with open("summary.json", "w") as f:
        json.dump(summary.format_summary_json(metrics), f, indent=2)
```

### Web API integration
```bash
# Get summary from API
curl -s http://localhost/sr1001/api/job/7a424a0bed4a465986723929a93c48a0/summary | jq '.avg_elapsed_seconds'

# Parse with jq
curl -s http://localhost/sr1001/api/job/7a424a0bed4a465986723929a93c48a0/summary | jq '{pages: .completed_pages, progress: .progress_percent}'
```

## Troubleshooting

### "Job not found" error
- Verify the job ID is correct (should be 32 hex characters)
- Check that the working directory is set correctly
- Ensure the job.yaml file exists in the job directory

### No summary statistics displayed
- Summary statistics only appear if there is at least one completed page
- Refresh the page or wait for a page to complete

### API returns empty metrics
- Ensure the job has been started
- Check that pages have at least started processing
