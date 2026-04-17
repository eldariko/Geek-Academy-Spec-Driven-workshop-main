COLOR_RESET = "\033[0m"
COLOR_CYAN = "\033[96m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_GRAY = "\033[90m"
COLOR_WHITE = "\033[97m"
COLOR_DARK_YELLOW = "\033[33m"


def write_section_title(title: str, color: str = COLOR_CYAN) -> None:
    print(f"{color}\n=== {title} ==={COLOR_RESET}")


def write_colored_line(text: str, color: str) -> None:
    print(f"{color}{text}{COLOR_RESET}")


def render_support_response(response) -> None:
    """Render a support response with key metadata for console users."""
    write_section_title(f"{response.response_type.upper()}", COLOR_GREEN)
    print(response.response_text)

    if getattr(response, "handbook_citations", None):
        write_colored_line("\nHandbook citations:", COLOR_GRAY)
        for citation in response.handbook_citations:
            write_colored_line(f"- {citation}", COLOR_GRAY)

    if getattr(response, "cited_policies", None):
        write_colored_line(f"\nPolicies applied: {', '.join(response.cited_policies)}", COLOR_GRAY)

    if getattr(response, "recommended_action", None):
        write_colored_line(f"Recommended action: {response.recommended_action}", COLOR_GRAY)

    if getattr(response, "escalation_reason", None):
        write_colored_line(f"Escalation reason: {response.escalation_reason}", COLOR_DARK_YELLOW)

    if getattr(response, "escalation_ticket_id", None):
        write_colored_line(f"Escalation ticket: {response.escalation_ticket_id}", COLOR_DARK_YELLOW)
