# 📋 Payment Service — Техническая спецификация

## 1. Обзор сервиса

### 1.1 Назначение

Payment Service — это микросервис, отвечающий за обработку платежей, управление промокодами и расчет скидок в платформе уцененных продуктов для заведений и кафе.

### 1.2 Цели и задачи

| Цель | Описание |
|------|----------|
| **Обработка платежей** | Прием, валидация и сохранение информации о платежах пользователей |
| **Управление промокодами** | CRUD операции, валидация, расчет скидок, отслеживание использований |
| **Финансовая консистентность** | Гарантия атомарности операций платежа и применения промокода |
| **Интеграция с экосистемой** | Взаимодействие с OrderService, VenueService, NotificationService |
| **Аудит и статистика** | Сбор метрик по платежам и использованию промокодов |

### 1.3 Границы ответственности

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Payment Service Boundaries                        │
├─────────────────────────────────────────────────────────────────────┤
│  В ОТВЕТСТВЕННОСТИ:                    │  НЕ В ОТВЕТСТВЕННОСТИ:     │
│  • Хранение записей о платежах         │  • Обработка заказов       │
│  • Валидация и расчет промокодов       │  • Доставка                │
│  • Применение скидок к платежам        │  • Управление меню         │
│  • Статистика по оплатам               │  • Аутентификация пользователей │
│  • Уведомления об успешных платежах    │  • Хранение данных заведений   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Архитектура

### 2.1 Схема взаимодействия сервисов

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           Payment Service                                 │
│                                                                           │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────────┐  │
│  │  REST API   │    │  gRPC Server│    │      RabbitMQ Publisher     │  │
│  │  (Client)   │    │  (Internal) │    │    (Notifications)          │  │
│  └──────┬──────┘    └──────┬──────┘    └──────────────┬──────────────┘  │
│         │                  │                          │                  │
└─────────┼──────────────────┼──────────────────────────┼──────────────────┘
          │                  │                          │
          ▼                  ▼                          ▼
    ┌──────────┐      ┌──────────────┐          ┌─────────────────┐
    │   API    │      │  gRPC Calls  │          │   RabbitMQ      │
    │  Gateway │      │              │          │   Exchange      │
    └────┬─────┘      └──────┬───────┘          └────────┬────────┘
         │                   │                           │
         │                   │                           │
         ▼                   ▼                           ▼
   ┌──────────┐      ┌──────────────┐            ┌──────────────┐
   │   User   │      │ OrderService │            │ Notification │
   │  Client  │      │ VenueService │            │   Service    │
   └──────────┘      └──────────────┘            └──────────────┘
```

### 2.2 Протоколы взаимодействия

| Сервис | Протокол | Направление | Описание |
|--------|----------|-------------|----------|
| **API Gateway** | HTTP/REST | Входящий | Клиентские запросы (платежи, промокоды) |
| **OrderService** | gRPC | Исходящий | Валидация заказа перед оплатой |
| **VenueService** | gRPC | Исходящий | Проверка заведения, получение данных |
| **NotificationService** | RabbitMQ | Исходящий | Уведомления об успешных платежах |

## 3. База данных

### 3.1 Схема БД

```sql
-- =============================================
-- PAYMENT SERVICE - db_payment
-- Таблицы: payments, promo_codes, promo_code_usages
-- =============================================

CREATE SCHEMA IF NOT EXISTS "public";

CREATE TYPE "public"."payment_method" AS ENUM ('bank_card', 'sbp');
CREATE TYPE "public"."payment_status" AS ENUM ('pending', 'succeeded', 'failed', 'refunded', 'partially_refunded');

