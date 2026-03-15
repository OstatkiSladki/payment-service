from core.config import get_settings


class VenueServiceClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.target = f'{settings.grpc_venue_service_host}:{settings.grpc_venue_service_port}'
