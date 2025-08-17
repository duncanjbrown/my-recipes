import pytest
from myrecipes.models import engine
from sqlmodel import SQLModel


@pytest.fixture(autouse=True)
def clean_database():
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)
