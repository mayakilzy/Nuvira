#!/usr/bin/env bash
# =============================================================================
#  Build the two base images and push them to Docker Hub (multi-arch).
#
#  Usage:   ./scripts/build-and-push.sh <version>      e.g. 1.0.0
#  Requires: docker login   +   docker buildx (ships with modern Docker)
# =============================================================================
set -euo pipefail

VERSION="${1:?Usage: build-and-push.sh <version> (e.g. 1.0.0)}"
DOCKER_NS="${DOCKER_NS:-aymansaeed}"
PLATFORMS="linux/amd64,linux/arm64"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Namespace : ${DOCKER_NS}"
echo "==> Version   : ${VERSION}"
echo "==> Platforms : ${PLATFORMS}"

# one-time builder (idempotent)
docker buildx create --name saasbuilder --use 2>/dev/null || docker buildx use saasbuilder

build_push () {
  local name="$1" ctx="$2"
  echo "==> Building ${DOCKER_NS}/${name}  (:${VERSION} and :latest)"
  docker buildx build \
    --platform "${PLATFORMS}" \
    -t "${DOCKER_NS}/${name}:${VERSION}" \
    -t "${DOCKER_NS}/${name}:latest" \
    --push \
    "${ctx}"
}

build_push "saas-base-backend"  "${ROOT}/backend"
build_push "saas-base-frontend" "${ROOT}/frontend"

echo "✅ Pushed:"
echo "   ${DOCKER_NS}/saas-base-backend:${VERSION}"
echo "   ${DOCKER_NS}/saas-base-frontend:${VERSION}"
echo
echo "On any server:  DOCKER_NS=${DOCKER_NS} TAG=${VERSION} docker compose pull && docker compose up -d"
