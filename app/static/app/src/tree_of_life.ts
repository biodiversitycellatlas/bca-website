import { phylotree } from "phylotree";

export function createTreeOfLife(id, file) {
    fetch(file)
        .then((res) => res.text())
        .then((newick) => {
            const tree = new phylotree(newick);

            const container = document.querySelector(id);
            const { width, height } = container.getBoundingClientRect();

            const fontSize = Math.max(6, Math.min(18, height / 25));

            tree.render({
                container: id,
                //width,
                //height,
                //"left-right-spacing": "fit-to-size",
                //"top-bottom-spacing": "fit-to-size",
                "font-size": 8,
                "align-tips": true,
                "show-scale": false,
                zoom: false,
                reroot: false,
                responsive: true,
                brush: false,
                "is-radial": true,
                selectable: false,
                collapsible: false,
            });

            const svg = tree.display.show();
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
