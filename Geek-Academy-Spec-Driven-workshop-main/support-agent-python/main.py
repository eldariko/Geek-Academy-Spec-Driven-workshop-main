import pathlib
import sys
import argparse
import os
import logging
from datetime import datetime

from dotenv import load_dotenv

from app.console_ui import (
    COLOR_CYAN,
    COLOR_GREEN,
    COLOR_DARK_YELLOW,
    COLOR_GRAY,
    write_colored_line,
    write_section_title,
    render_support_response,
)
from app.orchestrator import Orchestrator
from app.models import CustomerRequest
from app.services import FoundryClient

load_dotenv(pathlib.Path(__file__).with_name(".env"))


def main() -> int:
    """Main CLI entry point"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("azure").setLevel(logging.WARNING)
    logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
    logging.getLogger("azure.ai.inference").setLevel(logging.WARNING)

    parser = argparse.ArgumentParser(description="Customer Support Agent")
    parser.add_argument("--test-mode", action="store_true", help="Run test mode with sample requests")
    parser.add_argument("--use-llm", action="store_true", help="Enable LLM fallback for ambiguous intent classification")
    args = parser.parse_args()

    llm_client = None
    if args.use_llm:
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        if not api_key:
            write_colored_line(
                "Error: AZURE_OPENAI_API_KEY is required when --use-llm is enabled. "
                "Add AZURE_OPENAI_API_KEY to .env and run again.",
                COLOR_DARK_YELLOW,
            )
            return 1
        if not endpoint:
            write_colored_line(
                "Error: AZURE_OPENAI_ENDPOINT is required when --use-llm is enabled. "
                "Add AZURE_OPENAI_ENDPOINT to .env and run again.",
                COLOR_DARK_YELLOW,
            )
            return 1
        if not deployment_name:
            write_colored_line(
                "Error: AZURE_OPENAI_DEPLOYMENT_NAME is required when --use-llm is enabled. "
                "Add AZURE_OPENAI_DEPLOYMENT_NAME to .env and run again.",
                COLOR_DARK_YELLOW,
            )
            return 1
        llm_client = FoundryClient(api_key=api_key, endpoint=endpoint, deployment_name=deployment_name)
    
    try:
        # Initialize orchestrator
        handbook_path = pathlib.Path(__file__).parent / "data" / "support_handbook.md"
        orchestrator = Orchestrator(str(handbook_path), use_llm=args.use_llm, llm_client=llm_client)
    except Exception as ex:
        write_colored_line(f"Error initializing orchestrator: {ex}", COLOR_DARK_YELLOW)
        return 1
    
    if args.test_mode:
        return run_test_mode(orchestrator)
    else:
        return run_interactive_mode(orchestrator)


def run_interactive_mode(orchestrator: Orchestrator) -> int:
    """Interactive console mode"""
    write_section_title("=== Customer Support Agent ===", COLOR_CYAN)
    write_colored_line("Enter a customer support request (or type 'quit' to exit)", COLOR_GRAY)
    
    while True:
        try:
            message = input("\n> ").strip()
            
            if message.lower() in ["quit", "exit", "q"]:
                write_colored_line("\nGoodbye!", COLOR_GREEN)
                break
            
            if not message:
                continue
            
            # Process request
            response = orchestrator.process(message)

            # Display response with metadata.
            render_support_response(response)
        
        except KeyboardInterrupt:
            write_colored_line("\n\nInterrupted. Goodbye!", COLOR_GRAY)
            break
        except Exception as e:
            write_colored_line(f"Error: {e}", COLOR_DARK_YELLOW)
    
    return 0


def run_test_mode(orchestrator: Orchestrator) -> int:
    """Test mode: process sample requests"""
    write_section_title("=== TEST MODE ===", COLOR_CYAN)
    
    # Load sample requests
    sample_file = pathlib.Path(__file__).parent / "data" / "sample_requests.md"
    if not sample_file.exists():
        write_colored_line(f"Sample requests file not found: {sample_file}", COLOR_DARK_YELLOW)
        return 1
    
    try:
        with open(sample_file, 'r') as f:
            content = f.read()
        
        # Parse sample requests (format: ## Request Title\nRequest text)
        import re
        requests = re.split(r'^## ', content, flags=re.MULTILINE)[1:]
        
        if not requests:
            write_colored_line("No sample requests found", COLOR_DARK_YELLOW)
            return 1
        
        write_colored_line(f"Found {len(requests)} sample requests\n", COLOR_GREEN)
        
        for i, req_block in enumerate(requests, 1):
            lines = req_block.split('\n', 1)
            title = lines[0].strip()
            message = lines[1].strip() if len(lines) > 1 else ""
            
            write_section_title(f"[{i}] {title}", COLOR_CYAN)
            write_colored_line(f"Input: {message[:100]}...", COLOR_GRAY)

            request = CustomerRequest(
                raw_message=message,
                request_id=f"test_{i}_{datetime.now().strftime('%H%M%S')}",
            )
            state = orchestrator.workflow.execute(request, allow_clarification_prompt=False)
            response = state.response

            if not response or not state.classification or not state.policy_evaluation:
                write_colored_line("Failed to generate a full workflow result", COLOR_DARK_YELLOW)
                continue

            write_colored_line(f"Classification: {state.classification.classified_intent} ({state.classification.confidence_score:.2f})", COLOR_GREEN)
            write_colored_line(f"Decision: {state.policy_evaluation.final_decision}", COLOR_GREEN)
            write_colored_line(f"Response type: {response.response_type}", COLOR_GREEN)
            print(f"Response: {response.response_text[:150]}...\n")
        
        write_colored_line(f"\n[OK] Test mode completed: {len(requests)} requests processed", COLOR_GREEN)
        return 0
    
    except Exception as e:
        write_colored_line(f"Error in test mode: {e}", COLOR_DARK_YELLOW)
        return 1

    return 0


def read_multiline_input() -> str | None:
    lines: list[str] = []
    while True:
        try:
            line = input()
        except (EOFError, KeyboardInterrupt):
            print()
            return None

        trimmed = line.strip()

        if not lines and trimmed.lower() == "quit":
            return None

        if trimmed == "---":
            break

        lines.append(line)

    return "\n".join(lines).strip()


if __name__ == "__main__":
    sys.exit(main())
