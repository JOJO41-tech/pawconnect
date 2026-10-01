from __future__ import annotations

from typing import Any


def _match_level(
    score: float,
) -> str:
    if score >= 90:
        return "Excellent"

    if score >= 75:
        return "Very Good"

    if score >= 60:
        return "Good"

    if score >= 40:
        return "Fair"

    return "Low"


def _format_required_match(
    field: str,
    value: Any,
) -> str:
    field = str(field).strip().lower()

    if field == "pet_type":
        return f"Pet type: {str(value).title()}"

    if field == "breed":
        return f"Breed: {value}"

    if field == "gender":
        return f"Gender: {str(value).title()}"

    if field == "size":
        return f"Size: {str(value).title()}"

    if field == "location":
        return f"Location: {value}"

    if field == "age_years":
        number = float(value)

        if number.is_integer():
            number = int(number)

        unit = (
            "year"
            if number == 1
            else "years"
        )

        return f"Age: {number} {unit}"

    if field == "age_months":
        number = float(value)

        if number.is_integer():
            number = int(number)

        unit = (
            "month"
            if number == 1
            else "months"
        )

        return f"Age: {number} {unit}"

    return (
        f"{field.replace('_', ' ').title()}: "
        f"{value}"
    )


def _collect_required_matches(
    recommendation: dict[str, Any],
) -> list[str]:
    required = recommendation.get(
        "required_constraints",
        {},
    )

    if not isinstance(
        required,
        dict,
    ):
        return []

    matches: list[str] = []

    for field, value in required.items():
        if value is None or value == "":
            continue

        matches.append(
            _format_required_match(
                field,
                value,
            )
        )

    return matches


def build_explanation(
    recommendation: dict[str, Any],
) -> dict[str, Any]:
    """
    Add a transparent, grounded explanation.

    This function does not change ranking scores.
    It only explains why the pet matched or why
    it is being shown as an alternative.
    """

    result = dict(recommendation)

    matched = list(
        result.get(
            "matched_preferences",
            [],
        )
    )

    missing = list(
        result.get(
            "missing_preferences",
            [],
        )
    )

    failed_required = list(
        result.get(
            "failed_required_messages",
            [],
        )
    )

    required_matches = (
        _collect_required_matches(
            result
        )
    )

    is_exact = bool(
        result.get(
            "is_exact_match",
            False,
        )
    )

    score = float(
        result.get(
            "compatibility_score",
            0,
        )
    )

    lines: list[str] = []

    if is_exact:
        lines.append(
            "This pet matches all required "
            "constraints."
        )

    else:
        lines.append(
            "This is a closest alternative "
            "because no exact match was available."
        )

    if required_matches:
        lines.append("")
        lines.append(
            "Required matches:"
        )

        for item in required_matches:
            lines.append(
                f"✓ {item}"
            )

    if matched:
        lines.append("")
        lines.append(
            "Lifestyle matches:"
        )

        for item in matched:
            lines.append(
                f"✓ {item}"
            )

    if failed_required:
        lines.append("")
        lines.append(
            "Required constraints not matched:"
        )

        for item in failed_required:
            lines.append(
                f"✗ {item}"
            )

    if missing:
        lines.append("")
        lines.append(
            "Preferred traits not matched:"
        )

        for item in missing:
            lines.append(
                f"• {item}"
            )

    result["match_level"] = _match_level(
        score
    )

    result["explanation"] = "\n".join(
        lines
    )

    return result


def explain_recommendations(
    recommendations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        build_explanation(
            recommendation
        )
        for recommendation in recommendations
    ]


def build_no_match_response(
    message: str,
) -> dict[str, Any]:
    return {
        "success": False,
        "message": message,
        "recommendations": [],
    }


def build_success_response(
    recommendations: list[dict[str, Any]],
    message: str,
) -> dict[str, Any]:
    return {
        "success": True,
        "message": message,
        "recommendations": (
            explain_recommendations(
                recommendations
            )
        ),
    }