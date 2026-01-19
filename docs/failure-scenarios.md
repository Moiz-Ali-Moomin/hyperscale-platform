# Failure Scenarios & Recovery - HyperScale Platform

This document outlines failure modes, detection, and recovery strategies.

---

## 1. Pod Failures

### Scenario: Pod Crash Loop

**Cause:**
- Application bug
- Out of memory
- Misconfiguration

**Detection:**
- Kubernetes detects restart loop
- Prometheus alert: `PodCrashLooping`

**Recovery:**
1. **Automatic:** Kubernetes restarts pod (backoff: 10s, 20s, 40s, 80s...)
2. **Manual:** If crash persists:
   ```bash
   kubectl logs -f pod-name -n production --previous
   kubectl describe pod pod-name -n production
   ```
3. **Rollback:** Deploy previous stable version via ArgoCD

**Prevention:**
- Resource requests/limits prevent OOM
- Liveness probes detect hung processes
- Readiness probes prevent bad pods from receiving traffic

**Impact:**
- **With PDB:** Minimum 2 healthy pods always available
- **User Impact:** None (traffic routed to healthy pods)

---

## 2. Node Failures

### Scenario: EC2 Node Becomes Unavailable

**Cause:**
- Hardware failure
- Network partition
- AWS maintenance

**Detection:**
- Node status: NotReady (after 40 seconds)
- Prometheus alert: `NodeNotReady`

**Recovery Timeline:**

**T+0:** Node goes down

**T+40s:** Kubernetes marks node as NotReady

**T+5m:** Pods marked for eviction

**T+6m:** Pods scheduled on healthy nodes

**T+7m:** New pods running and healthy

**Impact:**
- **Multi-AZ deployment:** Pods spread across 3 AZs
- **User Impact:** None (traffic shifts to other AZs)

**Prevention:**
- Anti-affinity rules spread pods across zones
- PDB ensures minimum availability during eviction

---

## 3. Database Failures

### Scenario A: Primary RDS Instance Failure

**Cause:**
- Hardware failure
- Storage corruption

**Detection:**
- Database connection failures
- CloudWatch alarm: `DBInstanceDown`

**Automatic Recovery:**
- RDS Multi-AZ failover to standby (30-60 seconds)
- DNS automatically points to new primary

**Application Resilience:**
```python
# Exponential backoff retry
@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=30))
def connect_to_db():
    return db.connect()
```

**Impact:**
- **Downtime:** 30-60 seconds
- **Data Loss:** None (synchronous replication to standby)

---

### Scenario B: Read Replica Failure

**Detection:**
- Connection errors to replica endpoint
- Application switches to primary

**Recovery:**
- Manual: Create new read replica

**Impact:**
- **Load:** Temporarily shifts to remaining replica + primary
- **Performance:** Slight latency increase until replica restored

---

## 4. Kafka Broker Failures

### Scenario: 1 of 3 Kafka Brokers Down

**Cause:**
- Node failure
- Disk full

**Detection:**
- Broker offline
- `kafka_broker_count < 3`

**Automatic Recovery:**
- ISR (In-Sync Replicas) = 2 (still meets min.insync.replicas)
- Leader election for affected partitions (< 1 second)
- No data loss (replication factor = 3)

**Impact:**
- **Throughput:** 33% reduction (2 of 3 brokers)
- **Availability:** No downtime (automatic failover)

**Manual Action:**
1. Identify failed broker
2. Replace broker
3. Wait for data rebalancing

---

## 5. Redis Cluster Failure

### Scenario: Redis Shard Failure

**Cause:**
- Memory exhaustion
- Network partition

**Detection:**
- Cache miss rate > 50%
- `redis_up == 0`

**Automatic Recovery:**
- Replica promoted to primary (automatic)

**Application Behavior:**
- Cache-aside pattern: Falls back to database
- Temporarily higher database load

**Impact:**
- **Performance:** Queries slower (50ms → 200ms)
- **Availability:** No downtime (database still available)

