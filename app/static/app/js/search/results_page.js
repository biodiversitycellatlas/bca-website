/* global $ */

import { getDataPortalUrl } from "../utils/urls.js";
import { highlightMatch } from "../utils/utils.js";

export function updateQuery(key, value) {
    var searchParams = new URLSearchParams(window.location.search);
    if (value) {
        searchParams.set(key, value);
    } else {
        searchParams.delete(key);
    }

    var searchString = '?' + searchParams.toString();
    if (window.location.search != searchString) {
        window.location.search = searchString;
    }
}

function appendResult(title, title_url, subtitle, subtitle_url,
                      description, badges) {
    const template  = $('#result-template');
    const container = $('#results');
    let $clone = $(template.html());

    var title_mod = title,
        subtitle_mod = subtitle,
        description_mod = description;

    // Highlight query matches
    var query = $('#search').val().trim();
    if (query) {
        title_mod       = highlightMatch(title_mod, query);
        subtitle_mod    = highlightMatch(subtitle_mod, query);
        description_mod = highlightMatch(description_mod, query);
        badges          = badges.map(item => highlightMatch(item, query));
    }

    // Add word break lines on underscores
    const mods = { title_mod, subtitle_mod, description_mod };
    for (const key in mods) {
        // Regex: ignore HTML code, i.e. text inside brackets <>
        mods[key] = (mods[key] || '')
            .replace(/(?<!<[^>]*)[_/]/g, match => match + "<wbr>");
    }
    ({ title_mod, subtitle_mod, description_mod } = mods);

    $clone.find('.result-title')
        .html(title_mod).attr('href', title_url);
    $clone.find('.result-subtitle')
        .html(subtitle_mod).attr('href', subtitle_url);
    $clone.find('.result-description').html(description_mod);

    badges = badges
        .map(item => `<span class="badge bg-secondary">${item}</span>`)
        .join(" ");
    $clone.find('.result-badges').html(badges);

    container.append($clone);
}

export function loadSearchResults(species, query="", limit=12, offset=0, category='datasets') {
    // Fetch data from API
    var params = new URLSearchParams ({
        q: encodeURIComponent(query),
        limit: limit,
        offset: offset,
        species: species.replace('_', ' ')
    });

    if (category === "datasets") {
        var datasetsURL = new URL(
            getDataPortalUrl('rest:dataset-list'), window.location.href);
        datasetsURL.search = params;

        fetch(datasetsURL)
            .then(res => res.json())
            .then(data => {
                data.results.forEach(item => {
                    var title = `<i>${item.species}</i>`;
                    if (item.name) {
                        title = `${title} - ${item.name}`;
                    }
                    var subtitle = item.species_common_name || '';

                    var description = item.species_description;
                    var badges = item.species_meta.map(item => item.value).filter(item =>
                        !title.includes(item) && !subtitle.includes(item)
                    );

                    var dataset_url = getDataPortalUrl('atlas', item.slug);
                    appendResult(title, dataset_url, subtitle, dataset_url,
                                 description, badges);
                });
                $('#results_count').text(`${data.count.toLocaleString()} results`);
            })
            .catch(err => {
                console.error('Error loading data:', err);
            });
    } else if (category === "genes") {
        var genesURL = new URL(getDataPortalUrl("gene_list"), window.location.href);
        genesURL.search = params;

        fetch(genesURL)
            .then(res => res.json())
            .then(data => {
                data.results.forEach(item => {
                    var gene = item.name;
                    var species_name = item.species ? item.species.scientific_name : '';
                    var description = item.description;
                    var domains = item.domains;

                    var slug = item.species ?
                        item.species.scientific_name.slug : species.slug;
                    var species_url = getDataPortalUrl("atlas", slug);
                    var gene_url = getDataPortalUrl("atlas_gene", dataset=slug, gene=gene);
                    appendResult(gene, gene_url, species_name, species_url,
                                 description, domains);
                });
                $('#results_count').text(`${data.count.toLocaleString()} results`);
            })
            .catch(err => {
                console.error('Error loading data:', err);
            });
    }
}

export function initFormHandler() {
    // Modify form before submission to only modify query
    $('form').on('submit', function(event) {
        event.preventDefault();
        updateQuery('q', event.target.q.value);
    });
}