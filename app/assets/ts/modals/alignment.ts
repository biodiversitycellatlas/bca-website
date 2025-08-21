/**
 * Sequence alignment functions.
 */

import $ from "jquery";

import { getDataPortalUrl } from "../utils/urls.js";
import { appendUserList, redrawUserLists } from "./list_editor.js";

/**
 * File upload for FASTA sequences.
 * Validates file size and sequence count, then populates the input textarea.
 *
 * @param {string} id - Base element identifier.
 * @param {number} maxMB - Maximum file size in MB.
 * @param {number} maxSeqs - Maximum number of sequences.
 */
export function uploadSequenceFile(id, maxMB, maxSeqs) {
    $(`#${id}_upload`).on("change", function () {
        const file = this.files[0];

        if (!file) {
            console.error("Error uploading file: no file selected");
            return;
        } else if (file.size > maxMB * 1024 * 1024) {
            alert(`Size limit of ${maxMB} MB exceeded.`);
        } else {
            // Add text to sequence textarea
            const reader = new FileReader();
            reader.onload = function (event) {
                const content = event.target.result;
                const lines = content.split("\n");

                // Count number of sequences in FASTA file
                const count = lines.filter((line) =>
                    line.startsWith(">"),
                ).length;

                if (count > maxSeqs) {
                    alert(
                        `The uploaded file has ${count} sequences. Only files with up to ${maxSeqs} sequences are allowed.`,
                    );
                } else {
                    $(`#${id}_query`).val(content);

                    // Update sequence count in status bar
                    $(`#${id}_query`)[0].dispatchEvent(new Event("input"));
                }
            };

            reader.readAsText(file);
        }
        // Clear selection to allow uploading the same file again
        $(this).val("");
    });
}

/**
 * Monitors sequence text input and updates text input.
 * Updates number of sequences and highlights errors.
 *
 * @param {string} id - Base element identifier.
 * @param {number} maxSeqs - Maximum number of sequences.
 */
export function highlightSequenceText(id, maxSeqs) {
    $(`#${id}_query`).on("input", function () {
        let text = $(this).val();
        let matches = text.match(/^>/gm);
        let isEmptyText = text.trim() === "";
        let count = matches ? matches.length : isEmptyText ? 0 : 1;

        let text_color,
            disabled,
            count_label = $(`#${id}_count`);
        count_label.text(count);
        if (count > maxSeqs) {
            text_color = "var(--bs-danger)";
            disabled = true;
        } else if (isEmptyText) {
            text_color = "";
            disabled = true;
        } else {
            text_color = "";
            disabled = false;
        }

        count_label.css("color", text_color);
        $(`#${id}_align_btn`).prop("disabled", disabled);
    });
}

function startLoadingState(id) {
    $(`#${id}_align_btn`).prop("disabled", true);
    $(`#${id}_align_spinner`).removeClass("d-none");
}

function stopLoadingState(id) {
    $(`#${id}_align_spinner`).addClass("d-none");
}

/**
 * Renders an error alert using an HTML template.
 * Clears existing messages before showing the new one.
 *
 * @param {string} id - Base element ID.
 * @param {string} title - Error title.
 * @param {string} description - Detailed message.
 */
function setErrorMessage(id, title, description) {
    clearMessages(id);

    const template = document.getElementById(`${id}_errorTemplate`);
    const clone = template.content.cloneNode(true);

    clone.querySelector(".alert-title").textContent = title;
    clone.querySelector(".alert-description").textContent = description;

    document.getElementById(`${id}_alertContainer`).appendChild(clone);
}

/**
 * Removes all alerts from the container.
 */
function clearMessages(id) {
    $(`#${id}_alertContainer`).empty();
}

/**
 * Triggers sequence alignment via a REST API call.
 * Results are summarised into custom gene lists.
 *
 * @param {string} id - Base element ID.
 * @param {string} species - Target species.
 * @param {string} type - Alignment type (nucleotide or protein).
 */
export function alignSequence(id, species, type) {
    $(`#${id}_align_btn`).on("click", function () {
        startLoadingState(id);

        let url = getDataPortalUrl("rest:align-list");
        fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                sequences: $(`#${id}_query`).val(),
                type: $(`input[name="${id}_type"]:checked`).val(),
                species: species,
            }),
        })
            .then((response) => response.json())
            .then((data) => {
                clearMessages(id);
                if (data && data.length === 0) {
                    setErrorMessage(
                        id,
                        "Error!",
                        "No alignment found for this query.",
                    );
                    return;
                }

                const result = data.reduce((acc, { query, target }) => {
                    acc[query] ||= [];
                    acc[query].push(target);
                    return acc;
                }, {});

                let name;
                for (let key in result) {
                    name = key + " alignment";
                    name = appendUserList(
                        id + type,
                        species,
                        name,
                        result[key],
                        "Alignment results",
                        "gray",
                        false,
                    );
                }
                redrawUserLists(id, species, [name]);

                $(`#${id}_alignment`).modal("hide");
                $(`#${id}_${type}_editor`).modal("show");

                // Clean form state
                $(`#${id}_query`).val("");
                $(`#${id}_align_btn`).prop("disabled", true);
            })
            .catch((error) => {
                setErrorMessage(id, "Error!", error);
            })
            .finally(() => stopLoadingState(id));
    });
}
