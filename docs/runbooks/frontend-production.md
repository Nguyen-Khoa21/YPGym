# Production frontend container

YPGym keeps its existing Vite development container for local work. Deployments build the React application once and serve the generated static files from the separate Nginx image defined by `frontend/Dockerfile.production`.

## Prerequisites

- A public HTTPS API URL ending in `/api/v1`.
- A TLS-terminating reverse proxy or platform load balancer in front of this container.
- The deployed frontend origin added to the backend `FRONTEND_URL` or `CORS_EXTRA_ORIGINS` configuration.
- Google, Facebook and VNPay callback settings updated for the deployed HTTPS origins when those integrations are enabled.

`VITE_API_BASE_URL` is compiled into the browser bundle and is therefore public configuration, not a secret. The production build fails when it is omitted so an image cannot silently point at the development API.

## Build

From the repository root:

```powershell
docker build `
  -f frontend/Dockerfile.production `
  --build-arg VITE_API_BASE_URL=https://api.example.com/api/v1 `
  -t ypgym-frontend:production `
  frontend
```

Replace `https://api.example.com/api/v1` with the actual public API URL. Rebuild the image when this URL changes.

## Run a local smoke test

For a backend already available at `http://localhost:8001`, build and run a local image:

```powershell
docker build `
  -f frontend/Dockerfile.production `
  --build-arg VITE_API_BASE_URL=http://localhost:8001/api/v1 `
  -t ypgym-frontend:smoke `
  frontend

docker run --rm --name ypgym-frontend-smoke -p 8080:8080 ypgym-frontend:smoke
```

Open `http://localhost:8080/login`. Directly opening a client route such as `http://localhost:8080/app/dashboard` should return the React application rather than an Nginx 404. The container health endpoint is `http://localhost:8080/healthz`.

The CSP permits local API calls only to `localhost` or `127.0.0.1` over HTTP. Non-local deployments must use HTTPS.

## Deployment checks

1. Confirm `/healthz` returns `200 ok`.
2. Confirm `/login` and a directly opened client route both return the application.
3. Confirm hashed files under `/assets/` return `Cache-Control: public, max-age=31536000, immutable`.
4. Confirm HTML responses include CSP, frame denial, MIME-sniffing protection, referrer and permissions headers.
5. Confirm the browser can call the configured HTTPS API and that backend CORS allows the exact frontend origin.
6. Confirm the external TLS layer redirects HTTP to HTTPS and adds `Strict-Transport-Security`. The static container intentionally does not emit HSTS because it cannot know whether an upstream proxy delivered the original request over HTTPS.

Do not expose the Vite development server as the production website. The existing `docker compose --profile app` workflow remains the local development path.
