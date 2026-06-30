# Stage 1: Build Next.js
FROM node:18-alpine AS builder
WORKDIR /app

# Install dependencies based on package-lock.json
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .
# Type checking is disabled during build via next.config.mjs if errors exist, 
# which prevents unexpected CI build breakages.
RUN npm run build

# Stage 2: Serve Next.js
FROM node:18-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

# Copy built app and required assets
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/next.config.mjs ./next.config.mjs

EXPOSE 3000

CMD ["npm", "start"]
