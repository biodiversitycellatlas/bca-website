export function displaySearchResults(item, escape) {
    let group = escape(item.group);
    let res = "";

    if (group === "gene") {
        let badges = "";
        let domains_array = item.domains;
        for (let i = 0; i < domains_array.length; i++) {
            if (domains_array[i] !== "") {
                badges += `
                    <span class="badge rounded-pill text-bg-secondary">
                        <small>${escape(domains_array[i])}</small>
                    </span>
                `;
            }
        }

        let desc =
            item.description === null
                ? ""
                : `
                    <span class="text-muted">
                        <small>${escape(item.description)}</small>
                    </span>
                `;

        let shortenedName = escape(item.species.scientific_name)
            .split(" ")
            .map((word, index) => (index === 0 ? `${word[0]}.` : word))
            .join(" ");
        let species = `
            <span class='text-muted float-end'>
                <small><img src="${escape(item.species.image_url)}" class="w-15px">
                <i>${shortenedName}</i></small>
            </span>
        `;

        res = `<div class='option'>${escape(item.name)} ${desc} ${badges} ${species}</div>`;
    } else if (group === "dataset") {
        let imgURL = escape(item.image_url || item.species_image_url);
        let img = !imgURL ? "" : `<img src="${imgURL}" class="w-25px"> `;
        let desc = !item.species_common_name
            ? ""
            : `
                <span class="text-muted">
                    <small>${escape(item.species_common_name)}</small>
                </span>
            `;

        let meta_array = item.species_meta.map((i) => escape(i.value));
        let badges = "";
        for (let i = 0; i < meta_array.length; i++) {
            let elem = meta_array[i];
            if (
                elem &&
                !item.species.includes(elem) &&
                !item.species_common_name
            ) {
                badges += `
                    <span class="species-meta badge rounded-pill text-bg-secondary">
                        <small>${elem}</small>
                    </span>
                `;
            }
        }
        let dataset_label = !item.name ? "" : `(${escape(item.name)})`;
        res = `<div class='option'>${img}<i>${escape(item.species)}</i> ${dataset_label} ${desc} ${badges}</div>`;
    }
    return res;
}
