# 🏨 Hotel Management System API

A modern Hotel Management System backend built with **FastAPI**, **SQLAlchemy**, and **SQLite** for development, with a clear migration path to **PostgreSQL**, **Docker**, and **Kubernetes** for production.

## Quick start

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API starts at <http://127.0.0.1:8000>, Swagger UI is at
<http://127.0.0.1:8000/docs>, and the database is created and seeded on first
startup. You can also run `docker compose up --build -d`.

Seeded accounts:

| Email | Password | Role |
|---|---|---|
| `admin@auroragrand.test` | `Admin#2026` | Administrator |
| `ella.hart@example.test` | `Guest#2026` | Registered user |
| `noah.reid@example.test` | `Guest#2026` | Registered user |

## 🚀 Features

- RESTful API using FastAPI
- Automatic OpenAPI (Swagger) documentation
- SQLAlchemy ORM
- SQLite for local development
- PostgreSQL-ready architecture
- JWT access tokens with rotating, revocable refresh sessions
- Role-based access control and booking ownership isolation
- Persistent room, booking, user, guest and payment CRUD
- Calculated availability, pricing, occupancy and revenue reports
- Docker support
- Kubernetes deployment (planned)
- Database migrations using Alembic (planned)

---

# 🛠️ Tech Stack

| Technology | Purpose |
|------------|---------|
| Python 3.13 | Programming Language |
| FastAPI | REST API Framework |
| SQLAlchemy 2.0 | ORM |
| SQLite | Development Database |
| PostgreSQL | Production Database |
| Pydantic v2 | Data Validation |
| Alembic | Database Migrations |
| JWT | Authentication |
| Docker | Containerization |
| Kubernetes | Container Orchestration |

---

# 📁 Project Structure

```text
hotel-management/
│
├── app/
│   ├── api/
│   │   ├── auth.py
│   │   ├── bookings.py
│   │   ├── guests.py
│   │   ├── payments.py
│   │   ├── reports.py
│   │   ├── rooms.py
│   │   ├── room_types.py
│   │   └── users.py
│   │
│   ├── database/
│   │   └── database.py
│   │
│   ├── models/
│   │
│   ├── schemas/
│   │
│   ├── services/
│   │
│   ├── repositories/
│   │
│   ├── middleware/
│   │
│   ├── core/
│   │
│   └── main.py
│
├── tests/
│
├── kubernetes/
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── README.md
└── hotel.db
```

---

# 🏗️ System Architecture

```text
                Client (Web / Mobile)
                        │
                        ▼
                  FastAPI REST API
                        │
        ┌───────────────┼───────────────┐
        │               │               │
 Authentication    Business Logic   Validation
        │               │
        └───────────────┼───────────────┘
                        │
                 Repository Layer
                        │
                 SQLAlchemy ORM
                        │
                  SQLite / PostgreSQL
```

---

# 🗄️ Database Schema

Current entities include:

- Roles
- Users
- Guests
- Room Types
- Rooms
- Bookings
- Payments

Future additions:

- Invoices
- Housekeeping
- Maintenance
- Services
- Employees

---

# 📚 API Modules

## Authentication

```
POST   /auth/login
POST   /auth/register
POST   /auth/logout
POST   /auth/refresh
GET    /auth/me
PATCH  /auth/me
POST   /auth/change-password
```

## Users

```
GET    /users
GET    /users/{id}
POST   /users
PUT    /users/{id}
DELETE /users/{id}
```

## Guests

```
GET    /guests
GET    /guests/{id}
POST   /guests
PUT    /guests/{id}
DELETE /guests/{id}
```

## Room Types

```
GET    /room-types
POST   /room-types
PUT    /room-types/{id}
DELETE /room-types/{id}
```

## Rooms

```
GET    /rooms
GET    /rooms/available
GET    /rooms/{id}
GET    /rooms/{id}/quote
POST   /rooms
PUT    /rooms/{id}
DELETE /rooms/{id}
```

## Availability

```
GET    /availability
```

## Bookings

```
GET    /bookings
GET    /bookings/{id}
POST   /bookings
PATCH  /bookings/{id}
DELETE /bookings/{id}
```

## Payments

```
GET    /payments
GET    /payments/{id}
POST   /payments
```

## Reports

```
GET    /reports/occupancy
GET    /reports/revenue
GET    /reports/bookings
GET    /reports/dashboard
```

---

# ⚙️ Getting Started

## Create a Virtual Environment

### Windows

```bash
python -m venv .venv

.venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv .venv

source .venv/bin/activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Run the Application

```bash
uvicorn app.main:app --reload
```

Server:

```
http://127.0.0.1:8000
```

---

# 📖 API Documentation

Swagger UI

```
http://127.0.0.1:8000/docs
```

ReDoc

```
http://127.0.0.1:8000/redoc
```

OpenAPI JSON

```
http://127.0.0.1:8000/openapi.json
```

---

# Tests

The API integration suite uses an isolated SQLite database and requires Node
20 or newer:

```bash
cd e2e
npm install
npm test
```

It covers authentication, authorization, rooms, calculated availability,
booking persistence and overlap conflicts, reports, and administrator CRUD.

---

# 🧪 Running Tests

```bash
pytest
```

---

# 🎭 End-to-End Tests (Playwright)

API-level end-to-end tests live in the [`e2e/`](e2e/) folder and are written with
[Playwright](https://playwright.dev/) (TypeScript).

## Prerequisites

- Node.js 20+
- Python dependencies installed (`pip install -r requirements.txt`), so Playwright can boot the FastAPI app

## Install

```bash
cd e2e
npm install
npx playwright install --with-deps
```

## Run

```bash
npx playwright test
```

Before running the tests locally, make sure to have the backend running locallly against the port : http://127.0.0.1:8000
To run the endpoint tests.


These tests also run automatically in GitHub Actions on every push and pull request to `main`
(see [`.github/workflows/playwright.yml`](.github/workflows/playwright.yml)).

---

# 🐳 Docker (Planned)

```bash
docker compose up --build
```

---

# ☸️ Kubernetes (Planned)

```bash
kubectl apply -f kubernetes/
```

---

# 🚀 Development Roadmap

- [x] Project setup
- [x] FastAPI application
- [x] SQLite integration
- [x] SQLAlchemy models
- [x] CRUD API endpoints
- [ ] Pydantic schemas
- [ ] Service layer
- [ ] Repository layer
- [ ] JWT authentication
- [ ] Role-based authorization
- [ ] Alembic migrations
- [ ] PostgreSQL migration
- [ ] Docker support
- [ ] Kubernetes deployment
- [ ] Redis caching
- [ ] Prometheus monitoring
- [ ] Grafana dashboards
- [ ] CI/CD with GitHub Actions

---

# 📈 Future Enhancements

- Multi-hotel support
- Online reservations
- Email notifications
- QR code check-in
- Dynamic room pricing
- Payment gateway integration
- Audit logging
- File uploads
- Inventory management
- Analytics dashboard

---

# 🤝 Contributing

Contributions are welcome!

1. Fork the repository
2. Create a feature branch

```bash
git checkout -b feature/new-feature
```

3. Commit your changes

```bash
git commit -m "Add new feature"
```

4. Push your branch

```bash
git push origin feature/new-feature
```

5. Open a Pull Request

---

# 📄 License

This project is licensed under the MIT License.

---

# 👨‍💻 Author

**Shannon Smith**

Built using **FastAPI**, **SQLAlchemy**, and **Python** with a cloud-native architecture designed for Docker and Kubernetes deployment.
