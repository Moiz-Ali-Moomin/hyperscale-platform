# Scaling Strategies - HyperScale Platform

This document explains how the platform scales from **100K to 1M+ users** and handles traffic spikes.

---

## Multi-Layer Scaling Architecture

### Layer 1: Edge & CDN (CloudFront)

**Problem:** Users worldwide accessing static and dynamic content

**Solution:**
- CloudFront distributes content from 400+ edge locations
- Caches static assets (images, CSS, JS) for 7-30 days
- Caches API responses (where applicable) for 5-60 minutes
- Reduces origin load by 70-80%

**Impact:**
- Latency reduced from 200ms+ to 20-50ms for static content
- Backend receives only 20-30% of total traffic

### Layer 2: Application Load Balancer

**Problem:** Distributing traffic across multiple availability zones

**Solution:**
- Cross-zone load balancing enabled
- Connection draining for graceful shutdowns
- Health checks every 10 seconds
- Sticky sessions for stateful workloads

**Scaling Trigger:**
- ALB automatically scales based on traffic

**Impact:**
- Handles 1M+ requests per minute
- Zero downtime deployments

### Layer 3: Kubernetes Autoscaling

#### Horizontal Pod Autoscaler (HPA)

**Metrics:**
- CPU utilization > 70%
- Memory utilization > 80%
- Custom metric: requests/second > 1000

**Behavior:**
- **Scale Up:** Add 50% of current pods or 5 pods (whichever is higher) every 30 seconds
- **Scale Down:** Remove 25% or 2 pods every 5 minutes

**Configuration:**
```yaml
minReplicas: 3
maxReplicas: 20
```

**Scaling Math:**
- Normal load: 3 pods @ 1000 req/s each = 3000 req/s
- Peak load: 20 pods @ 1000 req/s each = 20,000 req/s
- **Capacity: 6.7x increase**

#### Vertical Pod Autoscaler (VPA)

**Purpose:** Right-size resource requests/limits

**Metrics:**
- Historical CPU/memory usage
- 95th percentile resource consumption

**Impact:**
- Reduces over-provisioning by 30-40%
- Prevents OOMKilled errors

#### Cluster Autoscaler

**Trigger:** Pods pending due to insufficient resources

**Behavior:**
- Adds EC2 nodes within 2-3 minutes
- Removes idle nodes after 10 minutes

**Configuration:**
- Min nodes: 2 per AZ (6 total across 3 AZs)
- Max nodes: 20 per AZ (60 total)

### Layer 4: Event Buffering (Kafka)

**Problem:** Traffic spikes overwhelm backend processing

**Solution:**
- Kafka absorbs bursts up to 100K events/second
- Consumers process at sustainable rate
- Prevents database overload

**Architecture:**
```
API Pods (synchronous)
   ↓ (publish to Kafka)
Kafka Topics (buffer)
   ↓ (consume async)
Consumer Pods (process at controlled rate)
   ↓
Database (protected from spikes)
```

**Scaling:**
- Topic partitions: 12 (allows 12 parallel consumers)
- Consumer replicas: 5-15 (auto-scaled)
- Throughput: 150K events/second

### Layer 5: Database Layer

#### Read Replicas

**Problem:** Heavy read load on primary database

**Solution:**
- 1 primary + 2 read replicas
- Read-heavy queries go to replicas
- Writes go to primary only

**Traffic Split:**
- 90% reads → replicas
- 10% writes → primary

**Impact:**
- 3x read capacity
- Primary handles only writes

#### Connection Pooling

**Problem:** Too many database connections

**Configuration:**
```
max_connections = 1000
connection_pool_size = 50 per pod
max_pods = 20
Total connections = 1000 (within limit)
```

#### Caching Layer (Redis)

**Problem:** Same data queried repeatedly

**Solution:**
- Redis Cluster (3 shards, 2 replicas each)
- Cache-aside pattern
- TTL: 5-60 minutes based on data type

**Cache Hit Ratio:**
- Target: 80%+
- Database load reduction: 80%

---

## Traffic Spike Scenario: Marketing Campaign

### Scenario
Black Friday sale announced via email to 1M users

**Normal Load:**
- 1,000 requests/second
- 3 pods
- 50% CPU

**Spike Load:**
- 10,000 requests/second (10x increase)
- Duration: 2 hours

### Response Timeline

**T+0 seconds:** Traffic spike begins

**T+30 seconds:**
- HPA detects CPU > 70%
- Adds 5 new pods (3 → 8)

**T+60 seconds:**
- Still high CPU
- Adds 4 more pods (8 → 12)

**T+90 seconds:**
- CPU stabilizes at 65%
- 12 pods handle load

**T+2 minutes:**
- Cluster Autoscaler adds 3 new nodes for pending pods

**T+2 hours:** Traffic returns to normal

**T+2 hours 5 minutes:**
- HPA scales down to 6 pods

**T+2 hours 15 minutes:**
- HPA scales down to 3 pods

**T+2 hours 25 minutes:**
- Cluster Autoscaler removes idle nodes

---

## Scaling Limits & Bottlenecks

### Current Limits

| Component | Limit | Bottleneck |
|-----------|-------|------------|
| ALB | 1M req/min | AWS account limit |
| Kubernetes Pods | 200 | EKS quota |
| Database | 1000 connections | RDS limit |
| Kafka | 150K events/s | Broker I/O |
| Redis | 250K ops/s | Network bandwidth |

### Future Scaling (1M → 10M users)

**Required Changes:**
1. **Database Sharding** — Horizontal partition by user ID
2. **Multi-Region** — Deploy to us-east-1, us-west-2, eu-west-1
3. **Read-through Cache** — Redis → DynamoDB for cold data
4. **Kafka Expansion** — 3 → 6 brokers, 12 → 24 partitions

---

## Cost vs. Scale

| Users | Monthly Cost | Per-User Cost |
|-------|--------------|---------------|
| 100K | $5,000 | $0.05 |
| 500K | $15,000 | $0.03 |
| 1M | $25,000 | $0.025 |
| 10M | $150,000 | $0.015 |

**Cost Optimization:**
- Spot instances for non-critical workloads (40% savings)
- Reserved instances for baseline capacity (50% savings)
- CloudFront reduces backend costs by 70%

---

## Key Takeaways

✅ Kafka decouples user traffic from backend processing  
✅ Multi-layer autoscaling handles 10x spikes gracefully  
✅ Redis caching reduces database load by 80%  
✅ Read replicas distribute read-heavy queries  
✅ CloudFront reduces origin traffic by 70%  

**Interview Line:**
> "The platform scales horizontally at every layer—CDN, load balancers, pods, Kafka consumers, and database replicas. Kafka is key—it buffers traffic spikes so the backend can scale gradually without overwhelming the database."
