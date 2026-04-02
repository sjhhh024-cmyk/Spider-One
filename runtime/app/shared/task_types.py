from enum import StrEnum


class TaskType(StrEnum):
    RECON = "recon"
    LIST_FETCH = "list_fetch"
    DETAIL_FETCH = "detail_fetch"
    SEARCH_FETCH = "search_fetch"
    VALIDATE = "validate"
    EXPORT = "export"
