#!/bin/bash
# Docker Image Cleanup Script
# Removes old and unused Docker images from registry

set -e

# Configuration
ECR_REGION="us-east-1"
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${ECR_REGION}.amazonaws.com"
REPOSITORIES=("hyperscale/api-service" "hyperscale/consumer-service")
KEEP_COUNT=10  # Keep last N images
DRY_RUN=false

echo "========================================="
echo "Docker Image Cleanup Tool"
echo "========================================="
echo ""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --keep)
            KEEP_COUNT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

if [ "$DRY_RUN" = true ]; then
    echo "DRY RUN MODE - No images will be deleted"
    echo ""
fi

# Authenticate with ECR
echo "Authenticating with ECR..."
aws ecr get-login-password --region "$ECR_REGION" | \
    docker login --username AWS --password-stdin "$ECR_REGISTRY"

total_deleted=0
total_size_saved=0

# Process each repository
for repo in "${REPOSITORIES[@]}"; do
    echo ""
    echo "Processing repository: $repo"
    echo "----------------------------------------"
    
    # Get all images sorted by push date
    images=$(aws ecr describe-images \
        --repository-name "$repo" \
        --region "$ECR_REGION" \
        --query 'sort_by(imageDetails,& imagePushedAt)[*].[imageDigest,imageTags[0],imageSizeInBytes,imagePushedAt]' \
        --output text)
    
    total_images=$(echo "$images" | wc -l)
    echo "Total images: $total_images"
    echo "Keeping: $KEEP_COUNT newest images"
    
    if [ "$total_images" -le "$KEEP_COUNT" ]; then
        echo "No cleanup needed"
        continue
    fi
    
    images_to_delete=$((total_images - KEEP_COUNT))
    echo "Images to delete: $images_to_delete"
    
    # Delete old images
    count=0
    while IFS=$'\t' read -r digest tag size pushed_at; do
        count=$((count + 1))
        
        if [ "$count" -gt "$images_to_delete" ]; then
            break
        fi
        
        size_mb=$((size / 1024 / 1024))
        
        if [ "$DRY_RUN" = true ]; then
            echo "  [DRY RUN] Would delete: $tag ($digest) - ${size_mb}MB"
        else
            echo "  Deleting: $tag ($digest) - ${size_mb}MB"
            aws ecr batch-delete-image \
                --repository-name "$repo" \
                --region "$ECR_REGION" \
                --image-ids imageDigest="$digest" \
                --output text > /dev/null
            
            total_deleted=$((total_deleted + 1))
            total_size_saved=$((total_size_saved + size_mb))
        fi
    done <<< "$images"
done

echo ""
echo "========================================="
echo "Cleanup Summary"
echo "========================================="
echo "Total images deleted: $total_deleted"
echo "Total space saved: ${total_size_saved}MB"

if [ "$DRY_RUN" = true ]; then
    echo ""
    echo "This was a dry run. Run without --dry-run to actually delete images."
fi
