import os
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

res = supabase.table("food_item_label").select("id, name").execute()
label_map = {row["name"]: row["id"] for row in (res.data or [])}

food_items_to_insert = []
links_to_insert = []

now_str = datetime.now(timezone.utc).isoformat()

def add_food(name, unit, weight, cals, prot, carbs, fat, labels_str):
    fid = str(uuid.uuid4())
    food_items_to_insert.append({
        "id": fid,
        "name": name,
        "nutrition_unit": unit,
        "weight_per_unit_g": weight,
        "calories": round(cals, 1),
        "protein_g": round(prot, 1),
        "carbs_g": round(carbs, 1),
        "fat_g": round(fat, 1),
        "is_verified": True,
        "created_at": now_str,
        "updated_at": now_str
    })
    for l_name in labels_str.split(","):
        l_name = l_name.strip()
        if l_name in label_map:
            links_to_insert.append({
                "food_item_id": fid,
                "food_item_label_id": label_map[l_name],
                "created_at": now_str
            })

print("Generating Combinations...")

# 1. Base Meats (6 x 6 = 36 items)
meats = [("Chicken", 165, 31, 0, 3.6, "meat,high_protein,low_carb,halal"), 
         ("Beef", 250, 26, 0, 15, "meat,high_protein,low_carb,halal"), 
         ("Turkey", 135, 30, 0, 1.5, "meat,high_protein,low_carb,low_fat,halal"), 
         ("Pork", 242, 27, 0, 14, "meat,high_protein,low_carb"), 
         ("Lamb", 294, 25, 0, 21, "meat,high_protein,low_carb,halal"), 
         ("Duck", 337, 19, 0, 28, "meat,high_protein,low_carb,halal")]
cuts = [("Breast", 0.9, 1.1), ("Thigh", 1.2, 0.9), ("Minced", 1.1, 1.0), ("Steak", 1.0, 1.0), ("Roast", 1.05, 0.95), ("Smoked", 1.1, 1.2)]

for m_name, m_cals, m_prot, m_carbs, m_fat, m_labels in meats:
    for c_name, cals_mult, prot_mult in cuts:
        add_food(f"{m_name} {c_name}", "gram", 0, m_cals*cals_mult, m_prot*prot_mult, m_carbs, m_fat*cals_mult, m_labels)

# 2. Base Fish (5 x 4 = 20 items)
fishes = [("Salmon", 208, 20, 0, 13, "fish,high_protein,low_carb,halal"), 
          ("Tuna", 132, 28, 0, 1, "fish,high_protein,low_carb,low_fat,halal"), 
          ("Cod", 82, 18, 0, 0.7, "fish,high_protein,low_carb,low_fat,halal"), 
          ("Tilapia", 96, 20, 0, 1.7, "fish,high_protein,low_carb,low_fat,halal"), 
          ("Trout", 148, 21, 0, 6.6, "fish,high_protein,low_carb,halal")]
fish_preps = [("Raw", 1.0), ("Baked", 1.1), ("Grilled", 1.1), ("Smoked", 1.2)]
for f_name, f_cals, f_prot, f_carbs, f_fat, f_labels in fishes:
    for p_name, x in fish_preps:
        add_food(f"{f_name}, {p_name}", "gram", 0, f_cals*x, f_prot*x, f_carbs*x, f_fat*x, f_labels)

# 3. Vegetables (20 x 3 = 60 items)
veg = [("Broccoli", 34, 2.8, 6.6, 0.4), ("Spinach", 23, 2.9, 3.6, 0.4), ("Carrot", 41, 0.9, 9.6, 0.2), 
       ("Tomato", 18, 0.9, 3.9, 0.2), ("Potato", 77, 2, 17, 0.1), ("Onion", 40, 1.1, 9.3, 0.1), 
       ("Garlic", 149, 6.4, 33, 0.5), ("Bell Pepper", 20, 0.9, 4.6, 0.2), ("Cucumber", 15, 0.7, 3.6, 0.1), 
       ("Zucchini", 17, 1.2, 3.1, 0.3), ("Cabbage", 25, 1.3, 5.8, 0.1), ("Cauliflower", 25, 1.9, 5, 0.3), 
       ("Asparagus", 20, 2.2, 3.9, 0.1), ("Mushroom", 22, 3.1, 3.3, 0.3), ("Lettuce", 15, 1.4, 2.9, 0.2), 
       ("Celery", 16, 0.7, 3, 0.2), ("Kale", 49, 4.3, 8.8, 0.9), ("Eggplant", 25, 1, 6, 0.2), 
       ("Sweet Potato", 86, 1.6, 20, 0.1), ("Green Beans", 31, 1.8, 7, 0.2)]
veg_preps = [("Raw", 1.0), ("Steamed", 1.05), ("Roasted", 1.3)]
for v_name, v_cals, v_prot, v_carbs, v_fat in veg:
    for p_name, x in veg_preps:
        labels = "vegetable,vegan,vegetarian,halal,high_fiber"
        if v_cals < 40 and p_name != "Roasted": labels += ",low_carb,low_fat"
        add_food(f"{v_name}, {p_name}", "gram", 0, v_cals*x, v_prot*x, v_carbs*x, v_fat*x, labels)

