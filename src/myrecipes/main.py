import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for


class Recipe:
    def __init__(self, id=None, title="", url="", ingredients=None, instructions="", image_url=""):
        self.id = id
        self.title = title
        self.url = url
        self.ingredients = ingredients or []
        self.instructions = instructions
        self.image_url = image_url


class RecipeDatabase:
    def __init__(self, db_path="recipes.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT,
                ingredients TEXT,
                instructions TEXT,
                image_url TEXT
            )
        ''')
        conn.commit()
        conn.close()
    
    def get_all_recipes(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id, title, url, ingredients, instructions, image_url FROM recipes')
        rows = cursor.fetchall()
        conn.close()
        
        recipes = []
        for row in rows:
            recipe = Recipe(
                id=row[0],
                title=row[1],
                url=row[2],
                ingredients=row[3].split('\n') if row[3] else [],
                instructions=row[4],
                image_url=row[5]
            )
            recipes.append(recipe)
        return recipes
    
    def add_recipe(self, recipe):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO recipes (title, url, ingredients, instructions, image_url)
            VALUES (?, ?, ?, ?, ?)
        ''', (recipe.title, recipe.url, '\n'.join(recipe.ingredients), recipe.instructions, recipe.image_url))
        conn.commit()
        recipe_id = cursor.lastrowid
        conn.close()
        return recipe_id


app = Flask(__name__)
db = RecipeDatabase()


@app.route('/')
def index():
    recipes = db.get_all_recipes()
    return render_template('index.html', recipes=recipes)


if __name__ == "__main__":
    app.run(debug=True)
