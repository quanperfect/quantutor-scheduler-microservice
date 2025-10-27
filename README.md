# QuanTutor Scheduler Microservice

A standalone job scheduling microservice for the QuanTutor platform.  
It handles scheduled and periodic jobs, communicates with the main backend via RabbitMQ, and manages retries for failed or unacknowledged jobs.

## Overview

This microservice is part of the full personal tutoring platform QuanTutor backend, which includes:
- **FastAPI backend**
- **PostgreSQL** for data storage
- **RabbitMQ** for inter-service messaging
- **MinIO** for file storage
- **ClamAV** for file scanning
- **Telegram Bot** microservice for telegram notifications and system alerts for admins
- **Scheduler** microservice for job scheduling (this repo)

## Tech Stack

- **Python 3.9**
- **FastAPI**
- **Uvicorn**
- **APScheduler** – for scheduling and managing jobs
- **RabbitMQ** – message broker
- **PostgreSQL** – job persistence and tracking
- **SQLAlchemy** with **asyncpg**
- **Docker** and **Docker Compose** for containerization and orchestration


## Running the Service (Local Setup)

### 1. Clone the repository
```bash
git clone https://github.com/quanperfect/quantutor-scheduler-microservice.git
cd quantutor-scheduler-microservice
```

### 2. Create an `.env` file
Provide your environment configuration according to [config.py](config.py)

### 3. Build and run the service
```bash
docker compose up --build
```

This starts:
- A local RabbitMQ instance (for message handling)
- The scheduler container

Logs are written to the `/logs` directory inside the container (mapped to `./logs` on the host).

## Integration with the Full QuanTutor Backend

In production, the bot service connects to the full QuanTutor backend and RabbitMQ broker defined in the central `docker-compose.yml`:
```yaml
postgres-jobs:
  image: postgres:17
  container_name: postgres-jobs
  ports:
    - "127.0.0.1:5434:5432" 
  environment:
    POSTGRES_DB: ${SCHEDULER_POSTGRES_DB}
    POSTGRES_USER: ${SCHEDULER_POSTGRES_USER}
    POSTGRES_PASSWORD: ${SCHEDULER_POSTGRES_PASSWORD}
    POSTGRES_INITDB_ARGS: "--encoding=UTF-8 --lc-collate=C --lc-ctype=C"
  env_file:
    - scheduler/.env
  volumes:
    - postgres-jobs-data:/var/lib/postgresql/data
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${SCHEDULER_POSTGRES_USER} -d ${SCHEDULER_POSTGRES_DB}"]
    interval: 5s
    timeout: 5s
    retries: 5
  restart: unless-stopped

scheduler:
  build:
    context: .
    dockerfile: scheduler/Dockerfile
  container_name: scheduler
  ports:
    - "127.0.0.1:8002:8001"
  env_file:
    - scheduler/.env  
  depends_on:
    postgres-jobs:
      condition: service_healthy
    rabbitmq:
      condition: service_healthy
  volumes:
    - .:/app
    - /app/venv 
    - ./logs:/app/logs
  restart: unless-stopped
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

## Repository Structure
```
quantutor-scheduler-microservice/
├── consumers/
│   ├── __init__.py
│   └── job_result_consumer.py
├── custom_logging/
│   ├── __init__.py
│   └── custom_logger.py
├── database/
│   ├── __init__.py
│   └── postgres_database.py
├── jobs/
│   ├── __init__.py
│   ├── check_jobs_initializer.py
│   ├── cleanup_jobs_initializer.py
│   ├── job_executor.py
│   └── periodic/
│       ├── __init__.py
│       ├── periodic_checker_job.py
│       └── cleanup/
│           └── mfa_expiry_cleanup_job.py
├── models/
│   ├── __init__.py
│   └── job.py
├── rabbitmq/
│   ├── __init__.py
│   ├── rabbitmq_controller.py
│   └── rabbitmq_error_handler.py
├── repositories/
│   ├── __init__.py
│   └── job_repository.py
├── routers/
│   ├── __init__.py
│   └── health_router.py
├── schemas/
│   └── rabbitmq_events.py
├── utils/
│   ├── __init__.py
│   └── timezone_utils.py
├── .dockerignore
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── config.py
├── main.py
├── requirements.txt
└── __init__.py                      
```

## Features

- **Periodic Job Scheduling**: runs recurring tasks (e.g., cleanup jobs)
- **RabbitMQ Messaging**: sends job execution requests to the main backend
- **Result Handling and Retry**: retries failed or unacknowledged jobs
- **Postgres Persistence**: tracks job execution results and states
- **Custom Logging**: unified structured logging for production debugging

## Roadmap

Planned features and improvements:

1. **Additional Cleanup Jobs**  
   More cleanup and maintenance jobs will be added (currently, only one is implemented here as an example).

2. **Dynamic Job Scheduling**  
   The FastAPI backend will be able to send requests to dynamically create scheduled jobs (e.g., scheduled notifications for users).
