GRAVIX — Admin Dashboard for Telegram Bot Hosting Platform

Overview
- GRAVIX is a secure, owner-only admin dashboard that monitors and controls your Telegram hosting platform in real time.
- Backend: FastAPI (async), Redis pub/sub for events, Postgres via SQLAlchemy.
- Frontend: React (Vite) + Tailwind CSS for a responsive, premium UI.
- Realtime: WebSocket endpoint /ws/admin streams container, build, support, and metrics events (fed by Redis channels).

Key Features (MVP)
- Login with secure password hashing (bcrypt) and HttpOnly session cookie; CSRF protection via double-submit cookie.
- Dashboard with live stats (users, premium users, active containers, running builds) and system metrics (CPU, RAM, Disk).
- Users list with Premium management (grant/revoke/extend).
- Containers list with Start/Stop/Restart/Delete actions (published to Redis command channel).
- Builds list and logs tail endpoint.
- Support tickets list and reply.
- Broadcast to All / Premium / Specific users.
- Audit log on admin actions.
- WebSocket: /ws/admin routes Redis pub/sub messages to the admin client.

Eventing Model
- Master bot publishes to Redis:
  - events:containers
  - events:builds
  - events:support
  - events:metrics
- GRAVIX backend subscribes and forwards to the admin WebSocket.
- Admin actions publish commands to Redis channel gravix:commands for the master bot to consume.

Security Best Practices
- Passwords stored hashed (bcrypt). No plaintext credentials committed.
- Session cookie: HttpOnly, Secure, SameSite=Strict.
- CSRF protection for state-changing requests.
- CORS restricted via env CORS_ORIGINS.
- Rate limiting on auth endpoints (slowapi).
- Secrets via environment variables (see .env.example).
- RBAC: only owner admin supported (single user).
- Audit logging for admin actions.

Database Schema (minimal)
- admins: id, username (unique), password_hash, is_owner, created_at
- users: id (telegram id), username, email, is_premium, premium_expires, created_at, last_seen
- containers: id (uuid), user_id, name, image_tag, container_id, status, host_port, resource_limits, created_at, last_started_at
- builds: id, app_id, status, logs, created_at, finished_at
- tickets: id, user_id, status, created_at
- messages: id, ticket_id, sender, content, created_at
- audit_logs: id, actor, action, target_type, target_id, details, timestamp

API Contract (selected)
- POST /api/auth/login {username, password} -> Set session + CSRF cookie
- GET /api/auth/me -> Admin info
- POST /api/auth/logout
- GET /api/stats
- GET /api/users
- POST /api/users/:id/grant {days}
- POST /api/users/:id/revoke
- GET /api/containers
- POST /api/containers/:id/action {action: start|stop|restart|delete}
- GET /api/containers/:id/logs?tail=100
- GET /api/builds
- POST /api/broadcast {scope, message, user_ids?}
- GET /api/support/tickets
- POST /api/support/tickets/:id/reply

Realtime
- WS /ws/admin — authenticate via session cookie. Forwards any JSON messages published on the Redis events channels.

Project Structure
- backend/ (FastAPI app, SQLAlchemy models, Redis pub/sub)
  - app/main.py
  - app/api/routes.py
  - app/core/config.py, db.py, redis_conn.py
  - app/models.py, app/schemas.py
  - app/security/auth.py
  - app/cli.py (init-db, create-admin)
  - requirements.txt, Dockerfile
- frontend/ (React + Tailwind)
  - index.html, vite.config.ts, tailwind.config.js, postcss.config.js
  - src/pages/Login.tsx, src/pages/Dashboard.tsx
  - src/lib/api.ts, src/lib/ws.ts
  - package.json, Dockerfile
- infra/nginx/nginx.conf (reverse proxy /, /api, and /ws)
- docker-compose.yml

Setup (Local Dev)
1) Copy .env.example to .env and fill values (generate SECRET_KEY).
2) Start services:
   docker compose up -d --build
3) Initialize DB and create admin:
   docker compose exec backend python -m app.cli init-db
   docker compose exec backend python -m app.cli create-admin --username Dravon --password '<secure-temp-password>'
   IMPORTANT: Change the password immediately after first login (provide a settings UI or rerun create-admin to overwrite).
4) Frontend dev (optional):
   cd frontend && npm install && npm run dev
   The vite dev server proxies /api and /ws to the backend.

Deployment (Ubuntu VPS with nginx + Docker)
- Use docker-compose.yml as provided. For production, put nginx in front:
  - Terminate TLS with certbot/letsencrypt on the VPS.
  - Adjust infra/nginx/nginx.conf to:
    - Serve the frontend build (you can also build to nginx html).
    - Proxy /api to backend:8000
    - Proxy /ws to backend:8000 (with Upgrade headers).
- Example with TLS (pseudo):
  server {
    listen 80;
    server_name example.com;
    return 301 https://$host$request_uri;
  }
  server {
    listen 443 ssl http2;
    server_name example.com;
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    # ... same locations as nginx.conf
  }

Master Bot Integration
- Ensure the existing master bot publishes to Redis channels mentioned above.
- GRAVIX publishes admin actions to gravix:commands, e.g.:
  {"type":"container_action","action":"restart","container_id":"...","actor":"Dravon"}
- For container logs tail: backend publishes a logs_request and expects master to place logs in a Redis key gravix:container:{id}:logs:tail:{N}.

Wireframes & Pages
- Login (owner only).
- Dashboard: Stats cards, system metrics, live events stream.
- Users: Paginated table, actions (grant, revoke, extend).
- Containers: Table with actions (start, stop, restart, delete), view logs dialog.
- Builds: Queue and running with % and logs.
- Support: Tickets and reply.
- Broadcast: Compose and send to All/Premium/Specific users.
- Audit Logs: List of admin actions.
- Settings: Change password, resource defaults, retention, etc.
- Mobile responsive: collapsible sidebar, cards stack vertically.

Security Checklist
- [x] Hashed passwords (bcrypt) and no plaintext in repo.
- [x] HttpOnly session cookie; Secure + SameSite=Strict.
- [x] CSRF via double-submit cookie + header.
- [x] Rate limit login endpoint.
- [x] CORS restricted to allowed origins (.env).
- [x] Secrets in env; not committed.
- [x] Single-owner RBAC.
- [x] Audit logs recorded for write actions.

Operational Notes
- Log rotation should be configured at the Docker/host level.
- For backups, snapshot the Postgres volume (db_data).
- Optional: integrate cAdvisor/Prometheus for richer metrics.
- Optional: add 2FA and multi-admin roles in future.

Troubleshooting
- 401 on /api: ensure cookies allowed; check CORS and domain.
- WebSocket not connecting: verify nginx Upgrade headers and /ws proxy.
- No events: ensure master bot publishes to Redis; check Redis URL.
- CSRF failures: frontend must echo the gravix_csrf cookie as x-csrf-token for POST/PUT/DELETE requests.

License
- Proprietary — internal tool for platform owner.