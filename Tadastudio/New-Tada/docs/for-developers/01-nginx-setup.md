# Nginx Reverse Proxy Setup

This setup uses nginx as a reverse proxy to route requests between the frontend and backend services, eliminating the
need for build-time API URL configuration.

## Architecture

```
http://localhost:3000
├── /                    → Frontend container (Next.js)
├── /api/*              → Backend container (FastAPI)
└── /api/graph/ws/*     → Backend container (WebSocket)
```

## How to Use

### Development with Docker Compose

```bash
# Build and start all services with nginx
docker compose up --build

# Access the application
open http://localhost:3000
```

### Individual Service Access

- **Application**: <http://localhost:3000> (nginx proxy)
- **Backend Direct**: <http://localhost:8000> (for debugging)
- **Nginx Health**: <http://localhost:3000/nginx-health>

### Development without Docker

If you prefer local development:

```bash
# Start only backend via docker
docker compose up backend

# Run frontend locally (uses Next.js rewrites)
cd frontend && npm run dev
```

## Benefits

✅ **Single Docker Image**: Same image works in all environments
✅ **No Build-time Configuration**: No need for `NEXT_PUBLIC_API_URL`
✅ **Production-like**: Matches real deployment architecture
✅ **WebSocket Support**: Handles real-time connections properly
✅ **Rate Limiting**: Built-in API rate limiting (10 req/s)
✅ **Security Headers**: Standard security headers included

## Configuration Files

- `nginx.conf`: Reverse proxy configuration
- `docker-compose.yml`: Updated with nginx service
- `frontend/next.config.ts`: Development rewrites for local testing

## Deployment

For production deployment, use the same nginx configuration pattern:

1. Deploy backend service
2. Deploy frontend service
3. Configure reverse proxy (nginx/ALB/Azure App Gateway) with:
    - `/api/*` → Backend service
    - `/` → Frontend service
    - WebSocket support for `/api/graph/ws/*`

## Troubleshooting

### Check nginx logs

```bash
docker compose logs nginx
```

### Check service connectivity

```bash
# Test backend health
curl http://localhost:8000/docs

# Test frontend through nginx
curl http://localhost:3000

# Test nginx health
curl http://localhost:3000/nginx-health
```

### Common Issues

1. **502 Bad Gateway**: Backend service not ready yet
    - Wait for backend to fully start
    - Check `docker compose logs backend`

2. **WebSocket connection failed**:
    - Verify nginx WebSocket configuration
    - Check browser developer tools

3. **API calls failing**:
    - Verify nginx is routing `/api/*` correctly
    - Check `docker compose logs nginx`
