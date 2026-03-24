"""Shared test fixtures."""
import pytest
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.event_bus import EventBus
from services.mlops.logger import StructuredLogger
from services.analysis_service.callbacks import GlobalObservability
import services.analysis_service.bedrock_client as bedrock_mod
import services.mlops.experiments as experiments_mod


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singletons before each test."""
    EventBus._instance = None
    StructuredLogger._instance = None
    GlobalObservability._instance = None
    bedrock_mod._router = None
    experiments_mod._manager = None
    yield
    EventBus._instance = None
    StructuredLogger._instance = None
    GlobalObservability._instance = None
    bedrock_mod._router = None
    experiments_mod._manager = None


@pytest.fixture
def sample_contract():
    return """PROFESSIONAL SERVICES AGREEMENT
This Agreement includes provisions for liability, indemnification, and breach penalties.
Provider shall comply with all applicable compliance requirements. Termination may occur
with 30 days notice. Confidentiality obligations survive for three years. Audit rights
are reserved by the Client. Default provisions require 15 days to cure."""


@pytest.fixture
def sample_financial():
    return """QUARTERLY FINANCIAL REPORT Q4 2024
Revenue reached $128.5 million, a 23% increase year-over-year. Growth was strong across
all segments. Cloud services revenue grew 31% to $72.3M. Net income was $24.6M with
favorable margins. The outlook for 2025 projects continued growth of 28-35%."""


@pytest.fixture
def sample_compliance():
    return """DATA PRIVACY COMPLIANCE ASSESSMENT
The organization processes personal data of 2.4 million EU residents. GDPR compliance
score is 78/100. Gaps identified in consent management and vendor security assessments.
Penalties for non-compliance can reach 4% of annual turnover. Remediation deadline is
90 days for critical items. Regular audit schedule must be maintained."""
