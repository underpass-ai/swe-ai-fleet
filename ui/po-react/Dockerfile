# Multi-stage build for React SPA
FROM docker.io/library/node:20-alpine AS build

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci

# Copy source
COPY . .

# Build
RUN npm run build

# Production image with nginx
FROM docker.io/library/nginx:1.27-alpine

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

# Add health endpoint
RUN printf '{"status":"ok"}\n' > /usr/share/nginx/html/health

# Copy nginx config (optional - add if needed)
# COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

