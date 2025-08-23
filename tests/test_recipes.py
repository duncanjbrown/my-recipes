import pytest
from unittest.mock import patch, MagicMock
from sqlmodel import Session, select
from myrecipes.main import app
from myrecipes.models import Recipe, RecipeList, Staple, engine, create_tables


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

            # Test the shopping list generation endpoint (POST to generate)
            response = client.post(f'/generate-shopping-list/{list_id}')
            
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

        response = client.post(f'/generate-shopping-list/{empty_list.id}')
        
        assert response.status_code == 200
        response_text = response.data.decode('utf-8')
        assert "No recipes in list" in response_text

    def test_shopping_list_generation_nonexistent_list(self, client):
        response = client.post('/generate-shopping-list/999')
        assert response.status_code == 302  # Redirect to index


class TestStartNewList:
    @pytest.fixture
    def client(self):
        create_tables()
        with app.test_client() as client:
            yield client

    def test_start_new_list_closes_current_and_shows_previous_lists(self, client):
        # Create a recipe and add it to current list
        test_recipe = Recipe(
            title="Original Recipe",
            ingredients='["flour", "eggs"]'
        )

        with Session(engine) as session:
            session.add(test_recipe)
            session.commit()
            session.refresh(test_recipe)

        # Add recipe to current list (creating the current list)
        response = client.post(f'/add-to-list/{test_recipe.id}', follow_redirects=True)
        assert response.status_code == 200

        # Verify current list exists with recipe
        with Session(engine) as session:
            current_lists = list(session.exec(select(RecipeList).where(RecipeList.is_current == True)))
            assert len(current_lists) == 1
            assert len(current_lists[0].recipes) == 1
            first_list_id = current_lists[0].id

        # Start a new list
        response = client.post('/start-new-list', follow_redirects=True)
        assert response.status_code == 200

        # Verify the original list is no longer current
        with Session(engine) as session:
            original_list = session.get(RecipeList, first_list_id)
            assert original_list.is_current == False
            
            # Verify no current list exists initially (will be created when first recipe is added)
            current_lists = list(session.exec(select(RecipeList).where(RecipeList.is_current == True)))
            assert len(current_lists) == 0

        # Check that the UI shows previous lists with date/time
        response = client.get('/')
        response_text = response.data.decode('utf-8')
        
        # Should show previous lists section
        assert "PREVIOUS LISTS" in response_text
        
        # Should show a link to view the previous list (by timestamp, not recipe name)
        assert f"/view-list/{first_list_id}" in response_text

        # Verify we can add a recipe to the new current list
        new_recipe = Recipe(
            title="New Recipe",
            ingredients='["butter", "sugar"]'
        )

        with Session(engine) as session:
            session.add(new_recipe)
            session.commit()
            session.refresh(new_recipe)

        # Add recipe to new current list
        response = client.post(f'/add-to-list/{new_recipe.id}', follow_redirects=True)
        assert response.status_code == 200

        # Verify new current list exists
        with Session(engine) as session:
            current_lists = list(session.exec(select(RecipeList).where(RecipeList.is_current == True)))
            assert len(current_lists) == 1
            assert current_lists[0].id != first_list_id
            assert len(current_lists[0].recipes) == 1
            assert current_lists[0].recipes[0].title == "New Recipe"

    def test_start_new_list_button_appears_when_current_list_exists(self, client):
        # Create and add recipe to current list
        test_recipe = Recipe(title="Test Recipe", ingredients='["ingredient"]')
        
        with Session(engine) as session:
            session.add(test_recipe)
            session.commit()
            session.refresh(test_recipe)

        client.post(f'/add-to-list/{test_recipe.id}')

        # Check that START NEW LIST button appears
        response = client.get('/')
        response_text = response.data.decode('utf-8')
        assert "START NEW LIST" in response_text

    def test_previous_lists_are_accessible_via_links(self, client):
        # Create two recipes
        recipe1 = Recipe(title="Recipe 1", ingredients='["ingredient1"]')
        recipe2 = Recipe(title="Recipe 2", ingredients='["ingredient2"]')
        
        with Session(engine) as session:
            session.add(recipe1)
            session.add(recipe2)
            session.commit()
            session.refresh(recipe1)
            session.refresh(recipe2)

        # Add first recipe to current list
        client.post(f'/add-to-list/{recipe1.id}')
        
        # Get the first list ID
        with Session(engine) as session:
            first_list = session.exec(select(RecipeList).where(RecipeList.is_current == True)).first()
            first_list_id = first_list.id

        # Start new list
        client.post('/start-new-list')

        # Add second recipe to new current list  
        client.post(f'/add-to-list/{recipe2.id}')

        # Verify we can access the previous list via its ID
        response = client.get(f'/view-list/{first_list_id}')
        assert response.status_code == 200
        response_text = response.data.decode('utf-8')
        assert "Recipe 1" in response_text


