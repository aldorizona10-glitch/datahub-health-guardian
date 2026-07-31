"""
DataHub Health Guardian — AI Agent Core

Uses Google Gemini to:
1. Analyze scan results and prioritize issues
2. Trace lineage impact for critical issues
3. Generate incident reports with root cause analysis
4. Suggest self-healing actions
"""
import json
import logging
from datetime import datetime, timezone

import google.generativeai as genai

from .config import Config
from .datahub_client import DataHubClient
from .scanner import HealthScanner, ScanResult, Severity

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """\
You are the DataHub Health Guardian, an expert AI agent specializing in data governance, 
data quality, and metadata management. You work with DataHub — the open-source metadata 
platform used by companies like Apple, Netflix, and Pinterest.

Your responsibilities:
1. Analyze health scan results to identify the most critical data quality issues
2. Prioritize issues based on business impact and downstream dependencies  
3. Generate clear, actionable incident reports
4. Suggest specific remediation steps

When analyzing issues, consider:
- Datasets without owners are governance risks (who gets paged at 2am?)
- Undocumented datasets are discoverability blockers
- Stale datasets may indicate broken pipelines
- Deprecated datasets with downstream consumers are ticking time bombs

Always provide specific, actionable recommendations. Be concise but thorough.
Output your analysis as structured JSON when asked.
"""


