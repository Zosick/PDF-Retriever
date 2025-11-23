"""
Defines the data contract for the thread-safe queue.

All messages passed between the GUI and the DownloadManager
must conform to these type definitions.
"""

import queue
from typing import Literal, TypedDict, Union

# --- Define the individual message structures ---


class DownloadSuccessMsg(TypedDict):
    status: Literal["success"]
    doi: str
    source: str
    citation: str


class DownloadSkippedMsg(TypedDict):
    status: Literal["skipped"]
    doi: str
    citation: str


class DownloadFailedMsg(TypedDict):
    status: Literal["failed", "error"]
    doi: str
    message: str


# A "Progress Message" is one of the three above
ProgressMessage = Union[DownloadSuccessMsg, DownloadSkippedMsg, DownloadFailedMsg]


class StatusStartMsg(TypedDict):
    status: Literal["start"]
    message: str


class StatusCompleteMsg(TypedDict):
    status: Literal["complete"]
    message: str


class StatusCancelledMsg(TypedDict):
    status: Literal["cancelled"]
    message: str


class StatusCriticalErrorMsg(TypedDict):
    status: Literal["critical_error"]
    message: str


class StatusFinishedMsg(TypedDict):
    status: Literal["finished"]


# A "Status Message" is one of the administrative messages
StatusMessage = Union[
    StatusStartMsg,
    StatusCompleteMsg,
    StatusCancelledMsg,
    StatusCriticalErrorMsg,
    StatusFinishedMsg,
]

# The queue can contain *any* of these messages
QueueMessage = Union[ProgressMessage, StatusMessage]

# This is the type for the queue itself
ProgressQueue = queue.Queue[QueueMessage]
