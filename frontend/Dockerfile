# Stage 1: Build Next.js
FROM node:18-alpine AS builder
WORKDIR /app

# Add build arguments for Next.js build-time env baking
ARG NEXT_PUBLIC_API_URL=http://localhost:8080/api
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL


# Install dependencies based on package-lock.json
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# Stage 2: serve the static export (next.config.mjs sets output: "export")
FROM nginx:1.27-alpine
COPY --from=builder /app/out /usr/share/nginx/html
# trailingSlash: true makes every page a directory with index.html, which nginx serves as is.
EXPOSE 80
