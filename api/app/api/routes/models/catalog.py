from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.openapi_responses import MODEL_PROVIDER_ERROR_RESPONSES
from app.api.params import MetricsWindowHeader, MetricsWindowQuery
from app.api.schemas import ModelDetailResponse, ModelListItem, ProviderCatalogItem
from app.domains.platform.services.model_catalog_service import ModelCatalogService

router = APIRouter(prefix="/v1")


@router.get("/models", summary="获取模型列表", response_model=list[ModelListItem])
def list_models(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return ModelCatalogService(db).list_models()


@router.get(
    "/models/{model_code}/providers",
    summary="获取模型供应商列表",
    response_model=list[ProviderCatalogItem],
    responses=MODEL_PROVIDER_ERROR_RESPONSES,
)
def get_model_providers(
    model_code: str,
    window: MetricsWindowQuery = "24h",
    metrics_window: MetricsWindowHeader = None,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    effective_window = metrics_window or window
    return ModelCatalogService(db).list_model_providers(model_code, effective_window)


@router.get(
    "/models/{model_code}",
    summary="获取模型详情",
    response_model=ModelDetailResponse,
    responses=MODEL_PROVIDER_ERROR_RESPONSES,
)
def get_model_detail(
    model_code: str,
    window: MetricsWindowQuery = "24h",
    metrics_window: MetricsWindowHeader = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    effective_window = metrics_window or window
    return ModelCatalogService(db).get_model_detail(model_code, effective_window)
