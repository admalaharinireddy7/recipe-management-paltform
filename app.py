
from flask import (
    Flask, render_template, request,
    redirect, url_for, send_file, abort
)
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
import os

load_dotenv()

app = Flask(__name__)

# ---------------- DATABASE ----------------

recipes_collection = None

mongo_uri = os.getenv("MONGO_URI")

if mongo_uri:
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        client.admin.command("ping")
        db = client["RecipeHub"]
        recipes_collection = db["recipes"]
        print("MongoDB connected successfully!")
    except Exception as e:
        print("MongoDB connection failed:", e)
else:
    print("MONGO_URI not configured. Running with demo recipes.")

# Demo data is used when MongoDB is unavailable.
demo_recipes = [
    {
        "key": "demo1",
        "name": "Chicken Biryani",
        "category": "Non-Vegetarian",
        "description": "Aromatic biryani prepared with chicken, rice and spices.",
        "time": "50 minutes",
        "servings": "3 people",
        "image": "https://images.unsplash.com/photo-1563379091339-03246963d51a?auto=format&fit=crop&w=900&q=80",
        "ingredients": ["Chicken", "Basmati rice", "Onions", "Ginger garlic paste", "Biryani masala", "Mint", "Salt"],
        "instructions": [
            "Wash and soak the rice.",
            "Marinate chicken with spices and ginger garlic paste.",
            "Cook onions and chicken in a pot.",
            "Add rice and water, then cook until done."
        ],
        "favorite": False,
        "rating": 0,
        "reviews": []
    },
    {
        "key": "demo2",
        "name": "Paneer Butter Masala",
        "category": "Vegetarian",
        "description": "Creamy paneer curry with tomato gravy and Indian spices.",
        "time": "30 minutes",
        "servings": "2 people",
        "image": "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=900&q=80",
        "ingredients": ["Paneer", "Tomatoes", "Onions", "Butter", "Cream", "Spices"],
        "instructions": [
            "Chop onions and tomatoes.",
            "Prepare a smooth tomato gravy.",
            "Add butter, spices and paneer.",
            "Simmer and finish with cream."
        ],
        "favorite": False,
        "rating": 0,
        "reviews": []
    },
    {
        "key": "demo3",
        "name": "Chocolate Cake",
        "category": "Dessert",
        "description": "Soft chocolate cake for a sweet treat.",
        "time": "45 minutes",
        "servings": "4 people",
        "image": "https://images.unsplash.com/photo-1578985545062-69928b1d9587?auto=format&fit=crop&w=900&q=80",
        "ingredients": ["Flour", "Cocoa powder", "Sugar", "Milk", "Butter", "Baking powder"],
        "instructions": [
            "Mix the dry ingredients.",
            "Add milk and melted butter.",
            "Pour into a prepared cake tin.",
            "Bake until cooked through."
        ],
        "favorite": False,
        "rating": 0,
        "reviews": []
    }
]

# ---------------- HELPERS ----------------

def get_all_recipes():
    if recipes_collection is not None:
        try:
            return [
                {**r, "key": str(r["_id"])}
                for r in recipes_collection.find()
            ]
        except Exception as e:
            print("Database read error:", e)

    return [dict(r) for r in demo_recipes]


def get_recipe(key):
    if recipes_collection is not None:
        try:
            if ObjectId.is_valid(key):
                recipe = recipes_collection.find_one({"_id": ObjectId(key)})
                if recipe:
                    recipe["key"] = str(recipe["_id"])
                    return recipe
        except Exception as e:
            print("Database lookup error:", e)

    for recipe in demo_recipes:
        if str(recipe.get("key")) == str(key):
            return recipe

    return None


def save_recipe(data, key=None):
    if recipes_collection is not None:
        try:
            if key and ObjectId.is_valid(key):
                recipes_collection.update_one(
                    {"_id": ObjectId(key)},
                    {"$set": data}
                )
            else:
                recipes_collection.insert_one(data)
            return True
        except Exception as e:
            print("Database save error:", e)
            return False

    if key:
        for recipe in demo_recipes:
            if str(recipe.get("key")) == str(key):
                recipe.update(data)
                return True

    data["key"] = "demo" + str(int(datetime.now().timestamp()))
    data.setdefault("favorite", False)
    data.setdefault("rating", 0)
    data.setdefault("reviews", [])
    demo_recipes.append(data)
    return True


