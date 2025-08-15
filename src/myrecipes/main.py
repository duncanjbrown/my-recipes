from flask import Flask, render_template, request, redirect, url_for
from sqlmodel import Session, select
from .models import Recipe, RecipeList, engine, create_tables


app = Flask(__name__)

# Create tables on startup
create_tables()


@app.route('/')
def index():
    with Session(engine) as session:
        statement = select(Recipe)
        recipes = list(session.exec(statement))
    return render_template('index.html', recipes=recipes)


if __name__ == "__main__":
    app.run(debug=True)
