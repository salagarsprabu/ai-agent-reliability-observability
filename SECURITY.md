# Security notes

This is a learning reference implementation, not a production banking system.

- Do not use real customer data.
- Replace the development salt and database credentials.
- Add authentication, authorization, TLS/mTLS and network policies before any shared deployment.
- Encrypt replay artifacts and use managed key services in real environments.
- Apply data classification, purpose limitation, retention and deletion controls.
- Review all OTel attributes before export. Collector redaction is defense in depth, not the only control.