-- =============================================
-- PAYMENTS
-- =============================================
CREATE TABLE "public"."payments" (
    "id" BIGSERIAL PRIMARY KEY,
    "order_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "transaction_id" VARCHAR(255) NOT NULL UNIQUE,
    "payment_gateway" VARCHAR(50) NOT NULL,
    "amount" DECIMAL(10, 2) NOT NULL,
    "refunded_amount" DECIMAL(10, 2) DEFAULT 0.00,
    "currency" VARCHAR(3) DEFAULT 'RUB',
    "status" payment_status DEFAULT 'pending',
    "payment_method" payment_method,
    "gateway_response" JSONB DEFAULT '{}',
    "failure_reason" TEXT,
    "promo_code_id" BIGINT,
    "discount_amount" DECIMAL(10, 2) DEFAULT 0.00,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "paid_at" TIMESTAMP WITH TIME ZONE,
    "refunded_at" TIMESTAMP WITH TIME ZONE,
    CONSTRAINT "fk_payment_promo" FOREIGN KEY ("promo_code_id") REFERENCES "public"."promo_codes"("id") ON DELETE SET NULL
);
CREATE INDEX "payments_idx_order" ON "public"."payments" ("order_id");
CREATE INDEX "payments_idx_user" ON "public"."payments" ("user_id");
CREATE INDEX "payments_idx_transaction" ON "public"."payments" ("transaction_id");
CREATE INDEX "payments_idx_status" ON "public"."payments" ("status");