def delete_recipe_data(key):
    if recipes_collection is not None:
        try:
            if ObjectId.is_valid(key):
                result = recipes_collection.delete_one({"_id": ObjectId(key)})
                return result.deleted_count > 0
        except Exception as e:
            print("Database delete error:", e)
        return False

    for recipe in demo_recipes:
        if str(recipe.get("key")) == str(key):
            demo_recipes.remove(recipe)
            return True

    return False


# ---------------- HOME & DASHBOARD ----------------

@app.route("/")
def index():
    all_recipes = get_all_recipes()

    q = request.args.get("q", "").strip().lower()
    category = request.args.get("category", "").strip().lower()
    view = request.args.get("view", "").strip()

    filtered = []

    for recipe in all_recipes:
        name = str(recipe.get("name", "")).lower()
        description = str(recipe.get("description", "")).lower()
        ingredients = str(recipe.get("ingredients", "")).lower()
        recipe_category = str(recipe.get("category", "")).lower()

        if q and q not in name and q not in description and q not in ingredients:
            continue

        if category and category not in recipe_category:
            continue

        if view == "favorites" and not recipe.get("favorite", False):
            continue

        filtered.append(recipe)

    veg_count = sum(
        1 for r in all_recipes
        if "vegetarian" in str(r.get("category", "")).lower()
        and "non" not in str(r.get("category", "")).lower()
    )
    nonveg_count = sum(
        1 for r in all_recipes
        if "non-vegetarian" in str(r.get("category", "")).lower()
        or "non vegetarian" in str(r.get("category", "")).lower()
    )
    dessert_count = sum(
        1 for r in all_recipes
        if "dessert" in str(r.get("category", "")).lower()
    )

    return render_template(
        "index.html",
        recipes=filtered,
        q=q,
        category=category,
        total_recipes=len(all_recipes),
        all_veg_count=veg_count,
        all_nonveg_count=nonveg_count,
        all_dessert_count=dessert_count
    )


# ---------------- ADD RECIPE ----------------

@app.route("/add", methods=["GET", "POST"])
def add_recipe():
    if request.method == "POST":
        ingredients = request.form.get("ingredients", "")
        instructions = request.form.get("instructions", "")

        data = {
            "name": request.form.get("name", "").strip(),
            "category": request.form.get("category", "Vegetarian"),
            "description": request.form.get("description", "").strip(),
            "time": request.form.get("time", "30 minutes"),
            "servings": request.form.get("servings", "2 people"),
            "image": request.form.get("image", "").strip(),
            "ingredients": [x.strip() for x in ingredients.splitlines() if x.strip()],
            "instructions": [x.strip() for x in instructions.splitlines() if x.strip()],
            "favorite": False,
            "rating": 0,
            "reviews": []
        }

        if not data["name"]:
            return "Recipe name is required.", 400

        if not save_recipe(data):
            return "Could not save recipe. Check your database connection.", 500

        return redirect(url_for("index"))

    return render_template("edit.html", recipe={}, action="Add")


# ---------------- EDIT RECIPE ----------------

@app.route("/edit/<key>", methods=["GET", "POST"])
def edit_recipe(key):
    recipe = get_recipe(key)

    if not recipe:
        return "Recipe not found.", 404

    if request.method == "POST":
        ingredients = request.form.get("ingredients", "")
        instructions = request.form.get("instructions", "")

        data = {
            "name": request.form.get("name", "").strip(),
            "category": request.form.get("category", "Vegetarian"),
            "description": request.form.get("description", "").strip(),
            "time": request.form.get("time", "30 minutes"),
            "servings": request.form.get("servings", "2 people"),
            "image": request.form.get("image", "").strip(),
            "ingredients": [x.strip() for x in ingredients.splitlines() if x.strip()],
            "instructions": [x.strip() for x in instructions.splitlines() if x.strip()]
        }

        if not data["name"]:
            return "Recipe name is required.", 400

        if not save_recipe(data, key):
            return "Could not update recipe.", 500

        return redirect(url_for("recipe_detail", key=key))

    return render_template("edit.html", recipe=recipe, action="Edit")


