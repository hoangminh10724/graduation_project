import math


def normalize_gop(mean_log_posterior: float, floor: float = -5.0) -> float:
    """Chuẩn hóa GOP (log posterior trung bình của âm vị, <= 0) về thang 0-100.

    0 -> 100 điểm; giá trị <= floor -> 0 điểm; nội suy tuyến tính ở giữa.
    """
    if math.isnan(mean_log_posterior):
        return 0.0
    x = max(floor, min(0.0, mean_log_posterior))
    return round(100.0 * (1.0 - x / floor), 1)
