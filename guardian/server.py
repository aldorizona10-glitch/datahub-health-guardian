"""
DataHub Health Guardian — FastAPI Server

REST API for the health guardian agent, serving:
- Health scan triggers
- Scan results history
- Real-time status
- Demo mode with mock data
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .config import Config
from .scanner import HealthIssue, ScanResult, Severity

logger = logging.getLogger(__name__)

app = FastAPI(
    title="DataHub Health Guardian",
    description="AI-powered data health monitoring agent for DataHub",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for demo
scan_history: list[dict] = []
latest_report: str = ""


def generate_demo_scan() -> ScanResult:
    """Generate realistic demo scan data for showcase."""
    scan = ScanResult(
        scan_id=str(uuid.uuid4())[:8],
        started_at=datetime.now(timezone.utc).isoformat(),
    )

    # Simulate scanning healthcare dataset
    demo_datasets = [
        {
            "urn": "urn:li:dataset:(urn:li:dataPlatform:postgres,healthcare.patients,PROD)",
            "name": "healthcare.patients",
            "issues": [
                HealthIssue(
                    dataset_urn="urn:li:dataset:(urn:li:dataPlatform:postgres,healthcare.patients,PROD)",
                    dataset_name="healthcare.patients",
                    category="governance",
                    severity=Severity.CRITICAL,
                    message="Dataset 'healthcare.patients' has no owner assigned",
                    details={"fix": "Assign data steward for PII-containing patient records"},
                ),
                HealthIssue(
                    dataset_urn="urn:li:dataset:(urn:li:dataPlatform:postgres,healthcare.patients,PROD)",
                    dataset_name="healthcare.patients",
                    category="classification",
                    severity=Severity.CRITICAL,
                    message="Dataset 'healthcare.patients' contains PII but has no classification tags",
                    details={"fix": "Add 'PII', 'HIPAA', 'Sensitive' tags immediately"},
                ),
            ],
        },
        {
            "urn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,nyc_taxi.trips,PROD)",
            "name": "nyc_taxi.trips",
            "issues": [
                HealthIssue(
                    dataset_urn="urn:li:dataset:(urn:li:dataPlatform:snowflake,nyc_taxi.trips,PROD)",
                    dataset_name="nyc_taxi.trips",
                    category="freshness",
                    severity=Severity.WARNING,
                    message="Dataset 'nyc_taxi.trips' hasn't been updated in 127 days",
                    details={"days_stale": 127, "fix": "Check if ETL pipeline is still running"},
                ),
            ],
        },
        {
            "urn": "urn:li:dataset:(urn:li:dataPlatform:bigquery,retail.orders,PROD)",
            "name": "retail.orders",
            "issues": [
                HealthIssue(
                    dataset_urn="urn:li:dataset:(urn:li:dataPlatform:bigquery,retail.orders,PROD)",
                    dataset_name="retail.orders",
                    category="documentation",
                    severity=Severity.WARNING,
                    message="Dataset 'retail.orders' has 12/15 undocumented fields",
                    details={"undocumented_fields": ["order_id", "customer_id", "amount", "tax", "discount"]},
                ),
            ],
        },
        {
            "urn": "urn:li:dataset:(urn:li:dataPlatform:kafka,events.clickstream,PROD)",
            "name": "events.clickstream",
            "issues": [
                HealthIssue(
                    dataset_urn="urn:li:dataset:(urn:li:dataPlatform:kafka,events.clickstream,PROD)",
                    dataset_name="events.clickstream",
                    category="lifecycle",
                    severity=Severity.CRITICAL,
                    message="Dataset 'events.clickstream' is deprecated but has 8 active downstream consumers",
                    details={"downstream_count": 8, "fix": "Migrate consumers before decommissioning"},
                ),
            ],
        },
        {
            "urn": "urn:li:dataset:(urn:li:dataPlatform:mysql,finance.transactions,PROD)",
            "name": "finance.transactions",
            "issues": [],
        },
        {
            "urn": "urn:li:dataset:(urn:li:dataPlatform:s3,logs.application,PROD)",
            "name": "logs.application",
            "issues": [
                HealthIssue(
                    dataset_urn="urn:li:dataset:(urn:li:dataPlatform:s3,logs.application,PROD)",
                    dataset_name="logs.application",
                    category="documentation",
                    severity=Severity.WARNING,
                    message="Dataset 'logs.application' has no description",
                    details={"fix": "Add description explaining log format and retention policy"},
                ),
                HealthIssue(
                    dataset_urn="urn:li:dataset:(urn:li:dataPlatform:s3,logs.application,PROD)",
                    dataset_name="logs.application",
                    category="governance",
                    severity=Severity.CRITICAL,
                    message="Dataset 'logs.application' has no owner assigned",
                    details={"fix": "Assign SRE team as owners"},
                ),
            ],
        },
        {
            "urn": "urn:li:dataset:(urn:li:dataPlatform:hive,warehouse.inventory,PROD)",
            "name": "warehouse.inventory",
            "issues": [
                HealthIssue(
                    dataset_urn="urn:li:dataset:(urn:li:dataPlatform:hive,warehouse.inventory,PROD)",
                    dataset_name="warehouse.inventory",
                    category="classification",
                    severity=Severity.INFO,
                    message="Dataset 'warehouse.inventory' has no tags",
                    details={"fix": "Add domain and classification tags"},
                ),
            ],
        },
    ]

    for ds in demo_datasets:
        scan.issues.extend(ds["issues"])

    scan.datasets_scanned = len(demo_datasets)
    scan.completed_at = datetime.now(timezone.utc).isoformat()

    # Calculate summary
    categories = {}
    for issue in scan.issues:
        categories[issue.category] = categories.get(issue.category, 0) + 1

    critical = len([i for i in scan.issues if i.severity == Severity.CRITICAL])
    warning = len([i for i in scan.issues if i.severity == Severity.WARNING])
    info = len([i for i in scan.issues if i.severity == Severity.INFO])
    total_penalty = critical * 10 + warning * 5 + info * 1
    max_penalty = scan.datasets_scanned * 30
    health_score = max(0, 100 - int((total_penalty / max_penalty) * 100))

    scan.summary = {
        "health_score": health_score,
        "by_category": categories,
    }

    return scan


DEMO_ANALYSIS = {
    "executive_summary": "The data ecosystem has significant governance gaps. 4 critical issues require immediate attention, primarily around missing ownership for sensitive datasets and a deprecated dataset with active consumers. Quick wins in documentation can rapidly improve the health score.",
    "risk_level": "high",
    "top_priorities": [
        {
            "rank": 1,
            "dataset": "healthcare.patients",
            "issue": "No owner + No PII classification on patient records",
            "business_impact": "HIPAA compliance risk — unclassified PII data without an accountable owner",
            "recommended_action": "Immediately assign a data steward and add PII/HIPAA tags",
        },
        {
            "rank": 2,
            "dataset": "events.clickstream",
            "issue": "Deprecated with 8 active downstream consumers",
            "business_impact": "When this dataset is decommissioned, 8 downstream pipelines will break",
            "recommended_action": "Notify consumer teams, create migration plan with deadline",
        },
        {
            "rank": 3,
            "dataset": "logs.application",
            "issue": "No owner and no documentation",
            "business_impact": "During incidents, nobody knows who to contact or what this data means",
            "recommended_action": "Assign SRE team ownership, document log format and retention",
        },
        {
            "rank": 4,
            "dataset": "nyc_taxi.trips",
            "issue": "127 days since last update",
            "business_impact": "Downstream analytics may be using stale data for decision-making",
            "recommended_action": "Verify ETL pipeline health, check for silent failures",
        },
    ],
    "quick_wins": [
        "Add descriptions to 'logs.application' and 'retail.orders' (15 min each)",
        "Tag 'healthcare.patients' with PII/HIPAA classifications (5 min)",
        "Add domain tags to 'warehouse.inventory' (5 min)",
        "Document the 12 undocumented fields in 'retail.orders' (30 min)",
    ],
    "trend_assessment": "The ecosystem shows signs of rapid growth without corresponding governance. Recommend establishing a data stewardship program and mandatory metadata requirements for new datasets.",
}

DEMO_LINEAGE_IMPACTS = {
    "urn:li:dataset:(urn:li:dataPlatform:kafka,events.clickstream,PROD)": {
        "downstream_count": 8,
        "blast_radius": "high",
        "impact_summary": "8 downstream consumers spanning analytics, ML features, and real-time dashboards will lose data when this deprecated source is decommissioned",
        "affected_systems": [
            "analytics.user_behavior (BigQuery)",
            "ml.recommendation_features (Snowflake)",
            "dashboard.realtime_metrics (Kafka → Druid)",
            "reports.weekly_engagement (Hive)",
        ],
        "mitigation_steps": [
            "1. Inventory all 8 downstream consumers with their SLAs",
            "2. Notify owning teams with 30-day migration deadline",
            "3. Provide replacement data source documentation",
            "4. Set up dual-write period for graceful transition",
            "5. Monitor consumer migration progress weekly",
        ],
    },
    "urn:li:dataset:(urn:li:dataPlatform:postgres,healthcare.patients,PROD)": {
        "downstream_count": 3,
        "blast_radius": "medium",
        "impact_summary": "Patient data flows to 3 downstream systems. Missing PII classification means these downstream datasets may also be untagged, creating compliance exposure across the pipeline",
        "affected_systems": [
            "analytics.patient_outcomes (BigQuery)",
            "ml.readmission_risk (Vertex AI)",
            "reports.monthly_clinical (Looker)",
        ],
        "mitigation_steps": [
            "1. Immediately tag source with PII/HIPAA",
            "2. Propagate classification tags to all downstream datasets",
            "3. Audit access controls on all 3 downstream systems",
            "4. Assign data steward for ongoing governance",
        ],
    },
}

DEMO_REPORT = """# 🏥 DataHub Health Report

