def clamp_unit(value: float) -> float:
    return min(1.0, max(0.0, value))


def figure_level(contrast: float, noise: float, span: float) -> float:
    return clamp_unit((contrast - noise) / span)


def loom_level(share: float, floor: float, span: float) -> float:
    return clamp_unit((share - floor) / span)
