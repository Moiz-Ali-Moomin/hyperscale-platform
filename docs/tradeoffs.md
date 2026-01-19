# Design Tradeoffs & Decisions - HyperScale Platform

This document explains key architectural decisions and their tradeoffs.

---

## 1. Kafka vs. SQS for Event Processing

### Decision: Apache Kafka (MSK)

**Alternatives Considered:**
- Amazon SQS
- Amazon EventBridge
- RabbitMQ

**Why Kafka:**

| Feature | Kafka | SQS | EventBridge |
|---------|-------|-----|-------------|
| Throughput | 150K+ msg/s | 3000 msg/s | 2400 msg/s |
| Ordered Processing | ✅ (per partition) | ❌ (FIFO limited) | ❌ |
| Replay Events | ✅ | ❌ | ❌ |
| Consumer Groups | ✅ | ❌ | ❌ |
| Cost (1M msgs) | $10 | $40 | $100 |

**Tradeoffs:**
- ✅ High throughput
- ✅ Event replay for debugging
- ✅ Multiple consumers on same topic
- ❌ More complex to operate
- ❌ Requires Zookeeper (added dependency)

**Interview Answer:**
> "We chose Kafka over SQS because we need high throughput (100K+ events/second), ordered processing within partitions, and the ability to replay events. Kafka also allows multiple consumer groups to process the same events independently, which is crucial for analytics pipelines."

---

## 2. EKS vs. ECS vs. EC2

### Decision: Amazon EKS (Kubernetes)

**Why EKS:**
- Industry-standard orchestration
- Declarative configuration
- Rich ecosystem (Helm, ArgoCD, Prometheus)
- Portability (can move to on-prem if needed)

**Why not ECS:**
- Vendor lock-in to AWS
- Less mature autoscaling (no VPA)
- Smaller community/ecosystem

**Why not EC2:**
- Manual scaling
- No self-healing
- Higher operational burden

**Tradeoffs:**
- ✅ Powerful autoscaling (HPA + VPA + Cluster Autoscaler)
- ✅ GitOps-friendly (ArgoCD)
- ❌ Steeper learning curve
- ❌ More complex than ECS

**Cost Comparison (monthly):**
- EKS Control Plane: $72
- EC2 Nodes (t3.large × 6): ~$450
- **Total: ~$520**

vs.

- ECS (no control plane cost): $0
- EC2 Nodes (t3.large × 6): ~$450
- **Total: ~$450**

**Verdict:** Worth $70/month for Kubernetes benefits

---

## 3. RDS MySQL vs. DynamoDB

### Decision: RDS MySQL

**Use Case:** Relational data with complex joins

**Why MySQL:**
- ACID transactions
- Complex queries (JOINs)
- Existing SQL knowledge in team

**Why not DynamoDB:**
- No JOINs (denormalization required)
- Query limitations
- Cost unpredictable at scale

**Future Consideration:**
- DynamoDB for high-write workloads (e.g., user sessions)

---

## 4. Multi-AZ vs. Multi-Region

### Decision: Multi-AZ (for now)

**Why Multi-AZ:**
- Automatic failover (30-60s)
- Lower latency (same region)
- Simpler to manage

**Why not Multi-Region:**
- Complex: Data replication, conflict resolution
- Latency: Cross-region writes
- Cost: 2x infrastructure

**Tradeoff:**
- ✅ 99.95% availability (3 AZs)
- ❌ Vulnerable to regional outage
- ❌ No geographic redundancy

**Future State:**
- Multi-region when SLA requires 99.99%+

---

## 5. GitOps (ArgoCD) vs. Push-Based Deployment

### Decision: GitOps with ArgoCD

**Why GitOps:**
- Git is single source of truth
- Automatic drift detection
- Easy rollback (revert Git commit)
- Audit trail built-in

**Why not Jenkins/GitHub Actions push:**
- Manual sync required
- No drift detection
- Credentials in CI system

**Tradeoffs:**
- ✅ Declarative, auditable
- ✅ Self-healing
- ❌ Requires ArgoCD expertise
- ❌ One more system to manage

---

## 6. Monolith vs. Microservices

### Decision: Modular Monolith (pragmatic approach)

**Current State:**
- API Service (monolith)
- Consumer Service (separate)

**Why not full microservices:**
- Team size (< 10 engineers)
- Overhead of managing 20+ services
- Network latency between services

