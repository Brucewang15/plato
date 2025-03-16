

def process_demonstration_data(demo_data: dict) -> list[dict]:
    """
    Process the demonstration data and return an ordered list of steps.
    
    Each step is a dict containing:
        - wait: time in milliseconds (end_timestamp - start_timestamp)
        - action_type: type of action (e.g., 'url_change', 'click')
        - action_details: all the details from the snapshot's action
        - before: before state details
        - after: after state details
    """
    steps = []
    for snapshot in demo_data["snapshots"]:
        wait_duration = snapshot["end_timestamp"] - snapshot["start_timestamp"]
        step = {
            "wait": wait_duration,
            "action_type": snapshot["action"]["type"],
            "action_details": snapshot["action"],
            "before": snapshot["before_state"],
            "after": snapshot["after_state"]
        }
        steps.append(step)
    
    return steps

def map_action_to_playwright(step: dict) -> str:
    """
    Use an LLM to generate a Playwright code snippet for a single action step.
    
    The prompt includes:
        - The before state (which could include a screenshot and HTML/metadata)
        - The action details (like the type, URL, selector, etc.)
        - The after state
    This helps the LLM determine what code to generate.
    
    Note: Passing images (like screenshots in base64) may be challenging. In practice,
        you might preprocess the image (e.g., run OCR or extract key features) and pass
        only textual descriptions to the LLM.
    """
    prompt = (
        "Generate a Playwright code snippet for the following action. "
        "Based on the 'before' and 'after' state, decide the proper command.\n\n"
        f"Before State: {step['before']}\n\n"
        f"Action Details: {step['action_details']}\n\n"
        f"After State: {step['after']}\n\n"
        "Write only the Python code snippet that performs this action."
    )
    code_snippet = llm_call(prompt)
    return code_snippet

def llm_call(prompt: str) -> str:
    return "LLM response"


def generate_script(demonstrations: list[dict]) -> str:
    """
    :args:
    demonstrations: a list of demonstration data, defined above
    
    :desc:
    consumes the demonstration data and uses LLM calls to convert it into a
    python playwright script. challenges: how to make sure its robust
    and reliable? 
    
    :returns:
    a python script
    """
    steps = process_demonstration_data(demonstrations[0])
    
    # Header: Basic script setup and definitions.
    header = '''import asyncio
import os
import json
from dotenv import load_dotenv
from scrapybara import Scrapybara
from undetected_playwright.async_api import async_playwright

load_dotenv()

async def get_scrapybara_browser():
    client = Scrapybara(api_key=os.getenv("SCRAPYBARA_API_KEY"))
    instance = client.start_browser()
    return instance

async def perform_automation(instance, start_url: str):
    cdp_url = instance.get_cdp_url().cdp_url
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(cdp_url)
        page = await browser.new_page()
        await page.goto(start_url)
    
        # Automation begin here
'''
    
    # Build the automation code: Loop through each step and insert the LLM-generated code.
    automation_lines = []
    for step in steps:
        automation_lines.append(f"        # Wait for {step['wait']} milliseconds")
        automation_lines.append(f"        await page.wait_for_timeout({step['wait']})")
        action_code = map_action_to_playwright(step)
        automation_lines.append(f"        {action_code}")
        automation_lines.append("        # Optionally add logging or state verification here")
        automation_lines.append("")  # Blank line for readability
    automation_code = "\n".join(automation_lines)
    
    # Footer: Closing automation, main function and entry point.
    footer = '''
        await browser.close()

async def main():
    print("Starting automation...")
    instance = await get_scrapybara_browser()

    try:
        await perform_automation(
            instance,
            "https://example.com"  # Replace with the actual start URL from demonstration
        )
    finally:
        instance.stop()
        print("Browser instance stopped")

if __name__ == "__main__":
    asyncio.run(main())
'''
    # Combine header, automation code, and footer into the final script.
    full_script = header + automation_code + footer
    return full_script


