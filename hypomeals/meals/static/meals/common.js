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
 * @param isMultiple whether the autocomplete will accept multiple,
 *      comma-separated words.
 */
function registerAutocomplete(input, url, isMultiple) {
    if (!url) {
        url = input.attr("data-autocomplete-url");
    }
    if (isMultiple === undefined || isMultiple === null) {
        isMultiple = input.attr("class")
            .search("meals-autocomplete-multiple") !== -1;
    }
    let opts = {
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
    };
    if (isMultiple) {
        opts["select"] = function( event, ui ) {
            let terms = split( this.value );
            // remove the current input
            terms.pop();
            // add the selected item
            terms.push(ui.item.value);
            // add placeholder to get the comma-and-space at the end
            terms.push("");
            this.value = terms.join( ", " );
            return false;
        }
    }
    input.on("keydown", function(ev) {
        if (ev.keyCode === $.ui.keyCode.TAB
            && $(this).autocomplete("instance").menu.active) {
            ev.preventDefault();
        }
    })
    .autocomplete(opts);
}

$(function() {
    let messagesDiv = $("#messagesDiv");
    if (messagesDiv.length > 0) {
        setTimeout(function() {
            messagesDiv.fadeOut();
        }, 3000);
    }

    $(".meals-autocomplete").each(function (i, e) {
        let element = $(e);
        let url = element.attr("data-autocomplete-url");
        let isMultiple = element.attr("class")
            .search("meals-autocomplete-multiple") !== -1;
        registerAutocomplete(element, url, isMultiple);
    })
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

/**
 * Makes a self-dismissing toast with title and message.
 * @param title the title of the toast
 * @param message the message of the toast
 * @param toastDiv an optional <div class="toast"> element to render the toast
 *      in. If undefined, one will be created. The toastDiv element can be
 *      an HTML element, a jQuery element, or an HTML string. It should have
 *      at least a <div class="toast-header"> and a <div class="toast-body">
 *      subelements, both of which should be initially empty.
 * @param timeout a timeout (in ms) before the toast disappears. If <=0, the
 *      toast must be dismissed manually.
 * @return a Promise which is resolved when the Toast is dismissed.
 */
function makeToast(title, message, timeout, toastDiv) {
    let header = null;
    let body = null;
    let deferred = $.Deferred();
    if (toastDiv === undefined) {
        let positioningDiv = $("<div>")
            .attr("style",
                "position: fixed; top: 50%; left: 50%;" +
                "transform: translate(-50%, -50%); min-width: 300px;");
        toastDiv = $("<div>").attr("class", "toast")
            .attr("role", "alert")
            .appendTo(positioningDiv);
        $("body").append(positioningDiv);
        header = $("<div>").attr("class", "toast-header");
        toastDiv.append(header);
        body = $("<div>").attr("class", "toast-body");
        toastDiv.append(body);
    } else {
        header = $(toastDiv).find(".toast-header");
        body = $(toastDiv).find(".toast-body");
    }

    if (timeout === undefined || timeout <= 0) {
        // Apparently not setting a timeout means "immediately"
        // 3 Hours should be enough...
        timeout = 10800000;
    }
    toastDiv.attr("data-autohide", true)
        .attr("data-delay", timeout);
    const originalHeader = header.clone(true);
    const originalBody = body.clone(true);
    header.append([
        $("<span>").attr("class", "fas fa-bell mr-2"),
        $("<strong>").attr("class", "mr-auto").text(" " +title),
        $("<small>").attr("class", "text-muted").text("Just Now"),
        $("<button>").attr("type", "button")
            .attr("class", "ml-2 mb-1 close")
            .attr("data-dismiss", "toast")
            .append($("<span>").attr("aria-hidden", true)
                .html("&times;")),
    ]);

    body.attr("style", "white-space: pre-line")
        .text(message);

    $(toastDiv).toast("show");

    $(toastDiv).on("hidden.bs.toast", function() {
        header.replaceWith(originalHeader);
        body.replaceWith(originalBody);
        deferred.resolve("hidden");
    });

    return deferred.promise();
}


/**
 * Makes a new modal alert dialog (can be used as a replacement to the native
 * browser confirm() function), and attach listeners.
 * For example,
 * makeModalAlert("Confirm", "Do you want to proceed?", function (modal) {
 *     console.log("modal is", modal);
 *     alert("user clicked OK");
 * }, function (modal) {
 *     alert("user canceled");
 * }).done(function () {
 *     alert("modal was dismissed");
 * });
 * @param title the title of the alert
 * @param message the message of the alert. Can be a string, in which case it
 *      is wrapped in a <p> element; or any jQuery object, in which case it is
 *      simply appended to the body of the modal.
 * @param success a callback when the user clicks the "OK" button. The callback
 *      will receive the modal jQuery object. If the callback returns false,
 *      the modal will not be hidden.
 *      Note: If not provided or null, the button will not be shown.
 * @param cancel a callback when the user clicks the "Cancel" button. The
 *      callback will receive the modal jQuery object. If the callback returns
 *      false, the modal will not be hidden.
 *      If not provided or null, the button will close the dialog.
 * @return {*|jQuery} a Deferred object that is resolved when the user dismisses
 *      the dialog.
 */
function makeModalAlert(title, message, success, cancel) {
    let modalHtml = `
<div class="modal fade" tabindex="-1" role="dialog">
  <div class="modal-dialog modal-dialog-centered" role="document">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">${title}</h5>
        <button type="button" class="close" data-dismiss="modal" aria-label="Close">
          <span aria-hidden="true">&times;</span>
        </button>
      </div>
      <div class="modal-body">
      </div>
      <div class="modal-footer">
        <button type="button" 
            id="modalCancelButton"
            class="btn btn-secondary">Close</button>
        <button type="button" 
            id="modalSuccessButton" 
            class="btn btn-primary">OK</button>
      </div>
    </div>
  </div>
</div>
`;
    let modal = $(modalHtml);
    let modalBody = modal.find(".modal-body");
    if (typeof message === "string" || message instanceof String) {
        message = $("<p>").attr("style", "white-space: pre-line")
            .html(message);
    } else {
        message = $(message).clone(true, true);
    }
    modalBody.append(message);
    let successButton = modal.find("#modalSuccessButton");
    if (success === undefined || success === null) {
        successButton.toggle("false");
    } else {
        successButton.on("click", function () {
            if (_.isFunction(success)) {
                if (success(modal) === false) {
                    return;
                }
            }
            modal.modal("hide");
        });
    }
    modal.find("#modalCancelButton").on("click", function() {
        if (_.isFunction(cancel)) {
            if (cancel(modal) === false) {
                return;
            }
        }
        modal.modal("hide");
    });
    modal.on("hidden.bs.modal", function() {
        modal.modal("dispose");
        modal.remove();
    });
    $("body").append(modal);
    modal.modal("show");
    return modal;
}