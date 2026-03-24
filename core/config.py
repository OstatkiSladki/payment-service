from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
  model_config = SettingsConfigDict(env_file=".env", extra="ignore")

  app_name: str = "payment-service"
  app_env: str = "production"
  app_host: str = "0.0.0.0"
  app_port: int = 8000
  app_debug: bool = False
  log_level: str = "INFO"

  db_host: str = "localhost"
  db_port: int = 5432
  db_name: str = "db_payment"
  db_user: str = "postgres"
  db_password: str = "postgres"
  db_pool_size: int = 10
  db_max_overflow: int = 20
  db_schema: str = "public"

  rabbitmq_host: str = "localhost"
  rabbitmq_port: int = 5672
  rabbitmq_user: str = "guest"
  rabbitmq_password: str = "guest"
  rabbitmq_vhost: str = "/"
  rabbitmq_exchange: str = "payments.events"

  grpc_order_service_host: str = "order-service.internal"
  grpc_order_service_port: int = 50051
  grpc_venue_service_host: str = "venue-service.internal"
  grpc_venue_service_port: int = 50052

  gateway_user_id_header: str = "X-User-ID"
  gateway_user_role_header: str = "X-User-Role"
  gateway_user_staff_role_header: str = "X-User-Staff-Role"
  gateway_user_email_header: str = "X-User-Email"
  gateway_user_is_active_header: str = "X-User-Is-Active"
  gateway_user_is_verified_header: str = "X-User-Is-Verified"
  gateway_user_venue_id_header: str = "X-User-Venue-ID"
  gateway_request_id_header: str = "X-Request-ID"

  webhook_secret_key: str = "changeme"

  @property
  def database_dsn(self) -> str:
    return (
      f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
      f"@{self.db_host}:{self.db_port}/{self.db_name}"
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
  return Settings()
