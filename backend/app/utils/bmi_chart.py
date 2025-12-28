def current_health_condition(bmi: float) -> str:
    if bmi <= 0:
        raise ValueError("BMI must be > 0")

    if bmi < 16:
        return "Severe thinness"
    elif 16 <= bmi < 17:
        return "Moderate thinness"
    elif 17 <= bmi < 18.5:
        return "Mild thinness"
    elif 18.5 <= bmi < 25:
        return "Normal"
    elif 25 <= bmi < 30:
        return "Overweight"
    elif 30 <= bmi < 35:
        return "Obese Class I"
    elif 35 <= bmi < 40:
        return "Obese Class II"
    else:
        return "Obese Class III"
