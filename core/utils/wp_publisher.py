"""
core/utils/wp_publisher.py

Publishes structured job-vacancy JSON data (extracted via Gemini) as a
formatted WordPress post using the WP REST API and Application Passwords.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests
from requests.auth import HTTPBasicAuth

from config import WP_BASE_URL, WP_USERNAME, WP_APPLICATION_PASSWORD
from core.utils.logger import logger

REQUEST_TIMEOUT_SECONDS = 20
POSTS_ENDPOINT = f"{WP_BASE_URL.rstrip('/')}/wp/v2/posts"


# --------------------------------------------------------------------------- #
# HTML formatting helpers
# --------------------------------------------------------------------------- #

def _row(label: str, value: Any) -> str:
    """Return a single styled <tr> for the info table."""
    if value in (None, "", "N/A"):
        value = "Not Specified"
    return (
        '<tr>'
        '<td style="padding:10px 15px;background:#f4f6f8;border:1px solid #ddd;'
        'font-weight:600;color:#333;width:35%;">{label}</td>'
        '<td style="padding:10px 15px;border:1px solid #ddd;color:#222;">{value}</td>'
        '</tr>'
    ).format(label=label, value=value)


def _format_important_dates(dates: Dict[str, Any]) -> str:
    start = dates.get("start_date", "N/A")
    end = dates.get("last_date", "N/A")
    return f"Start: {start} &nbsp;|&nbsp; Last Date: {end}"


def _format_application_fee(fee: Dict[str, Any]) -> str:
    general = fee.get("general_obc", "N/A")
    reserved = fee.get("sc_st_pwd", "N/A")
    return f"General/OBC: ₹{general} &nbsp;|&nbsp; SC/ST/PwD: ₹{reserved}"


def _format_age_limit(age: Dict[str, Any]) -> str:
    min_age = age.get("minimum_age", "N/A")
    max_age = age.get("maximum_age", "N/A")
    return f"{min_age} Years to {max_age} Years"


def format_html_table(job_data: Dict[str, Any]) -> str:
    """
    Convert job_data dict into a clean, modern, Sarkari-Result style
    HTML info table for the WordPress post body.
    """
    important_dates = job_data.get("important_dates", {}) or {}
    application_fee = job_data.get("application_fee", {}) or {}
    age_limit = job_data.get("age_limit", {}) or {}

    rows = [
        _row("Organization", job_data.get("organization")),
        _row("Total Vacancies", job_data.get("total_vacancies")),
        _row("Important Dates", _format_important_dates(important_dates)),
        _row("Application Fee", _format_application_fee(application_fee)),
        _row("Age Limit", _format_age_limit(age_limit)),
        _row("Eligibility Criteria", job_data.get("eligibility_criteria")),
        _row(
            "Official Website",
            f'<a href="{job_data.get("official_website", "#")}" '
            f'target="_blank" rel="noopener noreferrer">'
            f'{job_data.get("official_website", "N/A")}</a>',
        ),
    ]

    table_html = (
        '<div style="max-width:800px;margin:20px auto;font-family:Arial, sans-serif;">'
        f'<h2 style="text-align:center;color:#1a1a1a;">{job_data.get("job_title", "Job Notification")}</h2>'
        '<table style="width:100%;border-collapse:collapse;box-shadow:0 1px 4px rgba(0,0,0,0.1);">'
        f'{"".join(rows)}'
        '</table>'
        '</div>'
    )
    return table_html


# --------------------------------------------------------------------------- #
# WordPress publishing
# --------------------------------------------------------------------------- #

def _build_auth() -> HTTPBasicAuth:
    return HTTPBasicAuth(WP_USERNAME, WP_APPLICATION_PASSWORD)


def _build_payload(job_data: Dict[str, Any], html_content: str) -> Dict[str, Any]:
    return {
        "title": job_data.get("job_title", "Untitled Job Notification"),
        "content": html_content,
        "status": "publish",
    }


def _post_to_wordpress(payload: Dict[str, Any]) -> Optional[requests.Response]:
    """Perform the raw HTTP POST. Returns the Response object or None on failure."""
    try:
        response = requests.post(
            POSTS_ENDPOINT,
            json=payload,
            auth=_build_auth(),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        return response
    except requests.exceptions.RequestException as exc:
        logger.error(f"WordPress request failed: {exc}")
        return None


def publish_to_wordpress(job_data: Dict[str, Any]) -> Optional[int]:
    """
    Publish a job_data dict as a formatted WordPress post.

    Returns:
        int: The WordPress post ID on success.
        None: If publishing failed for any reason.
    """
    if not job_data:
        logger.error("publish_to_wordpress called with empty job_data.")
        return None

    try:
        html_content = format_html_table(job_data)
    except Exception as exc:
        logger.error(f"Failed to format HTML table for job_data: {exc}")
        return None

    payload = _build_payload(job_data, html_content)
    response = _post_to_wordpress(payload)

    if response is None:
        return None

    if response.status_code != 201:
        logger.error(
            f"WordPress publish failed with status {response.status_code}: {response.text}"
        )
        return None

    try:
        post_id = response.json().get("id")
    except ValueError as exc:
        logger.error(f"Failed to parse WordPress response JSON: {exc}")
        return None

    if post_id is None:
        logger.error(f"WordPress response missing post ID: {response.text}")
        return None

    logger.info(f"Successfully published job post. Post ID: {post_id}")
    return post_id