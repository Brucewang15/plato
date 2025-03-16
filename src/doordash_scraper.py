import asyncio
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


async def retrieve_menu_items(instance, start_url: str) -> list[dict]:
    """
    :args:
    instance: the scrapybara instance to use
    url: the initial url to navigate to

    :desc:
    this function navigates to {url}. then, it will collect the detailed
    data for each menu item in the store and return it.

    (hint: click a menu item, open dev tools -> network tab -> filter for
            "https://www.doordash.com/graphql/itemPage?operation=itemPage")

    one way to do this is to scroll through the page and click on each menu
    item.

    determine the most efficient way to collect this data.

    :returns:
    a list of menu items on the page, represented as dictionaries
    """
    cdp_url = instance.get_cdp_url().cdp_url
    menu_items = []
    visited = set()

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(cdp_url)
        page = await browser.new_page()
        

        print(f"Navigating to {start_url}")
    
        await page.goto(start_url)
        print("Page reached")

        await page.wait_for_load_state("networkidle")
        print("Page loaded")

        page_height = await page.evaluate("document.body.scrollHeight")
        scroll_steps = page_height // 200


        for i in range(scroll_steps):
            await page.evaluate("window.scrollBy(0, 200)")
            await page.wait_for_timeout(500)
            await page.screenshot(path=f"./screenshots/scroll_screenshot_{i}.png") 

            current_items = await page.query_selector_all('div[data-anchor-id="MenuItem"]')
            print(f"Iteration {i+1}: found {len(current_items)} menu items on page")

            for item in current_items:
                item_id = await item.get_attribute("data-item-id")

                if not item_id or item_id in visited:
                    continue
                visited.add(item_id)

                try:
                    await item.scroll_into_view_if_needed()
                    async with page.expect_request_finished(lambda request: "graphql/itemPage?operation=itemPage" in request.url) as request_info:
                        await item.click()
                        request = await request_info.value
                        
                        await page.screenshot(path=f"./click_screenshots/clicked_screenshot_{item_id}.png")
                        print(f"Clicked item {item_id}")

                        if request.response:
                            response_obj = await request.response()  
                            if response_obj:
                                response_body = await response_obj.body()
                                item_data = json.loads(response_body)
                                menu_items.append(item_data)
                                print(f"Retrieved data for menu item: {item_id}")

                        await page.wait_for_selector("button[aria-label*='Close']", timeout=5000)
                        close_button = await page.query_selector("button[aria-label*='Close']")

                        if close_button:
                            await close_button.click()
                            await page.wait_for_timeout(500)
                            print("Closed item details")

                except Exception as e:
                    print(f"Error processing item {item_id}: {str(e)}")
                    try:
                        close_button = await page.query_selector("button[aria-label*='Close']")
                        if close_button:
                            await close_button.click()
                            await page.wait_for_timeout(500)
                    except:
                        pass


    print(f"Successfully processed {len(menu_items)} menu items")
    return menu_items

async def main():
    print("Starting DoorDash scraper...")
    instance = await get_scrapybara_browser()

    try:
        menu_items = await retrieve_menu_items(
            instance,
            "https://www.doordash.com/store/panda-express-san-francisco-980938/12722988/?event_type=autocomplete&pickup=false",
        )
        
        with open("menu_items.json", "w") as f:
            json.dump(menu_items, f, indent=2)
        
        print(f"Saved {len(menu_items)} menu items to menu_items.json")
    finally:
        instance.stop()
        print("Browser instance stopped")

if __name__ == "__main__":
    asyncio.run(main())