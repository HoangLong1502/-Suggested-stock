# AI Multi-Agent Stock Analysis Platform

A full-stack, free-stack Vietnamese stock analysis platform built with Docker, FastAPI, and Next.js.

## Architecture

- Frontend: Next.js + TypeScript + TailwindCSS + Recharts + Zustand + React Query
- Backend: FastAPI + Python + PostgreSQL + Redis
- AI: local multi-agent orchestration with Ollama-compatible fallback
- Agents: market scanner, technical, fundamental, sentiment, risk, and decision-making components
- Messaging: Redis Pub/Sub for agent communication

## Local Run

### Prerequisites

- Docker Desktop installed and running
- Docker Compose available

### Start the app

From the project root:

```powershell
docker compose up --build
```

### Access the app

- Frontend: `http://localhost:3010`
- Backend API: `http://localhost:5555`
- Swagger docs: `http://localhost:5555/docs`

### Stop the app

```powershell
docker compose down
```

## Notes

- Frontend is configured to connect to backend using Docker internal networking when running in containers.
- The current backend port mapping is `5555:8000` and frontend port mapping is `3010:3000`.
- This project is intended to run fully locally with free, open-source stack components.

## GitHub Repository

This repository is prepared for pushing to:

`https://github.com/HoangLong1502/-Suggested-stock.git`
