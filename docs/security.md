# Security Best Practices - HyperScale Platform

This document outlines security measures implemented across the platform.

---

## 1. Network Security

### VPC Design

**Private Subnets:**
- All application pods run in private subnets
- No direct internet access
- NAT Gateway for outbound traffic only

**Public Subnets:**
- ALB only
- Minimal attack surface

**Security Groups:**
```
ALB → Port 443 (HTTPS) → From: 0.0.0.0/0
ALB → API Pods → Port 8000 → From: ALB SG only
API Pods → RDS → Port 3306 → From: EKS SG only
API Pods → Redis → Port 6379 → From: EKS SG only
API Pods → Kafka → Port 9092, 9094 → From: EKS SG only
```

**Network Policies (Kubernetes):**
```yaml
# API can only talk to DB, Redis, Kafka
# Consumer can only talk to Kafka, DB
# No pod-to-pod communication except via services
```

---

## 2. Identity & Access Management

### IAM Roles for Service Accounts (IRSA)

**Problem:** Pods shouldn't share AWS credentials

**Solution:**
- Each pod gets its own AWS IAM role
- Temporary credentials via OIDC
- Scoped to minimum required permissions

**Example:**
```yaml
serviceAccount:
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT:role/api-s3-access
```

**Permissions:**
- API pods: S3 read/write to specific buckets
- Consumer pods: CloudWatch Logs write-only
- No pods have EC2 or IAM permissions

---

## 3. Secrets Management

### Kubernetes Secrets

**Storage:**
- Encrypted at rest with AWS KMS
- EKS encryption config uses dedicated KMS key

**Access Control:**
- RBAC limits who can read secrets
- ServiceAccounts can only access their own secrets

### AWS Secrets Manager

**Database Credentials:**
- Stored in AWS Secrets Manager
- Rotated automatically every 30 days
- Accessed via IRSA (no hardcoded credentials)

**Example:**
```python
client = boto3.client('secretsmanager')
response = client.get_secret_value(SecretId='hyperscale/rds/password')
db_password = json.loads(response['SecretString'])['password']
```

---

## 4. Data Encryption

### At Rest

| Component | Encryption |
|-----------|----------|
| RDS MySQL | KMS encryption enabled |
| Redis ElastiCache | At-rest encryption enabled |
| MSK Kafka | KMS encryption enabled |
| EBS Volumes | Encrypted by default |
| S3 Buckets | SSE-S3 or SSE-KMS |

### In Transit

| Connection | Encryption |
|------------|-----------|
| User → CloudFront | HTTPS (TLS 1.2+) |
| CloudFront → ALB | HTTPS |
| ALB → Pods | HTTP (private network) |
| Pods → RDS | TLS enforced |
| Pods → Redis | TLS enabled |
| Pods → Kafka | TLS (port 9094) |

---

## 5. Container Security

### Image Scanning

**Trivy (CI Pipeline):**
```yaml
- name: Scan image
  run: trivy image --severity HIGH,CRITICAL myimage:latest
  # Fails build if critical vulnerabilities found
```

**ECR Image Scanning:**
- Automatic scan on push
- Continuous monitoring

### Dockerfile Best Practices

✅ Non-root user  
✅ Read-only root filesystem  
✅ Drop all capabilities  
✅ Multi-stage builds (smaller attack surface)  

```dockerfile
USER appuser  # Non-root
RUN chown appuser:appuser /app

securityContext:
  runAsNonRoot: true
  runAsUser: 1001
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
```

---

## 6. Authentication & Authorization

### API Authentication

**JWT Tokens:**
- Signed with RS256 (asymmetric)
- Short expiration (15 minutes)
- Refresh tokens (7 days)

**Validation:**
```python
token = jwt.decode(
    token_string,
    public_key,
    algorithms=['RS256'],
    audience='api.hyperscale.com'
)
```

### Kubernetes RBAC

