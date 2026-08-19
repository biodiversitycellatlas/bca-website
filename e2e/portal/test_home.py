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
        expect(page.get_by_label("Tree of life.").locator("svg")).to_be_visible()

    def test_species_datasets_links(self, page, live_server_url):
        page.goto(self.base_url)

        expect(page.get_by_role("link", name="species")).to_contain_text("2")
        expect(page.get_by_role("link", name="species")).to_contain_text("species")
        expect(page.get_by_role("link", name="datasets")).to_contain_text("2")
        expect(page.get_by_role("link", name="datasets")).to_contain_text("datasets")

    def test_dataset_select_opens(self, page, live_server_url):
        page.goto(self.base_url)

        page.get_by_role("combobox", name="Search datasets by species,").click()
        expect(page.locator(".optgroup-header").filter(has_text="Porifera")).to_be_visible()
        expect(page.locator(".optgroup-header").filter(has_text="Chordata")).to_be_visible()
        expect(page.get_by_role("option", name="Amphineuron queenslandicum sponge")).to_be_visible()
        expect(page.get_by_role("option", name="Homo sapiens (Baby) human")).to_be_visible()

    def test_dataset_select_search_by_phylum(self, page, live_server_url):
        page.goto(self.base_url)

        combobox = page.get_by_role("combobox", name="Search datasets by species,")
        combobox.click()
        combobox.fill("Chordata")

        expect(page.get_by_role("option", name="Homo sapiens (Baby) human")).to_be_visible()
        expect(page.get_by_text("Amphineuron queenslandicum sponge")).not_to_be_visible()

    def test_atlas_loads_using_select(self, page, live_server_url):
        page.goto(self.base_url)

        page.get_by_role("combobox", name="Search datasets by species,").click()
        page.get_by_role("option", name="Homo sapiens (Baby) human").click()

        expect(page).to_have_url("http://localhost:8000/atlas/homo-sapiens-baby/")
