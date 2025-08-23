# MyRecipes

This is a web application to help me build shopping lists out of recipes.

The UI has two panes. The left pane shows recipes. The right pane shows lists of recipes.

The application has no concept of meal plans, dates, lunch, dinner, etc. It only deals with the recipe database (on the left) and the lists of recipes (on the right).

It should use SQLite for the database but we will replace this with PostgreSQL later.

## Tech stack

This application should be pure python, rendered server-side.

We use uv for dependency management.

Recipes should be fetched using https://github.com/hhursev/recipe-scrapers.

Run the tests using `uv run pytest`.

## Technical approach

Test-driven development using pytest. Write an end-to-end test before implementing each user story. As you fill out the code, write further, more granular tests as appropriate.

ALWAYS write the test first!

## Code style

Use object-oriented programming.

## Cosmetics

The aesthetic should be brutalist web, i.e. default serif font everywhere, minimal styling

## Authentication

There is no authentication at this time. We will add authentication later.

## Users

There is only one user so there is no need for user management.

## Language

A RECIPE is the extracted recipe from a cooking website, provided by recipe scrapers.
A RECIPE LIST is a collection of recipes.
A COOKING INSTRUCTIONS is the full method and ingredients for a RECIPE LIST's RECIPES compiled into a single web page.
