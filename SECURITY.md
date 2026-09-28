# Security Policy

## 🔒 Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

---

## 🚨 Reporting a Vulnerability

The Mining Rover software is designed for underground industrial monitoring environments. If you discover a security vulnerability or critical defect that could compromise device integrity, local network isolation, or telemetry authenticity:

1. **Do not disclose the issue publicly** in GitHub issues or discussions.
2. Email the maintainers privately or open a **GitHub Security Advisory** under the `Security` tab.
3. Include:
   - Detailed steps to reproduce the vulnerability.
   - Target environment (OS, Python version, hardware setup).
   - Potential impact and recommended mitigation if known.

We will acknowledge your report within 48 hours and coordinate a fix and advisory release.

---

## 🛡️ Best Security Practices for Deployments

- **Local Network Isolation:** Always isolate the rover's local Wi-Fi / AP network from public access.
- **Environment Variables:** Never commit `.env` files containing production API keys or tokens.
- **Non-Root Execution:** The production systemd unit (`deployment/mining-rover.service`) is configured to run as an unprivileged user (`pi`), not `root`.
