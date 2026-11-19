FROM node:24-alpine AS dependencies
WORKDIR /workspace
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
RUN npm ci

FROM node:24-alpine AS builder
WORKDIR /workspace
ARG NEXT_PUBLIC_SITE_URL
ARG API_INTERNAL_URL
ENV NEXT_PUBLIC_SITE_URL=${NEXT_PUBLIC_SITE_URL}
ENV API_INTERNAL_URL=${API_INTERNAL_URL}
COPY --from=dependencies /workspace/node_modules ./node_modules
COPY --from=dependencies /workspace/apps/web/node_modules ./apps/web/node_modules
COPY . .
RUN npm run web:build

FROM node:24-alpine AS runtime
ENV NODE_ENV=production
WORKDIR /workspace
COPY --from=builder /workspace/package.json ./package.json
COPY --from=builder /workspace/node_modules ./node_modules
COPY --from=builder --chown=node:node /workspace/apps/web ./apps/web
USER node
EXPOSE 3000
CMD ["npm", "run", "start", "--workspace", "@bukkystore/web"]