class HealthGuardianAgent:
    """AI-powered agent for DataHub health monitoring."""

    def __init__(self, config: Config):
        self.config = config

        # Initialize Gemini
        genai.configure(api_key=config.google_api_key)
        self.model = genai.GenerativeModel(
            model_name=config.model_name,
            system_instruction=SYSTEM_PROMPT,
            generation_config=genai.GenerationConfig(
                max_output_tokens=config.max_output_tokens,
                temperature=config.temperature,
            ),
        )

        # Initialize DataHub client
        self.datahub = DataHubClient(config.datahub_gms_url, config.datahub_token)

        # Initialize scanner
        self.scanner = HealthScanner(self.datahub)

        # Chat session for multi-turn reasoning
        self.chat = None

    def run_health_check(self) -> dict:
        """Execute a full health check cycle."""
        logger.info("🚀 Health Guardian Agent starting health check...")

        # Step 1: Scan
        scan_result = self.scanner.scan_all()

        # Step 2: AI Analysis
        analysis = self.analyze_scan(scan_result)

        # Step 3: Lineage impact for critical issues
        critical_issues = [i for i in scan_result.issues if i.severity == Severity.CRITICAL]
        lineage_impacts = {}
        for issue in critical_issues[:5]:  # Limit to top 5
            impact = self.analyze_lineage_impact(issue.dataset_urn, issue.dataset_name)
            if impact:
                lineage_impacts[issue.dataset_urn] = impact

        # Step 4: Generate report
        report = self.generate_report(scan_result, analysis, lineage_impacts)

        return {
            "scan": scan_result.to_dict(),
            "analysis": analysis,
            "lineage_impacts": lineage_impacts,
            "report": report,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def analyze_scan(self, scan_result: ScanResult) -> dict:
        """Use Gemini to analyze scan results and prioritize issues."""
        self.chat = self.model.start_chat()

        prompt = f"""Analyze this DataHub health scan result and provide a prioritized assessment.

SCAN SUMMARY:
- Datasets scanned: {scan_result.datasets_scanned}
- Total issues: {len(scan_result.issues)}
- Critical: {len([i for i in scan_result.issues if i.severity == Severity.CRITICAL])}
- Warning: {len([i for i in scan_result.issues if i.severity == Severity.WARNING])}
- Info: {len([i for i in scan_result.issues if i.severity == Severity.INFO])}
- Health Score: {scan_result.summary.get('health_score', 'N/A')}%

TOP ISSUES:
{json.dumps([i.to_dict() for i in scan_result.issues[:20]], indent=2)}

Respond with JSON in this exact format:
{{
    "executive_summary": "2-3 sentence summary of the data health state",
    "risk_level": "low|medium|high|critical",
    "top_priorities": [
        {{
            "rank": 1,
            "dataset": "name",
            "issue": "description",
            "business_impact": "why this matters",
            "recommended_action": "specific fix"
        }}
    ],
    "quick_wins": ["list of easy fixes that improve health score fast"],
    "trend_assessment": "is the data ecosystem getting healthier or sicker?"
}}"""

        try:
            response = self.chat.send_message(prompt)
            text = response.text.strip()
            # Extract JSON from response
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            return json.loads(text)
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return {
                "executive_summary": f"Scan found {len(scan_result.issues)} issues across {scan_result.datasets_scanned} datasets.",
                "risk_level": "unknown",
                "top_priorities": [],
                "quick_wins": [],
                "trend_assessment": "Unable to assess — AI analysis failed",
            }

    def analyze_lineage_impact(self, dataset_urn: str, dataset_name: str) -> dict | None:
        """Analyze downstream lineage impact for a problematic dataset."""
        lineage = self.datahub.get_lineage(dataset_urn, direction="DOWNSTREAM")
        if not lineage:
            return None

        relationships = lineage.get("relationships", [])
        if not relationships:
            return {"downstream_count": 0, "impact": "No downstream consumers found"}

        downstream_urns = [r.get("entity", "") for r in relationships]

        prompt = f"""A critical issue was found in dataset "{dataset_name}" (URN: {dataset_urn}).
        
This dataset has {len(downstream_urns)} downstream consumers:
{json.dumps(downstream_urns[:10], indent=2)}

Assess the blast radius and impact. Respond with JSON:
{{
    "downstream_count": {len(downstream_urns)},
    "blast_radius": "low|medium|high",
    "impact_summary": "description of potential impact",
    "affected_systems": ["list of potentially affected downstream systems"],
    "mitigation_steps": ["ordered list of steps to contain the issue"]
}}"""

        try:
            if self.chat:
                response = self.chat.send_message(prompt)
            else:
                response = self.model.generate_content(prompt)
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            return json.loads(text)
        except Exception as e:
            logger.error(f"Lineage analysis failed: {e}")
            return {
                "downstream_count": len(downstream_urns),
                "blast_radius": "unknown",
                "impact_summary": f"{len(downstream_urns)} downstream consumers potentially affected",
            }

    def generate_report(self, scan: ScanResult, analysis: dict, lineage_impacts: dict) -> str:
        """Generate a comprehensive incident report."""
        prompt = f"""Generate a professional data health incident report based on this analysis.

SCAN DATA:
{json.dumps(scan.to_dict(), indent=2, default=str)}

AI ANALYSIS:
{json.dumps(analysis, indent=2)}

LINEAGE IMPACTS:
{json.dumps(lineage_impacts, indent=2)}

Generate a clean markdown report with:
1. Executive Summary (2-3 sentences)  
2. Health Score and Risk Level
3. Critical Issues (table format)
4. Lineage Impact Analysis  
5. Recommended Actions (prioritized)
6. Quick Wins

Keep it concise and actionable. Use emojis for visual clarity."""

        try:
            if self.chat:
                response = self.chat.send_message(prompt)
            else:
                response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return self._fallback_report(scan, analysis)

    def _fallback_report(self, scan: ScanResult, analysis: dict) -> str:
        """Generate a basic report without AI."""
        critical = len([i for i in scan.issues if i.severity == Severity.CRITICAL])
        warning = len([i for i in scan.issues if i.severity == Severity.WARNING])
        info = len([i for i in scan.issues if i.severity == Severity.INFO])

        report = f"""# 🏥 DataHub Health Report

## Summary
- **Datasets Scanned**: {scan.datasets_scanned}
- **Health Score**: {scan.summary.get('health_score', 'N/A')}%
- **Issues**: {critical} critical, {warning} warnings, {info} info

## Critical Issues
"""
        for issue in scan.issues:
            if issue.severity == Severity.CRITICAL:
                report += f"- ❌ **{issue.dataset_name}**: {issue.message}\n"

        report += "\n## Warnings\n"
        for issue in scan.issues:
            if issue.severity == Severity.WARNING:
                report += f"- ⚠️ **{issue.dataset_name}**: {issue.message}\n"

        return report

    def close(self):
        """Clean up resources."""
        self.datahub.close()
