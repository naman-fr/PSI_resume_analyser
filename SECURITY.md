# Security Policy

## Supported Versions

Currently, only the latest `v3.x` branch is actively supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| 3.0.x   | :white_check_mark: |
| 2.0.x   | :x:                |
| 1.0.x   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability within this project (such as a prompt injection exploit, a WebRTC bypass, or a JWT leakage), please DO NOT open a public issue.

Instead, please send a private email to the repository administrators. We will verify the vulnerability and issue a patch as quickly as possible.

### Out of Scope
* Rate limiting on the HuggingFace Spaces fallback.
* Expected hallucination rates within the LangGraph constraints (unless it forces a malicious code execution).
