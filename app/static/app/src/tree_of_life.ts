import { phylotree } from "phylotree";

export function createTreeOfLife(id, file) {
    fetch(file)
        .then((res) => res.text())
        .then((newick) => {
            const tree = new phylotree(newick);
            tree.render({
                container: id,
                "font-size": 20,
                "align-tips": true,
                "show-scale": false,
                zoom: false,
                reroot: false,
                responsive: true,
                brush: false,
            });
            tree.display.radial(true);
            tree.display.update();

            const container = document.querySelector(id);
            const svg = tree.display.show();
            const bbox = svg.querySelector(".phylotree-container").getBBox();
            const pad = 0;

            svg.style.width = "100%";
            svg.style.height = "100%";
            svg.removeAttribute("width");
            svg.removeAttribute("height");
            container.appendChild(svg);

            container.querySelectorAll(".phylotree-node-text").forEach((el) => {
                const name = el.textContent.trim();
                if (name && name.includes("_")) {
                    el.style.cursor = "pointer";
                    el.addEventListener("click", () => {
                        window.location.href = `/entry/species/${name.replace(/_/g, " ")}`;
                    });
                }
            });
        });
}