**Principle of Least Privilege:**
- Developers: Read-only access to production
- CI/CD: Can update deployments only
- Admins: Full access with audit logging

**Example:**
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind:Role
metadata:
  name: developer-readonly
rules:
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["get", "list", "watch"]
```

---

## 7. Application Security

### Input Validation

**SQL Injection Prevention:**
```python
# Use parameterized queries
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

**XSS Prevention:**
- Escape all user input
- Content Security Policy (CSP) headers

### Rate Limiting

**ALB Level:**
- WAF rate limiting: 2000 req/5min per IP

**Application Level:**
```python
@limiter.limit("100 per minute")
def api_endpoint():
    ...
```

---

## 8. Logging & Auditing

### CloudTrail

**Enabled for:**
- IAM actions
- S3 bucket access
- EKS API calls
- Database modifications

**Retention:** 90 days in S3

### Application Logs

**Centralized Logging (Loki):**
- All pod logs aggregated
- Parsed and indexed
- Retention: 7 days

**Audit Events:**
```json
{
  "timestamp": "2024-01-20T10:30:00Z",
  "user_id": "user123",
  "action": "UPDATE",
  "resource": "user_profile",
  "ip": "203.0.113.45",
  "status": "success"
}
```

---

## 9. Security Monitoring

### Vulnerability Scanning

**Automated Scans:**
- Docker images (Trivy) - Every build
- Dependencies (Safety, Snyk) - Daily
- Infrastructure (tfsec) - Every PR

### Intrusion Detection

**GuardDuty:** Enabled for threat detection

**Alerts:**
- Unusual API activity
- Compromised instance behavior
- Unauthorized access attempts

---

## 10. Incident Response

### Security Incident Runbook

**1. Detection:**
- Automated alerts (GuardDuty, WAF)
- Manual report

**2. Containment:**
- Isolate affected pods/nodes
- Revoke compromised credentials
- Block malicious IPs in WAF

**3. Investigation:**
- Analyze logs (CloudTrail, application logs)
- Identify root cause

**4. Remediation:**
- Patch vulnerability
- Rotate affected credentials
- Deploy fix

**5. Post-Mortem:**
- Document timeline
- Update runbooks
- Implement preventive measures

---

## 11. Compliance & Standards

### Industry Standards

✅ **OWASP Top 10** — Addressed  
✅ **CIS Benchmarks** — Kubernetes hardening  
✅ **SOC 2** — Audit logging, encryption  
✅ **PCI DSS** — Encryption, access control  

### Regular Audits

- Quarterly penetration testing
- Annual security audit
- Continuous compliance monitoring

---

## Security Checklist

### Infrastructure
- [x] VPC with private subnets
- [x] Security groups with minimal permissions
- [x] Network policies in Kubernetes
- [x] Encryption at rest (RDS, Redis, Kafka, EBS)
- [x] Encryption in transit (TLS everywhere)

### Access Control
- [x] IRSA for pod-level AWS permissions
- [x] Kubernetes RBAC
- [x] Secrets encrypted with KMS
- [x] Automatic credential rotation

### Application
- [x] Non-root containers
- [x] Read-only root filesystem
- [x] Input validation
- [x] Rate limiting
- [x] JWT authentication

### Monitoring
- [x] CloudTrail enabled
- [x] Centralized logging
- [x] Security scanning in CI/CD
- [x] GuardDuty threat detection

---

## Key Takeaways

✅ Defense in depth: Multiple security layers  
✅ Zero trust: Every component authenticated  
✅ Least privilege: Minimum required permissions  
✅ Encryption everywhere: At rest and in transit  
✅ Continuous monitoring: Automated threat detection  

**Interview Line:**
> "Security is built into every layer. We use IRSA for pod-level AWS permissions, encrypt everything at rest and in transit, run containers as non-root with read-only filesystems, and scan every image in the CI pipeline. Network policies restrict pod-to-pod traffic, and all access is logged and audited."
