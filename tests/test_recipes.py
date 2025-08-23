import pytest
from unittest.mock import patch, MagicMock
from sqlmodel import Session, select
from myrecipes.main import app
from myrecipes.models import Recipe, RecipeList, engine, create_tables


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


class TestAddRecipeToList:
    @pytest.fixture
    def client(self):
        create_tables()
        with app.test_client() as client:
            yield client

    def test_add_recipe_to_current_list(self, client):
        # First create a recipe
        test_recipe = Recipe(
            title="Spaghetti Carbonara",
            url="https://example.com/carbonara",
            ingredients='["pasta", "eggs", "cheese", "bacon"]',
            instructions="Cook pasta, mix with eggs and cheese"
        )

        with Session(engine) as session:
            session.add(test_recipe)
            session.commit()
            session.refresh(test_recipe)
            recipe_id = test_recipe.id

        # Add recipe to current list
        response = client.post(f'/add-to-list/{recipe_id}', follow_redirects=True)
        assert response.status_code == 200

        # Verify a current list was created and recipe was added
        with Session(engine) as session:
            recipe_lists = list(session.exec(select(RecipeList)))
            assert len(recipe_lists) == 1
            
            current_list = recipe_lists[0]
            assert current_list.is_current == True
            assert len(current_list.recipes) == 1
            assert current_list.recipes[0].title == "Spaghetti Carbonara"

        # Verify UI shows the recipe in the list
        response = client.get('/')
        response_text = response.data.decode('utf-8')
        assert "Current List" in response_text
        assert "Spaghetti Carbonara" in response_text

    def test_add_recipe_to_existing_current_list(self, client):
        # Create two recipes
        recipe1 = Recipe(title="Recipe 1", ingredients='["ingredient1"]')
        recipe2 = Recipe(title="Recipe 2", ingredients='["ingredient2"]')

        with Session(engine) as session:
            session.add(recipe1)
            session.add(recipe2)
            session.commit()
            session.refresh(recipe1)
            session.refresh(recipe2)

        # Add first recipe to list
        response = client.post(f'/add-to-list/{recipe1.id}', follow_redirects=True)
        assert response.status_code == 200

        # Add second recipe to same list
        response = client.post(f'/add-to-list/{recipe2.id}', follow_redirects=True)
        assert response.status_code == 200

        # Verify both recipes are in the same list
        with Session(engine) as session:
            recipe_lists = list(session.exec(select(RecipeList)))
            assert len(recipe_lists) == 1
            
            current_list = recipe_lists[0]
            assert len(current_list.recipes) == 2
            recipe_titles = [recipe.title for recipe in current_list.recipes]
            assert "Recipe 1" in recipe_titles
            assert "Recipe 2" in recipe_titles

    def test_empty_state_shows_helpful_message(self, client):
        response = client.get('/')
        response_text = response.data.decode('utf-8')
        assert "Start a list by adding a recipe from the left column" in response_text


class TestShoppingListGeneration:
    @pytest.fixture
    def client(self):
        create_tables()
        with app.test_client() as client:
            yield client

    def test_shopping_list_generation_with_mock_api(self, client):
        # Create recipes with ingredients
        recipe1 = Recipe(
            title="Pasta Dish",
            ingredients='["2 cups pasta", "1 cup tomato sauce", "1/2 cup cheese"]'
        )
        recipe2 = Recipe(
            title="Salad",
            ingredients='["1 cup lettuce", "1/2 cup cheese", "2 tomatoes"]'
        )

        with Session(engine) as session:
            session.add(recipe1)
            session.add(recipe2)
            session.commit()
            session.refresh(recipe1)
            session.refresh(recipe2)

        # Add recipes to current list
        client.post(f'/add-to-list/{recipe1.id}')
        client.post(f'/add-to-list/{recipe2.id}')

        # Get the current list
        with Session(engine) as session:
            current_list = session.exec(select(RecipeList).where(RecipeList.is_current == True)).first()
            list_id = current_list.id

        # Mock the Anthropic API call
        with patch('myrecipes.main.anthropic_client') as mock_client:
            mock_message = MagicMock()
            mock_message.content = [MagicMock()]
            mock_message.content[0].text = """PRODUCE
- 2 tomatoes
- 1 cup lettuce

DAIRY
- 1 cup cheese (combined from 1/2 cup + 1/2 cup)

PANTRY/DRY GOODS
- 2 cups pasta
- 1 cup tomato sauce"""

            mock_client.messages.create.return_value = mock_message

            # Test the shopping list generation endpoint
            response = client.get(f'/generate-shopping-list/{list_id}')
            
            assert response.status_code == 200
            response_text = response.data.decode('utf-8')
            assert "SHOPPING LIST" in response_text
            assert "PRODUCE" in response_text
            assert "DAIRY" in response_text
            assert "2 tomatoes" in response_text
            assert "1 cup cheese" in response_text
            assert "Pasta Dish, Salad" in response_text

            # Verify the API was called with correct parameters
            mock_client.messages.create.assert_called_once()
            call_args = mock_client.messages.create.call_args
            assert call_args[1]['model'] == "claude-3-haiku-20240307"
            assert call_args[1]['max_tokens'] == 1000
            assert "Pasta Dish, Salad" in call_args[1]['messages'][0]['content']
            assert "2 cups pasta" in call_args[1]['messages'][0]['content']
            assert "1 cup lettuce" in call_args[1]['messages'][0]['content']

    def test_shopping_list_generation_empty_list(self, client):
        # Create an empty recipe list
        empty_list = RecipeList(name="Empty List", is_current=True)
        
        with Session(engine) as session:
            session.add(empty_list)
            session.commit()
            session.refresh(empty_list)

        response = client.get(f'/generate-shopping-list/{empty_list.id}')
        
        assert response.status_code == 200
        response_text = response.data.decode('utf-8')
        assert "No recipes in list" in response_text

    def test_shopping_list_generation_nonexistent_list(self, client):
        response = client.get('/generate-shopping-list/999')
        assert response.status_code == 302  # Redirect to index
