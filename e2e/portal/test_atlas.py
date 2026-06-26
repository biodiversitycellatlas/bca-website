from playwright.sync_api import expect


class TestAtlasPage:
    base_url1 = "http://localhost:8000/atlas/homo-sapiens-baby/"
    base_url2 = "http://localhost:8000/atlas/amphineuron-queenslandicum/"

    def test_atlas_loads(self, page, live_server_url):
        page.goto(self.base_url1)

        expect(page.get_by_role("link", name="Atlas overview")).to_have_attribute(
            "href", "/atlas/homo-sapiens-baby/overview/"
        )
        expect(page.get_by_role("link", name="Atlas overview")).to_have_attribute(
            "href", "/atlas/homo-sapiens-baby/overview/"
        )
        expect(page.get_by_role("link", name="Gene lists")).to_have_attribute("href", "/atlas/homo-sapiens-baby/panel/")
        expect(page.get_by_role("link", name="Gene modules")).to_have_attribute(
            "href", "/atlas/homo-sapiens-baby/modules/"
        )
        expect(page.get_by_role("link", name="Gene and orthologs")).to_have_attribute(
            "href", "/atlas/homo-sapiens-baby/gene/"
        )
        expect(page.get_by_role("link", name="Cell type markers")).to_have_attribute(
            "href", "/atlas/homo-sapiens-baby/markers/"
        )
        expect(page.get_by_role("link", name="Cross-species")).to_have_attribute(
            "href", "/atlas/homo-sapiens-baby/compare/"
        )

        expect(page.locator("#info").get_by_text("Homo sapiens (Baby)")).to_be_visible()
        (expect(page.get_by_role("link", name="Gunn,")).to_have_attribute("href", "https://doi.org/10.1038/171737a0"))
        (
            expect(page.get_by_role("link", name="9606")).to_have_attribute(
                "href", "https://www.ncbi.nlm.nih.gov/datasets/taxonomy/9606"
            )
        )
        (
            expect(page.get_by_role("link", name="Chordata")).to_have_attribute(
                "href", "https://www.ncbi.nlm.nih.gov/datasets/taxonomy/7711"
            )
        )
        expect(page.locator("#n_cells")).to_contain_text("100")
        expect(page.locator("#n_metacells")).to_contain_text("12")
        expect(page.locator("#n_genes")).to_contain_text("12")
        expect(page.locator("#n_umis")).not_to_be_empty()

    def test_metacells_plots(self, page, live_server_url):
        page.goto(self.base_url1)

        expect(page.locator("#metacell-cells-plot canvas")).to_be_visible()
        expect(page.locator("#metacell-umis-plot canvas")).to_be_visible()

        page.locator("#metacell-cells-plot").get_by_role("img").click()

        expect(page.get_by_role("link", name="Save as SVG")).to_be_visible()

    def test_goto_atlas_sections(self, page, live_server_url):
        page.goto(self.base_url2)
        page.get_by_role("link", name="Atlas overview").click()
        expect(page).to_have_url("http://localhost:8000/atlas/amphineuron-queenslandicum/overview/")

        page.goto(self.base_url2)
        page.get_by_role("link", name="Gene lists").click()
        expect(page).to_have_url("http://localhost:8000/atlas/amphineuron-queenslandicum/panel/")

        page.goto(self.base_url2)
        page.get_by_role("link", name="Gene modules").click()
        expect(page).to_have_url("http://localhost:8000/atlas/amphineuron-queenslandicum/modules/")

        page.goto(self.base_url2)
        page.get_by_role("link", name="Gene and orthologs").click()
        expect(page).to_have_url("http://localhost:8000/atlas/amphineuron-queenslandicum/gene/")

        page.goto(self.base_url2)
        page.get_by_role("link", name="Cell type markers").click()
        expect(page).to_have_url("http://localhost:8000/atlas/amphineuron-queenslandicum/markers/")

        page.goto(self.base_url2)
        page.get_by_role("link", name="Cross-species").click()
        expect(page).to_have_url("http://localhost:8000/atlas/amphineuron-queenslandicum/compare/")
