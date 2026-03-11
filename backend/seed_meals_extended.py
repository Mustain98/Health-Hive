"""
Extended meal seed script (~100 new meals).
Run from /backend:
    python seed_meals_extended.py
Idempotent – skips rows that already exist.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from sqlmodel import Session, select
from app.core.database import engine
from app.models.user import User                                # noqa
from app.models.meal_plan.plan import WeekMealPlan, DayMealPlan  # noqa
from app.models.meal_plan.food_item import (
    FoodItem, FoodItemLabel, FoodItemLabelLink, FoodItemLabelName, MeasureUnit,
)
from app.models.meal_plan.meal import (
    Meal, MealLabel, MealLabelLink, MealLabelName, MealFoodItem,
)

# ── helpers ────────────────────────────────────────────────────────────────

def get_or_create_food_label(s, name):
    obj = s.exec(select(FoodItemLabel).where(FoodItemLabel.name == name)).first()
    if not obj:
        obj = FoodItemLabel(name=name); s.add(obj); s.flush()
        print(f"  [food label+] {name}")
    return obj

def get_or_create_food_item(s, d):
    obj = s.exec(select(FoodItem).where(FoodItem.name == d["name"])).first()
    if obj:
        return obj
    obj = FoodItem(
        name=d["name"], description=d.get("desc"), nutrition_unit=d["unit"],
        weight_per_unit_g=d.get("wpug"), calories=d["cal"], protein_g=d["pro"],
        carbs_g=d["carb"], fat_g=d["fat"], is_verified=True,
    )
    s.add(obj); s.flush()
    for ln in d.get("labels", []):
        lbl = get_or_create_food_label(s, ln)
        if not s.exec(select(FoodItemLabelLink).where(
            FoodItemLabelLink.food_item_id == obj.id,
            FoodItemLabelLink.food_item_label_id == lbl.id)).first():
            s.add(FoodItemLabelLink(food_item_id=obj.id, food_item_label_id=lbl.id))
    print(f"  [food item+] {d['name']}")
    return obj

def get_or_create_meal_label(s, name):
    obj = s.exec(select(MealLabel).where(MealLabel.name == name)).first()
    if not obj:
        obj = MealLabel(name=name); s.add(obj); s.flush()
        print(f"  [meal label+] {name}")
    return obj

def insert_meal(s, d, fi_map):
    if s.exec(select(Meal).where(Meal.name == d["name"])).first():
        print(f"  [exists] {d['name']}"); return
    m = Meal(
        name=d["name"], description=d.get("desc"), instructions=d.get("instr"),
        servings=d.get("srv", 1.0), total_weight_g=d.get("wt"),
        calories=d["cal"], protein_g=d["pro"], carbs_g=d["carb"], fat_g=d["fat"],
        is_verified=True,
    )
    s.add(m); s.flush()
    for iname, qty, unit in d.get("ing", []):
        fi = fi_map.get(iname)
        if fi:
            s.add(MealFoodItem(meal_id=m.id, food_item_id=fi.id, quantity=qty, unit=unit))
        else:
            print(f"    [warn] missing food item: {iname}")
    for ln in d.get("labels", []):
        lbl = get_or_create_meal_label(s, ln)
        if not s.exec(select(MealLabelLink).where(
            MealLabelLink.meal_id == m.id,
            MealLabelLink.meal_label_id == lbl.id)).first():
            s.add(MealLabelLink(meal_id=m.id, meal_label_id=lbl.id))
    print(f"  [meal+] {d['name']}")

# ── NEW FOOD ITEMS ─────────────────────────────────────────────────────────
G = MeasureUnit.gram
ML = MeasureUnit.milliliter
PC = MeasureUnit.piece
TB = MeasureUnit.tbsp

NEW_FOOD_ITEMS = [
    # Grains
    {"name":"Cooked Basmati Rice","unit":G,"cal":130,"pro":2.7,"carb":28.2,"fat":0.3,
     "desc":"Fragrant long-grain basmati rice, boiled. Per 100 g.",
     "labels":[FoodItemLabelName.grain,FoodItemLabelName.halal,FoodItemLabelName.vegan]},
    {"name":"Whole Wheat Flour","unit":G,"cal":340,"pro":13.2,"carb":68.0,"fat":2.5,
     "desc":"Stone-ground whole wheat flour. Per 100 g.",
     "labels":[FoodItemLabelName.grain,FoodItemLabelName.vegan,FoodItemLabelName.halal]},
    {"name":"All-Purpose Flour","unit":G,"cal":364,"pro":10.3,"carb":76.3,"fat":1.0,
     "desc":"Refined white flour. Per 100 g.",
     "labels":[FoodItemLabelName.grain,FoodItemLabelName.vegan,FoodItemLabelName.halal]},
    {"name":"Cooked Brown Rice","unit":G,"cal":112,"pro":2.6,"carb":23.5,"fat":0.9,
     "desc":"Cooked whole-grain brown rice. Per 100 g.",
     "labels":[FoodItemLabelName.grain,FoodItemLabelName.vegan,FoodItemLabelName.halal,
               FoodItemLabelName.high_fiber]},
    {"name":"Cooked Pasta","unit":G,"cal":158,"pro":5.8,"carb":30.9,"fat":0.9,
     "desc":"Al-dente cooked spaghetti / penne. Per 100 g.",
     "labels":[FoodItemLabelName.grain,FoodItemLabelName.vegan,FoodItemLabelName.halal]},
    {"name":"White Bread Slice","unit":PC,"wpug":30.0,"cal":79,"pro":2.7,"carb":14.8,"fat":1.0,
     "desc":"One slice of soft white sandwich bread (~30 g).",
     "labels":[FoodItemLabelName.grain,FoodItemLabelName.vegan,FoodItemLabelName.halal]},
    {"name":"Wheat Tortilla","unit":PC,"wpug":45.0,"cal":146,"pro":4.0,"carb":25.0,"fat":3.5,
     "desc":"Medium 20 cm wheat flour tortilla (~45 g).",
     "labels":[FoodItemLabelName.grain,FoodItemLabelName.vegan,FoodItemLabelName.halal]},
    # Fats / Oils
    {"name":"Ghee","unit":TB,"wpug":13.0,"cal":117,"pro":0.0,"carb":0.0,"fat":13.0,
     "desc":"Clarified butter (desi ghee). Per 1 tbsp.",
     "labels":[FoodItemLabelName.oil_fat,FoodItemLabelName.halal,FoodItemLabelName.vegetarian,
               FoodItemLabelName.low_carb]},
    {"name":"Unsalted Butter","unit":TB,"wpug":14.0,"cal":102,"pro":0.1,"carb":0.0,"fat":11.5,
     "desc":"Unsalted dairy butter. Per 1 tbsp (~14 g).",
     "labels":[FoodItemLabelName.oil_fat,FoodItemLabelName.dairy,FoodItemLabelName.vegetarian,
               FoodItemLabelName.halal]},
    # Dairy
    {"name":"Full-Fat Plain Yogurt","unit":G,"cal":61,"pro":3.5,"carb":4.7,"fat":3.3,
     "desc":"Whole-milk plain yogurt. Per 100 g.",
     "labels":[FoodItemLabelName.dairy,FoodItemLabelName.halal,FoodItemLabelName.vegetarian]},
    {"name":"Heavy Cream","unit":ML,"cal":340,"pro":2.8,"carb":2.8,"fat":36.0,
     "desc":"Whipping/heavy cream (36 % fat). Per 100 ml.",
     "labels":[FoodItemLabelName.dairy,FoodItemLabelName.halal,FoodItemLabelName.vegetarian,
               FoodItemLabelName.low_carb]},
    {"name":"Cream Cheese","unit":G,"cal":342,"pro":6.2,"carb":4.1,"fat":34.4,
     "desc":"Full-fat block cream cheese. Per 100 g.",
     "labels":[FoodItemLabelName.dairy,FoodItemLabelName.vegetarian,FoodItemLabelName.halal,
               FoodItemLabelName.low_carb]},
    {"name":"Parmesan (Grated)","unit":G,"cal":431,"pro":38.5,"carb":4.1,"fat":29.7,
     "desc":"Finely grated aged Parmesan cheese. Per 100 g.",
     "labels":[FoodItemLabelName.dairy,FoodItemLabelName.vegetarian,FoodItemLabelName.halal,
               FoodItemLabelName.high_protein,FoodItemLabelName.low_carb]},
    {"name":"Paneer","unit":G,"cal":265,"pro":18.3,"carb":1.2,"fat":20.8,
     "desc":"Indian fresh cheese (cottage/curd cheese). Per 100 g.",
     "labels":[FoodItemLabelName.dairy,FoodItemLabelName.vegetarian,FoodItemLabelName.halal,
               FoodItemLabelName.high_protein,FoodItemLabelName.low_carb]},
    # Egg
    {"name":"Egg White","unit":PC,"wpug":33.0,"cal":17,"pro":3.6,"carb":0.2,"fat":0.1,
     "desc":"White of one large egg (~33 g). Fat-free pure protein.",
     "labels":[FoodItemLabelName.egg,FoodItemLabelName.halal,FoodItemLabelName.low_fat,
               FoodItemLabelName.low_carb]},
    # Meat
    {"name":"Mutton / Lamb (Cooked)","unit":G,"cal":258,"pro":25.6,"carb":0.0,"fat":16.6,
     "desc":"Bone-in mutton/lamb, slow-cooked. Per 100 g.",
     "labels":[FoodItemLabelName.meat,FoodItemLabelName.halal,FoodItemLabelName.high_protein,
               FoodItemLabelName.low_carb]},
    {"name":"Beef Steak (Cooked)","unit":G,"cal":271,"pro":26.1,"carb":0.0,"fat":17.7,
     "desc":"Cooked lean beef sirloin steak. Per 100 g.",
     "labels":[FoodItemLabelName.meat,FoodItemLabelName.halal,FoodItemLabelName.high_protein,
               FoodItemLabelName.low_carb]},
    # Fish / Seafood
    {"name":"Shrimp / Prawn (Cooked)","unit":G,"cal":99,"pro":24.0,"carb":0.2,"fat":0.3,
     "desc":"Boiled or steamed shrimp, peeled. Per 100 g.",
     "labels":[FoodItemLabelName.fish,FoodItemLabelName.halal,FoodItemLabelName.high_protein,
               FoodItemLabelName.low_fat,FoodItemLabelName.low_carb]},
    {"name":"Tilapia Fillet (Cooked)","unit":G,"cal":128,"pro":26.2,"carb":0.0,"fat":2.7,
     "desc":"Baked or pan-seared tilapia fillet. Per 100 g.",
     "labels":[FoodItemLabelName.fish,FoodItemLabelName.halal,FoodItemLabelName.high_protein,
               FoodItemLabelName.low_fat]},
    # Vegetables
    {"name":"Potato (Boiled)","unit":G,"cal":87,"pro":1.9,"carb":20.1,"fat":0.1,
     "desc":"Peeled boiled potato. Per 100 g.",
     "labels":[FoodItemLabelName.vegetable,FoodItemLabelName.vegan,FoodItemLabelName.halal]},
    {"name":"Onion","unit":G,"cal":40,"pro":1.1,"carb":9.3,"fat":0.1,
     "desc":"Raw white/yellow onion. Per 100 g.",
     "labels":[FoodItemLabelName.vegetable,FoodItemLabelName.vegan,FoodItemLabelName.halal]},
    {"name":"Garlic Cloves","unit":G,"cal":149,"pro":6.4,"carb":33.1,"fat":0.5,
     "desc":"Raw garlic. Per 100 g.",
     "labels":[FoodItemLabelName.spice,FoodItemLabelName.vegan,FoodItemLabelName.halal]},
    {"name":"Fresh Ginger","unit":G,"cal":80,"pro":1.8,"carb":17.8,"fat":0.8,
     "desc":"Raw ginger root. Per 100 g.",
     "labels":[FoodItemLabelName.spice,FoodItemLabelName.vegan,FoodItemLabelName.halal]},
    {"name":"Carrot","unit":G,"cal":41,"pro":0.9,"carb":9.6,"fat":0.2,
     "desc":"Raw peeled carrot. Per 100 g.",
     "labels":[FoodItemLabelName.vegetable,FoodItemLabelName.vegan,FoodItemLabelName.halal,
               FoodItemLabelName.high_fiber]},
    {"name":"White Mushroom","unit":G,"cal":22,"pro":3.1,"carb":3.3,"fat":0.3,
     "desc":"Raw white button mushroom. Per 100 g.",
     "labels":[FoodItemLabelName.vegetable,FoodItemLabelName.vegan,FoodItemLabelName.halal,
               FoodItemLabelName.low_fat,FoodItemLabelName.low_carb]},
    {"name":"Zucchini","unit":G,"cal":17,"pro":1.2,"carb":3.1,"fat":0.3,
     "desc":"Raw green zucchini (courgette). Per 100 g.",
     "labels":[FoodItemLabelName.vegetable,FoodItemLabelName.vegan,FoodItemLabelName.halal,
               FoodItemLabelName.low_fat,FoodItemLabelName.low_carb]},
    {"name":"Cucumber","unit":G,"cal":15,"pro":0.7,"carb":3.6,"fat":0.1,
     "desc":"Raw fresh cucumber. Per 100 g.",
     "labels":[FoodItemLabelName.vegetable,FoodItemLabelName.vegan,FoodItemLabelName.halal,
               FoodItemLabelName.low_fat,FoodItemLabelName.low_carb]},
    {"name":"Romaine Lettuce","unit":G,"cal":17,"pro":1.2,"carb":3.3,"fat":0.3,
     "desc":"Fresh romaine lettuce leaves. Per 100 g.",
     "labels":[FoodItemLabelName.vegetable,FoodItemLabelName.vegan,FoodItemLabelName.halal,
               FoodItemLabelName.low_fat]},
    {"name":"Avocado","unit":G,"cal":160,"pro":2.0,"carb":8.5,"fat":14.7,
     "desc":"Fresh ripe Hass avocado flesh. Per 100 g.",
     "labels":[FoodItemLabelName.fruit,FoodItemLabelName.vegan,FoodItemLabelName.halal,
               FoodItemLabelName.high_fiber,FoodItemLabelName.low_carb]},
    {"name":"Coconut Milk","unit":ML,"cal":230,"pro":2.3,"carb":5.5,"fat":23.8,
     "desc":"Full-fat canned coconut milk. Per 100 ml.",
     "labels":[FoodItemLabelName.beverage,FoodItemLabelName.vegan,FoodItemLabelName.halal,
               FoodItemLabelName.low_carb]},
    {"name":"Tomato Puree","unit":G,"cal":74,"pro":3.2,"carb":17.6,"fat":0.4,
     "desc":"Concentrated tomato puree. Per 100 g.",
     "labels":[FoodItemLabelName.vegetable,FoodItemLabelName.vegan,FoodItemLabelName.halal]},
    {"name":"Peanut Butter","unit":TB,"wpug":16.0,"cal":94,"pro":4.0,"carb":3.2,"fat":8.1,
     "desc":"Natural peanut butter. Per 1 tbsp (~16 g).",
     "labels":[FoodItemLabelName.nut_seed,FoodItemLabelName.vegan,FoodItemLabelName.halal,
               FoodItemLabelName.high_protein]},
]

# ── BATCH 1: South Asian Classics ─────────────────────────────────────────
BATCH_1 = [
    {
        "name":"Chicken Biryani",
        "desc":"Fragrant basmati rice layered with spiced chicken, caramelised onions, and saffron. A true South Asian celebration dish.",
        "instr":"1. Marinate chicken in yogurt, spices 1 h.\n2. Fry onions in ghee until golden.\n3. Par-cook basmati rice to 70%.\n4. Layer rice over chicken, seal pot, dum-cook 25 min on low heat.",
        "srv":2.0,"wt":700.0,"cal":820,"pro":48.0,"carb":90.0,"fat":26.0,
        "labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.main_meal,MealLabelName.halal,MealLabelName.high_protein],
        "ing":[("Cooked Basmati Rice",300.0,G),("Grilled Chicken Breast",200.0,G),
               ("Full-Fat Plain Yogurt",80.0,G),("Onion",80.0,G),("Ghee",2.0,TB)],
    },
    {
        "name":"Beef Biryani",
        "desc":"Slow-cooked spiced beef pieces layered with aromatic basmati rice. Rich, hearty and deeply flavoured.",
        "instr":"1. Brown beef with whole spices, onion, ginger-garlic.\n2. Add yogurt & tomato, cook 40 min until tender.\n3. Layer par-cooked rice. Dum on low heat 20 min.",
        "srv":2.0,"wt":720.0,"cal":860,"pro":46.0,"carb":88.0,"fat":30.0,
        "labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.main_meal,MealLabelName.halal,MealLabelName.high_protein],
        "ing":[("Cooked Basmati Rice",300.0,G),("Lean Ground Beef (90/10)",220.0,G),
               ("Full-Fat Plain Yogurt",80.0,G),("Onion",80.0,G),("Ghee",2.0,TB)],
    },
    {
        "name":"Vegetable Biryani",
        "desc":"Fragrant basmati rice cooked with mixed vegetables, whole spices, and ghee. A satisfying vegan celebration meal.",
        "instr":"1. Sauté onion, carrot, potato, broccoli with spices in ghee.\n2. Add par-cooked rice on top. Seal and dum-cook 15 min.",
        "srv":2.0,"wt":650.0,"cal":580,"pro":14.0,"carb":100.0,"fat":14.0,
        "labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.main_meal,MealLabelName.vegetarian,MealLabelName.halal],
        "ing":[("Cooked Basmati Rice",300.0,G),("Potato (Boiled)",120.0,G),
               ("Carrot",80.0,G),("Broccoli Florets",80.0,G),("Onion",60.0,G),("Ghee",1.5,TB)],
    },
    {
        "name":"Egg Biryani",
        "desc":"Hard-boiled eggs nestled in spiced basmati rice. Quick, protein-rich biryani variant.",
        "instr":"1. Hard-boil and peel eggs; slash lightly.\n2. Fry onions, add spices and tomato puree.\n3. Layer par-cooked rice. Add eggs on top, dum 15 min.",
        "srv":2.0,"wt":620.0,"cal":720,"pro":34.0,"carb":90.0,"fat":24.0,
        "labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.main_meal,MealLabelName.vegetarian,MealLabelName.halal,MealLabelName.high_protein],
        "ing":[("Cooked Basmati Rice",300.0,G),("Whole Egg",4.0,PC),
               ("Onion",80.0,G),("Tomato Puree",50.0,G),("Ghee",1.5,TB)],
    },
    {
        "name":"Beef Curry",
        "desc":"Tender beef pieces simmered in a rich tomato-onion-spice gravy. Classic Bangladeshi-style beef curry.",
        "instr":"1. Sear beef until browned.\n2. Add onion, ginger, garlic, whole spices; cook 5 min.\n3. Add tomato puree, yogurt, chilli. Simmer 50 min until tender.",
        "srv":2.0,"wt":500.0,"cal":620,"pro":50.0,"carb":14.0,"fat":38.0,
        "labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.main_meal,MealLabelName.halal,MealLabelName.high_protein],
        "ing":[("Lean Ground Beef (90/10)",300.0,G),("Onion",100.0,G),
               ("Tomato Puree",60.0,G),("Full-Fat Plain Yogurt",60.0,G),
               ("Extra Virgin Olive Oil",1.0,TB)],
    },
    {
        "name":"Chicken Curry",
        "desc":"Juicy chicken pieces in a golden onion-tomato-ginger gravy. Pairs perfectly with roti or rice.",
        "instr":"1. Fry onion golden. Add ginger-garlic paste.\n2. Add spices, tomato; cook until oil separates.\n3. Add chicken, cook 25 min until done.",
        "srv":2.0,"wt":480.0,"cal":540,"pro":52.0,"carb":12.0,"fat":28.0,
        "labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.main_meal,MealLabelName.halal,MealLabelName.high_protein],
        "ing":[("Grilled Chicken Breast",300.0,G),("Onion",100.0,G),
               ("Tomato Puree",60.0,G),("Extra Virgin Olive Oil",1.5,TB),
               ("Full-Fat Plain Yogurt",50.0,G)],
    },
    {
        "name":"Egg Curry",
        "desc":"Hard-boiled eggs in a spiced onion-tomato gravy. Simple, nutritious, and incredibly satisfying.",
        "instr":"1. Hard-boil eggs; halve and set aside.\n2. Fry onion, add ginger, garlic, spices, tomato puree; simmer 10 min.\n3. Add eggs, simmer 5 min. Garnish with coriander.",
        "srv":2.0,"wt":440.0,"cal":440,"pro":28.0,"carb":14.0,"fat":30.0,
        "labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.main_meal,MealLabelName.vegetarian,MealLabelName.halal,MealLabelName.high_protein],
        "ing":[("Whole Egg",4.0,PC),("Onion",100.0,G),("Tomato Puree",60.0,G),
               ("Extra Virgin Olive Oil",2.0,TB),("Full-Fat Plain Yogurt",40.0,G)],
    },
    {
        "name":"Paratha (Porota)",
        "desc":"Flaky whole-wheat layered flatbread pan-fried with ghee. Classic South Asian breakfast or side.",
        "instr":"1. Knead whole wheat flour with water; rest 20 min.\n2. Roll thin, fold with ghee, reroll. Repeat 3 times.\n3. Cook on hot tawa with ghee until golden and puffed.",
        "srv":2.0,"wt":160.0,"cal":480,"pro":10.0,"carb":64.0,"fat":20.0,
        "labels":[MealLabelName.breakfast,MealLabelName.side_meal,MealLabelName.vegetarian,MealLabelName.halal],
        "ing":[("Whole Wheat Flour",120.0,G),("Ghee",2.0,TB)],
    },
    {
        "name":"Plain Roti (Chapati)",
        "desc":"Thin unleavened whole-wheat flatbread cooked dry on a tawa. Low-fat, high-fibre everyday bread.",
        "instr":"1. Mix whole wheat flour with water into a soft dough; rest 15 min.\n2. Divide, roll into thin circles.\n3. Cook on hot tawa 1 min per side until charred spots appear.",
        "srv":3.0,"wt":180.0,"cal":360,"pro":12.0,"carb":72.0,"fat":3.0,
        "labels":[MealLabelName.breakfast,MealLabelName.side_meal,MealLabelName.vegan,MealLabelName.halal],
        "ing":[("Whole Wheat Flour",150.0,G)],
    },
    {
        "name":"Khichuri (Moong Dal & Rice)",
        "desc":"Soft one-pot comfort dish of rice and yellow moong lentils cooked with turmeric, cumin, and ghee.",
        "instr":"1. Rinse rice and lentils.\n2. Sauté cumin in ghee; add onion & turmeric.\n3. Add rice, lentils, and 3× water. Cook 20–25 min until soft and porridge-like.",
        "srv":2.0,"wt":600.0,"cal":560,"pro":22.0,"carb":96.0,"fat":10.0,
        "labels":[MealLabelName.breakfast,MealLabelName.lunch,MealLabelName.main_meal,MealLabelName.vegetarian,MealLabelName.halal],
        "ing":[("Cooked White Rice",200.0,G),("Red Lentils (Cooked)",150.0,G),
               ("Onion",60.0,G),("Ghee",1.5,TB)],
    },
]

# ── SEED ──────────────────────────────────────────────────────────────────

BATCH_2 = [
    {"name":"Mutton Curry","desc":"Slow-cooked bone-in mutton in spiced onion-tomato gravy.","instr":"1. Fry onion.\n2. Brown mutton with ginger-garlic, spices.\n3. Add tomato puree, yogurt. Pressure cook 30 min.","srv":2.0,"wt":480.0,"cal":660,"pro":50.0,"carb":12.0,"fat":44.0,"labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.main_meal,MealLabelName.halal,MealLabelName.high_protein],"ing":[("Mutton / Lamb (Cooked)",300.0,G),("Onion",100.0,G),("Tomato Puree",60.0,G),("Full-Fat Plain Yogurt",60.0,G),("Extra Virgin Olive Oil",1.5,TB)]},
    {"name":"Tilapia Fish Curry","desc":"Flaky tilapia in a tangy mustard-turmeric gravy. Classic Bengali-style fish curry.","instr":"1. Marinate fish with turmeric and salt.\n2. Fry onion, add spices and tomato puree.\n3. Add fish, simmer 10 min.","srv":2.0,"wt":450.0,"cal":380,"pro":52.0,"carb":10.0,"fat":14.0,"labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.main_meal,MealLabelName.halal,MealLabelName.high_protein],"ing":[("Tilapia Fillet (Cooked)",300.0,G),("Onion",80.0,G),("Tomato Puree",50.0,G),("Extra Virgin Olive Oil",1.0,TB)]},
    {"name":"Prawn Masala","desc":"Juicy prawns cooked in a bold onion-tomato-coconut masala. Bold South Asian flavours.","instr":"1. Sauté onion and garlic.\n2. Add spices and tomato puree, cook 5 min.\n3. Add prawns and coconut milk, simmer 8 min.","srv":2.0,"wt":420.0,"cal":380,"pro":48.0,"carb":10.0,"fat":16.0,"labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.main_meal,MealLabelName.halal,MealLabelName.high_protein],"ing":[("Shrimp / Prawn (Cooked)",280.0,G),("Onion",80.0,G),("Coconut Milk",60.0,ML),("Tomato Puree",40.0,G),("Extra Virgin Olive Oil",1.0,TB)]},
    {"name":"Butter Chicken","desc":"Tender chicken in a rich, creamy tomato-butter sauce. North Indian restaurant favourite.","instr":"1. Marinate chicken in yogurt and spices, grill 15 min.\n2. Sauté garlic-ginger, add tomato puree, cream, butter, spices. Simmer 10 min.\n3. Add grilled chicken, simmer 5 min.","srv":2.0,"wt":500.0,"cal":680,"pro":52.0,"carb":16.0,"fat":42.0,"labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.main_meal,MealLabelName.halal,MealLabelName.high_protein],"ing":[("Grilled Chicken Breast",280.0,G),("Tomato Puree",80.0,G),("Heavy Cream",60.0,ML),("Unsalted Butter",2.0,TB),("Full-Fat Plain Yogurt",50.0,G)]},
    {"name":"Dal Makhani","desc":"Creamy black lentil dal slow-simmered overnight with butter and cream. Indulgent vegetarian comfort food.","instr":"1. Soak and boil black lentils until very soft.\n2. Add tomato puree, butter, cream, spices.\n3. Simmer 20 min on low heat until thick and creamy.","srv":2.0,"wt":500.0,"cal":520,"pro":22.0,"carb":56.0,"fat":22.0,"labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.main_meal,MealLabelName.vegetarian,MealLabelName.halal],"ing":[("Black Beans (Cooked)",250.0,G),("Tomato Puree",70.0,G),("Heavy Cream",50.0,ML),("Unsalted Butter",2.0,TB),("Onion",60.0,G)]},
    {"name":"Palak Paneer","desc":"Indian cottage cheese cubes in a smooth, spiced spinach purée. Classic vegetarian main dish.","instr":"1. Blanch and blend spinach.\n2. Sauté onion, ginger, garlic, add spices.\n3. Add spinach purée and paneer cubes. Simmer 8 min, finish with cream.","srv":2.0,"wt":450.0,"cal":560,"pro":28.0,"carb":14.0,"fat":42.0,"labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.main_meal,MealLabelName.vegetarian,MealLabelName.halal,MealLabelName.high_protein],"ing":[("Paneer",200.0,G),("Baby Spinach",200.0,G),("Onion",80.0,G),("Heavy Cream",40.0,ML),("Ghee",1.5,TB)]},
    {"name":"Aloo Bhaji","desc":"Spiced stir-fried potatoes with onion, green chilli, and mustard seeds. Classic vegan side or breakfast.","instr":"1. Boil and dice potatoes.\n2. Temperate mustard seeds in oil, add onion and chilli.\n3. Add potatoes, turmeric, salt. Stir-fry 5 min.","srv":2.0,"wt":380.0,"cal":360,"pro":7.0,"carb":64.0,"fat":10.0,"labels":[MealLabelName.breakfast,MealLabelName.side_meal,MealLabelName.vegan,MealLabelName.halal],"ing":[("Potato (Boiled)",300.0,G),("Onion",60.0,G),("Extra Virgin Olive Oil",1.5,TB)]},
    {"name":"Chana Masala","desc":"Boldly spiced chickpeas in tangy onion-tomato gravy. High-protein vegan classic.","instr":"1. Fry onion until golden, add ginger-garlic paste.\n2. Add tomato puree and spices, cook 5 min.\n3. Add chickpeas, simmer 15 min.","srv":2.0,"wt":480.0,"cal":480,"pro":24.0,"carb":70.0,"fat":12.0,"labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.main_meal,MealLabelName.vegan,MealLabelName.halal,MealLabelName.high_protein],"ing":[("Cooked Chickpeas",280.0,G),("Tomato Puree",70.0,G),("Onion",80.0,G),("Extra Virgin Olive Oil",1.5,TB)]},
    {"name":"Sheekh Kebab","desc":"Minced beef mixed with spices and herbs, shaped on skewers and grilled. Perfect starter or snack.","instr":"1. Mix ground beef with onion, garlic, spices, fresh herbs.\n2. Shape around skewers.\n3. Grill or pan-fry on high heat 8–10 min, turning often.","srv":2.0,"wt":300.0,"cal":480,"pro":44.0,"carb":6.0,"fat":30.0,"labels":[MealLabelName.snack,MealLabelName.halal,MealLabelName.high_protein,MealLabelName.low_carb],"ing":[("Lean Ground Beef (90/10)",250.0,G),("Onion",40.0,G),("Extra Virgin Olive Oil",1.0,TB)]},
    {"name":"Naan Bread","desc":"Soft leavened flatbread baked in a tandoor-style oven, brushed with butter. Classic accompaniment.","instr":"1. Mix flour, yogurt, yeast, salt; knead and rest 1 h.\n2. Roll into ovals.\n3. Cook on very hot cast-iron pan 2 min per side. Brush with butter.","srv":2.0,"wt":200.0,"cal":500,"pro":14.0,"carb":84.0,"fat":13.0,"labels":[MealLabelName.side_meal,MealLabelName.vegetarian,MealLabelName.halal],"ing":[("All-Purpose Flour",160.0,G),("Full-Fat Plain Yogurt",50.0,G),("Unsalted Butter",1.5,TB)]},
]

BATCH_3 = [
    {"name":"Spaghetti Bolognese","desc":"Classic Italian pasta with a rich, slow-cooked beef and tomato ragù.","instr":"1. Brown beef with onion, carrot, garlic.\n2. Add tomato puree, herbs, simmer 30 min.\n3. Serve over boiled pasta, top with Parmesan.","srv":1.0,"wt":450.0,"cal":580,"pro":34.0,"carb":65.0,"fat":18.0,"labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.main_meal,MealLabelName.halal],"ing":[("Cooked Pasta",150.0,G),("Lean Ground Beef (90/10)",120.0,G),("Tomato Puree",80.0,G),("Onion",40.0,G),("Carrot",40.0,G),("Parmesan (Grated)",10.0,G)]},
    {"name":"Creamy Mushroom Pasta","desc":"Vegetarian pasta dish in a rich garlic and mushroom cream sauce.","instr":"1. Sauté mushrooms and garlic in butter.\n2. Add heavy cream, simmer until slightly thickened.\n3. Toss with cooked pasta and top with Parmesan.","srv":1.0,"wt":400.0,"cal":540,"pro":16.0,"carb":48.0,"fat":32.0,"labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.main_meal,MealLabelName.vegetarian,MealLabelName.halal],"ing":[("Cooked Pasta",150.0,G),("White Mushroom",120.0,G),("Heavy Cream",60.0,ML),("Unsalted Butter",1.0,TB),("Garlic Cloves",10.0,G),("Parmesan (Grated)",10.0,G)]},
    {"name":"Chicken & Broccoli Stir-Fry","desc":"Quick and healthy Asian-style stir-fry with lean chicken and broccoli.","instr":"1. Stir-fry chicken with garlic and ginger until browned.\n2. Add broccoli, stir-fry 3 min.\n3. Serve over boiled rice.","srv":1.0,"wt":420.0,"cal":460,"pro":42.0,"carb":45.0,"fat":12.0,"labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.main_meal,MealLabelName.halal,MealLabelName.high_protein],"ing":[("Grilled Chicken Breast",150.0,G),("Broccoli Florets",120.0,G),("Cooked Basmati Rice",120.0,G),("Garlic Cloves",10.0,G),("Extra Virgin Olive Oil",1.0,TB)]},
    {"name":"Vegetable Stir-Fry with Tofu","desc":"Vegan stir-fry with mixed vegetables and protein-rich tofu (paneer sub used here).","instr":"1. Pan-fry paneer cubes until golden.\n2. Stir-fry zucchini, mushroom, carrot, onion.\n3. Toss together with soy sauce/spices, serve over rice.","srv":1.0,"wt":450.0,"cal":520,"pro":22.0,"carb":52.0,"fat":26.0,"labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.main_meal,MealLabelName.vegetarian,MealLabelName.halal],"ing":[("Paneer",100.0,G),("Cooked Brown Rice",120.0,G),("Zucchini",80.0,G),("White Mushroom",60.0,G),("Carrot",60.0,G),("Extra Virgin Olive Oil",1.0,TB)]},
    {"name":"Steak Salad with Avocado","desc":"Grilled beef steak strips over fresh romaine lettuce with sliced avocado.","instr":"1. Slice cooked steak.\n2. Toss romaine, cucumber, and avocado.\n3. Top with steak and dress with olive oil.","srv":1.0,"wt":380.0,"cal":560,"pro":32.0,"carb":12.0,"fat":44.0,"labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.main_meal,MealLabelName.halal,MealLabelName.high_protein,MealLabelName.low_carb],"ing":[("Beef Steak (Cooked)",120.0,G),("Romaine Lettuce",80.0,G),("Avocado",100.0,G),("Cucumber",60.0,G),("Extra Virgin Olive Oil",1.0,TB)]},
]

BATCH_4 = [
    {"name":"Garlic Butter Shrimp","desc":"Succulent shrimp seared in garlic butter, served with a side of steamed veggies.","instr":"1. Sauté garlic in butter.\n2. Add shrimp, cook 2 min per side until pink.\n3. Serve hot with steamed zucchini.","srv":1.0,"wt":320.0,"cal":340,"pro":36.0,"carb":6.0,"fat":18.0,"labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.main_meal,MealLabelName.halal,MealLabelName.high_protein,MealLabelName.low_carb],"ing":[("Shrimp / Prawn (Cooked)",150.0,G),("Zucchini",120.0,G),("Unsalted Butter",1.5,TB),("Garlic Cloves",15.0,G)]},
    {"name":"Salmon & Asparagus Foil Pack","desc":"Healthy baked salmon with vegetables, perfect for easy clean-up.","instr":"1. Place salmon, zucchini, and cherry tomatoes on foil.\n2. Drizzle olive oil, seal pack.\n3. Bake at 200°C for 15-20 min.","srv":1.0,"wt":350.0,"cal":420,"pro":34.0,"carb":8.0,"fat":26.0,"labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.main_meal,MealLabelName.halal,MealLabelName.high_protein,MealLabelName.low_carb],"ing":[("Atlantic Salmon Fillet",150.0,G),("Zucchini",100.0,G),("Cherry Tomatoes",80.0,G),("Extra Virgin Olive Oil",1.0,TB)]},
    {"name":"Chicken & Avocado Wrap","desc":"Grilled chicken, avocado, and lettuce wrapped in a wheat tortilla.","instr":"1. Mash half the avocado on the tortilla.\n2. Add sliced chicken and lettuce.\n3. Roll tightly and slice in half.","srv":1.0,"wt":280.0,"cal":460,"pro":35.0,"carb":30.0,"fat":22.0,"labels":[MealLabelName.lunch,MealLabelName.snack,MealLabelName.halal,MealLabelName.high_protein],"ing":[("Grilled Chicken Breast",100.0,G),("Avocado",80.0,G),("Wheat Tortilla",1.0,PC),("Romaine Lettuce",40.0,G)]},
    {"name":"Egg Salad Sandwich","desc":"Classic egg salad made with boiled eggs and a touch of yogurt on wheat bread.","instr":"1. Mash boiled eggs with yogurt, salt, and pepper.\n2. Spread on white bread slices.\n3. Top with lettuce.","srv":1.0,"wt":250.0,"cal":380,"pro":20.0,"carb":34.0,"fat":16.0,"labels":[MealLabelName.breakfast,MealLabelName.lunch,MealLabelName.vegetarian,MealLabelName.halal],"ing":[("Whole Egg",2.0,PC),("Full-Fat Plain Yogurt",40.0,G),("White Bread Slice",2.0,PC),("Romaine Lettuce",30.0,G)]},
    {"name":"Peanut Butter & Banana Toast","desc":"Quick energy boost: wheat bread topped with peanut butter and banana slices.","instr":"1. Toast bread.\n2. Spread peanut butter evenly.\n3. Top with sliced banana.","srv":1.0,"wt":200.0,"cal":360,"pro":12.0,"carb":52.0,"fat":14.0,"labels":[MealLabelName.breakfast,MealLabelName.snack,MealLabelName.vegan,MealLabelName.halal],"ing":[("White Bread Slice",2.0,PC),("Peanut Butter",1.5,TB),("Banana",0.5,PC)]},
]

BATCH_5 = [
    {"name":"Creamy Tomato Soup","desc":"Rich, comforting tomato soup made from scratch.","instr":"1. Sauté onion and garlic.\n2. Add tomato puree and water, simmer 20 min.\n3. Blend until smooth, finish with heavy cream.","srv":1.0,"wt":350.0,"cal":280,"pro":4.0,"carb":22.0,"fat":20.0,"labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.side_meal,MealLabelName.vegetarian,MealLabelName.halal],"ing":[("Tomato Puree",200.0,G),("Onion",80.0,G),("Garlic Cloves",10.0,G),("Heavy Cream",40.0,ML),("Extra Virgin Olive Oil",0.5,TB)]},
    {"name":"Mushroom Risotto (Faux)","desc":"Creamy rice dish cooked slowly with white mushrooms and Parmesan.","instr":"1. Sauté onions and mushrooms in butter.\n2. Add basmati rice, stirring in water gradually.\n3. Finish with Parmesan cheese.","srv":1.0,"wt":380.0,"cal":480,"pro":12.0,"carb":65.0,"fat":18.0,"labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.main_meal,MealLabelName.vegetarian,MealLabelName.halal],"ing":[("Cooked Basmati Rice",180.0,G),("White Mushroom",120.0,G),("Onion",40.0,G),("Unsalted Butter",1.5,TB),("Parmesan (Grated)",15.0,G)]},
    {"name":"Grilled Cheese Sandwich","desc":"Classic comfort food: melted cheddar between toasted white bread.","instr":"1. Butter the outside of two bread slices.\n2. Place cheddar inside, grill on a pan until golden and melted.","srv":1.0,"wt":160.0,"cal":420,"pro":18.0,"carb":30.0,"fat":24.0,"labels":[MealLabelName.lunch,MealLabelName.snack,MealLabelName.vegetarian,MealLabelName.halal],"ing":[("White Bread Slice",2.0,PC),("Cheddar Cheese",50.0,G),("Unsalted Butter",1.0,TB)]},
    {"name":"Greek Salad","desc":"Fresh Mediterranean salad with cucumber, tomato, onion, and a light dressing.","instr":"1. Chop cucumber, tomatoes, and onion.\n2. Toss with olive oil and a dash of lemon juice.","srv":1.0,"wt":280.0,"cal":180,"pro":3.0,"carb":14.0,"fat":14.0,"labels":[MealLabelName.lunch,MealLabelName.side_meal,MealLabelName.vegan,MealLabelName.halal],"ing":[("Cucumber",100.0,G),("Cherry Tomatoes",100.0,G),("Onion",40.0,G),("Extra Virgin Olive Oil",1.0,TB)]},
    {"name":"Lentil & Vegetable Stew","desc":"Hearty, warming stew with red lentils, carrots, and potatoes.","instr":"1. Sauté onions and carrots.\n2. Add potatoes, lentils, and water. Simmer 30 min until soft.","srv":1.0,"wt":450.0,"cal":360,"pro":16.0,"carb":65.0,"fat":4.0,"labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.main_meal,MealLabelName.vegan,MealLabelName.halal],"ing":[("Red Lentils (Cooked)",150.0,G),("Potato (Boiled)",120.0,G),("Carrot",80.0,G),("Onion",60.0,G),("Extra Virgin Olive Oil",0.25,TB)]},
]

BATCH_6 = [
    {"name":"Avocado Toast with Egg","desc":"Trendy and nutritious: mashed avocado on toast topped with a boiled egg.","instr":"1. Toast wheat bread.\n2. Mash avocado and spread on toast.\n3. Slice boiled egg and place on top.","srv":1.0,"wt":220.0,"cal":380,"pro":14.0,"carb":25.0,"fat":24.0,"labels":[MealLabelName.breakfast,MealLabelName.lunch,MealLabelName.vegetarian,MealLabelName.halal],"ing":[("White Bread Slice",1.0,PC),("Avocado",80.0,G),("Whole Egg",1.0,PC)]},
    {"name":"Beef & Broccoli Bowl","desc":"Savory beef strips stir-fried with broccoli florets, served over rice.","instr":"1. Stir-fry beef until browned.\n2. Add broccoli, soy sauce (or alternative), cook 4 min.\n3. Serve over boiled rice.","srv":1.0,"wt":450.0,"cal":520,"pro":38.0,"carb":42.0,"fat":20.0,"labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.main_meal,MealLabelName.halal,MealLabelName.high_protein],"ing":[("Beef Steak (Cooked)",120.0,G),("Broccoli Florets",150.0,G),("Cooked Basmati Rice",150.0,G),("Extra Virgin Olive Oil",1.0,TB)]},
    {"name":"Chicken Tikka Wrap","desc":"Spiced grilled chicken wrapped in a flatbread with yogurt and onions.","instr":"1. Marinate and grill chicken breast.\n2. Spread yogurt on tortilla.\n3. Add chicken and onions, roll up.","srv":1.0,"wt":300.0,"cal":480,"pro":44.0,"carb":34.0,"fat":16.0,"labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.halal,MealLabelName.high_protein],"ing":[("Grilled Chicken Breast",120.0,G),("Wheat Tortilla",1.0,PC),("Full-Fat Plain Yogurt",40.0,G),("Onion",40.0,G)]},
    {"name":"Paneer Tikka Masala","desc":"Grilled paneer cubes in a spiced tomato-cream sauce.","instr":"1. Sauté onion and garlic.\n2. Add tomato puree, cream, spices, simmer 10 min.\n3. Add paneer cubes, cook 5 min.","srv":1.0,"wt":400.0,"cal":540,"pro":26.0,"carb":20.0,"fat":40.0,"labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.main_meal,MealLabelName.vegetarian,MealLabelName.halal,MealLabelName.high_protein],"ing":[("Paneer",120.0,G),("Tomato Puree",100.0,G),("Onion",60.0,G),("Heavy Cream",40.0,ML),("Extra Virgin Olive Oil",1.0,TB)]},
    {"name":"Apple & Peanut Butter Slices","desc":"Simple, refreshing snack of crisp apple slices dipped in peanut butter.","instr":"1. Core and slice the apple.\n2. Serve with peanut butter for dipping.","srv":1.0,"wt":230.0,"cal":240,"pro":6.0,"carb":32.0,"fat":12.0,"labels":[MealLabelName.snack,MealLabelName.vegan,MealLabelName.halal],"ing":[("Apple",1.0,PC),("Peanut Butter",1.5,TB)]},
]

BATCH_7 = [
    {"name":"Spicy Tuna Sushi Bowl","desc":"Deconstructed sushi roll with rice, tuna, cucumber, and avocado.","instr":"1. Season rice with vinegar (optional).\n2. Top with canned tuna, sliced avocado, and cucumber.\n3. Drizzle with soy sauce and serve cold.","srv":1.0,"wt":380.0,"cal":460,"pro":32.0,"carb":42.0,"fat":16.0,"labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.main_meal,MealLabelName.halal,MealLabelName.high_protein],"ing":[("Cooked White Rice",150.0,G),("Canned Tuna in Water",100.0,G),("Avocado",60.0,G),("Cucumber",60.0,G)]},
    {"name":"Caprese Pasta Salad","desc":"Cold pasta salad with cherry tomatoes, mozzarella (paneer sub), and fresh basil.","instr":"1. Toss cooked pasta with halved tomatoes and paneer cubes.\n2. Drizzle with olive oil and season.","srv":1.0,"wt":350.0,"cal":510,"pro":20.0,"carb":45.0,"fat":28.0,"labels":[MealLabelName.lunch,MealLabelName.side_meal,MealLabelName.vegetarian,MealLabelName.halal],"ing":[("Cooked Pasta",150.0,G),("Cherry Tomatoes",100.0,G),("Paneer",80.0,G),("Extra Virgin Olive Oil",1.0,TB)]},
    {"name":"Beef Fajita Wraps","desc":"Sizzling beef strips with onions and peppers, wrapped in a tortilla.","instr":"1. Stir-fry beef strips, sliced onion, and bell pepper with fajita spices.\n2. Serve wrapped in a warm tortilla.","srv":1.0,"wt":300.0,"cal":540,"pro":35.0,"carb":35.0,"fat":26.0,"labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.halal,MealLabelName.high_protein],"ing":[("Beef Steak (Cooked)",120.0,G),("Wheat Tortilla",1.0,PC),("Red Bell Pepper",50.0,G),("Onion",50.0,G),("Extra Virgin Olive Oil",1.0,TB)]},
    {"name":"Creamy Spinach Chicken","desc":"Pan-seared chicken breast smothered in a garlic-spinach cream sauce.","instr":"1. Sear chicken until cooked through.\n2. In same pan, add garlic, spinach, and cream; simmer slightly.\n3. Pour sauce over chicken.","srv":1.0,"wt":320.0,"cal":440,"pro":45.0,"carb":6.0,"fat":26.0,"labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.main_meal,MealLabelName.halal,MealLabelName.high_protein,MealLabelName.low_carb],"ing":[("Grilled Chicken Breast",150.0,G),("Baby Spinach",100.0,G),("Heavy Cream",40.0,ML),("Garlic Cloves",10.0,G),("Extra Virgin Olive Oil",0.5,TB)]},
    {"name":"Classic French Omelette","desc":"Tender, buttery rolled omelette made with three eggs.","instr":"1. Whisk eggs thoroughly.\n2. Melt butter in pan, add eggs, stir constantly over medium heat.\n3. Roll it up when softly set and serve.","srv":1.0,"wt":200.0,"cal":310,"pro":20.0,"carb":2.0,"fat":25.0,"labels":[MealLabelName.breakfast,MealLabelName.snack,MealLabelName.vegetarian,MealLabelName.halal,MealLabelName.high_protein,MealLabelName.low_carb],"ing":[("Whole Egg",3.0,PC),("Unsalted Butter",1.0,TB)]},
]

BATCH_8 = [
    {"name":"Mashed Potato & Gravy Bowl","desc":"Ultimate comfort side: creamy mashed potatoes with a touch of butter.","instr":"1. Mash boiled potatoes with butter and a splash of milk.\n2. Season generously.","srv":1.0,"wt":200.0,"cal":240,"pro":4.0,"carb":30.0,"fat":12.0,"labels":[MealLabelName.side_meal,MealLabelName.vegetarian,MealLabelName.halal],"ing":[("Potato (Boiled)",180.0,G),("Unsalted Butter",1.0,TB),("Whole Milk",20.0,ML)]},
    {"name":"Crispy Baked Chicken Wings","desc":"Baked chicken pieces (breast sub used) coated with spices until crispy.","instr":"1. Cut chicken into bite sizes.\n2. Coat in oil and spices, bake at 220°C for 25 mins.","srv":1.0,"wt":200.0,"cal":380,"pro":46.0,"carb":0.0,"fat":20.0,"labels":[MealLabelName.snack,MealLabelName.main_meal,MealLabelName.halal,MealLabelName.high_protein,MealLabelName.low_carb],"ing":[("Grilled Chicken Breast",180.0,G),("Extra Virgin Olive Oil",1.0,TB)]},
    {"name":"Coconut Rice & Shrimp","desc":"Jasmine-style rice cooked in coconut milk, paired with garlic shrimp.","instr":"1. Mix rice with coconut milk.\n2. Sauté shrimp in oil.\n3. Plate together.","srv":1.0,"wt":350.0,"cal":510,"pro":28.0,"carb":45.0,"fat":24.0,"labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.main_meal,MealLabelName.halal],"ing":[("Cooked Basmati Rice",150.0,G),("Coconut Milk",60.0,ML),("Shrimp / Prawn (Cooked)",120.0,G),("Extra Virgin Olive Oil",0.5,TB)]},
    {"name":"Loaded Sweet Potato","desc":"Baked sweet potato stuffed with black beans and Cheddar cheese.","instr":"1. Bake sweet potato until soft.\n2. Split open, top with warm black beans and grated cheese.","srv":1.0,"wt":350.0,"cal":420,"pro":18.0,"carb":55.0,"fat":14.0,"labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.vegetarian,MealLabelName.halal],"ing":[("Sweet Potato",200.0,G),("Black Beans (Cooked)",100.0,G),("Cheddar Cheese",30.0,G)]},
    {"name":"Oats & Yogurt Breakfast Jar","desc":"Make-ahead jar of oats, yogurt, milk, and chia seeds.","instr":"1. Mix oats, milk, yogurt, and chia seeds in a jar.\n2. Refrigerate overnight.","srv":1.0,"wt":300.0,"cal":320,"pro":15.0,"carb":48.0,"fat":8.0,"labels":[MealLabelName.breakfast,MealLabelName.vegetarian,MealLabelName.halal],"ing":[("Rolled Oats",50.0,G),("Full-Fat Plain Yogurt",100.0,G),("Skimmed Milk",100.0,ML),("Chia Seeds",10.0,G)]},
]

BATCH_9 = [
    {"name":"Zucchini Noodles with Prawns","desc":"Low-carb \"zoodles\" with garlic prawns and cherry tomatoes.","instr":"1. Spiralize zucchini into noodles.\n2. Sauté prawns and tomatoes in oil.\n3. Toss in zoodles for the last 1 min (do not overcook).","srv":1.0,"wt":350.0,"cal":250,"pro":28.0,"carb":12.0,"fat":10.0,"labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.main_meal,MealLabelName.halal,MealLabelName.high_protein,MealLabelName.low_carb],"ing":[("Zucchini",200.0,G),("Shrimp / Prawn (Cooked)",120.0,G),("Cherry Tomatoes",50.0,G),("Extra Virgin Olive Oil",0.5,TB)]},
    {"name":"Tuna Melt Flatbread","desc":"Canned tuna mixed with light mayo, topped with cheddar, melted on wheat tortilla.","instr":"1. Spread tuna mix on the tortilla.\n2. Top with cheese, grill until melted.","srv":1.0,"wt":220.0,"cal":380,"pro":28.0,"carb":26.0,"fat":18.0,"labels":[MealLabelName.lunch,MealLabelName.snack,MealLabelName.halal,MealLabelName.high_protein],"ing":[("Wheat Tortilla",1.0,PC),("Canned Tuna in Water",100.0,G),("Cheddar Cheese",30.0,G),("Full-Fat Plain Yogurt",20.0,G)]},
    {"name":"Berry & Spinach Smoothie","desc":"Nutrient-packed smoothie blending spinach, berries, milk, and peanut butter.","instr":"1. Combine all ingredients in a blender.\n2. Blend until perfectly smooth.","srv":1.0,"wt":350.0,"cal":280,"pro":12.0,"carb":30.0,"fat":14.0,"labels":[MealLabelName.breakfast,MealLabelName.drink,MealLabelName.snack,MealLabelName.vegetarian,MealLabelName.halal],"ing":[("Baby Spinach",50.0,G),("Blueberries",80.0,G),("Skimmed Milk",200.0,ML),("Peanut Butter",1.0,TB)]},
    {"name":"Chicken & Bean Quesadilla","desc":"Grilled tortilla stuffed with chopped chicken and black beans.","instr":"1. Place chicken and beans inside folded tortilla.\n2. Pan-toast both sides until crispy.","srv":1.0,"wt":260.0,"cal":420,"pro":34.0,"carb":42.0,"fat":12.0,"labels":[MealLabelName.lunch,MealLabelName.snack,MealLabelName.halal,MealLabelName.high_protein],"ing":[("Wheat Tortilla",1.0,PC),("Grilled Chicken Breast",100.0,G),("Black Beans (Cooked)",80.0,G),("Extra Virgin Olive Oil",0.5,TB)]},
    {"name":"Roasted Root Veggie Tray","desc":"Mixture of carrots, sweet potatoes, and onions roasted in olive oil.","instr":"1. Chop all vegetables.\n2. Toss in oil, roast at 200°C for 35 mins.","srv":1.0,"wt":320.0,"cal":260,"pro":4.0,"carb":45.0,"fat":8.0,"labels":[MealLabelName.side_meal,MealLabelName.vegan,MealLabelName.halal],"ing":[("Sweet Potato",150.0,G),("Carrot",100.0,G),("Onion",50.0,G),("Extra Virgin Olive Oil",0.5,TB)]},
]

BATCH_10 = [
    {"name":"Cottage Cheese & Apple Bowl","desc":"High protein cottage cheese (paneer sub) topped with fresh apple and cinnamon.","instr":"1. Crumble paneer slightly.\n2. Top with diced apple and a little honey.","srv":1.0,"wt":230.0,"cal":340,"pro":20.0,"carb":25.0,"fat":18.0,"labels":[MealLabelName.breakfast,MealLabelName.snack,MealLabelName.vegetarian,MealLabelName.halal,MealLabelName.high_protein],"ing":[("Paneer",100.0,G),("Apple",0.5,PC),("Honey",0.5,TB)]},
    {"name":"Salmon & Cucumber Salad","desc":"Refreshing cold salad of flaked cooked salmon and crisp cucumber.","instr":"1. Flake baked salmon.\n2. Mix with sliced cucumber, yogurt dressing.","srv":1.0,"wt":250.0,"cal":320,"pro":30.0,"carb":8.0,"fat":18.0,"labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.halal,MealLabelName.high_protein,MealLabelName.low_carb],"ing":[("Atlantic Salmon Fillet",120.0,G),("Cucumber",100.0,G),("Full-Fat Plain Yogurt",30.0,G)]},
    {"name":"Mushroom Cheese Omelette","desc":"Fluffy omelette stuffed with sautéed mushrooms and cheddar.","instr":"1. Sauté mushrooms in a little butter.\n2. Add beaten eggs, top with cheese, and fold.","srv":1.0,"wt":250.0,"cal":390,"pro":24.0,"carb":6.0,"fat":30.0,"labels":[MealLabelName.breakfast,MealLabelName.vegetarian,MealLabelName.halal,MealLabelName.high_protein,MealLabelName.low_carb],"ing":[("Whole Egg",3.0,PC),("White Mushroom",80.0,G),("Cheddar Cheese",20.0,G),("Unsalted Butter",0.5,TB)]},
    {"name":"Beef Mince & Pea Pilaf","desc":"Quick one-pot rice dish with ground beef and peas.","instr":"1. Brown beef, add uncooked rice and stock.\n2. Cook 15 mins. (Using pre-cooked rice in ingredients for simplicity).","srv":1.0,"wt":350.0,"cal":480,"pro":30.0,"carb":45.0,"fat":20.0,"labels":[MealLabelName.lunch,MealLabelName.dinner,MealLabelName.main_meal,MealLabelName.halal],"ing":[("Lean Ground Beef (90/10)",100.0,G),("Cooked Basmati Rice",200.0,G),("Onion",40.0,G),("Extra Virgin Olive Oil",1.0,TB)]},
    {"name":"Chocolate Protein Oats","desc":"Oatmeal cooked with milk and cocoa (choc alternative) for a rich breakfast.","instr":"1. Cook oats in milk.\n2. Stir in peanut butter and honey for flavour.","srv":1.0,"wt":280.0,"cal":420,"pro":16.0,"carb":60.0,"fat":14.0,"labels":[MealLabelName.breakfast,MealLabelName.vegetarian,MealLabelName.halal],"ing":[("Rolled Oats",60.0,G),("Skimmed Milk",200.0,ML),("Peanut Butter",1.0,TB),("Honey",1.0,TB)]},
]

ALL_BATCHES = [
    ("Batch 1: South Asian Classics", BATCH_1),
    ("Batch 2: More South Asian", BATCH_2),
    ("Batch 3", BATCH_3),
    ("Batch 4", BATCH_4),
    ("Batch 5", BATCH_5),
    ("Batch 6", BATCH_6),
    ("Batch 7", BATCH_7),
    ("Batch 8", BATCH_8),
    ("Batch 9", BATCH_9),
    ("Batch 10", BATCH_10),
]


def seed(session):
    print("\n=== Ensuring New Food Items ===")
    for fi_data in NEW_FOOD_ITEMS:
        get_or_create_food_item(session, fi_data)
    session.commit()

    # Load ALL food items from DB into fi_map (avoids duplicates)
    fi_map = {fi.name: fi for fi in session.exec(select(FoodItem)).all()}
    print(f"  Loaded {len(fi_map)} food items from DB")

    for batch_name, batch in ALL_BATCHES:
        print(f"\n=== {batch_name} ===")
        for meal_data in batch:
            insert_meal(session, meal_data, fi_map)
        session.commit()

    print("\n✅  All batches done!")

if __name__ == "__main__":
    with Session(engine) as session:
        seed(session)
