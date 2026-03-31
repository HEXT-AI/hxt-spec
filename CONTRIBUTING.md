# Contributing to HEXT Protocol

Thank you for your interest in the HEXT protocol! We are dedicated to building an open standard for AI-aware Markdown documents to restore digital trust.

## Our Philosophy
We value **integrity, verifiability, and transparency**. Every contribution should aim to strengthen the bond between human intent and digital representation.

## How Can You Help?

### 1. Porting the Validator
We currently have reference implementations in:
- **JavaScript (Node.js)**
- **Python**

We are actively looking for contributors to port the `.hxt` validator to:
- **Rust** (for high-performance edge computing)
- **Go** (for cloud-native services)
- **Ruby, PHP, Swift, and more.**

### 2. Tooling and Plugins
Help us integrate HEXT into the creator workflow:
- VS Code Extensions (Syntax highlighting for `.hxt`)
- Obsidian / Logseq Plugins
- Hugo / Jekyll / Next.js static site generator integration

### 3. Edge Cases and Security
As a protocol built on hashes and metadata, security is paramount.
- Report any vulnerabilities in the hashing logic.
- Provide `examples/invalid.hxt` cases that challenge the current spec.

## Development Process

1. **Fork the Repository**: Create your own copy of `hxt-spec`.
2. **Create a Feature Branch**: `git checkout -b feat/your-feature-name`.
3. **Write Tests**: Ensure your changes don't break the core `.hxt` validation logic.
4. **Submit a Pull Request (PR)**: Describe your changes clearly and link to any related issues.

## Reporting Bugs
Please use [GitHub Issues](https://github.com/HEXT-AI/hxt-spec/issues) to report bugs. Include:
- Your environment (OS, Language version)
- A sample `.hxt` file that causes the issue.

---
*By contributing, you agree that your contributions will be licensed under the **MIT License**.*
