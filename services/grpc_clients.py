from __future__ import annotations

import json
import time

import grpc
from grpc_health.v1 import health_pb2, health_pb2_grpc

from core.config import get_settings
from rpc.generated import (
  order_query_pb2,
  order_query_pb2_grpc,
  venue_directory_pb2,
  venue_directory_pb2_grpc,
)

_SERVICE_CONFIG = json.dumps(
  {
    "methodConfig": [
      {
        "name": [{}],
        "retryPolicy": {
          "maxAttempts": 4,
          "initialBackoff": "0.2s",
          "maxBackoff": "2s",
          "backoffMultiplier": 2,
          "retryableStatusCodes": ["UNAVAILABLE"],
        },
      }
    ]
  }
)
_CHANNEL_OPTIONS = (
  ("grpc.enable_retries", 1),
  ("grpc.service_config", _SERVICE_CONFIG),
)


class CircuitBreakerOpenError(RuntimeError):
  pass


class GrpcDependencyError(RuntimeError):
  pass


class _CircuitBreaker:
  def __init__(self, failure_threshold: int, reset_timeout: float) -> None:
    self._failure_threshold = failure_threshold
    self._reset_timeout = reset_timeout
    self._consecutive_failures = 0
    self._opened_at: float | None = None
    self._state = "closed"

  def before_call(self) -> None:
    if self._state != "open":
      return
    if self._opened_at is not None and (time.monotonic() - self._opened_at) >= self._reset_timeout:
      self._state = "half-open"
      return
    raise CircuitBreakerOpenError("gRPC circuit breaker is open")

  def record_success(self) -> None:
    self._consecutive_failures = 0
    self._opened_at = None
    self._state = "closed"

  def record_failure(self) -> None:
    if self._state == "half-open":
      self._open()
      return
    self._consecutive_failures += 1
    if self._consecutive_failures >= self._failure_threshold:
      self._open()

  def _open(self) -> None:
    self._state = "open"
    self._opened_at = time.monotonic()
    self._consecutive_failures = 0


class _BaseGrpcClient:
  def __init__(self, *, target: str, service_name: str, startup_timeout: float, call_timeout: float, failure_threshold: int, reset_timeout: float) -> None:
    self._startup_timeout = startup_timeout
    self._call_timeout = call_timeout
    self._service_name = service_name
    self._breaker = _CircuitBreaker(failure_threshold, reset_timeout)
    self._channel = grpc.aio.insecure_channel(target, options=_CHANNEL_OPTIONS)
    self._health_stub = health_pb2_grpc.HealthStub(self._channel)

  async def close(self) -> None:
    await self._channel.close()

  async def wait_until_serving(self) -> None:
    try:
      response = await self._health_stub.Check(
        health_pb2.HealthCheckRequest(service=self._service_name),
        timeout=self._startup_timeout,
        wait_for_ready=True,
      )
    except grpc.RpcError as exc:
      raise GrpcDependencyError(f"{self._service_name} health check failed") from exc
    if response.status != health_pb2.HealthCheckResponse.SERVING:
      raise GrpcDependencyError(f"{self._service_name} is not serving")

  async def _call(self, func, request):
    self._breaker.before_call()
    try:
      response = await func(request, timeout=self._call_timeout, wait_for_ready=True)
    except grpc.RpcError as exc:
      self._breaker.record_failure()
      raise exc
    self._breaker.record_success()
    return response


class OrderServiceClient(_BaseGrpcClient):
  def __init__(self) -> None:
    settings = get_settings()
    super().__init__(
      target=f"{settings.grpc_order_service_host}:{settings.grpc_order_service_port}",
      service_name="ostatki.grpc.v1.OrderQueryService",
      startup_timeout=settings.grpc_startup_check_timeout,
      call_timeout=settings.grpc_call_timeout,
      failure_threshold=settings.grpc_circuit_breaker_failure_threshold,
      reset_timeout=settings.grpc_circuit_breaker_reset_timeout,
    )
    self._stub = order_query_pb2_grpc.OrderQueryServiceStub(self._channel)

  async def validate_order(self, order_id: int, user_id: int) -> order_query_pb2.ValidateOrderResponse:
    return await self._call(
      self._stub.ValidateOrder,
      order_query_pb2.ValidateOrderRequest(order_id=order_id, user_id=user_id),
    )

  async def get_order_by_id(self, order_id: int) -> order_query_pb2.GetOrderByIdResponse:
    return await self._call(
      self._stub.GetOrderById,
      order_query_pb2.GetOrderByIdRequest(order_id=order_id),
    )


class VenueServiceClient(_BaseGrpcClient):
  def __init__(self) -> None:
    settings = get_settings()
    super().__init__(
      target=f"{settings.grpc_venue_service_host}:{settings.grpc_venue_service_port}",
      service_name="ostatki.grpc.v1.VenueDirectoryService",
      startup_timeout=settings.grpc_startup_check_timeout,
      call_timeout=settings.grpc_call_timeout,
      failure_threshold=settings.grpc_circuit_breaker_failure_threshold,
      reset_timeout=settings.grpc_circuit_breaker_reset_timeout,
    )
    self._stub = venue_directory_pb2_grpc.VenueDirectoryServiceStub(self._channel)

  async def validate_venue(self, venue_id: int) -> venue_directory_pb2.ValidateVenueResponse:
    return await self._call(
      self._stub.ValidateVenue,
      venue_directory_pb2.ValidateVenueRequest(venue_id=venue_id),
    )

  async def get_venue_info(self, venue_id: int) -> venue_directory_pb2.GetVenueInfoResponse:
    return await self._call(
      self._stub.GetVenueInfo,
      venue_directory_pb2.GetVenueInfoRequest(venue_id=venue_id),
    )
