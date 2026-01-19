#!/bin/bash
# SVN to Git Migration Script
# Migrates large SVN repository (1TB+) to Git

set -e

# Configuration
SVN_REPO_URL="https://svn.example.com/repo"
GIT_REPO_URL="https://github.com/company/hyperscale-platform.git"
TEMP_DIR="/tmp/svn-migration"
AUTHORS_FILE="authors.txt"

echo "========================================="
echo "SVN to Git Migration Tool"
echo "========================================="
echo ""

# Check dependencies
command -v git >/dev/null 2>&1 || { echo "Error: git is not installed"; exit 1; }
command -v git-svn >/dev/null 2>&1 || { echo "Error: git-svn is not installed"; exit 1; }

# Create temporary directory
mkdir -p "$TEMP_DIR"
cd "$TEMP_DIR"

# Generate authors file from SVN
echo "Step 1: Extracting SVN authors..."
if [ ! -f "$AUTHORS_FILE" ]; then
    svn log -q "$SVN_REPO_URL" | \
        awk -F '|' '/^r/ {sub("^ ", "", $2); sub(" $", "", $2); print $2" = "$2" <"$2"@example.com>"}' | \
        sort -u > "$AUTHORS_FILE"
    echo "Authors file created: $AUTHORS_FILE"
else
    echo "Using existing authors file"
fi

# Clone SVN repository with git-svn
echo ""
echo "Step 2: Cloning SVN repository..."
echo "This may take several hours for large repositories..."

git svn clone "$SVN_REPO_URL" \
    --authors-file="$AUTHORS_FILE" \
    --no-metadata \
    --stdlayout \
    repo

cd repo

# Convert SVN ignore to .gitignore
echo ""
echo "Step 3: Converting svn:ignore to .gitignore..."
git svn show-ignore > .gitignore
git add .gitignore
git commit -m "Convert svn:ignore to .gitignore" || echo "No changes to commit"

# Convert SVN tags to Git tags
echo ""
echo "Step 4: Converting SVN tags to Git tags..."
git for-each-ref --format='%(refname)' refs/remotes/tags | \
while read tag; do
    TAG_NAME="${tag#refs/remotes/tags/}"
    git tag -a "$TAG_NAME" -m "Converted tag $TAG_NAME from SVN" "refs/remotes/tags/$TAG_NAME" || true
done

# Delete SVN tag branches
git for-each-ref --format='%(refname)' refs/remotes/tags | \
while read tag; do
    git branch -rd "$tag"
done

# Convert SVN branches
echo ""
echo "Step 5: Converting SVN branches..."
git for-each-ref --format='%(refname)' refs/remotes | \
    grep -v 'refs/remotes/tags' | \
    grep -v 'refs/remotes/trunk' | \
while read branch; do
    BRANCH_NAME="${branch#refs/remotes/}"
    git branch "$BRANCH_NAME" "$branch" || echo "Branch $BRANCH_NAME already exists"
done

# Rename trunk to main
echo ""
echo "Step 6: Renaming trunk to main..."
git branch -m trunk main || git branch -m master main || echo "Main branch already exists"

# Optimize repository
echo ""
echo "Step 7: Optimizing Git repository..."
git gc --aggressive --prune=now

# Repository statistics
echo ""
echo "========================================="
echo "Migration Statistics"
echo "========================================="
echo "Total commits: $(git rev-list --all --count)"
echo "Total branches: $(git branch -a | wc -l)"
echo "Total tags: $(git tag | wc -l)"
echo "Repository size: $(du -sh .git | cut -f1)"

# Add remote and push
echo ""
echo "Step 8: Pushing to Git remote..."
git remote add origin "$GIT_REPO_URL"

echo "Ready to push. Run the following commands to complete:"
echo "  git push -u origin main"
echo "  git push --all origin"
echo "  git push --tags origin"

echo ""
echo "Migration complete! Repository is at: $TEMP_DIR/repo"
