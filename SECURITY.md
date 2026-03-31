# Security Policy

## Supported Versions

We are currently in the early specification and reference implementation phase. Security updates will be applied to the following versions:

| Version | Supported          |
| ------- | ------------------ |
| v0.1.x  | :white_check_mark: |
| < v0.1  | :x:                |

## Reporting a Vulnerability

The HEXT-AI team takes security and the integrity of the `.hxt` protocol seriously. If you discover a security vulnerability, please do not report it via public GitHub issues. Instead, follow these steps:

1. **Email us**: Send a detailed report to **promo@hextai.com**.
2. **Details**: Include a description of the vulnerability, potential impact, and steps to reproduce (or a sample `.hxt` file that bypasses validation).
3. **Acknowledgment**: We will acknowledge your report within 48 hours and provide a timeline for a fix.

### What to Report
- Flaws in the `human_touch` index calculation that allow spoofing.
- Vulnerabilities in the reference implementations (`hxt.js`, `hxt.py`) such as ReDoS or Buffer Overflows.
- Cryptographic weaknesses in the metadata hashing structure.

## Our Commitment
We will coordinate a fix and credit the researcher in our release notes (unless anonymity is requested). Thank you for helping us keep the "human touch" verifiable and secure.
