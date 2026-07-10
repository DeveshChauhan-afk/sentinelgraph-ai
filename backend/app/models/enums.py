# app/models/enums.py

"""
Domain-specific enumerations for the SentinelGraph AI platform.
"""

from enum import Enum


class IncidentStatus(str, Enum):
    """Lifecycle states of an incident."""

    NEW = "new"
    PROCESSING = "processing"
    ANALYZED = "analyzed"
    UNDER_INVESTIGATION = "under_investigation"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Priority(str, Enum):
    """Urgency level of an incident."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReporterType(str, Enum):
    """Origin entity of the report."""

    CITIZEN = "citizen"
    POLICE = "police"
    BANK = "bank"
    CYBER_CELL = "cyber_cell"
    OTHER = "other"


class ScamCategory(str, Enum):
    """Nature of the fraudulent activity."""

    DIGITAL_ARREST = "digital_arrest"
    UPI_FRAUD = "upi_fraud"
    PHISHING = "phishing"
    QR_SCAM = "qr_scam"
    IDENTITY_THEFT = "identity_theft"
    INVESTMENT_FRAUD = "investment_fraud"
    OTHER = "other"
    UNKNOWN = "unknown"


class IncidentSource(str, Enum):
    """Channel through which the incident was received."""

    WEB_PORTAL = "web_portal"
    MOBILE_APP = "mobile_app"
    API = "api"
    BULK_IMPORT = "bulk_import"
