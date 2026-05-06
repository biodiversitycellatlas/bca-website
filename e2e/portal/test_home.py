from playwright.sync_api import expect


class TestHomepage:
    base_url = "http://localhost:8000/"

    def test_homepage_loads(self, page, live_server_url):
        page.goto(self.base_url)
        expect(page).to_have_title("Biodiversity Cell Atlas: Data Portal")
        expect(page.locator("#navbarSupportedContent").get_by_role("link", name="Cell Atlas")).to_be_visible()
        expect(page.locator("#navbarSupportedContent").get_by_role("link", name="Downloads")).to_be_visible()
        expect(page.locator("#navbarSupportedContent").get_by_role("link", name="Docs")).to_be_visible()
        expect(page.locator("#navbarSupportedContent").get_by_role("link", name="Blog")).to_be_visible()
        expect(page.locator("#navbarSupportedContent").get_by_role("link", name="About")).to_be_visible()
