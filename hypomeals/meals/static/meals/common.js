/************** Autocomplete **************/
// Adapted from https://jqueryui.com/autocomplete/#multiple-remote

function split(val) {
    return val.split(/,\s*/);
}

function lastTerm(val) {
    return split(val).pop();
}

/**
 * Registers autocompletion on a jQuery object with the given URL.
 * @param input a jQuery object
 * @param url the backend URL for autocompletion
 */
function registerAutocomplete(input, url) {
    input.on("keydown", function(ev) {
        if (ev.keyCode === $.ui.keyCode.TAB
            && $(this).autocomplete("instance").menu.active) {
            ev.preventDefault();
        }
    })
    .autocomplete({
        source: function(request, response) {
            $.getJSON(url, {
                term: lastTerm(request.term)
            }, response)
        },
        search: function() {
            let term = lastTerm(this.value);
            // Only perform a search when user has typed more than 2 chars
            return term.length >= 2;
        },
        focus: function() {
            return false;
        },
    });
}

$(function() {
    let messagesDiv = $("#messagesDiv");
    if (messagesDiv.length > 0) {
        setTimeout(function() {
            messagesDiv.fadeOut();
        }, 3000);
    }
});

/**
 * Displays an error in a JSON response, if there is one. Suitable for use in
 * the {@code done} handler of a {@code jqXHR} object.
 * @param data the JSON data returned by the server
 * @param textStatus the status of the response
 * @returns {boolean} whether processing should continue: true iff there's an
 *      error.
 */
function showNetworkError(data, textStatus) {
    if (textStatus !== "success" || !("resp" in data)) {
        alert(
            `[status=${textStatus}] Cannot get data from server.\n` +
            (data.error !== null) ? "Error: " + data.error : "" +
            "\nPlease refresh the page and try again."
        );
        return false;
    }
    return true;
}
