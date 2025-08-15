import pytest
from sqlmodel import Session
from myrecipes.main import app
from myrecipes.models import Recipe, engine, create_tables


class TestViewRecipeInList:
    @pytest.fixture
    def client(self):
        create_tables()

        with app.test_client() as client:
            yield client

    def test_view_single_recipe_in_list(self, client):
        test_recipe = Recipe(
            title="Chocolate Chip Cookies",
            url="https://example.com/cookies",
            ingredients='["2 cups flour", "1 cup sugar", "1/2 cup butter", "chocolate chips"]',
            instructions="Mix ingredients and bake at 350°F for 12 minutes"
        )

        with Session(engine) as session:
            session.add(test_recipe)
            session.commit()

        response = client.get('/')

        assert response.status_code == 200

        response_text = response.data.decode('utf-8')
        assert "Chocolate Chip Cookies" in response_text
        assert "https://example.com/cookies" in response_text
        assert "2 cups flour" in response_text
        assert "1 cup sugar" in response_text
        assert "Mix ingredients and bake at 350°F for 12 minutes" in response_text

        assert "RECIPES" in response_text
        assert "RECIPE LISTS" in response_text
