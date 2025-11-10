from playwright.sync_api import Playwright, sync_playwright


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://www.naver.com/")
    with page.expect_popup() as page1_info:
        page.locator(
            "html > body:nth-child(2) > div:nth-child(3) > div:nth-child(1) > div > div:nth-child(5) > ul > li:nth-child(5) > a"
        ).click()
    page1 = page1_info.value
    page1.locator(
        "html > body:nth-child(2) > section:nth-child(2) > header > div:nth-child(2) > div > div > div > div > div > ul > li:nth-child(3) > a"
    ).click()
    page1.locator(
        "html > body:nth-child(2) > div:nth-child(1) > header:nth-child(2) > div > div:nth-child(2) > div:nth-child(1) > div > ul > li:nth-child(5) > a"
    ).click()
    page1.locator(
        "html > body:nth-child(2) > div:nth-child(1) > header:nth-child(2) > div > div:nth-child(2) > div > div > ul > li:nth-child(6) > a"
    ).click()
    page1.locator(
        "html > body:nth-child(2) > div:nth-child(1) > div:nth-child(5) > div:nth-child(2) > div:nth-child(3) > div:nth-child(2) > div:nth-child(1) > div:nth-child(2) > div > div > div > div:nth-child(1) > ul:nth-child(1) > li:nth-child(1) > div > a:nth-child(3)"
    ).click()
    with page.expect_popup() as page2_info:
        page.locator(
            "html > body:nth-child(2) > div:nth-child(3) > div:nth-child(1) > div > div:nth-child(5) > ul > li:nth-child(3) > a"
        ).click()
    page2 = page2_info.value
    page2.locator(
        "html > body:nth-child(2) > ui-view:nth-child(1) > div > main:nth-child(2) > div:nth-child(3) > div:nth-child(1) > section > div:nth-child(1) > div:nth-child(2) > div > a:nth-child(3)"
    ).click()
    with page2.expect_popup() as page3_info:
        page2.locator(
            "html > body:nth-child(2) > ui-view:nth-child(1) > div > main:nth-child(2) > div:nth-child(3) > div:nth-child(1) > section > div:nth-child(2) > div:nth-child(1) > div:nth-child(1) > div:nth-child(2) > a:nth-child(1)"
        ).click()
    page3 = page3_info.value
    with page.expect_popup() as page4_info:
        page.locator(
            "html > body:nth-child(2) > div:nth-child(3) > div:nth-child(1) > div > div:nth-child(5) > ul > li:nth-child(5) > a"
        ).click()
    page4 = page4_info.value
    page4.locator(
        "html > body:nth-child(2) > section:nth-child(2) > header > div:nth-child(2) > div > div > div > div > div > ul > li:nth-child(5) > a"
    ).click()
    page4.locator(
        "html > body:nth-child(2) > div:nth-child(1) > div:nth-child(5) > div:nth-child(2) > div:nth-child(2) > div:nth-child(1) > div:nth-child(1) > ul:nth-child(2) > li:nth-child(3) > div > div > div:nth-child(2) > a:nth-child(1)"
    ).click()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
