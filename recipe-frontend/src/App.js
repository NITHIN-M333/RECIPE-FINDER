import React, { useState } from "react";
import axios from "axios";

function App() {
  const [file, setFile] = useState(null);
  const [ingredients, setIngredients] = useState([]);
  const [recipes, setRecipes] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleUpload = async () => {
    if (!file) {
      alert("Please upload an image first!");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setLoading(true);
    setIngredients([]);
    setRecipes([]);

    try {
      const res = await axios.post("http://localhost:8000/generate-recipes/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      setIngredients(res.data.ingredients || []);
      setRecipes(res.data.recipes || []);
    } catch (err) {
      console.error("Error uploading image:", err);
      alert("Failed to fetch recipes. Check backend logs.");
    }

    setLoading(false);
  };

  return (
    <div style={{ padding: "20px", fontFamily: "Arial" }}>
      <h1>🥦 Recipe Finder</h1>

      <input type="file" accept="image/*" onChange={handleFileChange} />
      <button onClick={handleUpload} disabled={loading}>
        {loading ? "Processing..." : "Upload & Find Recipes"}
      </button>

      {ingredients.length > 0 && (
        <div>
          <h2>🧾 Detected Ingredients</h2>
          <ul>
            {ingredients.map((ing, i) => (
              <li key={i}>{ing}</li>
            ))}
          </ul>
        </div>
      )}

      {recipes.length > 0 && (
        <div>
          <h2>🍲 Suggested Recipes</h2>
          {recipes.map((r, i) => (
            <div key={i} style={{ border: "1px solid #ddd", margin: "10px 0", padding: "10px", borderRadius: "8px" }}>
              <h3>{r.title}</h3>
              {r.image && <img src={r.image} alt={r.title} width="200" />}
              <h4>Ingredients:</h4>
              <ul>
                {r.ingredients.map((ing, j) => (
                  <li key={j}>{ing}</li>
                ))}
              </ul>
              <h4>Steps:</h4>
              <ol>
                {r.steps.map((s, k) => (
                  <li key={k}>{s}</li>
                ))}
              </ol>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default App;
