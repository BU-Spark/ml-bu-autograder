"""
AI Generated File.

Model: Gemini 2.5 Pro

Prompt: Create a utility class in python for managing background jobs.
This utility class can be initialized specifying how many threads should the thread pool maintain. When a job is
submitted, you can optionally supply a job id. This job id can be used to obtain a status on the progress of this job.
Querying the job status returns a float between 0 and 1 (representing how close is the job to being complete) or the
computed result if the job is complete. Think carefully about the API of this utility class about what might a
developer need. The worker function that is supplied should accept a reference to a variable that can be used to
update its progress. OOP style strongly preferred for everything. This class is intended to be used in a fastapi
server. Since this is a thread pool, it's instance expected to last throughout the lifetime of the app.
"""

import concurrent.futures
import threading
import uuid
import time
from typing import Any, Callable, Dict, Optional, Union, Tuple
from enum import Enum, auto


# --- Enums and Helper Classes ---

class JobState(Enum):
    """Represents the possible states of a background job."""
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()


class _JobStatus:
    """Internal class to hold the status and result of a single job."""

    def __init__(self):
        self.state: JobState = JobState.PENDING
        self.progress: float = 0.0
        self.result: Optional[Any] = None
        self.exception: Optional[Exception] = None
        self.future: Optional[concurrent.futures.Future] = None
        self.lock = threading.Lock()  # Lock to protect updates to this specific job's status

    def set_running(self):
        with self.lock:
            self.state = JobState.RUNNING
            self.progress = 0.0  # Reset progress when starting

    def update_progress(self, progress: float):
        with self.lock:
            # Ensure progress stays within bounds and only increases
            # while in the running state.
            if self.state == JobState.RUNNING:
                # Clamp progress between 0.0 and 1.0
                clamped_progress = max(0.0, min(progress, 1.0))
                # Ensure progress doesn't go backwards (optional, but often desired)
                self.progress = max(self.progress, clamped_progress)

    def set_completed(self, result: Any):
        with self.lock:
            self.state = JobState.COMPLETED
            self.result = result
            self.progress = 1.0  # Explicitly set progress to 1.0 on completion

    def set_failed(self, exception: Exception):
        with self.lock:
            self.state = JobState.FAILED
            self.exception = exception
            # Progress might be anywhere, leave it as is or set to 1.0?
            # Leaving it as is might indicate *where* it failed.
            # Setting to 1.0 indicates the process terminated. Let's set to 1.0.
            self.progress = 1.0


# --- Main Manager Class ---
background_job_manager: Optional["BackgroundJobManager"] = None