# 4. Fruits (25 items)
fruits = [
    ("Apple", 52, 0.3, 14, 0.2, 150), ("Banana", 89, 1.1, 23, 0.3, 118), ("Orange", 47, 0.9, 12, 0.1, 131),
    ("Strawberry", 32, 0.7, 7.7, 0.3, 12), ("Blueberry", 57, 0.7, 14, 0.3, 2), ("Mango", 60, 0.8, 15, 0.4, 200),
    ("Pineapple", 50, 0.5, 13, 0.1, 905), ("Grapes", 69, 0.7, 18, 0.2, 5), ("Watermelon", 30, 0.6, 8, 0.2, 4500),
    ("Peach", 39, 0.9, 10, 0.3, 150), ("Pear", 57, 0.4, 15, 0.1, 178), ("Cherry", 50, 1, 12, 0.3, 8),
    ("Kiwi", 61, 1.1, 15, 0.5, 69), ("Plum", 46, 0.7, 11, 0.3, 66), ("Raspberry", 52, 1.2, 12, 0.7, 5),
    ("Blackberry", 43, 1.4, 10, 0.5, 6), ("Papaya", 43, 0.5, 11, 0.3, 500), ("Cantaloupe", 34, 0.8, 8, 0.2, 1000),
    ("Avocado", 160, 2, 8.5, 15, 170), ("Grapefruit", 42, 0.8, 11, 0.1, 246), ("Lemon", 29, 1.1, 9, 0.3, 58),
    ("Lime", 30, 0.7, 11, 0.2, 67), ("Pomegranate", 83, 1.7, 19, 1.2, 282), ("Fig", 74, 0.8, 19, 0.3, 50),
    ("Apricot", 48, 1.4, 11, 0.4, 35)
]
for p_name, cals, prot, carbs, fat, w_g in fruits:
    lbls = "fruit,vegan,vegetarian,halal"
    if p_name != "Avocado": lbls += ",low_fat"
    add_food(f"{p_name}, raw", "piece", w_g, cals, prot, carbs, fat, lbls)

# 5. Dairy & Eggs (12 items)
add_food("Egg, Whole, Raw", "piece", 50, 143, 12.6, 0.7, 9.5, "egg,vegetarian,halal,high_protein,low_carb")
add_food("Egg, Whole, Boiled", "piece", 50, 155, 12.6, 1.1, 10.6, "egg,vegetarian,halal,high_protein,low_carb")
add_food("Egg, White Only", "piece", 33, 52, 10.9, 0.7, 0.2, "egg,vegetarian,halal,high_protein,low_carb,low_fat")
add_food("Milk, Whole 3.25%", "milliliter", 0, 61, 3.2, 4.8, 3.3, "dairy,vegetarian,halal")
add_food("Milk, Skim 0%", "milliliter", 0, 34, 3.4, 5, 0.1, "dairy,vegetarian,halal,low_fat")
add_food("Cheddar Cheese", "gram", 0, 402, 25, 1.3, 33, "dairy,vegetarian,halal,high_protein,low_carb")
add_food("Mozzarella Cheese", "gram", 0, 280, 28, 3.1, 17, "dairy,vegetarian,halal,high_protein,low_carb")
add_food("Greek Yogurt, Plain", "gram", 0, 59, 10, 3.6, 0.4, "dairy,vegetarian,halal,high_protein,low_carb,low_fat")
add_food("Butter", "tbsp", 14, 717, 0.9, 0.1, 81, "dairy,oil_fat,vegetarian,halal,low_carb")
add_food("Cottage Cheese", "gram", 0, 98, 11, 3.4, 4.3, "dairy,vegetarian,halal,high_protein,low_carb")

# 6. Grains, Pasta, Legumes (24 items = 12 x 2)
grains = [("White Rice", 130, 2.7, 28, 0.3), ("Brown Rice", 111, 2.6, 23, 0.9), ("Oats", 389, 16.9, 66, 6.9),
          ("Quinoa", 120, 4.4, 21, 1.9), ("Whole Wheat Bread", 247, 13, 41, 3.4), ("White Bread", 266, 9, 49, 3.2),
          ("Pasta, Regular", 131, 5, 25, 1.1), ("Pasta, Whole Wheat", 124, 5.3, 26, 0.5), ("Lentils", 116, 9, 20, 0.4),
          ("Chickpeas", 164, 8.9, 27, 2.6), ("Black Beans", 132, 8.9, 23.7, 0.5), ("Pinto Beans", 143, 9, 26, 0.6)]
g_preps = [("Dry/Raw", 1.0), ("Cooked", 0.35)]
for g_name, g_cals, g_prot, g_carbs, g_fat in grains:
    for p_name, x in g_preps:
        lbls = "vegan,vegetarian,halal,high_fiber"
        if "Bean" in g_name or "Lentil" in g_name or "Chickpea" in g_name: lbls += ",legume,high_protein"
        else: lbls += ",grain"
        # Bread doesn't really have a "Cooked" vs "Dry" state, but this is a rough generator
        add_food(f"{g_name}, {p_name}", "gram", 0, g_cals*x, g_prot*x, g_carbs*x, g_fat*x, lbls)

print(f"Total Master Food Items to spawn: {len(food_items_to_insert)}")
print(f"Total Link Joins to map: {len(links_to_insert)}")

# Insert in chunks of 50 to avoid API limits on Supabase request sizes
for i in range(0, len(food_items_to_insert), 50):
    supabase.table("food_item").insert(food_items_to_insert[i:i+50]).execute()
    
for i in range(0, len(links_to_insert), 50):
    supabase.table("food_item_label_link").insert(links_to_insert[i:i+50]).execute()

print("Database Seeding Successful!")
