let templateData = new Map();

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
    });

    let templateDataDiv = $("div#hiddenData");
    if (templateDataDiv.length > 0) {
        templateDataDiv.children().each(function(i, el) {
            el = $(el);
            if (el.is("a")) {
                templateData.set(el.attr("id"), el.attr("href"));
            } else if (el.is("input")) {
                templateData.set(el.attr("id"), el.val());
            } else {
                let data = {};
                let found = false;
                $.each(el[0].attributes, function(_, att) {
                    if (att.name.startsWith("data")) {
                        data[att.name] = att.value;
                        found = true;
                    }
                });
                if (found) {
                    templateData.set(el.attr("id"), data);
                }
            }
        });
    }
});

/**
 * Displays an error in a JSON response, if there is one. Suitable for use in
 * the {@code done} handler of a {@code jqXHR} object.
 * @param data the JSON data returned by the server
 * @param textStatus the status of the response
 * @param suppressAlerts whether to show an alert to the user if a network error
 *      has occurred
 * @returns {boolean} whether processing should continue: true iff there's an
 *      error.
 */
function showNetworkError(data, textStatus, suppressAlerts) {
    if (textStatus !== "success" && !suppressAlerts) {
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
  <div class="modal-dialog modal-dialog-centered bd-example-modal-lg" style="width:3000px;" role="document">
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
        successButton.toggle(false);
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

function makeCustomAlert(title, message, success, cancel) {
    let modalHtml = `
<div class="modal fade" tabindex="-1" role="dialog">
  <div class="modal-dialog modal-lg" style="width:3000px;" role="document">
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
            id="modalSuccessButton" 
            class="btn btn-primary">Query</button>
        <button type="button" 
            id="modalCopyButton" 
            class="btn btn-primary">Copy to Goal</button>
        <button type="button" 
            id="modalCancelButton"
            class="btn btn-secondary">Close</button>
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
        successButton.toggle(false);
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
    modal.find("#modalCopyButton").on("click", function() {
       modal.find()
    });
    modal.on("hidden.bs.modal", function() {
        modal.modal("dispose");
        modal.remove();
    });
    $("body").append(modal);
    modal.modal("show");
    return modal;
}

function ajaxJson(url, method, data, suppressAlerts) {
    let deferred = $.Deferred();
    $.ajax({
        url: url,
        method: method,
        data: data,
    }).done(function(data, textStatus) {
        if (!showNetworkError(data, textStatus, suppressAlerts)) {
            return;
        }
        if ("error" in data && data.error) {
            if (!suppressAlerts) {
                makeModalAlert("Error", data.error);
            }
            deferred.reject(data.error);
            return;
        }
        if (!("resp" in data)) {
            let msg = "The server returned an empty response.";
            if (!suppressAlerts) {
                makeModalAlert("Error",
                    msg + " Please try again later.")
            }
            deferred.reject(msg);
            return;
        }
        deferred.resolve(data.resp);
    }).fail(function(jqxhr, textStatus, errorThrown) {
        showNetworkError({error: errorThrown}, textStatus, suppressAlerts);
        deferred.reject(errorThrown);
    });
    return deferred;
}

function getJson(url, data, suppressAlerts) {
    return ajaxJson(url, "get", data, suppressAlerts);
}

function postJson(url, data, suppressAlerts) {
    return ajaxJson(url, "post", data, suppressAlerts);
}

/**
 * Turns an <input> element into an input group, optionally appending/prepending
 * text/elements
 * @param input an <input> element, or a jQuery object representing it
 * @param prepend {string|jQuery} optional element/text to prepend to the
 *      input element
 * @param append {string|jQuery} optional element/text to append to the input
 *      element
 * @param replaceOriginal {boolean} if true, the new input group will replace
 *      the original input element
 * @return {jQuery} the general input element.
 */
function makeInputGroup(input, prepend, append, replaceOriginal) {
    let html = $(`
<div class="input-group">
  <div class="input-group-prepend">
  </div>
  <div id="placeholder"></div>
  <div class="input-group-append">
  </div>
</div>`);
    if (prepend !== undefined && prepend !== null) {
        if (typeof prepend === "string") {
            prepend = $(`<span class="input-group-text">${prepend}</span>`);
        } else {
            prepend = $(prepend)
        }
        html.find(".input-group-prepend").append(prepend);
    }
    if (append !== undefined && append !== null) {
        if (typeof append === "string") {
            append = $(`<span class="input-group-text">${append}</span>`);
        } else {
            append = $(append);
        }
        html.find(".input-group-append").append(append);
    }
    input = $(input);
    if (input.is("select")) {
        input.addClass("custom-select").removeClass("form-control");
    }
    html.find("#placeholder").replaceWith($(input).clone());
    if (replaceOriginal) {
        $(input).replaceWith(html);
    }
    return html;
}

function randomChoice(choices) {
    return choices[Math.floor(Math.random() * choices.length)];
}

function upcCheckDigit(upcNumber) {
    let sum = 0;
    for (let i of [1, 3, 5, 7, 9, 11]) {
        sum += Number(upcNumber[i - 1]);
    }
    sum *= 3;
    for (let i of [2, 4, 6, 8, 10]) {
        sum += Number(upcNumber[i - 1]);
    }
    sum %= 10;
    return sum === 0 ? 0 : (10 - sum);
}

function generateRandomUpc() {
    let upc = randomChoice(["0", "1", "6", "7", "8", "9"]);
    for (let i = 0; i < 10; i++) {
        upc += String(Math.floor(Math.random() * 10));
    }
    upc += upcCheckDigit(upc);
    return upc;
}