from playwright.sync_api import expect


class TestOverviewPage:
    def test_overview_loads(self, page, base_url):
        page.goto(f"{base_url}atlas/homo-sapiens-baby/overview/")

        expect(page.get_by_text("Metacell projection")).to_be_visible()
        expect(page.get_by_text("Gene expression heatmap")).to_be_visible()
        expect(page.locator("#projection-plot canvas")).to_be_visible()
        expect(page.locator("#expression-plot canvas")).to_be_visible()

    def test_metacell_projection(self, page, base_url):
        page.goto(f"{base_url}atlas/homo-sapiens-baby/overview/")
        page.locator("#expression-plot").get_by_role("img").click()

        expect(page.get_by_role("link", name="Save as SVG")).to_be_visible()

    def test_expression_heatmap(self, page, base_url):
        page.goto(f"{base_url}atlas/homo-sapiens-baby/overview/")
        page.locator("#projection-plot").get_by_role("img").click()

        expect(page.get_by_role("link", name="Save as PNG")).to_be_visible()
