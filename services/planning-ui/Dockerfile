# Multi-stage build for Planning UI (Astro with SSR)
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY services/planning-ui/package*.json ./
COPY services/planning-ui/astro.config.mjs services/planning-ui/tsconfig.json ./

# Install dependencies (includes grpc-tools for code generation)
RUN npm ci

# Copy protobuf definition and generation script
COPY specs/fleet/planning/v2/planning.proto ./specs/fleet/planning/v2/planning.proto
COPY services/planning-ui/scripts/generate-grpc.js ./scripts/generate-grpc.js

# Generate gRPC code from .proto during build
# This generates TypeScript/JavaScript client stubs in gen/
RUN chmod +x scripts/generate-grpc.js && \
    node scripts/generate-grpc.js

# Copy source files
COPY services/planning-ui/src ./src
COPY services/planning-ui/public ./public

# Build the application (SSR mode)
RUN npm run build

# Production stage with Node.js (for SSR)
FROM node:20-alpine

WORKDIR /app

# Copy package files and install production dependencies
COPY services/planning-ui/package*.json ./
RUN npm ci --omit=dev

# Copy built application
COPY --from=builder /app/dist ./dist

# Copy generated gRPC code (needed at runtime)
COPY --from=builder /app/gen ./gen

# Copy proto file for fallback proto-loader (needed if generated code fails)
# Create directory structure first, then copy proto
RUN mkdir -p ./proto/fleet/planning/v2
COPY --from=builder /app/specs/fleet/planning/v2/planning.proto ./proto/fleet/planning/v2/planning.proto

# Expose port (use non-privileged port for non-root user)
ENV PORT=3000
ENV HOST=0.0.0.0
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:3000/ || exit 1

# Start Astro server
CMD ["node", "dist/server/entry.mjs"]