## Executive Summary
The data ecosystem has **significant governance gaps**. 4 critical issues require immediate attention, primarily around missing ownership for sensitive datasets and a deprecated dataset with active consumers.

## 📊 Health Score: **62%** | Risk Level: 🔴 HIGH

## ❌ Critical Issues

| # | Dataset | Issue | Business Impact |
|---|---------|-------|-----------------|
| 1 | `healthcare.patients` | No owner + No PII tags | HIPAA compliance risk |
| 2 | `events.clickstream` | Deprecated, 8 consumers | Pipeline breakage risk |
| 3 | `logs.application` | No owner, no docs | Incident response blind spot |
| 4 | `healthcare.patients` | PII without classification | Regulatory exposure |

## 🔗 Lineage Impact Analysis

### `events.clickstream` — Blast Radius: 🔴 HIGH
- **8 downstream consumers** will break when decommissioned
- Affects: analytics, ML features, real-time dashboards, weekly reports
- **Action**: 30-day migration plan with dual-write period

### `healthcare.patients` — Blast Radius: 🟡 MEDIUM  
- **3 downstream systems** may inherit untagged PII
- Affects: patient outcomes analytics, ML risk model, clinical reports
- **Action**: Propagate PII tags downstream, audit access controls

## 🎯 Recommended Actions (Prioritized)

