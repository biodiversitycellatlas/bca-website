export function displaySearchResults(item, escape) {
    let group = item.group;
    let res = "";

    if (group === "gene") {
        let badges = "";
        let domains_array = item.domains;
        for (let i = 0; i < domains_array.length; i++) {
            if (domains_array[i] !== "") {
                let span =
                    '<span class="badge rounded-pill text-bg-secondary">';
                badges += ` ${span}<small>${domains_array[i]}</small></span>`;
            }
        }

        let desc =
            item.description === null
                ? ""
                : `<span class="text-muted"><small>${item.description}</small></span>`;

        let shortenedName = item.species.scientific_name
            .split(" ")
            .map((word, index) => (index === 0 ? `${word[0]}.` : word))
            .join(" ");
        let species = `<span class='text-muted float-end'><small><img src="${item.species.image_url}" class="w-15px"> <i>${shortenedName}</i></small></span>`;

        res = `<div class='option'>${item.name} ${desc} ${badges} ${species}</div>`;
    } else if (group === "dataset") {
        let imgURL = item.image_url || item.species_image_url;
        let img = !imgURL ? "" : `<img src="${imgURL}" class="w-25px"> `;
        let desc = !item.species_common_name
            ? ""
            : `<span class="text-muted"><small>${item.species_common_name}</small></span>`;

        let meta_array = item.species_meta.map((i) => i.value);
        let badges = "";
        for (let i = 0; i < meta_array.length; i++) {
            let elem = meta_array[i];
            if (
                elem &&
                !item.species.includes(elem) &&
                !item.species_common_name
            ) {
                let span =
                    '<span class="species-meta badge rounded-pill text-bg-secondary">';
                badges += ` ${span}<small>${elem}</small></span>`;
            }
        }
        let dataset_label = !item.name ? "" : `(${item.name})`;
        res = `<div class='option'>${img}<i>${item.species}</i> ${dataset_label} ${desc} ${badges}</div>`;
    }
    return res;
}
