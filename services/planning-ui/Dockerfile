# Multi-stage build for Planning UI (Astro with SSR)
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./
COPY astro.config.mjs tsconfig.json ./

# Install dependencies
RUN npm ci

# Copy source files
COPY src ./src
COPY public ./public

# Build the application (SSR mode)
RUN npm run build

# Production stage with Node.js (for SSR)
FROM node:20-alpine

WORKDIR /app

# Copy package files and install production dependencies
COPY package*.json ./
RUN npm ci --omit=dev

# Copy built application
COPY --from=builder /app/dist ./dist

# Expose port
ENV PORT=80
ENV HOST=0.0.0.0
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

# Start Astro server
CMD ["node", "dist/server/entry.mjs"]

