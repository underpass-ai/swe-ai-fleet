#!/bin/bash
set -e
echo "=== Proto Docs Server ==="
echo "Serving pre-generated documentation..."
echo "Documentation available at: http://localhost:${DOCS_PORT:-8080}"
echo ""
cd docs/api
exec python3 -m http.server ${DOCS_PORT:-8080} --bind 0.0.0.0



