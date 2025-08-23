import json
from sqlmodel import SQLModel, Field, create_engine, Relationship
from typing import Optional, List
from datetime import datetime

from .environment import config


class RecipeListRecipe(SQLModel, table=True):
    """Join table for many-to-many relationship between RecipeList and Recipe"""
    recipe_list_id: Optional[int] = Field(
        default=None, foreign_key="recipelist.id", primary_key=True)
    recipe_id: Optional[int] = Field(
        default=None, foreign_key="recipe.id", primary_key=True)


class Recipe(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    url: Optional[str] = None
    ingredients: str = Field(default="[]")  # Store as JSON string
    instructions: Optional[str] = None
    image_url: Optional[str] = None

    # Relationship to recipe lists
    recipe_lists: List["RecipeList"] = Relationship(
        back_populates="recipes", link_model=RecipeListRecipe)

    @property
    def ingredients_list(self) -> List[str]:
        """Get ingredients as a list"""
        try:
            return json.loads(self.ingredients)
        except (json.JSONDecodeError, TypeError):
            return []

    @ingredients_list.setter
    def ingredients_list(self, value: List[str]):
        """Set ingredients from a list"""
        self.ingredients = json.dumps(value)


class RecipeList(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    is_current: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)

    # Relationship to recipes
    recipes: List[Recipe] = Relationship(
        back_populates="recipe_lists", link_model=RecipeListRecipe)


class Staple(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    is_checked: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)


engine = None

if config.environment == "test":
    engine = create_engine("sqlite:///recipes_test.db")
else:
    engine = create_engine("sqlite:///recipes.db")


def create_tables():
    SQLModel.metadata.create_all(engine)
