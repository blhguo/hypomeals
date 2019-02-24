$(function() {
    let removeButton = $("#removeButton");
    let productlineCheckboxes = $(".product_line-checkbox");
    let selectAllCheckbox = $("#selectAllCheckbox");
    let resetAllButton = $("#resetAllButton");
    let submitButton = $("#submitButton");
    const productlineFilterForm = $("#productlineFilterForm");
    const removeProductLinesUrl = $("#removeProductLinesUrl").attr("href");
    const productlineUrl = $("#productlineUrl").attr("href");
    //const acProductLineUrl = $("#acProductLineUrl").attr("href");
    const pageNumInputId = $("#pageNumInputId").val();
    //const nameInputId = $("#nameInputId").val();
    const exportButton = $("#exportButton");
    const reportButton = $("#reportButton");

    $("[data-toggle='tooltip']").tooltip();

    function refreshPage() {
        window.location.href = productlineUrl;
    }

    productlineCheckboxes.change(function() {
        removeButton.attr("disabled",
            $(".product_line-checkbox:selected").length > 0);
    });

    selectAllCheckbox.on("change", function(ev) {
        productlineCheckboxes.prop("checked",
            $(this).prop("checked"));
        productlineCheckboxes.trigger("change");
    });

    resetAllButton.click(function() {
        refreshPage();
        return false;
    });

    submitButton.click(function() {
        productlineFilterForm.submit();
    });

    removeButton.on("click", function(ev) {
        let toRemove = [];
        productlineCheckboxes.each(function(_, cb) {
            if (cb.checked) {
                toRemove.push(cb.id);
            }
        });
        let csrf_token = $("input[name=csrfmiddlewaretoken]").val();
        if (confirm(
            `Are you sure you want to remove ${toRemove.length} Product Lines(s)?\n` +
            "This cannot be undone."
        )) {
            $.ajax(removeProductLinesUrl, {
                type: "POST",
                data: {
                    to_remove: JSON.stringify(toRemove),
                    csrfmiddlewaretoken: csrf_token,
                },
                dataType: "json",
            }).done(function(data, textStatus) {
                if (!showNetworkError(data, textStatus)) {
                    return;
                }
                if ("resp" in data) {
                    alert(data.resp);
                }
                refreshPage();
            });
        }
    });

    $("#pageList").find("a").on("click", function() {
        let page = $(this).attr("page");
        $(`#${pageNumInputId}`).val(page);
        $("#product_lineFilterForm").submit();
    });

    /***************** View Related SKUs ****************/

    let viewPLSkusButtons = $('.viewPLSkus');
    let viewPLSkusUrl = $("#viewPLSkusUrl").attr("href");
    let loadingSpinner = $("#loadingSpinner");
    let modalBody = $("#modalBody");
    let modalDiv = $("#modalDiv");

    function viewPLSkus() {
        let product_line_name = $(this).attr("id");
        let url = viewPLSkusUrl.replace("0", String(product_line_name));
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
        })
    }
    viewPLSkusButtons.click(viewPLSkus);

    exportButton.on("click", function() {
        const original = productlineFilterForm.attr("action");
        productlineFilterForm.attr("action", original + "?export=1")
            .submit()
            .attr("action", original);

        return false;
    });

    reportButton.click(function() {
        const original = productlineFilterForm.attr("action");
        productlineFilterForm.attr("action", original + "?report=1")
            .submit()
            .attr("action", original);

        return false;
    });

});