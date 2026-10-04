from .models import Report

ICON = {"CRITICAL": "🔴", "MAJOR": "🟠", "MINOR": "🟡", "INFO": "🔵"}


def to_markdown(report: Report, max_details: int = 15) -> str:
    out = [f"## 🤖 Autonomous Code Review: `{report.target}`", ""]
    if report.simulated:
        out += ["> ⚠️ **DEMO MODE: sample code and simulated results, not a real review.**", ""]
    out += [f"**Score: {report.score}/100**: {report.verdict}", "", report.summary, ""]
    if report.issues:
        out += ["| Severity | Category | Location | Issue |", "|---|---|---|---|"]
        for i in report.issues[:100]:
            out.append(f"| {ICON.get(i.severity, '')} {i.severity} | {i.category} | `{i.file}:{i.line}` | "
                       f"{i.message.replace('|', '/')} |")
        out += ["", "### Details and suggested fixes", ""]
        for i in report.issues[:max_details]:
            out += [f"**{ICON.get(i.severity, '')} {i.message}** (`{i.file}:{i.line}`, rule `{i.rule}`, "
                    f"{'AI' if i.ai_generated else i.source})", "", i.explanation, "",
                    "```", i.suggested_fix, "```", ""]
        if len(report.issues) > max_details:
            out.append(f"_...and {len(report.issues) - max_details} more issues in the full report._")
    for n in report.notes:
        out.append(f"\n_Note: {n}_")
    return "\n".join(out)
