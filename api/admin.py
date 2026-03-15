from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from dependency import CurrentUser, get_current_user, get_db_session
from schemas.admin import (
    OverviewStatistics,
    PromoCodeCreateRequest,
    PromoCodeResponse,
    PromoCodeStatistics,
    PromoCodeUpdateRequest,
)
from schemas.common import PaginatedResponse
from schemas.queries import (
    AdminPromoListQuery,
    OverviewStatsQuery,
    PromoStatsQuery,
)
from services.admin import AdminService

router = APIRouter()


@router.post('/promo-codes', response_model=PromoCodeResponse, status_code=status.HTTP_201_CREATED)
async def create_promo_code(
    payload: PromoCodeCreateRequest,
    actor: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PromoCodeResponse:
    service = AdminService(session)
    return await service.create_promo(payload, actor)


@router.get('/promo-codes', response_model=PaginatedResponse)
async def list_promo_codes(
    query: Annotated[AdminPromoListQuery, Query()],
    actor: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse:
    service = AdminService(session)
    items, total = await service.list_promos(
        actor,
        query.limit,
        query.offset,
        query.is_active,
        query.discount_type.value if query.discount_type else None,
        query.search,
    )
    return PaginatedResponse(items=items, total=total, offset=query.offset, limit=query.limit)


@router.get('/promo-codes/{promo_id}', response_model=PromoCodeResponse)
async def get_promo_code(
    promo_id: int,
    actor: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PromoCodeResponse:
    service = AdminService(session)
    return await service.get_promo(promo_id, actor)


@router.put('/promo-codes/{promo_id}', response_model=PromoCodeResponse)
async def update_promo_code(
    promo_id: int,
    payload: PromoCodeUpdateRequest,
    actor: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PromoCodeResponse:
    service = AdminService(session)
    return await service.update_promo(promo_id, payload, actor)


@router.delete('/promo-codes/{promo_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_promo_code(
    promo_id: int,
    actor: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    service = AdminService(session)
    await service.delete_promo(promo_id, actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get('/promo-codes/{promo_id}/statistics', response_model=PromoCodeStatistics)
async def get_promo_code_statistics(
    promo_id: int,
    query: Annotated[PromoStatsQuery, Query()],
    actor: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PromoCodeStatistics:
    service = AdminService(session)
    return await service.promo_statistics(promo_id, query.period, actor)


@router.get('/statistics/overview', response_model=OverviewStatistics)
async def get_overview_statistics(
    query: Annotated[OverviewStatsQuery, Query()],
    actor: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> OverviewStatistics:
    service = AdminService(session)
    return await service.overview_statistics(actor, query.from_date, query.to_date)