# ---------------- RECIPE DETAILS ----------------

@app.route("/recipe/<key>")
def recipe_detail(key):
    recipe = get_recipe(key)

    if not recipe:
        return "Recipe not found.", 404

    return render_template("recipe_detail.html", recipe=recipe)


# ---------------- DELETE RECIPE ----------------

@app.route("/delete/<key>")
def delete_recipe(key):
    if not delete_recipe_data(key):
        return "Recipe not found or could not be deleted.", 404

    return redirect(url_for("index"))


# ---------------- FAVORITES ----------------

@app.route("/favorite/<key>")
def toggle_favorite(key):
    recipe = get_recipe(key)

    if not recipe:
        return "Recipe not found.", 404

    new_value = not bool(recipe.get("favorite", False))

    if recipes_collection is not None:
        try:
            recipes_collection.update_one(
                {"_id": ObjectId(key)},
                {"$set": {"favorite": new_value}}
            )
        except Exception:
            return "Could not update favorite.", 500
    else:
        recipe["favorite"] = new_value

    return redirect(request.referrer or url_for("index"))


@app.route("/favorites")
def favorites_page():
    return redirect(url_for("index", view="favorites"))


# ---------------- REVIEWS & RATINGS ----------------

@app.route("/review/<key>", methods=["POST"])
def review_recipe(key):
    recipe = get_recipe(key)

    if not recipe:
        return "Recipe not found.", 404

    try:
        rating = int(request.form.get("rating", "0"))
    except ValueError:
        rating = 0

    review_text = request.form.get("review", "").strip()

    if rating not in range(1, 6) or not review_text:
        return "Please select a rating and enter a review.", 400

    reviews = list(recipe.get("reviews", []))
    reviews.append({
        "rating": rating,
        "review": review_text,
        "date": datetime.now().strftime("%d-%m-%Y")
    })

    average = round(sum(int(r.get("rating", 0)) for r in reviews) / len(reviews), 1)

    if recipes_collection is not None:
        recipes_collection.update_one(
            {"_id": ObjectId(key)},
            {"$set": {"reviews": reviews, "rating": average}}
        )
    else:
        recipe["reviews"] = reviews
        recipe["rating"] = average

    return redirect(url_for("recipe_detail", key=key))


# ---------------- PDF DOWNLOAD ----------------

@app.route("/download")
def download_recipes():
    recipes = get_all_recipes()
    buffer = BytesIO()

    pdf = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=45,
        leftMargin=45,
        topMargin=45,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()
    story = [
        Paragraph("RecipeHub - Recipe Collection", styles["Title"]),
        Spacer(1, 18)
    ]

    for number, recipe in enumerate(recipes, start=1):
        story.append(
            Paragraph(f"{number}. {recipe.get('name', 'Recipe')}", styles["Heading2"])
        )
        story.append(
            Paragraph(f"Category: {recipe.get('category', 'N/A')}", styles["Normal"])
        )
        story.append(
            Paragraph(f"Cooking time: {recipe.get('time', 'N/A')}", styles["Normal"])
        )
        story.append(
            Paragraph(str(recipe.get("description", "")), styles["BodyText"])
        )
        story.append(Spacer(1, 8))

        story.append(Paragraph("Ingredients", styles["Heading3"]))
        ingredients = recipe.get("ingredients", [])
        if isinstance(ingredients, str):
            ingredients = ingredients.splitlines()

        for ingredient in ingredients:
            story.append(Paragraph("• " + str(ingredient), styles["BodyText"]))

        story.append(Spacer(1, 8))
        story.append(Paragraph("Preparation Steps", styles["Heading3"]))

        instructions = recipe.get("instructions", recipe.get("steps", []))
        if isinstance(instructions, str):
            instructions = instructions.splitlines()

        for step_number, step in enumerate(instructions, start=1):
            story.append(
                Paragraph(f"{step_number}. {step}", styles["BodyText"])
            )

        story.append(Spacer(1, 20))

    pdf.build(story)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="RecipeHub_Recipes.pdf",
        mimetype="application/pdf"
    )


# ---------------- RUN APP ----------------

if __name__ == "__main__":
    app.run(debug=True)











