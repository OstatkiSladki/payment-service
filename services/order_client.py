from core.config import get_settings


class OrderServiceClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.target = f'{settings.grpc_order_service_host}:{settings.grpc_order_service_port}'
