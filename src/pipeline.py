"""
Mortgage origination pipeline definition.

The real application-to-funding journey has ~35 micro-steps. For scheduling
purposes they collapse into the 11 resource-consuming (or clock-consuming)
tasks below, connected as a precedence DAG. Branches (appraisal, title,
doc collection) run in parallel and converge at final underwriting --
which is what makes this a job-shop / RCPSP problem rather than a simple
flow shop.

Time unit: 1 business hour. 8 business hours = 1 business day.
"""

from dataclasses import dataclass, field

HOURS_PER_DAY = 8

# Resource pools. "external" tasks (appraisal turn-time, title search)
# consume calendar time but no internal staff capacity.
PROCESSOR = "processor"
UNDERWRITER = "underwriter"
CLOSER = "closer"
EXTERNAL = "external"


@dataclass(frozen=True)
class Stage:
    key: str
    name: str
    resource: str
    # (min_hours, max_hours) -- per-loan duration drawn from this range
    duration_range: tuple
    predecessors: tuple = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# The pipeline DAG
#
#                    intake
#                      |
#                  le_prep  (TRID: must finish <= 3 business days after app)
#                      |
#               +------+---------+----------------+
#               |                |                |
#           doc_collect    order_appraisal    title_search (external)
#               |                |                |
#           initial_uw     appraisal_turn        |
#               |          (external)            |
#           conditions           |               |
#               +-------+--------+-------+-------+
#                       |
#                   final_uw   (clear to close)
#                       |
#                    cd_prep   (Closing Disclosure)
#                       |
#                   [TRID: >= 3 business day waiting period]
#                       |
#                  closing_funding
# ---------------------------------------------------------------------------

STAGES = [
    Stage("intake", "Application intake & setup", PROCESSOR, (2, 4)),
    Stage("le_prep", "Loan Estimate prep & delivery", PROCESSOR, (2, 4),
          ("intake",)),
    Stage("doc_collect", "Borrower document collection", PROCESSOR, (8, 24),
          ("le_prep",)),
    Stage("order_appraisal", "Order appraisal", PROCESSOR, (1, 2),
          ("le_prep",)),
    Stage("appraisal_turn", "Appraisal turn-time (vendor)", EXTERNAL, (40, 80),
          ("order_appraisal",)),
    Stage("title_search", "Title search & commitment (vendor)", EXTERNAL, (24, 56),
          ("le_prep",)),
    Stage("initial_uw", "Initial underwriting", UNDERWRITER, (4, 8),
          ("doc_collect",)),
    Stage("conditions", "Conditions collection & review", PROCESSOR, (8, 20),
          ("initial_uw",)),
    Stage("final_uw", "Final underwriting / clear to close", UNDERWRITER, (3, 6),
          ("conditions", "appraisal_turn", "title_search")),
    Stage("cd_prep", "Closing Disclosure prep & delivery", CLOSER, (2, 4),
          ("final_uw",)),
    Stage("closing_funding", "Closing & funding", CLOSER, (3, 5),
          ("cd_prep",)),
]

STAGE_INDEX = {s.key: i for i, s in enumerate(STAGES)}

# --- Regulatory constants (TRID, 12 CFR 1026.19) ---------------------------
# Loan Estimate must be delivered within 3 business days of application.
LE_DEADLINE_DAYS = 3
# Closing Disclosure must be received >= 3 business days before consummation.
CD_WAITING_DAYS = 3

LE_DEADLINE_HOURS = LE_DEADLINE_DAYS * HOURS_PER_DAY
CD_WAITING_HOURS = CD_WAITING_DAYS * HOURS_PER_DAY
