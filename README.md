# Event-Driven Architecture Proof of Concept

A comprehensive demonstration of modern event-driven architecture patterns using microservices, event sourcing, and distributed system observability.

## 🏗️ Architecture Overview

This proof-of-concept implements a complete event-driven system with the following components:

- **Frontend**: React 18 application with modern UI components
- **API Service**: Flask-based REST API with event publishing
- **Mailer Service**: Automated email processing with Mustache templates
- **Workflow Agent**: Multi-step business process automation
- **Event Broker**: Apache Kafka for reliable event streaming
- **Infrastructure**: Docker containers with docker-compose orchestration

## 🚀 Quick Start

### Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- 8GB+ RAM recommended
- Ports 3000, 5000, 8080, 9092 available

### One-Command Deployment

```bash
./deploy.sh start
```

This will:
1. Build all service containers
2. Start Kafka, Zookeeper, and all microservices
3. Wait for services to be healthy
4. Display service URLs and status

### Access the Application

- **Frontend**: http://localhost:3000
- **API Documentation**: http://localhost:5000/api/docs
- **Kafka UI**: http://localhost:8080

## 📋 Deployment Commands

```bash
# Start all services
./deploy.sh start

# Stop all services
./deploy.sh stop

# Restart all services
./deploy.sh restart

# Show service status
./deploy.sh status

# View logs (all services)
./deploy.sh logs

# View logs for specific service
./deploy.sh logs api
./deploy.sh logs mailer
./deploy.sh logs workflow-agent

# Restart specific service
./deploy.sh restart-service api

# Build services without starting
./deploy.sh build

# Clean up all resources
./deploy.sh cleanup

# Show help
./deploy.sh help
```

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

Key configuration options:

```env
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=kafka:29092
KAFKA_TOPIC=events.contact_form

# Email Configuration
SMTP_HOST=localhost
FROM_EMAIL=noreply@event-driven-poc.com

# API Configuration
CORS_ORIGINS=*
API_PORT=5000
```

### Service Configuration

Each service can be configured via environment variables:

#### API Service
- `FLASK_ENV`: Environment (development/production)
- `KAFKA_BOOTSTRAP_SERVERS`: Kafka connection string
- `CORS_ORIGINS`: Allowed CORS origins

#### Mailer Service
- `SMTP_HOST`: SMTP server hostname
- `SMTP_PORT`: SMTP server port
- `FROM_EMAIL`: Sender email address

#### Workflow Agent
- `CRM_API_BASE`: CRM API base URL
- `CRM_API_TIMEOUT`: API timeout in seconds

## 🏃‍♂️ Development Mode

For development with hot reloading:

```bash
# Start infrastructure only
docker-compose up -d kafka zookeeper kafka-ui

# Run services locally
cd api && python main.py
cd mailer-service && python main.py
cd workflow-agent && python main.py
cd frontend && pnpm run dev
```

## 📊 Monitoring and Observability

### Kafka UI
Access Kafka topics, consumers, and messages at http://localhost:8080

### Service Health Checks
```bash
# API health
curl http://localhost:5000/health

# Frontend health
curl http://localhost:3000/health

# Service status
./deploy.sh status
```

### Logs
```bash
# All service logs
docker-compose logs -f

# Specific service logs
docker-compose logs -f api
docker-compose logs -f mailer
docker-compose logs -f workflow-agent
```

## 🔄 Event Flow

1. **Form Submission**: User submits contact form via React frontend
2. **Event Publishing**: API publishes `ContactFormSubmitted` event to Kafka
3. **Parallel Processing**: 
   - Mailer service consumes event and sends confirmation email
   - Workflow agent consumes event and executes 3-step workflow
4. **Email Dispatch**: Mailer publishes `EmailDispatched` event
5. **Workflow Completion**: Agent publishes `WorkflowCompleted` event
6. **CRM Integration**: Lead created in mock CRM system

## 🧪 Testing the System

### End-to-End Test

1. Open http://localhost:3000
2. Click "Try Live Demo"
3. Fill out the contact form
4. Submit the form
5. Check logs to see event processing:
   ```bash
   ./deploy.sh logs
   ```

### Event Verification

Monitor events in Kafka UI:
1. Go to http://localhost:8080
2. Navigate to Topics → `events.contact_form`
3. View messages to see event flow

## 🏗️ Service Architecture

### API Service (`/api`)
- Flask REST API with CORS support
- Event publishing to Kafka
- Contact form validation
- Mock CRM endpoints

### Mailer Service (`/mailer-service`)
- Kafka event consumer
- Mustache template engine
- HTML/text email generation
- SMTP integration (mock in development)

### Workflow Agent (`/workflow-agent`)
- Multi-step workflow engine
- Lead tagging and assignment logic
- CRM integration
- Compensation pattern implementation

### Frontend (`/frontend`)
- React 18 with modern UI components
- Responsive design
- Form validation
- Real-time status updates

## 🐳 Docker Configuration

### Service Images
- **API**: Python 3.11 slim with Flask
- **Mailer**: Python 3.11 slim with email libraries
- **Workflow**: Python 3.11 slim with HTTP clients
- **Frontend**: Multi-stage build (Node.js → Nginx)

### Networking
All services communicate via `event-poc-network` bridge network.

### Volumes
- `kafka-data`: Persistent Kafka data
- `zookeeper-data`: Persistent Zookeeper data
- Service logs mounted for debugging

## 🔒 Security Considerations

### Development Security
- Services run as non-root users
- Network isolation via Docker networks
- Health checks for service monitoring

### Production Recommendations
- Enable TLS for Kafka
- Use secrets management for credentials
- Implement authentication/authorization
- Enable audit logging
- Use production SMTP server

## 🚨 Troubleshooting

### Common Issues

#### Services Not Starting
```bash
# Check Docker status
docker info

# Check service logs
./deploy.sh logs

# Restart specific service
./deploy.sh restart-service <service-name>
```

#### Port Conflicts
```bash
# Check port usage
netstat -tulpn | grep :3000
netstat -tulpn | grep :5000
netstat -tulpn | grep :9092
```

#### Kafka Connection Issues
```bash
# Check Kafka health
docker-compose exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092

# Restart Kafka
./deploy.sh restart-service kafka
```

#### Frontend Not Loading
```bash
# Check nginx logs
docker-compose logs frontend

# Verify API connectivity
curl http://localhost:5000/health
```

### Resource Requirements

Minimum system requirements:
- **CPU**: 2 cores
- **RAM**: 4GB (8GB recommended)
- **Disk**: 2GB free space
- **Network**: Internet access for Docker images

## 📈 Performance Tuning

### Kafka Optimization
```env
KAFKA_NUM_PARTITIONS=3
KAFKA_CONSUMER_MAX_POLL_RECORDS=10
KAFKA_PRODUCER_BATCH_SIZE=16384
```

### Service Scaling
```bash
# Scale specific service
docker-compose up -d --scale mailer=2
docker-compose up -d --scale workflow-agent=2
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test with `./deploy.sh start`
5. Submit pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review service logs: `./deploy.sh logs`
3. Open an issue with system information and logs

