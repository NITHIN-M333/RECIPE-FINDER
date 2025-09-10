from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from PIL import Image
import io, requests, traceback
import numpy as np
import tensorflow as tf

app = FastAPI()

# Allow frontend (React) to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =======================
# Load Trained Ingredient Model
# =======================
print("🔄 Loading ingredient classification model...")
model = tf.keras.models.load_model("ingredient_classifier.h5")
print("✅ Ingredient model loaded successfully.")

# Class names (from your training script)
class_names = [
    'Bean', 'Bitter_Gourd', 'Bottle_Gourd', 'Brinjal', 'Broccoli',
    'Cabbage', 'Capsicum', 'Carrot', 'Cauliflower', 'Cucumber',
    'Papaya', 'Potato', 'Pumpkin', 'Radish', 'Tomato'
]

# Spoonacular API Key
SPOONACULAR_API_KEY = "39238a0e8f6342469d58ee9bae3e05b7"  # Replace with your actual key

# =======================
# Ingredient Extraction (using classifier)
# =======================
def extract_ingredients_from_image(image_bytes: bytes):
    try:
        print("🖼️ Decoding uploaded image...")
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = img.resize((224, 224))  # resize to match model input

        # Preprocess
        img_array = np.array(img) / 255.0
        img_array = np.expand_dims(img_array, axis=0)

        print("🔍 Running ingredient classifier...")
        preds = model.predict(img_array)
        pred_idx = np.argmax(preds)
        ingredient = class_names[pred_idx]

        print(f"🍎 Predicted Ingredient: {ingredient}")
        return [ingredient]  # return list for compatibility

    except Exception as e:
        print("❌ Error in extract_ingredients_from_image:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# =======================
# Fetch Recipes from Spoonacular
# =======================
def fetch_recipes_from_spoonacular(ingredients: list[str]):
    try:
        if not ingredients:
            print("⚠️ No ingredients detected, skipping Spoonacular call.")
            return []

        ingredients_str = ",".join(ingredients)
        print(f"📡 Fetching recipes for: {ingredients_str}")

        # Step 1: Search recipes by ingredients
        url = "https://api.spoonacular.com/recipes/findByIngredients"
        params = {
            "ingredients": ingredients_str,
            "number": 5,
            "apiKey": SPOONACULAR_API_KEY,
        }
        res = requests.get(url, params=params)
        print(f"🔎 Spoonacular response status: {res.status_code}")

        if res.status_code != 200:
            print("❌ Spoonacular API error:", res.text)
            raise HTTPException(status_code=500, detail="Spoonacular API error")

        recipes = res.json()

        # Step 2: Get detailed info for each recipe
        detailed_recipes = []
        for r in recipes:
            recipe_id = r["id"]
            print(f"📄 Fetching details for recipe {recipe_id}...")

            info_url = f"https://api.spoonacular.com/recipes/{recipe_id}/information"
            info_res = requests.get(info_url, params={"apiKey": SPOONACULAR_API_KEY})
            if info_res.status_code != 200:
                print(f"❌ Failed to fetch details for recipe {recipe_id}: {info_res.text}")
                continue

            info = info_res.json()
            detailed_recipes.append({
                "title": info.get("title"),
                "image": info.get("image"),
                "ingredients": [i["name"] for i in info.get("extendedIngredients", [])],
                "steps": [
                    step["step"] for step in info.get("analyzedInstructions", [{}])[0].get("steps", [])
                ]
            })

        print(f"✅ Found {len(detailed_recipes)} recipes.")
        return detailed_recipes

    except Exception as e:
        print("❌ Error in fetch_recipes_from_spoonacular:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# =======================
# API Endpoint
# =======================
@app.post("/generate-recipes/")
async def generate_recipes(file: UploadFile = File(...)):
    try:
        print(f"📂 Received file: {file.filename}")
        image_bytes = await file.read()

        # Detect ingredient
        ingredients = extract_ingredients_from_image(image_bytes)

        # Fetch recipes
        recipes = fetch_recipes_from_spoonacular(ingredients)

        print("✅ Request completed successfully.\n")
        return {"ingredients": ingredients, "recipes": recipes}

    except Exception as e:
        print("❌ Error in generate_recipes:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