class TestStaplesFeature:
    @pytest.fixture
    def client(self):
        create_tables()
        with app.test_client() as client:
            yield client

    def test_staples_end_to_end_workflow(self, client):
        # Test the complete staples workflow
        # 1. Access staples configuration page
        response = client.get('/staples')
        assert response.status_code == 200
        response_text = response.data.decode('utf-8')
        assert "STAPLES CONFIGURATION" in response_text

        # 2. Add staples to the list (test multiline functionality)
        response = client.post('/staples/add', data={
            'names': 'Butter\nCheese\nEggs'
        }, follow_redirects=True)
        assert response.status_code == 200

        # 3. Verify staples appear in configuration page
        response = client.get('/staples')
        response_text = response.data.decode('utf-8')
        assert "Butter" in response_text
        assert "Cheese" in response_text
        assert "Eggs" in response_text

        # 4. Mark one staple as checked (eggs)
        # First get the staple ID from database
        from myrecipes.models import Staple
        with Session(engine) as session:
            eggs_staple = session.exec(select(Staple).where(Staple.name == "Eggs")).first()
            eggs_id = eggs_staple.id

        response = client.post(f'/staples/toggle/{eggs_id}', follow_redirects=True)
        assert response.status_code == 200

        # 5. Create a recipe and add it to a list
        test_recipe = Recipe(
            title="Pasta Dish",
            ingredients='["2 cups pasta", "1 cup tomato sauce"]'
        )
        with Session(engine) as session:
            session.add(test_recipe)
            session.commit()
            session.refresh(test_recipe)

        # Add recipe to current list
        response = client.post(f'/add-to-list/{test_recipe.id}', follow_redirects=True)
        assert response.status_code == 200

        # 6. Get current list for shopping list generation
        with Session(engine) as session:
            current_list = session.exec(select(RecipeList).where(RecipeList.is_current == True)).first()
            list_id = current_list.id

        # 7. Generate shopping list with staples option checked
        # Mock the Anthropic API call
        with patch('myrecipes.main.anthropic_client') as mock_client:
            mock_message = MagicMock()
            mock_message.content = [MagicMock()]
            mock_message.content[0].text = """PRODUCE
- (no produce items)

DAIRY
- Butter
- Cheese

PANTRY/DRY GOODS
- 2 cups pasta  
- 1 cup tomato sauce"""

            mock_client.messages.create.return_value = mock_message

            response = client.post(f'/generate-shopping-list/{list_id}', data={
                'include_staples': 'on'
            })
            
            assert response.status_code == 200
            response_text = response.data.decode('utf-8')
            
            # Should include butter and cheese (not eggs because it's checked off)
            assert "Butter" in response_text
            assert "Cheese" in response_text
            assert "Eggs" not in response_text
            
            # Should still include recipe ingredients
            assert "2 cups pasta" in response_text
            assert "1 cup tomato sauce" in response_text

        # 8. Generate shopping list WITHOUT staples option
        with patch('myrecipes.main.anthropic_client') as mock_client:
            mock_message = MagicMock()
            mock_message.content = [MagicMock()]
            mock_message.content[0].text = """PANTRY/DRY GOODS
- 2 cups pasta
- 1 cup tomato sauce"""

            mock_client.messages.create.return_value = mock_message

            response = client.post(f'/generate-shopping-list/{list_id}')
            
            assert response.status_code == 200
            response_text = response.data.decode('utf-8')
            
            # Should NOT include any staples
            assert "Butter" not in response_text
            assert "Cheese" not in response_text
            assert "Eggs" not in response_text
            
            # Should still include recipe ingredients
            assert "2 cups pasta" in response_text
            assert "1 cup tomato sauce" in response_text

        # 9. Test removing a staple
        with Session(engine) as session:
            butter_staple = session.exec(select(Staple).where(Staple.name == "Butter")).first()
            butter_id = butter_staple.id

        response = client.post(f'/staples/remove/{butter_id}', follow_redirects=True)
        assert response.status_code == 200

        # Verify butter is removed from staples page
        response = client.get('/staples')
        response_text = response.data.decode('utf-8')
        
        # Check that Butter is not in a staple-name div (more specific check)
        import re
        butter_pattern = r'<div class="staple-name[^"]*">\s*Butter\s*</div>'
        assert not re.search(butter_pattern, response_text)
        
        # Cheese should still be there
        cheese_pattern = r'<div class="staple-name[^"]*">\s*Cheese\s*</div>'
        assert re.search(cheese_pattern, response_text)

        # 10. Test that staples configuration link appears on main page
        response = client.get('/')
        response_text = response.data.decode('utf-8')
        assert 'href="/staples"' in response_text  # Link to staples config
        assert 'name="include_staples"' in response_text  # Checkbox for including staples

    def test_staples_checkbox_toggle_functionality(self, client):
        # Test that checking/unchecking staples works correctly
        from myrecipes.models import Staple
        
        # Add a staple
        response = client.post('/staples/add', data={'names': 'Milk'}, follow_redirects=True)
        assert response.status_code == 200

        # Get staple ID
        with Session(engine) as session:
            staple = session.exec(select(Staple).where(Staple.name == "Milk")).first()
            staple_id = staple.id
            assert staple.is_checked == False  # Should start unchecked

        # Toggle to checked
        response = client.post(f'/staples/toggle/{staple_id}', follow_redirects=True)
        assert response.status_code == 200

        # Verify it's checked
        with Session(engine) as session:
            staple = session.get(Staple, staple_id)
            assert staple.is_checked == True

        # Toggle back to unchecked
        response = client.post(f'/staples/toggle/{staple_id}', follow_redirects=True)
        assert response.status_code == 200

        # Verify it's unchecked
        with Session(engine) as session:
            staple = session.get(Staple, staple_id)
            assert staple.is_checked == False

    def test_empty_staples_configuration_page(self, client):
        # Test that empty staples page shows appropriate message
        response = client.get('/staples')
        assert response.status_code == 200
        response_text = response.data.decode('utf-8')
        assert "STAPLES CONFIGURATION" in response_text
        assert "Add staples that you want to include" in response_text

    def test_multiline_staples_add(self, client):
        # Test adding multiple staples with multiline input
        from myrecipes.models import Staple
        
        # Add multiple staples in one request
        multiline_input = "Salt\nPepper\nOlive Oil\nGarlic\nOnion"
        response = client.post('/staples/add', data={'names': multiline_input}, follow_redirects=True)
        assert response.status_code == 200
        
        # Verify all staples were added to database
        with Session(engine) as session:
            salt = session.exec(select(Staple).where(Staple.name == "Salt")).first()
            pepper = session.exec(select(Staple).where(Staple.name == "Pepper")).first()
            olive_oil = session.exec(select(Staple).where(Staple.name == "Olive Oil")).first()
            garlic = session.exec(select(Staple).where(Staple.name == "Garlic")).first()
            onion = session.exec(select(Staple).where(Staple.name == "Onion")).first()
            
            assert salt is not None
            assert pepper is not None
            assert olive_oil is not None
            assert garlic is not None
            assert onion is not None
            
        # Verify they appear on the page
        response = client.get('/staples')
        response_text = response.data.decode('utf-8')
        assert "Salt" in response_text
        assert "Pepper" in response_text  
        assert "Olive Oil" in response_text
        assert "Garlic" in response_text
        assert "Onion" in response_text

    def test_multiline_staples_with_empty_lines(self, client):
        # Test multiline input with empty lines and extra whitespace
        from myrecipes.models import Staple
        
        multiline_input = "  Tomatoes  \n\n  \nBasil\n\n\nMozzarella  \n  "
        response = client.post('/staples/add', data={'names': multiline_input}, follow_redirects=True)
        assert response.status_code == 200
        
        # Verify only non-empty names were added (trimmed)
        with Session(engine) as session:
            tomatoes = session.exec(select(Staple).where(Staple.name == "Tomatoes")).first()
            basil = session.exec(select(Staple).where(Staple.name == "Basil")).first()  
            mozzarella = session.exec(select(Staple).where(Staple.name == "Mozzarella")).first()
            
            assert tomatoes is not None
            assert basil is not None
            assert mozzarella is not None
