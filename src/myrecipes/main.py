from flask import Flask, render_template, request, redirect, url_for, jsonify
import requests
from recipe_scrapers import scrape_me
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
import os
from anthropic import Anthropic

from .models import Recipe, RecipeList, Staple, engine, create_tables


app = Flask(__name__, template_folder="../templates")

# Initialize Claude client
anthropic_client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

# Create tables on startup
create_tables()


@app.route('/')
def index():
    with Session(engine) as session:
        statement = select(Recipe)
        recipes = list(session.exec(statement))

        # Get current list if it exists
        current_list_statement = select(RecipeList).options(
            selectinload(RecipeList.recipes)).where(RecipeList.is_current == True)
        current_list = session.exec(current_list_statement).first()

        # Get previous lists ordered by creation time
        previous_lists_statement = select(RecipeList).options(
            selectinload(RecipeList.recipes)).where(RecipeList.is_current == False).order_by(RecipeList.created_at.desc())
        previous_lists = list(session.exec(previous_lists_statement))

    return render_template('index.html', recipes=recipes, current_list=current_list, previous_lists=previous_lists)


@app.route('/add-recipe', methods=['POST'])
def add_recipe():
    urls_input = request.form.get('url')
    if not urls_input or not urls_input.strip():
        return redirect(url_for('index'))

    # Split by lines and clean up each URL
    urls = [url.strip() for url in urls_input.strip().split('\n') if url.strip()]

    with Session(engine) as session:
        for url in urls:
            try:
                scraper = scrape_me(url)

                recipe = Recipe(
                    title=scraper.title(),
                    url=url,
                    instructions=scraper.instructions()
                )
                recipe.ingredients_list = scraper.ingredients()

                if hasattr(scraper, 'image') and scraper.image():
                    recipe.image_url = scraper.image()

                session.add(recipe)

            except Exception as e:
                print(f"Error fetching recipe from {url}: {e}")
                # Continue with next URL even if one fails

        session.commit()

    return redirect(url_for('index'))


@app.route('/add-to-list/<int:recipe_id>', methods=['POST'])
def add_to_list(recipe_id):
    with Session(engine) as session:
        # Get the recipe
        recipe = session.get(Recipe, recipe_id)
        if not recipe:
            return redirect(url_for('index'))

        # Get or create current list
        current_list_statement = select(RecipeList).where(
            RecipeList.is_current == True)
        current_list = session.exec(current_list_statement).first()

        if not current_list:
            # Create new current list
            current_list = RecipeList(name="Current List", is_current=True)
            session.add(current_list)
            session.commit()
            session.refresh(current_list)

        # Add recipe to current list if not already there
        if recipe not in current_list.recipes:
            current_list.recipes.append(recipe)
            session.add(current_list)
            session.commit()

    return redirect(url_for('index'))


def generate_shopping_list(recipe_list, include_staples=False):
    """Generate a shopping list from a recipe list using Claude API"""
    if not recipe_list.recipes:
        return "No recipes in list"
    
    # Collect all ingredients from all recipes
    all_ingredients = []
    recipe_names = []
    
    for recipe in recipe_list.recipes:
        recipe_names.append(recipe.title)
        all_ingredients.extend(recipe.ingredients_list)
    
    # Add unchecked staples if requested
    if include_staples:
        with Session(engine) as session:
            unchecked_staples = list(session.exec(
                select(Staple).where(Staple.is_checked == False)
            ))
            for staple in unchecked_staples:
                all_ingredients.append(staple.name)
    
    # Read prompt template
    prompt_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'shopping_list_prompt.txt')
    with open(prompt_file_path, 'r') as f:
        prompt_template = f.read()
    
    # Format prompt
    ingredient_text = "\n".join(f"- {ingredient}" for ingredient in all_ingredients)
    recipe_names_text = ", ".join(recipe_names)
    
    prompt = prompt_template.format(
        recipe_names=recipe_names_text,
        ingredients=ingredient_text
    )

    try:
        message = anthropic_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        return message.content[0].text
    except Exception as e:
        return f"Error generating shopping list: {str(e)}"


