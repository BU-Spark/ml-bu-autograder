"""
This class was AI generated: https://chatgpt.com/share/6801c20a-d18c-800f-ab5c-036e9dbf6e7c
"""
import logging
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from typing import Callable, Any, Optional, Iterable, TypeVar

T = TypeVar('T')


class ErrorHandlingThreadPool:
    """
    A wrapper around ThreadPoolExecutor that intercepts exceptions in submitted tasks
    and forwards them to an error handler.
    """

    def __init__(
            self,
            max_workers: Optional[int] = None,
            error_handler: Optional[Callable[[Callable[..., Any], tuple], Any]] = None,
            **executor_kwargs
    ):
        """
        :param max_workers: same as ThreadPoolExecutor
        :param error_handler: fn(fn, exc_info) -> None; by default prints traceback
        :param executor_kwargs: other ThreadPoolExecutor kwargs
        """
        self._executor = ThreadPoolExecutor(max_workers=max_workers, **executor_kwargs)
        self._error_handler = error_handler or self._default_error_handler

    def _default_error_handler(self, fn: Callable[..., Any], exc_info: tuple):
        """Default: print traceback to stderr."""
        logging.error(f"[ErrorHandlingThreadPool] Exception in {fn!r}:")
        traceback.print_exception(*exc_info, file=sys.stderr)

    def submit(self, fn: Callable[..., T], *args, **kwargs) -> Future:
        """
        Submit a task, wrapping it so exceptions get caught.
        """

        def _wrapped(*a, **kw):
            try:
                return fn(*a, **kw)
            except Exception:
                exc_info = sys.exc_info()
                self._error_handler(fn, exc_info)
                # Re-raise if you want Future.exception() to capture it, otherwise swallow
                raise

        return self._executor.submit(_wrapped, *args, **kwargs)

    def map(
            self,
            fn: Callable[..., T],
            *iterables: Iterable,
            timeout: Optional[float] = None,
            chunksize: int = 1
    ):
        """
        Like executor.map, but with error handling on each call.
        """

        def _wrapped(item):
            try:
                return fn(item)
            except Exception:
                exc_info = sys.exc_info()
                self._error_handler(fn, exc_info)
                raise

        return self._executor.map(_wrapped, *iterables, timeout=timeout, chunksize=chunksize)

    def as_completed(self, fs, timeout: Optional[float] = None):
        """
        Proxy for as_completed, so you can handle results/errors in iteration.
        """
        return as_completed(fs, timeout=timeout)

    def shutdown(self, wait: bool = True):
        """
        Shutdown the pool. Same semantics as ThreadPoolExecutor.shutdown.
        """
        return self._executor.shutdown(wait=wait)

    def __enter__(self):
        self._executor.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        return self._executor.__exit__(exc_type, exc, tb)

    def __getattr__(self, name):
        """
        Delegate any other attribute lookups to the underlying executor.
        """
        return getattr(self._executor, name)
