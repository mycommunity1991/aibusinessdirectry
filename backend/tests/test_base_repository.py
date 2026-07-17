from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.repositories.base_repository import BaseRepository


class DummyModel(Base):
    __tablename__ = "dummy_model"
    __table_args__ = {"extend_existing": True}
    id: Mapped[int] = mapped_column(primary_key=True)


class DummyRepository(BaseRepository[DummyModel]):
    pass


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def repository(mock_session: AsyncSession) -> DummyRepository:
    return DummyRepository(model=DummyModel, session=mock_session)


@pytest.mark.anyio
async def test_get_by_id(repository: DummyRepository, mock_session: AsyncMock) -> None:
    expected_obj = DummyModel()
    mock_session.get.return_value = expected_obj

    result = await repository.get_by_id(1)

    mock_session.get.assert_awaited_once_with(DummyModel, 1)
    assert result is expected_obj


@pytest.mark.anyio
async def test_get_all(repository: DummyRepository, mock_session: AsyncMock) -> None:
    expected_objs = [DummyModel(), DummyModel()]
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = expected_objs
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    result = await repository.get_all(skip=10, limit=5)

    mock_session.execute.assert_awaited_once()
    assert result == expected_objs


@pytest.mark.anyio
async def test_create_from_dict(
    repository: DummyRepository, mock_session: AsyncMock
) -> None:
    obj_in = {"id": 1}
    result = await repository.create(obj_in)

    mock_session.add.assert_called_once()
    mock_session.flush.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(result)
    assert result.id == 1
    assert isinstance(result, DummyModel)


@pytest.mark.anyio
async def test_create_from_model(
    repository: DummyRepository, mock_session: AsyncMock
) -> None:
    obj_in = DummyModel(id=2)
    result = await repository.create(obj_in)

    mock_session.add.assert_called_once_with(obj_in)
    mock_session.flush.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(result)
    assert result is obj_in


@pytest.mark.anyio
async def test_update(repository: DummyRepository, mock_session: AsyncMock) -> None:
    db_obj = DummyModel(id=1)
    obj_in = {"id": 2}
    result = await repository.update(db_obj, obj_in)

    assert result.id == 2
    mock_session.add.assert_called_once_with(db_obj)
    mock_session.flush.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(db_obj)


@pytest.mark.anyio
async def test_delete_existing(
    repository: DummyRepository, mock_session: AsyncMock
) -> None:
    db_obj = DummyModel()
    mock_session.get.return_value = db_obj
    result = await repository.delete(1)

    assert result is True
    mock_session.delete.assert_awaited_once_with(db_obj)
    mock_session.flush.assert_awaited_once()


@pytest.mark.anyio
async def test_delete_non_existing(
    repository: DummyRepository, mock_session: AsyncMock
) -> None:
    mock_session.get.return_value = None
    result = await repository.delete(1)

    assert result is False
    mock_session.delete.assert_not_called()
    mock_session.flush.assert_not_called()


@pytest.mark.anyio
async def test_exists_true(
    repository: DummyRepository, mock_session: AsyncMock
) -> None:
    mock_session.get.return_value = DummyModel()
    result = await repository.exists(1)

    assert result is True
    mock_session.get.assert_awaited_once_with(DummyModel, 1)


@pytest.mark.anyio
async def test_exists_false(
    repository: DummyRepository, mock_session: AsyncMock
) -> None:
    mock_session.get.return_value = None
    result = await repository.exists(1)

    assert result is False
    mock_session.get.assert_awaited_once_with(DummyModel, 1)
