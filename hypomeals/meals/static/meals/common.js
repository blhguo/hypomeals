/************** Autocomplete **************/
// Adapted from https://jqueryui.com/autocomplete/#multiple-remote

function split(val) {
    return val.split(/,\s*/);
}

function lastTerm(val) {
    return split(val).pop();
}

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
