from __future__ import annotations

from pydantic import BaseModel

from app.core.domain.entities.model_card import ModelCard


class ExperimentMetricResponse(BaseModel):
    name: str
    value: float
    description: str


class ModelCardResponse(BaseModel):
    id: str
    display_name: str
    description: str
    architecture: str
    task: str
    classes: list[str]
    metrics: list[ExperimentMetricResponse]
    dataset: str
    notebook: str
    status: str
    extra: dict[str, str] = {}
    processing_steps: list[str] = []


class ModelsListResponse(BaseModel):
    count: int
    items: list[ModelCardResponse]


def model_card_to_response(card: ModelCard) -> ModelCardResponse:
    return ModelCardResponse(
        id=card.id,
        display_name=card.display_name,
        description=card.description,
        architecture=card.architecture,
        task=card.task,
        classes=list(card.classes),
        metrics=[
            ExperimentMetricResponse(name=m.name, value=m.value, description=m.description)
            for m in card.metrics
        ],
        dataset=card.dataset,
        notebook=card.notebook,
        status=card.status,
        extra=dict(card.extra),
        processing_steps=list(card.processing_steps),
    )
