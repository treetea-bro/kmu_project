import asyncio
import io
import json
import re
import unicodedata

import ollama
from icecream import ic
from PIL import Image

from models import ClickVideoParams, FilterParams, SearchParams
from playwright import PlaywrightManager
from prompt import LLM_SYSTEM_PROMPT
from tools import TOOLS

playwright = PlaywrightManager()


async def wait_for_navigation(max_retries=3):
    for attempt in range(max_retries):
        try:
            playwright_manager = PlaywrightManager()
            page = await playwright_manager.get_current_page()
            await page.wait_for_load_state("domcontentloaded", timeout=30000)
            print(f"[DEBUG] Navigation successful on attempt {attempt + 1}")
            return
        except Exception as e:
            print(f"[DEBUG] Navigation error on attempt {attempt + 1}: {str(e)}")
    print(f"[DEBUG] Navigation failed after {max_retries} attempts")


async def get_current_screen() -> bytes:
    await wait_for_navigation()
    page = await playwright.get_current_page()
    screenshot_bytes = await page.screenshot(full_page=False)

    # Resize to 896x896 using PIL
    img = Image.open(io.BytesIO(screenshot_bytes))
    img = img.resize((896, 896), Image.LANCZOS)

    # Convert back to bytes (JPEG format)
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="JPEG")
    return img_byte_arr.getvalue()


# ==============================
# 🧰 YouTube Functions
# ==============================
async def search(params: SearchParams):
    print(f"🔍 Searching: {params.query}")
    page = await playwright.get_current_page()
    await page.wait_for_selector('input[name="search_query"]')
    await page.fill('input[name="search_query"]', params.query)
    await page.press('input[name="search_query"]', "Enter")
    await page.wait_for_selector("ytd-item-section-renderer", timeout=10000)


async def apply_youtube_filters(params: FilterParams, timeout: int = 10000):
    page = await playwright.get_current_page()
    await page.wait_for_selector("#filter-button button", timeout=timeout)
    await page.click("#filter-button button")
    await page.wait_for_selector("ytd-search-filter-group-renderer", timeout=timeout)

    for idx, f in enumerate(params.filters):
        filter_groups = await page.query_selector_all(
            "ytd-search-filter-group-renderer"
        )
        for group in filter_groups:
            name_el = await group.query_selector(
                "#filter-group-name yt-formatted-string"
            )
            name = (await name_el.inner_text()).strip() if name_el else ""
            if name.lower() == f.group_name.lower():
                options = await group.query_selector_all("ytd-search-filter-renderer")
                for opt in options:
                    label_el = await opt.query_selector("#label yt-formatted-string")
                    label = (await label_el.inner_text()).strip() if label_el else ""
                    if label.lower() == f.option_label.lower():
                        link = await opt.query_selector("a#endpoint")
                        if link:
                            href = await link.get_attribute("href")
                            print(
                                f"✅ Applying filter: {f.group_name} → {f.option_label}"
                            )
                            await page.goto(f"https://www.youtube.com{href}")
                            await page.wait_for_selector(
                                "ytd-item-section-renderer", timeout=timeout
                            )
                            if idx < len(params.filters) - 1:
                                await page.wait_for_selector(
                                    "#filter-button button", timeout=timeout
                                )
                                await page.click("#filter-button button")
                                await page.wait_for_selector(
                                    "ytd-search-filter-group-renderer", timeout=timeout
                                )
                            break
                break


async def click_video_by_title(params: ClickVideoParams, timeout: int = 10000):
    page = await playwright.get_current_page()
    await page.wait_for_selector("ytd-rich-item-renderer", timeout=timeout)
    items = await page.query_selector_all("ytd-rich-item-renderer")
    for item in items:
        title_span = await item.query_selector("h3 a span")
        if not title_span:
            continue
        text = (await title_span.inner_text()).strip()
        if text == params.title:
            link = await item.query_selector("h3 a")
            if link:
                await link.click()
                print(f"🎬 Clicked video: {params.title}")
                return True
    print(f"❌ No matching video found: {params.title}")
    return False


async def run_with_llama(user_input: str):
    await playwright.async_initialize()
    model_name = "llama4:latest"

    for step in range(5):
        screenshot_bytes = await get_current_screen()
        messages = [
            {"role": "system", "content": LLM_SYSTEM_PROMPT},
            {"role": "user", "content": user_input, "images": [screenshot_bytes]},
        ]

        print("ollama start")
        response = await ollama.AsyncClient().chat(
            model=model_name,
            messages=messages,
            tools=TOOLS,
        )
        print("ollama end")
        ic(response)

        tool_calls = []
        if "message" in response and "content" in response["message"]:
            content = response["message"]["content"]
            ic(content)
            clean_content = re.sub(r"<\|.*?\|\>", "", content).strip()
            json_matches = re.findall(
                r"\{(?:[^{}]|\{[^{}]*\})*\}", clean_content, re.DOTALL
            )
            for json_str in json_matches:
                try:
                    json_str = unicodedata.normalize(
                        "NFKD", json_str.encode().decode("unicode_escape")
                    )
                    json_str = re.sub(r"\s+", " ", json_str.strip())
                    tool_call = json.loads(json_str)
                    if "type" in tool_call and tool_call["type"] == "function":
                        tool_calls.append(tool_call)
                except json.JSONDecodeError as e:
                    print(f"[ERROR] JSON parse error: {json_str} - {str(e)}")
                    continue
                except UnicodeDecodeError as e:
                    print(f"[ERROR] Unicode decode error: {json_str} - {str(e)}")
                    continue

        for call in tool_calls:
            fn_name = call.get("name")
            args = call.get("parameters", {})

            try:
                if fn_name == "search":
                    params = SearchParams(**args)
                    await search(params)
                elif fn_name == "apply_youtube_filters":
                    # Map legacy 'group' and 'option' to 'group_name' and 'option_label'
                    for f in args.get("filters", []):
                        if "group" in f:
                            f["group_name"] = f.pop("group")
                        if "option" in f:
                            f["option_label"] = f.pop("option")
                    params = FilterParams(**args)
                    await apply_youtube_filters(params)
                elif fn_name == "click_video_by_title":
                    params = ClickVideoParams(**args)
                    await click_video_by_title(params)
            except Exception as e:
                print(f"[ERROR] Tool execution failed for {fn_name}: {str(e)}")


if __name__ == "__main__":
    asyncio.run(
        run_with_llama(
            "Search for Pokémon AMV, apply 4K filter, then click the full battle video"
        )
    )
