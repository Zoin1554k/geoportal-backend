def parse_bbox(bbox: str) -> tuple[float, float, float, float]:
    w, s, e, n = (float(x) for x in bbox.split(","))
    if not (-180 <= w <= 180 and -180 <= e <= 180):
        raise ValueError("Longitudes fora de [-180, 180]")
    if not (-90 <= s <= 90 and -90 <= n <= 90):
        raise ValueError("Latitudes fora de [-90, 90]")
    if w >= e or s >= n:
        raise ValueError("bbox inválida (oeste>=leste ou sul>=norte)")
    return w, s, e, n