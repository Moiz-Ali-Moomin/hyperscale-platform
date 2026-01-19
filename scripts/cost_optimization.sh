#!/bin/bash
# AWS Cost Optimization Script
# Identifies cost-saving opportunities

set -e

AWS_REGION="${AWS_REGION:-us-east-1}"
OUTPUT_FILE="cost-optimization-report.txt"

echo "=========================================" | tee "$OUTPUT_FILE"
echo "AWS Cost Optimization Analysis" | tee -a "$OUTPUT_FILE"
echo "Generated: $(date)" | tee -a "$OUTPUT_FILE"
echo "=========================================" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

# 1. Unused EBS Volumes
echo "1. Unused EBS Volumes" | tee -a "$OUTPUT_FILE"
echo "----------------------------------------" | tee -a "$OUTPUT_FILE"

unused_volumes=$(aws ec2 describe-volumes \
    --region "$AWS_REGION" \
    --filters Name=status,Values=available \
    --query 'Volumes[*].[VolumeId,Size,VolumeType]' \
    --output text)

if [ -n "$unused_volumes" ]; then
    echo "$unused_volumes" | while read vol_id size vol_type; do
        cost_per_month=$(echo "scale=2; $size * 0.10" | bc)  # Approximate cost
        echo "  Volume: $vol_id | Size: ${size}GB | Type: $vol_type | Est. Cost: \$${cost_per_month}/month" | tee -a "$OUTPUT_FILE"
    done
else
    echo "  No unused volumes found" | tee -a "$OUTPUT_FILE"
fi

echo "" | tee -a "$OUTPUT_FILE"

# 2. Unattached Elastic IPs
echo "2. Unattached Elastic IPs" | tee -a "$OUTPUT_FILE"
echo "----------------------------------------" | tee -a "$OUTPUT_FILE"

unattached_eips=$(aws ec2 describe-addresses \
    --region "$AWS_REGION" \
    --query 'Addresses[?AssociationId==`null`].[PublicIp,AllocationId]' \
    --output text)

if [ -n "$unattached_eips" ]; then
    count=$(echo "$unattached_eips" | wc -l)
    cost_per_month=$(echo "scale=2; $count * 3.60" | bc)  # $0.005/hour
    echo "  Found $count unattached EIPs" | tee -a "$OUTPUT_FILE"
    echo "  Estimated waste: \$${cost_per_month}/month" | tee -a "$OUTPUT_FILE"
    echo "$unattached_eips" | tee -a "$OUTPUT_FILE"
else
    echo "  No unattached EIPs found" | tee -a "$OUTPUT_FILE"
fi

echo "" | tee -a "$OUTPUT_FILE"

# 3. Old EBS Snapshots
echo "3. Old EBS Snapshots (>90 days)" | tee -a "$OUTPUT_FILE"
echo "----------------------------------------" | tee -a "$OUTPUT_FILE"

ninety_days_ago=$(date -d '90 days ago' +%Y-%m-%d)

old_snapshots=$(aws ec2 describe-snapshots \
    --region "$AWS_REGION" \
    --owner-ids self \
    --query "Snapshots[?StartTime<\`${ninety_days_ago}\`].[SnapshotId,VolumeSize,StartTime]" \
    --output text)

if [ -n "$old_snapshots" ]; then
    total_size=0
    while read snap_id size start_time; do
        total_size=$((total_size + size))
        echo "  Snapshot: $snap_id | ${size}GB | Created: $start_time" | tee -a "$OUTPUT_FILE"
    done <<< "$old_snapshots"
    
    cost_per_month=$(echo "scale=2; $total_size * 0.05" | bc)
    echo "  Total size: ${total_size}GB" | tee -a "$OUTPUT_FILE"
    echo "  Estimated cost: \$${cost_per_month}/month" | tee -a "$OUTPUT_FILE"
else
    echo "  No old snapshots found" | tee -a "$OUTPUT_FILE"
fi

echo "" | tee -a "$OUTPUT_FILE"

# 4. Underutilized RDS Instances
echo "4. Potentially Underutilized RDS Instances" | tee -a "$OUTPUT_FILE"
echo "----------------------------------------" | tee -a "$OUTPUT_FILE"

rds_instances=$(aws rds describe-db-instances \
    --region "$AWS_REGION" \
    --query 'DBInstances[*].[DBInstanceIdentifier,DBInstanceClass,Engine]' \
    --output text)

if [ -n "$rds_instances" ]; then
    echo "$rds_instances" | while read db_id instance_class engine; do
        echo "  Instance: $db_id | Class: $instance_class | Engine: $engine" | tee -a "$OUTPUT_FILE"
        echo "    Recommendation: Check CloudWatch metrics for CPU < 20%" | tee -a "$OUTPUT_FILE"
    done
else
    echo "  No RDS instances found" | tee -a "$OUTPUT_FILE"
fi

echo "" | tee -a "$OUTPUT_FILE"

# 5. Idle Load Balancers
echo "5. Idle Application Load Balancers" | tee -a "$OUTPUT_FILE"
echo "----------------------------------------" | tee -a "$OUTPUT_FILE"

albs=$(aws elbv2 describe-load-balancers \
    --region "$AWS_REGION" \
    --query 'LoadBalancers[?Type==`application`].[LoadBalancerName,LoadBalancerArn]' \
    --output text)

if [ -n "$albs" ]; then
    while read alb_name alb_arn; do
        target_groups=$(aws elbv2 describe-target-groups \
            --load-balancer-arn "$alb_arn" \
            --region "$AWS_REGION" \
            --query 'length(TargetGroups)')
        
        if [ "$target_groups" -eq 0 ]; then
            echo "  ALB: $alb_name (No target groups attached)" | tee -a "$OUTPUT_FILE"
            echo "    Estimated cost: \$22.50/month" | tee -a "$OUTPUT_FILE"
        fi
    done <<< "$albs"
else
    echo "  No ALBs found" | tee -a "$OUTPUT_FILE"
fi

echo "" | tee -a "$OUTPUT_FILE"
echo "=========================================" | tee -a "$OUTPUT_FILE"
echo "Report saved to: $OUTPUT_FILE" | tee -a "$OUTPUT_FILE"
echo "=========================================" | tee -a "$OUTPUT_FILE"
