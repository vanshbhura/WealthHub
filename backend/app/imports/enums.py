import enum


class ImportType(str, enum.Enum):
    BROKER = "BROKER"
    BANK = "BANK"
    MUTUAL_FUND = "MUTUAL_FUND"
    DIGITAL_GOLD = "DIGITAL_GOLD"
    DIGITAL_SILVER = "DIGITAL_SILVER"
    P2P = "P2P"
    GENERIC_PORTFOLIO = "GENERIC_PORTFOLIO"


class ImportJobStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    PARSING = "PARSING"
    READY = "READY"
    VALIDATING = "VALIDATING"
    VALID = "VALID"
    INVALID = "INVALID"
    COMMITTING = "COMMITTING"
    COMMITTED = "COMMITTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ValidationSeverity(str, enum.Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class DuplicateStatus(str, enum.Enum):
    EXACT_DUPLICATE = "EXACT_DUPLICATE"
    POSSIBLE_DUPLICATE = "POSSIBLE_DUPLICATE"
    NEW = "NEW"