-- =============================================
-- PROMO CODES
-- =============================================
CREATE TABLE "public"."promo_codes" (
    "id" BIGSERIAL PRIMARY KEY,
    "code" VARCHAR(50) NOT NULL UNIQUE,
    "discount_type" VARCHAR(20) NOT NULL,
    "discount_value" DECIMAL(10, 2) NOT NULL,
    "min_order_amount" DECIMAL(10, 2) DEFAULT 0.00,
    "valid_until" TIMESTAMP WITH TIME ZONE,
    "is_active" BOOLEAN DEFAULT TRUE,
    "rules_json" JSONB DEFAULT '{}',
    "max_usages_per_user" INTEGER,
    "total_max_usages" INTEGER,
    "venue_id" BIGINT,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX "promo_codes_idx_code" ON "public"."promo_codes" ("code", "is_active");
CREATE INDEX "promo_codes_idx_venue" ON "public"."promo_codes" ("venue_id");

-- =============================================
-- PROMO CODE USAGES
-- =============================================
CREATE TABLE "public"."promo_code_usages" (
    "id" BIGSERIAL PRIMARY KEY,
    "promo_code_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,
    "order_id" BIGINT,
    "payment_id" BIGINT,
    "discount_applied" DECIMAL(10, 2) NOT NULL,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "fk_pcu_promo" FOREIGN KEY ("promo_code_id") REFERENCES "public"."promo_codes"("id") ON DELETE CASCADE
);
CREATE INDEX "promo_code_usages_idx_user" ON "public"."promo_code_usages" ("user_id", "promo_code_id");
CREATE INDEX "promo_code_usages_idx_order" ON "public"."promo_code_usages" ("order_id");
CREATE INDEX "promo_code_usages_idx_payment" ON "public"."promo_code_usages" ("payment_id");
```

### 3.2 Описание таблиц

| Таблица | Назначение | Ключевые поля |
|---------|------------|---------------|
| `payments` | Хранение записей о платежах | `id`, `order_id`, `user_id`, `transaction_id`, `status`, `amount` |
| `promo_codes` | Промокоды и правила скидок | `id`, `code`, `discount_type`, `discount_value`, `valid_until` |
| `promo_code_usages` | История использований промокодов | `id`, `promo_code_id`, `user_id`, `payment_id`, `discount_applied` |

---

## 4. API Specification

**Файл:** `openapi.yaml` (отдельный файл в корне проекта)

API спецификация вынесена в отдельный файл `openapi.yaml` и включает:
- Client API (платежи, валидация промокодов)
- Admin API (управление промокодами, статистика)
- Webhooks (уведомления от платежных шлюзов)
- Health checks

**См. файл:** `openapi.yaml`

---

## 5. gRPC Контракты (Межсервисное взаимодействие)

### 5.1 OrderService — Валидация заказа

**Файл:** `src/rpc/proto/order_service.proto`

```protobuf
syntax = "proto3";

package order_service;

option go_package = "github.com/company/orderservice/proto";
option python_package = "payments_service.rpc.proto";

// =============================================
// Сервис валидации заказов
// =============================================
service OrderValidationService {
    // Проверка существования и статуса заказа
    rpc ValidateOrder (ValidateOrderRequest) returns (ValidateOrderResponse);
    
    // Получение деталей заказа для расчета платежа
    rpc GetOrderDetails (GetOrderDetailsRequest) returns (GetOrderDetailsResponse);
}

// =============================================
// Запросы
// =============================================
message ValidateOrderRequest {
    int64 order_id = 1;
    int64 user_id = 2;
}

message GetOrderDetailsRequest {
    int64 order_id = 1;
}

// =============================================
// Ответы
// =============================================
message ValidateOrderResponse {
    bool is_valid = 1;
    string error_code = 2;
    string error_message = 3;
    OrderStatus order_status = 4;
}

message GetOrderDetailsResponse {
    int64 order_id = 1;
    int64 user_id = 2;
    int64 venue_id = 3;
    decimal amount = 4;
    decimal discount_amount = 5;
    decimal final_amount = 6;
    string currency = 7;
    OrderStatus status = 8;
    repeated OrderItem items = 9;
}

// =============================================
// Типы данных
// =============================================
enum OrderStatus {
    ORDER_STATUS_UNSPECIFIED = 0;
    ORDER_STATUS_PENDING = 1;
    ORDER_STATUS_CONFIRMED = 2;
    ORDER_STATUS_PAID = 3;
    ORDER_STATUS_CANCELLED = 4;
    ORDER_STATUS_REFUNDED = 5;
}

message OrderItem {
    int64 product_id = 1;
    string name = 2;
    int32 quantity = 3;
    decimal price = 4;
    decimal total = 5;
}

// Decimal для точных финансовых расчетов
message decimal {
    string value = 1;  // Строковое представление десятичного числа
}
```

### 5.2 VenueService — Проверка заведения

**Файл:** `src/rpc/proto/venue_service.proto`

```protobuf
syntax = "proto3";

package venue_service;

option go_package = "github.com/company/venueservice/proto";
option python_package = "payments_service.rpc.proto";

// =============================================
// Сервис проверки заведений
// =============================================
service VenueValidationService {
    // Проверка существования и статуса заведения
    rpc ValidateVenue (ValidateVenueRequest) returns (ValidateVenueResponse);
    
    // Получение данных заведения для промокодов
    rpc GetVenueInfo (GetVenueInfoRequest) returns (GetVenueInfoResponse);
}

// =============================================
// Запросы
// =============================================
message ValidateVenueRequest {
    int64 venue_id = 1;
}

message GetVenueInfoRequest {
    int64 venue_id = 1;
}

// =============================================
// Ответы
// =============================================
message ValidateVenueResponse {
    bool is_valid = 1;
    bool is_active = 2;
    string error_code = 3;
    string error_message = 4;
}

message GetVenueInfoResponse {
    int64 venue_id = 1;
    string name = 2;
    bool accepts_promo_codes = 3;
    repeated string allowed_payment_methods = 4;
    VenueStatus status = 5;
}

// =============================================
// Типы данных
// =============================================
enum VenueStatus {
    VENUE_STATUS_UNSPECIFIED = 0;
    VENUE_STATUS_ACTIVE = 1;
    VENUE_STATUS_SUSPENDED = 2;
    VENUE_STATUS_CLOSED = 3;
}
```

### 5.3 Конфигурация gRPC клиентов

**Файл:** `src/core/config.py`

```python
class GRPCSettings(BaseSettings):
    """Настройки gRPC клиентов"""
    
    ORDER_SERVICE_HOST: str = "order-service.internal"
    ORDER_SERVICE_PORT: int = 50051
    ORDER_SERVICE_TIMEOUT: int = 5
    
    VENUE_SERVICE_HOST: str = "venue-service.internal"
    VENUE_SERVICE_PORT: int = 50052
    VENUE_SERVICE_TIMEOUT: int = 5
    
    class Config:
        env_prefix = "GRPC_"
```

---

## 6. RabbitMQ — Уведомления

### 6.1 Конфигурация обменника и очередей

| Параметр | Значение | Описание |
|----------|----------|----------|
| **Exchange Name** | `payments.events` | Topic exchange для событий платежей |
| **Exchange Type** | `topic` | Маршрутизация по routing key |
| **Durable** | `true` | Сохранение при перезапуске брокера |

### 6.2 Сообщения

**Файл:** `src/core/events.py`

```python
# =============================================
# События для публикации в RabbitMQ
# =============================================

PAYMENT_SUCCEEDED_EVENT = "payment.succeeded"
PAYMENT_FAILED_EVENT = "payment.failed"
PAYMENT_REFUNDED_EVENT = "payment.refunded"

# =============================================
# Структура сообщения
# =============================================

class PaymentEvent(BaseModel):
    """Базовое событие платежа"""
    event_type: str
    event_id: str
    timestamp: datetime
    payment_id: int
    order_id: int
    user_id: int
    amount: Decimal
    currency: str = "RUB"

class PaymentSucceededEvent(PaymentEvent):
    """Событие успешной оплаты"""
    event_type: str = PAYMENT_SUCCEEDED_EVENT
    payment_method: str
    promo_code: Optional[str] = None
    discount_amount: Optional[Decimal] = None
    venue_id: Optional[int] = None

class PaymentFailedEvent(PaymentEvent):
    """Событие неудачной оплаты"""
    event_type: str = PAYMENT_FAILED_EVENT
    failure_reason: str
    error_code: Optional[str] = None

class PaymentRefundedEvent(PaymentEvent):
    """Событие возврата средств"""
    event_type: str = PAYMENT_REFUNDED_EVENT
    refunded_amount: Decimal
    refund_reason: Optional[str] = None
```

### 6.3 Маршрутизация

| Routing Key | Queue | Consumer |
|-------------|-------|----------|
| `payment.succeeded` | `notifications.payment` | NotificationService |
| `payment.failed` | `notifications.payment` | NotificationService |
| `payment.refunded` | `notifications.payment` | NotificationService |

### 6.4 Пример публикации

**Файл:** `src/core/events.py`

```python
import aio_pika
import uuid
from datetime import datetime
from typing import Optional
from decimal import Decimal

class EventPublisher:
    """Публикация событий в RabbitMQ"""
    
    def __init__(self, connection: aio_pika.Connection):
        self.connection = connection
        self._channel: Optional[aio_pika.Channel] = None
        self._exchange: Optional[aio_pika.Exchange] = None
    
    async def connect(self):
        self._channel = await self.connection.channel()
        self._exchange = await self._channel.declare_exchange(
            "payments.events",
            aio_pika.ExchangeType.TOPIC,
            durable=True
        )
    
    async def publish_payment_succeeded(
        self,
        payment_id: int,
        order_id: int,
        user_id: int,
        amount: Decimal,
        payment_method: str,
        promo_code: Optional[str] = None,
        discount_amount: Optional[Decimal] = None,
        venue_id: Optional[int] = None
    ):
        """Публикация события успешной оплаты"""
        message = PaymentSucceededEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            payment_id=payment_id,
            order_id=order_id,
            user_id=user_id,
            amount=amount,
            payment_method=payment_method,
            promo_code=promo_code,
            discount_amount=discount_amount,
            venue_id=venue_id
        )
        
        await self._exchange.publish(
            aio_pika.Message(
                body=message.model_dump_json().encode(),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=PAYMENT_SUCCEEDED_EVENT
        )
```

---

## 7. Структура проекта

```
payment-service/
├── .venv/                          # Виртуальное окружение (uv)
├── .gitignore
├── .python-version                 # Версия Python для uv (3.12)
├── pyproject.toml                  # Зависимости и метаданные (uv)
├── uv.lock                         # Lock file (uv)
├── alembic.ini                     # Конфигурация Alembic
├── openapi.yaml                    # OpenAPI спецификация (отдельный файл)
├── Dockerfile
├── .dockerignore
├── main.py                         # Точка входа приложения
├── dependency.py                   # FastAPI зависимости (get_current_user, db session)
├── .env.example                    # Пример переменных окружения
│
├── migrations/                     # Alembic миграции
│   ├── versions/
│   │   ├── 001_initial_schema.py
│   │   ├── 002_add_venue_id_to_promo.py
│   │   └── ...
│   └── env.py
│
├── api/                            # API слой (роутеры)
│   ├── __init__.py
│   ├── router.py                   # Агрегатор всех роутеров
│   │
│   ├── payments.py                 # Эндпоинты /payments/*
│   ├── promo.py                    # Эндпоинты /promo/*
│   ├── admin.py                    # Эндпоинты /admin/*
│   ├── webhooks.py                 # Эндпоинты /webhooks/*
│   └── health.py                   # Эндпоинты /health
│
├── core/                           # Ядро приложения
│   ├── __init__.py
│   ├── config.py                   # Настройки из env
│   ├── database.py                 # Создание сессий БД
│   ├── security.py                 # Проверка подписей вебхуков
│   └── events.py                   # RabbitMQ publisher
│
├── models/                         # SQLAlchemy модели
│   ├── __init__.py
│   ├── payment.py
│   ├── promo_code.py
│   └── promo_code_usage.py
│
├── repositories/                   # Репозитории (паттерн Repository)
│   ├── __init__.py
│   ├── base.py                     # Базовый репозиторий (CRUD)
│   ├── payment.py
│   ├── promo_code.py
│   └── promo_code_usage.py
│
├── schemas/                        # Pydantic схемы
│   ├── __init__.py
│   ├── payment.py                  # Схемы для payments
│   ├── promo.py                    # Схемы для promo
│   ├── admin.py                    # Схемы для admin
│   ├── webhook.py                  # Схемы для webhook payload
│   └── common.py                   # Общие схемы (Error, Health, etc.)
│
├── services/                       # Бизнес-логика и внешние сервисы
│   ├── __init__.py
│   ├── payment.py                  # Бизнес-логика payments
│   ├── promo.py                    # Бизнес-логика promo validation
│   ├── admin.py                    # Бизнес-логика admin operations
│   ├── order_client.py             # gRPC клиент для Order Service
│   └── venue_client.py             # gRPC клиент для Venue Service
│
├── rpc/                            # gRPC контракты
│   ├── __init__.py
│   └── proto/                      # .proto файлы
│       ├── order_service.proto
│       └── venue_service.proto
│
├── tests/                          # Тесты
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_payments.py
│   │   ├── test_promo.py
│   │   └── test_events.py
│   └── integration/
│       ├── __init__.py
│       ├── test_payments_flow.py
│       └── test_webhooks.py
│
└── sql/                            # SQL файлы (для миграций/дампов)
    ├── 001_init_schema.sql
    └── 002_seed_promo_codes.sql
```

### Описание ключевых файлов

| Файл/Папка | Назначение |
|------------|------------|
| `main.py` | Точка входа, создание FastAPI app, подключение роутеров |
| `dependency.py` | FastAPI Depends для авторизации, сессий БД, пользователей |
| `api/router.py` | Агрегатор всех API роутеров, префиксы `/v1` |
| `core/config.py` | Загрузка переменных окружения через pydantic-settings |
| `core/database.py` | Движок SQLAlchemy, сессии, base модель |
| `core/events.py` | Публикация событий в RabbitMQ |
| `models/*.py` | SQLAlchemy ORM модели для таблиц БД |
| `repositories/*.py` | CRUD операции для моделей (паттерн Repository) |
| `schemas/*.py` | Pydantic схемы для request/response валидации |
| `services/*.py` | Бизнес-логика, gRPC клиенты для внешних сервисов |
| `rpc/proto/*.proto` | gRPC контракты для межсервисного взаимодействия |

## 8. Конфигурация

### 8.1 Переменные окружения

**Файл:** `.env.example`

```bash
# =============================================
# Application
# =============================================
APP_NAME=payment-service
APP_ENV=production
LOG_LEVEL=INFO

# =============================================
# Database
# =============================================
DB_HOST=postgres.internal
DB_PORT=5432
DB_NAME=db_payment
DB_USER=payment_user
DB_PASSWORD=changeme
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# =============================================
# RabbitMQ
# =============================================
RABBITMQ_HOST=rabbitmq.internal
RABBITMQ_PORT=5672
RABBITMQ_USER=payment_user
RABBITMQ_PASSWORD=changeme
RABBITMQ_VHOST=/payments

# =============================================
# gRPC Clients
# =============================================
GRPC_ORDER_SERVICE_HOST=order-service.internal
GRPC_ORDER_SERVICE_PORT=50051
GRPC_VENUE_SERVICE_HOST=venue-service.internal
GRPC_VENUE_SERVICE_PORT=50052

# =============================================
# Gateway Headers
# =============================================
GATEWAY_USER_ID_HEADER=X-User-ID
GATEWAY_USER_ROLE_HEADER=X-User-Role
GATEWAY_USER_STAFF_ROLE_HEADER=X-User-Staff-Role
GATEWAY_USER_EMAIL_HEADER=X-User-Email
GATEWAY_REQUEST_ID_HEADER=X-Request-ID

# =============================================
# Webhooks
# =============================================
WEBHOOK_SECRET_KEY=changeme
```

### 8.2 pyproject.toml

```toml
[project]
name = "payment-service"
version = "1.0.0"
description = "Payment and Promo Codes Service"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "sqlalchemy[asyncio]>=2.0.25",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    "aio-pika>=9.4.0",
    "grpcio>=1.60.0",
    "grpcio-tools>=1.60.0",
    "python-jose[cryptography]>=3.3.0",
    "argon2-cffi>=23.1.0",
    "structlog>=24.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.26.0",
    "factory-boy>=3.3.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

---

## 9. Flow: Обработка платежа

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Payment Creation Flow                                     │
└─────────────────────────────────────────────────────────────────────────────┘

  Client              API Gateway         Payment Service      Order Service
    │                      │                    │                    │
    │ POST /payments       │                    │                    │
    │ (JWT + order_id)     │                    │                    │
    │─────────────────────>│                    │                    │
    │                      │ Validate JWT       │                    │
    │                      │ Add X-User-*       │                    │
    │                      │ headers            │                    │
    │                      │───────────────────>│                    │
    │                      │                    │                    │
    │                      │                    │ 1. Validate order  │
    │                      │                    │ (gRPC call)        │
    │                      │                    │───────────────────>│
    │                      │                    │                    │
    │                      │                    │ Order valid?       │
    │                      │                    │<───────────────────│
    │                      │                    │                    │
    │                      │                    │ 2. Validate promo  │
    │                      │                    │ (if provided)      │
    │                      │                    │                    │
    │                      │                    │ 3. Create payment  │
    │                      │                    │ (DB transaction)   │
    │                      │                    │ - payments         │
    │                      │                    │ - promo_code_usages│
    │                      │                    │                    │
    │                      │                    │ 4. Publish event   │
    │                      │                    │ (RabbitMQ)         │
    │                      │                    │────────┐           │
    │                      │                    │        │           │
    │                      │                    │<───────┘           │
    │                      │                    │                    │
    │                      │  201 Created       │                    │
    │                      │<───────────────────│                    │
    │  201 Created         │                    │                    │
    │<─────────────────────│                    │                    │
    │                      │                    │                    │
```

---

## 10. Безопасность

### 10.1 Аутентификация

| Метод | Описание |
|-------|----------|
| **Gateway Headers** | Все запросы проходят через API Gateway, который валидирует JWT и добавляет `X-User-*` заголовки |
| **Internal Trust** | Payment Service доверяет заголовкам от Gateway (закрытая сеть) |
| **Webhook Signature** | Вебхуки от шлюзов проверяются по HMAC подписи |

### 10.2 Авторизация

| Роль          | Доступ                                                        |
| ------------- | ------------------------------------------------------------- |
| `user`        | `/payments/*`, `/promo/validate`                              |
| `staff`       | `/payments/*`                                                  |
| `admin`       | Полный доступ, включая `/admin/*`                             |

### 10.3 Идемпотентность

- `transaction_id` — уникальный индекс в таблице `payments`
- Повторный запрос с тем же `transaction_id` возвращает результат первого запроса
- Реализовано через `INSERT ... ON CONFLICT` или обработку `IntegrityError`

---

## 11. Мониторинг и логирование

### 11.1 Логирование

- Все запросы логируются с `X-Request-ID`
- Структурированные логи (JSON) через `structlog`
- Уровни: INFO (продакшн), DEBUG (разработка)

### 11.2 Метрики

| Метрика | Тип | Описание |
|---------|-----|----------|
| `payment_created_total` | Counter | Количество созданных платежей |
| `payment_succeeded_total` | Counter | Количество успешных платежей |
| `payment_failed_total` | Counter | Количество неудачных платежей |
| `promo_validation_total` | Counter | Количество валидаций промокодов |
| `grpc_call_duration` | Histogram | Длительность gRPC вызовов |
| `db_query_duration` | Histogram | Длительность запросов к БД |
