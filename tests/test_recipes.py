import pytest
from unittest.mock import patch, MagicMock
from sqlmodel import Session, select
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


class TestFetchRecipeFromUrl:
    @pytest.fixture
    def client(self):
        create_tables()
        with app.test_client() as client:
            yield client

    def test_fetch_recipe_from_url_end_to_end(self, client):
        with open('/Users/duncanbrown/projects/myrecipes/tests/examples/bbc-chicken-pasta-bake.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        mock_response = MagicMock()
        mock_response.content = html_content.encode('utf-8')
        mock_response.status_code = 200
        
        with patch('requests.get', return_value=mock_response):
            response = client.post('/add-recipe', data={
                'url': 'https://www.bbcgoodfood.com/recipes/chicken-pasta-bake'
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            with Session(engine) as session:
                recipes = list(session.exec(select(Recipe)))
                assert len(recipes) == 1
                
                recipe = recipes[0]
                assert recipe.title == "Chicken pasta bake"
                assert recipe.url == "https://www.bbcgoodfood.com/recipes/chicken-pasta-bake"
                assert len(recipe.ingredients_list) > 0
                assert any("olive oil" in ingredient for ingredient in recipe.ingredients_list)
                assert recipe.instructions is not None
                assert "Heat 2 tbsp of the oil" in recipe.instructions
