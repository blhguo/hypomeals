$(function() {
    let removeButton = $("#removeButton");
    let plCheckboxes = $(".selectProductLineCheckboxes");
    let selectAllCheckbox = $("#selectAllCheckbox");
    let pageUrl = window.location.href;

    $("[data-toggle='tooltip']").tooltip();

    function refreshPage() {
        window.location.href = pageUrl;
    }

    plCheckboxes.change(function() {
        removeButton.prop("disabled",
            $(".selectProductLineCheckboxes:checked").length  === 0);
    });

    selectAllCheckbox.on("change", function(ev) {
        plCheckboxes.prop("checked",
            $(this).prop("checked"));
        plCheckboxes.trigger("change");
    });

    removeButton.on("click", function(ev) {
        ev.preventDefault();
        let toRemove = $(".selectProductLineCheckboxes:checked")
            .toArray()
            .map((pl) => $(pl).attr("data-pl-id"));
        if (toRemove.length === 0) {
            makeModalAlert("Error",
                "You must select at least one product line.");
            return;
        }
        let url = $(this).attr("data-href");
        makeModalAlert("Confirm",
            `Are you sure you want to remove ${toRemove.length} Product Line(s)?
            This will remove all SKUs belonging to these Product Line(s).
            This operation cannot be undone.`,
            function() {
                $.getJSON(url, {
                    toRemove: JSON.stringify(toRemove),
                }).done(function(data, textStatus) {
                    if (!showNetworkError(data, textStatus)) {
                        return;
                    }
                    if ("error" in data && data.error) {
                        makeModalAlert("Error", data.error);
                    }
                    makeModalAlert("Success", data.resp, refreshPage);
                })
            });
    });

    /***************** View Related SKUs ****************/

    let viewPLSkusButtons = $('.viewPLSkus');
    let viewPLSkusUrl = $("#viewPLSkusUrl").attr("href");
    let loadingSpinner = $("#loadingSpinner");
    let modalBody = $("#modalBody");
    let modalDiv = $("#modalDiv");

    function viewPLSkus() {
        let id = $(this).attr("data-pl-id");
        let url = viewPLSkusUrl.replace("0", String(id));
        let removed = modalBody.find("div.container").remove();
        if (removed.length > 0) {
            loadingSpinner.toggle(false);
        }
        $.getJSON(url, {})
            .done(function(data, textStatus) {
                if (!showNetworkError(data, textStatus)) {
                    return;
                }
                if ("error" in data && data.error != null) {
                    alert(data.error);
                    modalDiv.modal("hide");
                    return;
                }
                loadingSpinner.toggle(false);
                $(data.resp).appendTo(modalBody);
        });
    }
    viewPLSkusButtons.click(viewPLSkus);
});