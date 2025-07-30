**Event-Driven Architecture Proof of Concept**

A monorepo demonstrating a full event‑driven system with microservices, event sourcing, and observability, orchestrated via Docker Compose.

---

## Overview

* **Frontend**: React 18 application served by Nginx
* **API Service**: Flask‑based REST API that publishes events to Kafka
* **Mailer Service**: Kafka consumer sending emails via Mustache templates
* **Workflow Agent**: Multi‑step business workflow driven by events
* **Event Broker**: Apache Kafka with Zookeeper
* **Monitoring**: Prometheus, Grafana, Kafka‑UI, cAdvisor, Node Exporter
* **Shared**: common logging, metrics, security, and tracing configuration

---

## Repository Layout

```
/
├── docker-compose.yml           # Orchestration for all services
├── .env.example                 # Environment‑variable template
├── deploy.sh                    # Helper script (in backend/ by default)
├── api/                         # Flask API service
├── frontend/                    # React + Vite + Nginx
├── mailer-service/              # Email‑processing microservice
├── workflow-agent/              # Event‑driven workflow executor
├── shared/                      # Cross‑service configs and utilities
└── monitoring/                  # Prometheus, Alert Rules, Grafana dashboards
```

---

## Prerequisites

* Docker 20.10+ & Docker Compose 2.x
* ≥ 8 GB RAM (4 GB minimum)
* Ports 3000, 5000, 9092, 9090, 8080, 8025 free

---

## Quick Start

1. Copy and customize environment variables:

   ```bash
   cp .env.example .env
   ```
2. Launch all services:

   ```bash
   docker-compose up -d
   ```
3. Verify health:

   * Frontend → [http://localhost:3000](http://localhost:3000)
   * API → [http://localhost:5001/health](http://localhost:5001/health)
   * Kafka‑UI → [http://localhost:8080](http://localhost:8080)
   * Prometheus → [http://localhost:9090](http://localhost:9090)
   * Grafana → [http://localhost:3001](http://localhost:3001)

---

## Service Endpoints

* **API**

  * Health: `GET /health`
  * Contact form: `POST /api/contact`
  * CRM (mock): `POST /api/internal/leads`
* **Mailer**

  * Consumes `ContactFormSubmitted` events → sends email
* **Workflow Agent**

  * Listens on same Kafka topic → runs multi‑step workflow

---

## Configuration

All services read from environment variables. Key settings:

```env
# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:29092
KAFKA_TOPIC=events.contact_form

# API
API_PORT=5000
CORS_ORIGINS=*

# Mailer
SMTP_HOST=mailhog
SMTP_PORT=1025

# Workflow Agent
CRM_API_BASE=http://api:5000/api
CRM_API_TIMEOUT=30

# Frontend
REACT_APP_API_BASE_URL=http://localhost:5001/api
```

---

## Development

### Running Locally (without Docker)

1. Start Kafka & Zookeeper:

   ```bash
   docker-compose up -d zookeeper kafka kafka-ui
   ```
2. In separate terminals, run each service:

   ```bash
   # API
   cd api && pip install -r requirements.txt && python main.py

   # Mailer
   cd mailer-service && pip install -r requirements.txt && python main.py

   # Workflow Agent
   cd workflow-agent && pip install -r requirements.txt && python main.py

   # Frontend
   cd frontend && pnpm install && pnpm run dev
   ```

---

## Testing

Each service includes its own tests. From repo root:

```bash
# Example: run API tests
cd api && python -m pytest

# Or use the included runner script
./run_tests.sh all
```

---

## Monitoring & Observability

* **Kafka‑UI**: inspect topics and messages at `http://localhost:8080`
* **Prometheus**: metrics collection at `http://localhost:9090`
* **Grafana**: dashboards at `http://localhost:3001` (admin/password = admin)
* **cAdvisor** & **Node Exporter**: container and host metrics

---

## Troubleshooting

* **Port conflicts**:

  ```bash
  netstat -tulpn | grep -E "3000|5001|9092|9090|8080"
  ```
* **Check logs**:

  ```bash
  docker-compose logs -f <service-name>
  ```
* **Restart a service**:

  ```bash
  docker-compose restart api
  ```

---

## Contributing

1. Fork this repository
2. Create a feature branch
3. Make changes & add tests
4. Ensure all tests pass
5. Submit a pull request

---

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.
