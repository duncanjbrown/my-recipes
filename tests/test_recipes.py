import pytest
import os
import sqlite3
from myrecipes.main import Recipe, RecipeDatabase, app


class TestRecipe:
    def test_recipe_creation(self):
        recipe = Recipe(
            title="Test Recipe",
            url="https://example.com",
            ingredients=["flour", "water"],
            instructions="Mix and bake"
        )
        assert recipe.title == "Test Recipe"
        assert recipe.url == "https://example.com"
        assert recipe.ingredients == ["flour", "water"]
        assert recipe.instructions == "Mix and bake"


class TestRecipeDatabase:
    @pytest.fixture
    def temp_db(self):
        db_path = "test_recipes.db"
        db = RecipeDatabase(db_path)
        yield db
        if os.path.exists(db_path):
            os.remove(db_path)
    
    def test_database_initialization(self, temp_db):
        conn = sqlite3.connect(temp_db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='recipes'")
        result = cursor.fetchone()
        conn.close()
        assert result is not None
    
    def test_add_recipe(self, temp_db):
        recipe = Recipe(
            title="Test Recipe",
            url="https://example.com",
            ingredients=["flour", "water"],
            instructions="Mix and bake"
        )
        recipe_id = temp_db.add_recipe(recipe)
        assert recipe_id is not None
        assert recipe_id > 0
    
    def test_get_all_recipes_empty(self, temp_db):
        recipes = temp_db.get_all_recipes()
        assert recipes == []
    
    def test_get_all_recipes_with_data(self, temp_db):
        recipe = Recipe(
            title="Test Recipe",
            url="https://example.com",
            ingredients=["flour", "water"],
            instructions="Mix and bake"
        )
        temp_db.add_recipe(recipe)
        
        recipes = temp_db.get_all_recipes()
        assert len(recipes) == 1
        assert recipes[0].title == "Test Recipe"
        assert recipes[0].url == "https://example.com"
        assert recipes[0].ingredients == ["flour", "water"]
        assert recipes[0].instructions == "Mix and bake"


class TestApp:
    @pytest.fixture
    def client(self):
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_index_route(self, client):
        response = client.get('/')
        assert response.status_code == 200
        assert b'RECIPES' in response.data
        assert b'RECIPE LISTS' in response.data
