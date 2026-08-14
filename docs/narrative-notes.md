# Narrative Notes

- Good use of handling financial data types
- unable to test resource utilisation
- triage is done as a parallel activity to rebuild
- most variable names ok despite dramatic rule violations
- LLM created a bunk smoke test
- Consistant within its own ruleset
- Self-documenting code "the code describes what it does" despite no external context. New people would require something to bridge the gap

## Unverifiable

- CA-REQ-019|FCA & SOX compliance|Data is backed up and secure from tampering and loss|''
- CA-REQ-020|FCA & SOX compliance|Data is stored on sovereign territories within the same regulatory environment as the bank|''
- CA-REQ-021|FCA & SOX compliance|Security breach events are recorded and reported to SOX auditors|''
- CA-REQ-023|ISO/IEC27001 Compliance|The application passes an audit by a dedicated audit team|''
- CA-REQ-025|ISO/IEC27001 Compliance|All system and data locations are documented|''

## Scans

- safety
- pip-audit
- sast
- bandit
- semgrep

Affected packages: python-jose, cryptography, python-multipart, pytest

## Findings

- 71 issues

Severity|Count
---|---
1|5
2|17
3|7
4|8
5|11
6|7
7|17
