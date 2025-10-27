FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/scheduler/

# these should live at top level, they are from other code part as expected by python imports in the code
RUN rm -rf /app/scheduler/rabbitmq /app/scheduler/schemas /app/scheduler/custom_logging /app/scheduler/utils

COPY rabbitmq /app/rabbitmq
COPY schemas /app/schemas
COPY custom_logging /app/custom_logging
COPY utils /app/utils

ENV PYTHONPATH=/app

# 0.0.0.0 because in docker network
CMD ["uvicorn", "scheduler.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
