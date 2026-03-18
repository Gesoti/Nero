# Security Policy

## Supported Versions

Only the latest release on the `main` branch receives security updates.

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do not** open a public GitHub issue
2. Use [GitHub Security Advisories](https://github.com/Gesoti/Nero/security/advisories/new) to report privately
3. Include steps to reproduce, affected components, and potential impact

We will acknowledge reports within 7 days and aim to release a fix within 30 days for confirmed vulnerabilities.

## Scope

This project serves publicly available government water data. It does not store user accounts, passwords, or personally identifiable information. The primary security surface is:

- HTTP security headers (CSP, X-Frame-Options, Referrer-Policy)
- Input validation on URL parameters
- SQLite query parameterisation
- Upstream API request handling

## Not in Scope

- Vulnerabilities in upstream government APIs
- Issues requiring physical access to the deployment server
- Social engineering attacks
