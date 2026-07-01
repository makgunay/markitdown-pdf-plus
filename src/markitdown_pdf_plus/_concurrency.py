from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

_T = TypeVar("_T")
_R = TypeVar("_R")


def map_ordered(fn: Callable[[_T], _R], items: Sequence[_T], concurrency: int) -> list[_R]:
    """Apply ``fn`` over ``items`` preserving input order.

    Runs concurrently in a thread pool when it helps (``concurrency`` > 1 and more
    than one item); otherwise sequentially. The VLM/OCR calls are I/O-bound network
    requests, so threads overlap their latency. ``fn`` must be fail-soft (the VLM
    methods catch their own exceptions and return ``None``).
    """
    if not items:
        return []
    if concurrency <= 1 or len(items) == 1:
        return [fn(it) for it in items]
    with ThreadPoolExecutor(max_workers=min(concurrency, len(items))) as ex:
        return list(ex.map(fn, items))
