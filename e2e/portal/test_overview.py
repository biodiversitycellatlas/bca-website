from playwright.sync_api import expect


class TestOverviewPage:
    base_url = "http://localhost:8000/atlas/homo-sapiens-baby/overview/"

    def test_overview_loads(self, page, live_server_url):
        page.goto(self.base_url)

        expect(page.get_by_text("Metacell projection")).to_be_visible()
        expect(page.get_by_text("Gene expression heatmap")).to_be_visible()
        expect(page.locator("#projection-plot canvas")).to_be_visible()
        expect(page.locator("#expression-plot canvas")).to_be_visible()

    def test_metacell_projection(self, page, live_server_url):
        page.goto(self.base_url)
        page.locator("#expression-plot").get_by_role("img").click()

        expect(page.get_by_role("link", name="Save as SVG")).to_be_visible()

    def test_expression_heatmap(self, page, live_server_url):
        page.goto(self.base_url)
        page.locator("#projection-plot").get_by_role("img").click()

        expect(page.get_by_role("link", name="Save as PNG")).to_be_visible()
