class ImportError(Exception):
    """Base exception for all statement import failures."""
    def __init__(self, message: str, code: str = "IMPORT_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class FileSecurityError(ImportError):
    def __init__(self, message: str):
        super().__init__(message, code="FILE_SECURITY_ERROR")


class ParseError(ImportError):
    def __init__(self, message: str):
        super().__init__(message, code="PARSE_ERROR")


class ValidationError(ImportError):
    def __init__(self, message: str):
        super().__init__(message, code="VALIDATION_ERROR")


class MappingError(ImportError):
    def __init__(self, message: str):
        super().__init__(message, code="MAPPING_ERROR")


class CommitError(ImportError):
    def __init__(self, message: str):
        super().__init__(message, code="COMMIT_ERROR")
