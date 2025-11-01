#!/bin/bash
# Inline documentation generator for Dockerfile
# This script generates markdown from proto files

set -e

mkdir -p /build/docs/api

for service in context orchestrator ray_executor planning storycoach workspace; do
    if [ -f "specs/fleet/${service}/v1/${service}.proto" ]; then
        echo "  Generating docs for: $service"
        
        # Capitalize service name: context -> Context, ray_executor -> Ray Executor
        name=$(echo "$service" | sed 's/_/ /g' | awk '{for(i=1;i<=NF;i++)sub(/./,toupper(substr($i,1,1)),$i)}1')
        
        # Generate markdown
        cat > docs/api/${service}.md << EOF
# $name Service API

**Package**: \`fleet.${service}.v1\`  
**Version**: v1  
**Generated**: $(date +%Y-%m-%d)

---

## Full Protocol Definition

<details>
<summary>Click to expand full proto definition</summary>

\`\`\`protobuf
$(cat specs/fleet/${service}/v1/${service}.proto)
\`\`\`

</details>
EOF
    fi
done

echo "✓ Documentation generated"



