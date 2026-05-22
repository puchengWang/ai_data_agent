from app.analysis.growth_rate import calculate_growth_rate
from app.analysis.peak_valley import find_peak_valley
from app.analysis.contribution import calculate_contribution
from app.analysis.volatility import calculate_volatility
from app.analysis.anomaly_basic import detect_basic_anomaly


OPERATOR_REGISTRY = {
    "growth_rate": calculate_growth_rate,
    "peak_valley": find_peak_valley,
    "contribution": calculate_contribution,
    "volatility": calculate_volatility,
    "basic_anomaly": detect_basic_anomaly,
}