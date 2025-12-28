from typing import Literal

def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    """
    BMI = weight(kg) / (height(m)^2)
    Returns BMI rounded to 2 decimals.
    """
    if weight_kg <= 0:
        raise ValueError("weight_kg must be > 0")
    if height_cm <= 0:
        raise ValueError("height_cm must be > 0")

    height_m = height_cm / 100.0
    bmi = weight_kg / (height_m ** 2)
    return round(bmi, 2)

def calculate_bmr_mifflin(age: int, gender: str, height_cm: float, weight_kg: float) -> float:
    """
    Mifflin–St Jeor BMR:
      Male   : 10W + 6.25H - 5A + 5
      Female : 10W + 6.25H - 5A - 161
    """
    if age <= 0: raise ValueError("age must be > 0")
    if height_cm <= 0: raise ValueError("height_cm must be > 0")
    if weight_kg <= 0: raise ValueError("weight_kg must be > 0")

    g = gender.lower()
    if g not in ("male", "female"):
        raise ValueError("gender must be 'male' or 'female'")

    bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age
    bmr += 5 if g == "male" else -161
    return bmr

def calculate_tdee(
    age: int,
    gender: str,
    height_cm: float,
    weight_kg: float,
    activity_level: str,
) -> int:
    """
    TDEE = BMR * activity_factor
    Returns TDEE as an int (kcal/day).
    """
    activity_factors = {
        "sedentary": 1.2,     # little/no exercise
        "light": 1.375,       # 1–3 days/week
        "moderate": 1.55,     # 3–5 days/week
        "active": 1.725,      # 6–7 days/week
        "very_active": 1.9,   # hard exercise + physical job
    }

    al = activity_level.lower()
    if al not in activity_factors:
        raise ValueError(f"activity_level must be one of {list(activity_factors.keys())}")

    bmr = calculate_bmr_mifflin(age, gender, height_cm, weight_kg)
    tdee = bmr * activity_factors[al]
    return int(round(tdee))
