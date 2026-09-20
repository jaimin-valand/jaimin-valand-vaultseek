# Security Policy

## Scope

This project is an educational, local-first private search engine. It demonstrates security controls such as API-key authentication, request-size limits, rate limiting, safe tracing, health/readiness endpoints, and non-root container execution.

It is **not** a security-certified production search platform.

## Supported versions

| Version | Status |
|---|---|
| 3.0.x | Supported for project maintenance |
| < 3.0 | Historical |

## Reporting a vulnerability

Please do not disclose exploitable details in a public issue. Use GitHub's private vulnerability reporting for the repository when available. Include reproduction steps, affected component/version, impact, and a minimal proof of concept.

## Security design notes

- API keys are compared using constant-time comparison.
- Request bodies are bounded before application processing.
- Rate limiting is process-local and therefore not a substitute for a distributed gateway.
- Trace events intentionally exclude document bodies and credentials.
- Remote RPC uses bounded timeouts, retries, and circuit breaking.
- Docker runs the application as a non-root user.
- The project does not claim production-grade consensus or distributed security guarantees.