@app.route('/generate-shopping-list/<int:list_id>', methods=['POST'])
def generate_shopping_list_page(list_id):
    with Session(engine) as session:
        # Get the recipe list with recipes
        recipe_list = session.get(RecipeList, list_id)
        if not recipe_list:
            return redirect(url_for('index'))
        
        # Load recipes
        statement = select(RecipeList).options(
            selectinload(RecipeList.recipes)).where(RecipeList.id == list_id)
        recipe_list = session.exec(statement).first()
        
        # Handle form submission - always generate shopping list
        include_staples = 'include_staples' in request.form
        shopping_list = generate_shopping_list(recipe_list, include_staples)
        
        return render_template('shopping_list.html', 
                             recipe_list=recipe_list, 
                             shopping_list=shopping_list,
                             include_staples=include_staples)


@app.route('/start-new-list', methods=['POST'])
def start_new_list():
    with Session(engine) as session:
        # Set all current lists to not current
        current_lists_statement = select(RecipeList).where(RecipeList.is_current == True)
        current_lists = list(session.exec(current_lists_statement))
        
        for current_list in current_lists:
            current_list.is_current = False
            session.add(current_list)
        
        session.commit()
    
    return redirect(url_for('index'))


@app.route('/view-list/<int:list_id>')
def view_list(list_id):
    with Session(engine) as session:
        # Get the recipe list with recipes
        statement = select(RecipeList).options(
            selectinload(RecipeList.recipes)).where(RecipeList.id == list_id)
        recipe_list = session.exec(statement).first()
        
        if not recipe_list:
            return redirect(url_for('index'))
        
        # Get all recipes and previous lists for the template
        all_recipes = list(session.exec(select(Recipe)))
        previous_lists_statement = select(RecipeList).options(
            selectinload(RecipeList.recipes)).where(RecipeList.is_current == False).order_by(RecipeList.created_at.desc())
        previous_lists = list(session.exec(previous_lists_statement))
        
        return render_template('index.html', 
                             recipes=all_recipes, 
                             current_list=None, 
                             previous_lists=previous_lists,
                             viewing_list=recipe_list)


@app.route('/staples')
def staples_config():
    with Session(engine) as session:
        staples = list(session.exec(select(Staple).order_by(Staple.name)))
    
    return render_template('staples.html', staples=staples)


@app.route('/staples/add', methods=['POST'])
def add_staple():
    names_input = request.form.get('names')
    if not names_input or not names_input.strip():
        return redirect(url_for('staples_config'))
    
    # Split by lines and clean up each name
    names = [name.strip() for name in names_input.strip().split('\n') if name.strip()]
    
    with Session(engine) as session:
        for name in names:
            # Check if staple already exists
            existing = session.exec(select(Staple).where(Staple.name == name)).first()
            if not existing:
                staple = Staple(name=name)
                session.add(staple)
        session.commit()
    
    return redirect(url_for('staples_config'))


@app.route('/staples/remove/<int:staple_id>', methods=['POST'])
def remove_staple(staple_id):
    with Session(engine) as session:
        staple = session.get(Staple, staple_id)
        if staple:
            session.delete(staple)
            session.commit()
            
            # Return JSON for AJAX requests
            if request.headers.get('Content-Type') == 'application/json':
                return jsonify({
                    'success': True,
                    'message': 'Staple removed successfully'
                })
    
    return redirect(url_for('staples_config'))


@app.route('/staples/toggle/<int:staple_id>', methods=['POST'])
def toggle_staple(staple_id):
    with Session(engine) as session:
        staple = session.get(Staple, staple_id)
        if staple:
            staple.is_checked = not staple.is_checked
            session.add(staple)
            session.commit()
            
            # Return JSON for AJAX requests
            if request.headers.get('Content-Type') == 'application/json':
                return jsonify({
                    'success': True,
                    'is_checked': staple.is_checked
                })
    
    return redirect(url_for('staples_config'))


if __name__ == "__main__":
    app.run(debug=True)
