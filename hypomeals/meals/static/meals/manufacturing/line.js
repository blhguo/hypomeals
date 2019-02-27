$(function() {
    let pageUrl = window.location.href;
    function refreshPage() {
        window.location.href = pageUrl;
    }

    Mousetrap.bind(["command+a", "ctrl+a"], function(ev) {
        ev.preventDefault();
        let selectAll = $("#selectAllCheckbox");
        selectAll.prop("checked", !selectAll.prop("checked"))
            .trigger("change");
    });

    Mousetrap.bind("n", function(ev) {
        ev.preventDefault();
        $("#addButton").trigger("click");
    });

    Mousetrap.bind(["del", "backspace"], function(ev) {
        ev.preventDefault();
        $("#removeButton").trigger("click");
    });

    $("#selectAllCheckbox").change(function() {
        $(".selectLineCheckboxes").prop("checked",
            $(this).prop("checked")).trigger("change");
    });

    $(".selectLineCheckboxes").change(function() {
        $("#removeButton").prop("disabled",
            $(".selectLineCheckboxes:checked").length === 0);
    });

    $("#removeButton").click(function(ev) {
        ev.preventDefault();
        let toRemove = $(".selectLineCheckboxes:checked").toArray()
            .map((l) => $(l).attr("data-line-id"));
        if (toRemove.length === 0) {
            makeModalAlert("Error",
                "You must select at least one manufacturing line.");
            return;
        }
        getJson($(this).attr("data-href"), {
            toRemove: JSON.stringify(toRemove),
        }).done(function(resp) {
            makeModalAlert("Success", resp, null, refreshPage);
        });
    });

    function onModalChanged(ev, modal) {
        modal.find("#formSubmitBtnGroup").toggle(false);
        modal.find(".meals-autocomplete")
            .each((_, e) => registerAutocomplete($(e)));
    }
    $("#addButton").click(function(ev) {
        ev.preventDefault();
        getJson($(this).attr("data-href"), {})
            .done(function(resp) {
                let modal = makeModalAlert("Add Manufacturing Line",
                    $(resp),onFormSubmit);
                modal.find(".modal-dialog").addClass("modal-lg");
                $(modal.find("input[type=text]")[0]).focus();
                modal.on("modal:changed", onModalChanged)
                    .trigger("modal:changed", [modal]);
            });
    });

    $(".editLineButtons").click(function(ev) {
        ev.preventDefault();
        getJson($(this).attr("href"), {})
            .done(function(resp) {
                let modal = makeModalAlert("Add Manufacturing Line",
                    $(resp),onFormSubmit);
                modal.find(".modal-dialog").addClass("modal-lg");
                modal.on("modal:changed", onModalChanged)
                    .trigger("modal:changed", [modal]);
            });
    });

    function onFormSubmit(modal) {
        modal.find("form").ajaxSubmit({
            success: function(data, textStatus) {
                if (!showNetworkError(data, textStatus)) {
                    return true;
                }
                if ("success" in data && data.success === true) {
                    alert(data.resp);
                    refreshPage();
                    return true;
                }
                modal.find("#formContainer").replaceWith($(data.resp));
                modal.trigger("modal:changed", [modal]);
            }
        });
        return false;
    }
});