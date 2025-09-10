from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from ultralytics import YOLO
from PIL import Image
import io, requests, traceback
import torch
import pandas

app = FastAPI()

# Allow frontend (React) to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load YOLOv8 (COCO pretrained model – detects apples, bananas, oranges, etc.)
print("🔄 Loading YOLOv8 model...")
model = YOLO("yolov8n.pt")
print("✅ YOLOv8 model loaded successfully.")

# Spoonacular API Key
SPOONACULAR_API_KEY = "39238a0e8f6342469d58ee9bae3e05b7"  # Replace with your actual key

def extract_ingredients_from_image(image_bytes: bytes):
    try:
        print("🖼️ Decoding uploaded image...")
        img = Image.open(io.BytesIO(image_bytes))
        print(f"✅ Image loaded. Format={img.format}, Size={img.size}")

        print("🔍 Running YOLO model...")
        results = model(img)

        ingredients = []
        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                if conf > 0.5:  # filter low-confidence detections
                    label = model.names[cls_id]
                    ingredients.append(label)
                    print(f"🍎 Detected: {label} (conf={conf:.2f})")

        ingredients = list(set(ingredients))
        print(f"✅ Final ingredients: {ingredients}")
        return ingredients

    except Exception as e:
        print("❌ Error in extract_ingredients_from_image:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

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

@app.post("/generate-recipes/")
async def generate_recipes(file: UploadFile = File(...)):
    try:
        print(f"📂 Received file: {file.filename}")
        image_bytes = await file.read()

        # Detect ingredients
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