class BackgroundJobManager:
    """
    Manages background jobs using a configurable thread pool.

    Allows submitting jobs, querying their status (progress or result),
    and provides a mechanism for jobs to report their progress.
    Designed to be thread-safe and suitable for long-running applications
    like FastAPI servers.
    """

    def __init__(self, num_threads: int = 4):
        """
        Initializes the BackgroundJobManager.

        Args:
            num_threads: The number of worker threads in the pool.
        """
        if num_threads <= 0:
            raise ValueError("Number of threads must be positive.")

        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=num_threads)
        self._jobs: Dict[str, _JobStatus] = {}
        self._jobs_lock = threading.Lock()  # Lock to protect the main jobs dictionary

    def _job_wrapper(
            self,
            job_id: str,
            worker_func: Callable[..., Any],
            progress_callback_arg_name: str,
            *args: Any,
            **kwargs: Any
    ):
        """
        Internal wrapper function executed by the thread pool for each job.

        Handles state transitions, progress updates, result/exception storage.
        """
        job_status = self._get_job_status_internal(job_id)
        if not job_status:
            # Should not happen if submit_job is correct, but defensive check
            print(f"Error: Job {job_id} not found during execution start.")
            return

        job_status.set_running()

        # Create the progress update callback function for the worker
        def update_progress_func(progress: float):
            """Callback for the worker to report its progress."""
            job_status.update_progress(progress)

        # Inject the progress callback into kwargs if the arg name is provided
        if progress_callback_arg_name:
            kwargs[progress_callback_arg_name] = update_progress_func
        # If no name provided, the worker can't update progress via this mechanism

        try:
            # Execute the actual worker function
            result = worker_func(*args, **kwargs)
            job_status.set_completed(result)
        except Exception as e:
            print(f"Error executing job {job_id}: {e}")  # Optional: Log the error
            job_status.set_failed(e)
        # Note: The future object implicitly stores the result or exception too.
        # We store it explicitly in _JobStatus for easier access via get_job_status.

    def submit_job(
            self,
            worker_func: Callable[..., Any],
            *args: Any,
            job_id: Optional[str] = None,
            progress_callback_arg_name: str = None,
            **kwargs: Any
    ) -> str:
        """
        Submits a new job to the thread pool.

        Args:
            worker_func: The function to execute in the background.
            *args: Positional arguments to pass to the worker_func.
            job_id: An optional unique ID for the job. If None, a UUID is generated.
            progress_callback_arg_name: The name of the keyword argument via which
                the `update_progress` callback function will be passed to the
                `worker_func`. If empty or None, no callback is passed.
            **kwargs: Keyword arguments to pass to the worker_func.

        Returns:
            The unique job ID (either provided or generated).

        Raises:
            ValueError: If the provided job_id already exists.
        """
        if job_id is None:
            job_id = str(uuid.uuid4())
        else:
            # Ensure provided job_id is a string, just in case
            job_id = str(job_id)

        with self._jobs_lock:
            if job_id in self._jobs:
                raise ValueError(f"Job ID '{job_id}' already exists.")

            job_status = _JobStatus()
            self._jobs[job_id] = job_status

        # Submit the wrapper function to the executor
        future = self._executor.submit(
            self._job_wrapper,
            job_id,
            worker_func,
            progress_callback_arg_name,
            *args,
            **kwargs
        )
        job_status.future = future  # Store the future for potential cancellation etc.

        return job_id

    def _get_job_status_internal(self, job_id: str) -> Optional[_JobStatus]:
        """Internal helper to get job status object without acquiring outer lock."""
        # Assumes self._jobs_lock is already held or not needed
        return self._jobs.get(job_id)

    def get_job_status(self, job_id: str) -> Union[float, Any, None]:
        """
        Queries the status or result of a specific job.

        Args:
            job_id: The unique ID of the job to query.

        Returns:
            - If the job is PENDING or RUNNING: A float between 0.0 and 1.0
              representing the job's progress.
            - If the job is COMPLETED: The return value of the worker function.
            - If the job FAILED: The exception object raised by the worker function.
            - If the job ID is not found: None (or consider raising KeyError).
        """
        with self._jobs_lock:
            job_status = self._jobs.get(job_id)

        if not job_status:
            return None  # Job not found

        # Acquire the lock specific to this job's status object
        with job_status.lock:
            state = job_status.state
            if state == JobState.COMPLETED:
                return job_status.result
            elif state == JobState.FAILED:
                return job_status.exception  # Return the actual exception object
            elif state == JobState.RUNNING or state == JobState.PENDING:
                return job_status.progress
            else:
                # Should not happen with current states
                return job_status.progress  # Default fallback

    def get_job_state(self, job_id: str) -> Optional[JobState]:
        """Gets the current state enum of the job."""
        with self._jobs_lock:
            job_status = self._jobs.get(job_id)

        if not job_status:
            return None

        with job_status.lock:
            return job_status.state

    def list_job_ids(self) -> list[str]:
        """Returns a list of all known job IDs."""
        with self._jobs_lock:
            return list(self._jobs.keys())

    def shutdown(self, wait: bool = True, cancel_futures: bool = False):
        """
        Shuts down the thread pool executor.

        Args:
            wait: If True (default), waits for all currently running jobs to complete.
                  If False, signals them to shutdown but doesn't wait.
            cancel_futures: If True (Python 3.9+), attempt to cancel pending futures
                            that haven't started running yet. This option is only
                            available in `shutdown()` since Python 3.9.
                            Requires `wait=True`.
        """
        print("Shutting down background job manager...")
        if cancel_futures and wait and hasattr(self._executor, '_threads'):
            # Basic check for Python 3.9+ feature availability might need refinement
            # The 'cancel_futures' argument was added in Python 3.9
            try:
                # Check Python version for safety, as the argument might not exist
                import sys
                if sys.version_info >= (3, 9):
                    self._executor.shutdown(wait=wait, cancel_futures=cancel_futures)
                else:
                    print("Warning: cancel_futures requires Python 3.9+. Shutting down without cancelling.")
                    self._executor.shutdown(wait=wait)  # Fallback for older Python
            except TypeError:
                # Catch if cancel_futures is not a valid argument in the current version
                print(
                    "Warning: cancel_futures argument not supported in this Python version. Shutting down without cancelling.")
                self._executor.shutdown(wait=wait)

        else:
            if cancel_futures and not wait:
                print("Warning: cancel_futures=True requires wait=True. Ignoring cancel_futures.")
            self._executor.shutdown(wait=wait)
        print("Background job manager shut down.")

