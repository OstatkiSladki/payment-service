# WAL.md — Write-Ahead Log (состояние сессии)

Этот файл содержит текущее состояние проекта. Он обновляется AI в конце каждой сессии, а также при критических изменениях. Человек проверяет его ежедневно.

## Current Phase
**payment-service: API v1 hardening (roles + typed query schemas + migration metadata) — IN PROGRESS**

## Completed
- `spec://com.ostatki-sladki.payment-service/payment-specs#section-10` — стандартизованы роли под Auth Service: `UsersRole={user,staff,admin}`, `StaffRole={staff,manager,admin,owner}`.
- `spec://com.ostatki-sladki.payment-service/payment-specs#section-10` — добавлен и валидируется заголовок `X-User-Staff-Role` (обязателен при `X-User-Role=staff`).
- `spec://com.ostatki-sladki.payment-service/payment-specs#section-4` — удалены legacy role-ветки (`marketing`, `venue_admin`) из runtime-авторизации.
- `spec://com.ostatki-sladki.payment-service/payment-specs#section-4` — admin endpoints ограничены только `admin`.
- `spec://com.ostatki-sladki.payment-service/payment-specs#section-4` — query параметры вынесены в typed Pydantic схемы и используются в роутерах через `Annotated + Query`.
- `spec://com.ostatki-sladki.payment-service/payment-specs#section-3` — `order_id` зафиксирован как numeric в схемах/валидации и отражен в API spec.
- `spec://com.ostatki-sladki.payment-service/payment-specs#section-7` — `migrations/env.py` переведен на явный импорт моделей и `target_metadata = Base.metadata`.
- `spec://com.ostatki-sladki.payment-service/payment-specs#section-4` — синхронизированы `specs/common/payments-api.yaml` и root `openapi.yaml` под новую role-модель.

## In Progress
### DONE
- Внедрены `schemas/auth.py`, `schemas/queries.py`.
- Обновлены `dependency.py`, `repositories/payment.py`, `repositories/promo_code.py`, `repositories/promo_code_usage.py`.
- Обновлены `services/payment.py`, `services/admin.py`, `api/payments.py`, `api/admin.py`.
- Тесты обновлены под новый контракт ролей и numeric `order_id`.
- Проверки: `.venv/bin/pytest` -> `14 passed`; `.venv/bin/alembic heads` -> `002_restrict_payment_method_enum (head)`.
### TODO
- `spec://com.ostatki-sladki.payment-service/payment-specs#section-5` — подключить gRPC валидации order/venue по TODO-маркерам.
- `spec://com.ostatki-sladki.payment-service/payment-specs#section-2` — заменить event publisher stub на реальный RabbitMQ publisher.
- `spec://com.ostatki-sladki.payment-service/payment-specs#section-4` — реализовать gateway-specific webhook mapping и orphan webhook persistence.

## Known Issues
1. В `specs/common/payments-api.yaml` сохраняется `X-User-Venue-ID` как опциональный header (runtime сейчас не использует venue-scoped authorization).
2. `migrations/versions/002_restrict_payment_method_enum.py` остается scaffold no-op с TODO для production-safe enum migration.
3. Предупреждение в тестах: использование `status.HTTP_422_UNPROCESSABLE_ENTITY` помечено deprecated в FastAPI (функционально корректно).

## Decisions Pending
- Нужен ли полноценный venue-scoped authorization в этом сервисе при текущей role-модели (`user/staff/admin`) или оставляем platform-admin only для `/admin/*`.

## Session Context
- **Start with**: подключение gRPC contract checks в `services/payment.py` и `services/promo.py`.
- **Key files**:
  - `dependency.py`
  - `schemas/auth.py`
  - `schemas/queries.py`
  - `api/admin.py`
  - `migrations/env.py`
- **Run first**: `.venv/bin/pytest` и `.venv/bin/alembic heads`
- **Watch out**: держать role contract строго `user/staff/admin`; не возвращать legacy роли без явного решения.

---
