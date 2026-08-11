# Build from the repo root: docker build -f deploy/cloud-run/frontend/Dockerfile
#   --build-arg VITE_BACKEND_HTTP_URL=https://<backend-url>
#   --build-arg VITE_BACKEND_WS_URL=wss://<backend-url>/stream
#   --build-arg VITE_GRAFANA_BASE_URL=https://<your-stack>.grafana.net .
#
# Vite bakes VITE_* env vars into the static bundle at build time, not runtime — the
# backend must already be deployed (its URL known) before building this image.
FROM node:22-slim AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_BACKEND_HTTP_URL
ARG VITE_BACKEND_WS_URL
ARG VITE_GRAFANA_BASE_URL
ARG VITE_LATENCY_BUDGET_MS=15000
ENV VITE_BACKEND_HTTP_URL=$VITE_BACKEND_HTTP_URL \
    VITE_BACKEND_WS_URL=$VITE_BACKEND_WS_URL \
    VITE_GRAFANA_BASE_URL=$VITE_GRAFANA_BASE_URL \
    VITE_LATENCY_BUDGET_MS=$VITE_LATENCY_BUDGET_MS
RUN npm run build

FROM nginx:1.27-alpine
COPY deploy/cloud-run/frontend/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
ENV PORT=8080
EXPOSE 8080
# The official nginx image's docker-entrypoint runs envsubst on templates/*.template
# into conf.d/ automatically before starting nginx, substituting ${PORT}.
CMD ["nginx", "-g", "daemon off;"]
