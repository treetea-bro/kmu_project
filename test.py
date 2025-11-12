from playwright.sync_api import Playwright, sync_playwright


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://www.naver.com/")
    page.locator(
        "html > body:nth-child(2) > div:nth-child(3) > div:nth-child(1) > div > div:nth-child(3) > div > div > form:nth-child(2) > fieldset:nth-child(1) > div:nth-child(15) > input"
    ).click()
    page.get_by_role("combobox", name="검색어를 입력해 주세요").fill("sdafsdf")
    page.locator(
        "html > body:nth-child(2) > div:nth-child(3) > div:nth-child(1) > div > div:nth-child(3) > div > div > form:nth-child(2) > fieldset:nth-child(1) > button:nth-child(16)"
    ).click()
    with page.expect_popup() as page1_info:
        page.locator(
            "html > body:nth-child(2) > div:nth-child(3) > div:nth-child(2) > div:nth-child(1) > div:nth-child(2) > div:nth-child(8) > div > div > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(2) > div:nth-child(1) > a"
        ).click()
    page1 = page1_info.value

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