# --- Example Usage ---

if __name__ == "__main__":

    # Example worker function that reports progress
    def long_running_task(duration: int, task_name: str, update_progress: Callable[[float], None]):
        print(f"Task '{task_name}' started.")
        for i in range(duration):
            time.sleep(1)
            progress = (i + 1) / duration
            print(f"Task '{task_name}' progress: {progress:.2f}")
            update_progress(progress)  # Report progress back
        print(f"Task '{task_name}' finished.")
        return f"Result from {task_name}"


    # Example worker function that fails
    def failing_task(update_progress: Callable[[float], None]):
        print("Failing task started.")
        time.sleep(1)
        update_progress(0.25)
        time.sleep(1)
        update_progress(0.5)
        raise ValueError("Something went wrong in the failing task!")


    # Example worker function without progress reporting needed
    def simple_task(x, y):
        print("Simple task started.")
        time.sleep(2)
        print("Simple task finished.")
        return x + y


    # --- Simulation ---
    manager = BackgroundJobManager(num_threads=3)

    print("Submitting jobs...")
    job1_id = manager.submit_job(long_running_task, 5, task_name="Data Processing")
    job2_id = manager.submit_job(failing_task)  # Will fail
    # Submit a job where the worker *doesn't* accept update_progress
    # Pass progress_callback_arg_name=None or an empty string
    job3_id = manager.submit_job(simple_task, 10, 20, progress_callback_arg_name=None)
    # Submit a job with a custom ID
    custom_job_id = "my-custom-job-123"
    job4_id = manager.submit_job(long_running_task, 3, task_name="Quick Job", job_id=custom_job_id)

    print(f"Job 1 ID: {job1_id}")
    print(f"Job 2 ID: {job2_id}")
    print(f"Job 3 ID: {job3_id}")
    print(f"Job 4 ID: {job4_id}")
    print("-" * 20)

    # Monitor job progress
    all_done = False
    while not all_done:
        all_done = True
        print("\n--- Current Status ---")
        for jid in [job1_id, job2_id, job3_id, job4_id, "nonexistent_job"]:
            status = manager.get_job_status(jid)
            state = manager.get_job_state(jid)  # Get state separately if needed

            if state is None:
                print(f"Job '{jid}': Not Found")
                continue  # Skip further processing for this non-existent job

            print(f"Job '{jid}' (State: {state.name}): ", end="")

            if state == JobState.COMPLETED:
                print(f"COMPLETED, Result: {status}")
            elif state == JobState.FAILED:
                print(f"FAILED, Exception: {status}")
            elif state == JobState.RUNNING or state == JobState.PENDING:
                print(f"In Progress: {status * 100:.1f}%")
                all_done = False  # At least one job is still running
            else:  # Should not happen
                print(f"Unknown state, Status Value: {status}")
                all_done = False

        if not all_done:
            time.sleep(1.5)  # Wait before checking again

    print("\nAll jobs finished processing.")

    # Remember to shut down the manager gracefully in a real application
    # In FastAPI, this would typically be done during the 'shutdown' lifespan event.
    manager.shutdown(wait=True)

    print("\nExample finished.")