---

## 6. Networking Failures

### Scenario: AZ Isolation

**Cause:**
- AWS network partition between AZs

**Detection:**
- Increased cross-AZ traffic errors
- Health check failures in affected AZ

**Recovery:**
- ALB stops routing to unhealthy AZ
- Pods in healthy AZs handle traffic

**Impact:**
- **Capacity:** 33% reduction (1 of 3 AZs)
- **Availability:** Service continues in 2 AZs

**Prevention:**
- Over-provision by 50% to handle AZ loss

---

## 7. Deployment Failures

### Scenario: Bad Deployment (Rollout)

**Cause:**
- Bug in new version
- Configuration error

**Detection:**
- Increased error rate (5XX responses)
- Failed readiness probes

**Automatic Rollback:**
```yaml
strategy:
  rollingUpdate:
    maxUnavailable: 0  # Zero-downtime
    maxSurge: 1
```

**Kubernetes Behavior:**
- Stops rollout if new pods don't become ready
- Old pods remain running

**Manual Rollback:**
```bash
kubectl rollout undo deployment/api-service -n production
```

**ArgoCD Auto-Sync:**
- Detects drift from Git
- Auto-reverts if sync policy enabled

---

## 8. Kafka Consumer Lag Spike

### Scenario: Consumer Can't Keep Up

**Cause:**
- Traffic spike exceeding consumer capacity
- Slow database writes

**Detection:**
- `kafka_consumer_lag > 50,000`
- Alert: `CriticalConsumerLag`

**Recovery:**
1. **Automatic:** HPA scales consumers (5 → 15 pods)
2. **Manual:** Increase partition count (requires coordination)

**Prevention:**
- Monitor lag continuously
- Tune `max.poll.records` and `session.timeout.ms`

---

## 9. Complete Region Failure

### Scenario: AWS us-east-1 Complete Outage

**Current State:** Single-region deployment

**Impact:**
- **Availability:** Total outage
- **RTO:** 4-6 hours (manual failover to new region)
- **RPO:** < 15 minutes (database backups)

**Future State:** Multi-region active-active

**Recovery:**
1. Deploy infrastructure to us-west-2 via Terraform
2. Restore database from automated snapshot
3. Update DNS to point to new region
4. Redeploy application via ArgoCD

---

## 10. DDoS Attack

### Scenario: Malicious Traffic Spike

**Detection:**
- Abnormal traffic pattern
- WAF detects attack signature

**Mitigation:**
1. **CloudFront:** Built-in DDoS protection
2. **WAF:** Rate limiting rules
3. **ALB:** Connection limits
4. **Application:** Rate limiting middleware

---

## Recovery Metrics (SLOs)

| Failure Type | Detection Time | Recovery Time | Data Loss |
|-------------|----------------|---------------|-----------|
| Pod Crash | < 10s | 30s | None |
| Node Failure | 40s | 6m | None |
| DB Primary Failover | 10s | 60s | None |
| Kafka Broker Down | < 5s | < 1s | None |
| Redis Shard Down | < 10s | < 5s | None |
| AZ Outage | 30s | 2m | None |
| Bad Deployment | 60s | 5m | None |

---

## Runbooks

Each failure scenario has a runbook in `/runbooks/` directory:

- `runbook-pod-crash.md`
- `runbook-db-failover.md`
- `runbook-kafka-lag.md`
- `runbook-rollback.md`

---

## Key Takeaways

✅ Multi-AZ deployment prevents single-AZ failures  
✅ Database Multi-AZ failover is automatic (30-60s)  
✅ Kafka replication prevents data loss  
✅ Rolling updates with zero downtime  
✅ PDB ensures minimum pods available during disruptions  

**Interview Line:**
> "We design for failure at every layer. Multi-AZ deployment, database failover, Kafka replication, and pod anti-affinity ensure that no single failure takes down the system. PodDisruptionBudget ensures we always have minimum healthy pods even during voluntary disruptions like node drains."