**Why modular monolith:**
- Easier to develop and test
- Can extract microservices later
- Lower operational complexity

**Future:**
- Extract auth, payments as microservices when team grows

---

## 7. Helm vs. Kustomize

### Decision: Helm

**Why Helm:**
- Templating with values
- Chart versioning
- Mature ecosystem

**Why not Kustomize:**
- Less flexible
- No versioning

---

## 8. Prometheus vs. CloudWatch

### Decision: Prometheus + CloudWatch

**Why both:**
- **Prometheus:** Application metrics, Kafka lag, custom metrics
- **CloudWatch:** AWS service metrics (RDS, ALB, EKS)

**Why not CloudWatch only:**
- Expensive at scale
- Limited custom metrics

**Why not Prometheus only:**
- No native AWS integration

---

## 9. Redis Cluster vs. Single-Node Redis

### Decision: Redis Cluster

**Why Cluster:**
- Horizontal scaling (3 shards)
- High availability (2 replicas per shard)

**Tradeoff:**
- ✅ Scales to 250K ops/s
- ❌ Certain commands not supported (MGET across shards)
- ❌ More expensive

**Cost:**
- Cluster (cache.r7g.large × 9 nodes): ~$1200/month
- Single (cache.r7g.large × 1): ~$130/month

**Verdict:** Worth it for scale and HA

---

## 10. Synchronous vs. Asynchronous Processing

### Decision: Hybrid

**Synchronous (via API):**
- User login
- Read product details

**Asynchronous (via Kafka):**
- Send email
- Update analytics
- Process purchases
- Generate reports

**Why Hybrid:**
- Fast user response for reads
- Offload heavy processing to background

**Tradeoff:**
- ✅ Better user experience
- ✅ System resilience (Kafka buffers spikes)
- ❌ Eventual consistency
- ❌ More complex debugging

---

## 11. Automated vs. Manual Scaling

### Decision: Automated (HPA + VPA + Cluster Autoscaler)

**Why Automated:**
- Handles unpredictable traffic
- Cost-efficient (scale down when idle)
- Reduces manual intervention

**Tradeoffs:**
- ✅ Responds to spikes within 30-60s
- ❌ Can over-scale (costs)
- ❌ Requires tuning (thresholds)

---

## 12. Blue/Green vs. Rolling vs. Canary Deployment

### Decision: Rolling Update

**Why Rolling:**
- Zero downtime
- Gradual rollout
- Built into Kubernetes

**Configuration:**
```yaml
maxUnavailable: 0  # Always have at least 100% capacity
maxSurge: 1        # Can go up to 133% during deployment
```

**Why not Blue/Green:**
- Doubles infrastructure cost during deployment

**Why not Canary:**
- Adds complexity (traffic splitting)
- Overkill for current scale

**Future:** Canary with Flagger when we reach 10M+ users

---

## Summary of Key Decisions

| Decision | Chosen | Rationale |
|----------|--------|-----------|
| Messaging | Kafka | Throughput + replay |
| Orchestration | EKS | Portability + ecosystem |
| Database | RDS MySQL | Relational data + ACID |
| Availability | Multi-AZ | Balance cost & HA |
| Deployment | GitOps | Auditability + drift detection |
| Architecture | Modular Monolith | Team size + simplicity |
| Metrics | Prometheus + CloudWatch | Best of both |
| Caching | Redis Cluster | Scale + HA |
| Processing | Hybrid (sync/async) | UX + resilience |
| Scaling | Automated | Handles unpredictable load |

---

## Interview Talking Points

**On Kafka:**
> "We chose Kafka over SQS because we process 100K+ events per second. Kafka gives us ordered processing, event replay for debugging, and multiple consumer groups. The trade-off is operational complexity, but MSK handles most of that."

**On Kubernetes:**
> "EKS costs $70/month more than ECS, but we get industry-standard orchestration, GitOps with ArgoCD, advanced autoscaling with HPA and VPA, and portability. It's worth the trade-off."

**On Multi-AZ vs. Multi-Region:**
> "Right now, Multi-AZ gives us 99.95% availability with automatic failover in under a minute. Multi-region would double our infrastructure cost and add data replication complexity. We'll move to multi-region when SLA requirements justify it."

**On Async Processing:**
> "We use Kafka for async processing so user-facing requests stay fast. Heavy operations like sending emails, updating analytics, and generating reports happen in the background. Kafka buffers traffic spikes so consumers can process at a sustainable rate without overwhelming the database."