1. **[URGENT]** Assign data steward to `healthcare.patients` + add PII/HIPAA tags
2. **[URGENT]** Create migration plan for `events.clickstream` consumers
3. **[HIGH]** Assign SRE ownership to `logs.application`, add documentation
4. **[MEDIUM]** Investigate stale `nyc_taxi.trips` pipeline (127 days)
5. **[LOW]** Document fields in `retail.orders` (12/15 undocumented)

## ⚡ Quick Wins (< 1 hour total)
- Tag `healthcare.patients` with PII/HIPAA (5 min)
- Add descriptions to `logs.application` (15 min)  
- Add domain tags to `warehouse.inventory` (5 min)
- Document `retail.orders` fields (30 min)

---
*Generated by DataHub Health Guardian Agent at {timestamp}*
""".format(timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))


@app.get("/")
async def root():
    return {"status": "ok", "service": "DataHub Health Guardian", "version": "1.0.0"}


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/api/scan")
async def trigger_scan(demo: bool = True):
    """Trigger a health scan. Use demo=true for showcase mode."""
    if demo:
        scan = generate_demo_scan()
        result = {
            "scan": scan.to_dict(),
            "analysis": DEMO_ANALYSIS,
            "lineage_impacts": DEMO_LINEAGE_IMPACTS,
            "report": DEMO_REPORT,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    else:
        config = Config()
        issues = config.validate()
        if issues:
            raise HTTPException(status_code=400, detail=f"Configuration issues: {', '.join(issues)}")

        from .agent import HealthGuardianAgent
        agent = HealthGuardianAgent(config)
        try:
            result = agent.run_health_check()
        finally:
            agent.close()

    scan_history.append(result)
    return JSONResponse(content=result)


@app.get("/api/scan/latest")
async def get_latest_scan():
    """Get the most recent scan result."""
    if not scan_history:
        # Auto-generate demo scan on first request
        scan = generate_demo_scan()
        result = {
            "scan": scan.to_dict(),
            "analysis": DEMO_ANALYSIS,
            "lineage_impacts": DEMO_LINEAGE_IMPACTS,
            "report": DEMO_REPORT,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        scan_history.append(result)
    return JSONResponse(content=scan_history[-1])


@app.get("/api/scan/history")
async def get_scan_history():
    """Get all scan results."""
    return JSONResponse(content={"scans": scan_history, "total": len(scan_history)})


@app.get("/api/demo/datasets")
async def get_demo_datasets():
    """Get demo dataset list for the dashboard."""
    datasets = [
        {"urn": "urn:li:dataset:(urn:li:dataPlatform:postgres,healthcare.patients,PROD)", "name": "healthcare.patients", "platform": "postgres", "status": "critical", "health_score": 30},
        {"urn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,nyc_taxi.trips,PROD)", "name": "nyc_taxi.trips", "platform": "snowflake", "status": "warning", "health_score": 55},
        {"urn": "urn:li:dataset:(urn:li:dataPlatform:bigquery,retail.orders,PROD)", "name": "retail.orders", "platform": "bigquery", "status": "warning", "health_score": 60},
        {"urn": "urn:li:dataset:(urn:li:dataPlatform:kafka,events.clickstream,PROD)", "name": "events.clickstream", "platform": "kafka", "status": "critical", "health_score": 25},
        {"urn": "urn:li:dataset:(urn:li:dataPlatform:mysql,finance.transactions,PROD)", "name": "finance.transactions", "platform": "mysql", "status": "healthy", "health_score": 100},
        {"urn": "urn:li:dataset:(urn:li:dataPlatform:s3,logs.application,PROD)", "name": "logs.application", "platform": "s3", "status": "critical", "health_score": 35},
        {"urn": "urn:li:dataset:(urn:li:dataPlatform:hive,warehouse.inventory,PROD)", "name": "warehouse.inventory", "platform": "hive", "status": "info", "health_score": 80},
    ]
    return JSONResponse(content={"datasets": datasets})
