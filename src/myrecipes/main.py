from flask import Flask, render_template, request, redirect, url_for
import requests
from recipe_scrapers import scrape_me
from sqlmodel import Session, select

from .models import Recipe, engine, create_tables


app = Flask(__name__, template_folder="../templates")

# Create tables on startup
create_tables()


@app.route('/')
def index():
    with Session(engine) as session:
        statement = select(Recipe)
        recipes = list(session.exec(statement))
    return render_template('index.html', recipes=recipes)


@app.route('/add-recipe', methods=['POST'])
def add_recipe():
    url = request.form.get('url')
    if not url:
        return redirect(url_for('index'))
    
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
        
        with Session(engine) as session:
            session.add(recipe)
            session.commit()
            
    except Exception as e:
        print(f"Error fetching recipe: {e}")
    
    return redirect(url_for('index'))


if __name__ == "__main__":
    app.run(debug=True)
