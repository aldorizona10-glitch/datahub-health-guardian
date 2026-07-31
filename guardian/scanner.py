"""
DataHub Health Guardian — Health Scanner

Scans DataHub datasets for health issues:
- Missing descriptions
- Missing ownership
- Schema with no field descriptions
- Stale datasets (no recent updates)
- Missing tags/glossary terms
- Deprecated but still referenced datasets
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class HealthIssue:
    """Represents a single health issue found during scanning."""
    dataset_urn: str
    dataset_name: str
    category: str
    severity: Severity
    message: str
    details: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "dataset_urn": self.dataset_urn,
            "dataset_name": self.dataset_name,
            "category": self.category,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
        }


@dataclass
class ScanResult:
    """Result of a full health scan."""
    scan_id: str
    started_at: str
    completed_at: str = ""
    datasets_scanned: int = 0
    issues: list[HealthIssue] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "scan_id": self.scan_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "datasets_scanned": self.datasets_scanned,
            "total_issues": len(self.issues),
            "by_severity": {
                "critical": len([i for i in self.issues if i.severity == Severity.CRITICAL]),
                "warning": len([i for i in self.issues if i.severity == Severity.WARNING]),
                "info": len([i for i in self.issues if i.severity == Severity.INFO]),
            },
            "issues": [i.to_dict() for i in self.issues],
            "summary": self.summary,
        }


class HealthScanner:
    """Scans DataHub datasets for health issues."""

    def __init__(self, datahub_client):
        self.client = datahub_client

    def scan_all(self, max_datasets: int = 100) -> ScanResult:
        """Run a full health scan across all datasets."""
        import uuid

        scan = ScanResult(
            scan_id=str(uuid.uuid4())[:8],
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        logger.info("🔍 Starting health scan...")

        # Fetch all datasets
        datasets = self.client.search_all_datasets_graphql("*", count=max_datasets)
        scan.datasets_scanned = len(datasets)
        logger.info(f"  Found {len(datasets)} datasets to scan")

        for dataset in datasets:
            urn = dataset.get("urn", "")
            name = dataset.get("name", urn)
            props = dataset.get("properties") or {}
            schema = dataset.get("schemaMetadata") or {}
            ownership = dataset.get("ownership") or {}
            tags = dataset.get("globalTags") or {}
            deprecation = dataset.get("deprecation") or {}

            # Check: Missing description
            if not props.get("description"):
                scan.issues.append(HealthIssue(
                    dataset_urn=urn,
                    dataset_name=name,
                    category="documentation",
                    severity=Severity.WARNING,
                    message=f"Dataset '{name}' has no description",
                    details={"fix": "Add a description to help data consumers understand this dataset"},
                ))

            # Check: Missing ownership
            owners = (ownership.get("owners") or [])
            if not owners:
                scan.issues.append(HealthIssue(
                    dataset_urn=urn,
                    dataset_name=name,
                    category="governance",
                    severity=Severity.CRITICAL,
                    message=f"Dataset '{name}' has no owner assigned",
                    details={"fix": "Assign an owner for accountability and incident response"},
                ))

            # Check: Schema fields without descriptions
            fields = (schema.get("fields") or [])
            undocumented_fields = [f["fieldPath"] for f in fields if not f.get("description")]
            if fields and len(undocumented_fields) > len(fields) * 0.5:
                scan.issues.append(HealthIssue(
                    dataset_urn=urn,
                    dataset_name=name,
                    category="documentation",
                    severity=Severity.WARNING,
                    message=f"Dataset '{name}' has {len(undocumented_fields)}/{len(fields)} undocumented fields",
                    details={
                        "undocumented_fields": undocumented_fields[:10],
                        "fix": "Add field descriptions to improve data discoverability",
                    },
                ))

            # Check: No tags
            tag_list = (tags.get("tags") or [])
            if not tag_list:
                scan.issues.append(HealthIssue(
                    dataset_urn=urn,
                    dataset_name=name,
                    category="classification",
                    severity=Severity.INFO,
                    message=f"Dataset '{name}' has no tags",
                    details={"fix": "Add classification tags (e.g., PII, public, internal)"},
                ))

            # Check: Stale dataset (no recent modification)
            last_modified = props.get("lastModified", {})
            if last_modified and last_modified.get("time"):
                mod_time = last_modified["time"]
                # DataHub returns epoch millis
                if isinstance(mod_time, (int, float)):
                    mod_dt = datetime.fromtimestamp(mod_time / 1000, tz=timezone.utc)
                    days_stale = (datetime.now(timezone.utc) - mod_dt).days
                    if days_stale > 90:
                        scan.issues.append(HealthIssue(
                            dataset_urn=urn,
                            dataset_name=name,
                            category="freshness",
                            severity=Severity.WARNING,
                            message=f"Dataset '{name}' hasn't been updated in {days_stale} days",
                            details={
                                "last_modified": mod_dt.isoformat(),
                                "days_stale": days_stale,
                                "fix": "Verify if pipeline is running or deprecate if no longer needed",
                            },
                        ))

            # Check: Deprecated but might still be referenced
            if deprecation.get("deprecated"):
                scan.issues.append(HealthIssue(
                    dataset_urn=urn,
                    dataset_name=name,
                    category="lifecycle",
                    severity=Severity.CRITICAL,
                    message=f"Dataset '{name}' is deprecated: {deprecation.get('note', 'no reason given')}",
                    details={
                        "note": deprecation.get("note", ""),
                        "fix": "Check downstream lineage — consumers may still depend on this dataset",
                    },
                ))

        scan.completed_at = datetime.now(timezone.utc).isoformat()

        # Build summary
        categories = {}
        for issue in scan.issues:
            categories[issue.category] = categories.get(issue.category, 0) + 1
        scan.summary = {
            "health_score": self._calculate_health_score(scan),
            "by_category": categories,
        }

        logger.info(
            f"✅ Scan complete: {scan.datasets_scanned} datasets, "
            f"{len(scan.issues)} issues found (health score: {scan.summary['health_score']}%)"
        )
        return scan

    def _calculate_health_score(self, scan: ScanResult) -> int:
        """Calculate overall health score (0-100)."""
        if scan.datasets_scanned == 0:
            return 100

        # Weighted penalty per issue type
        penalty = 0
        for issue in scan.issues:
            if issue.severity == Severity.CRITICAL:
                penalty += 10
            elif issue.severity == Severity.WARNING:
                penalty += 5
            else:
                penalty += 1

        # Max penalty is proportional to dataset count
        max_penalty = scan.datasets_scanned * 30  # theoretical max
        score = max(0, 100 - int((penalty / max_penalty) * 100))
        return score
