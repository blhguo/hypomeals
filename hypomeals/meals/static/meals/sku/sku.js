$(function() {
    let removeButton = $("#removeButton");
    let skuCheckboxes = $(".sku-checkbox");
    const acIngredientUrl = $("#acIngredientUrl").attr("href");
    const acProductLineUrl = $("#acProductLineUrl").attr("href");
    const ingredientsInputId = $("#ingredientsInputId").val();
    const productLinesInputId = $("#productLinesInputId").val();
    const pageNumInputId = $("#pageNumInputId").val();
    const skuUrl = $("#skuUrl").attr("href");
    const removeSkuUrl = $("#removeSkuUrl").attr("href");
    let selectAllCheckbox = $("#selectAll");
    let submitButton = $("#submitButton");
    let exportButton = $("#exportButton");
    let exportFormulaCheckbox = $("#exportFormulaCheckbox");
    let exportProductLineCheckbox = $("#exportProductLineCheckbox");
    let skuFilterForm = $("#skuFilterForm");

    $("[data-toggle='tooltip']").tooltip();

    function refreshPage() {
        window.location.href = skuUrl;
    }

    skuCheckboxes.change(function() {
        removeButton.attr("disabled",
            $(".sku-checkbox:checked").length === 0);
    });

    selectAllCheckbox.change(function() {
        skuCheckboxes.prop("checked", $(this).prop("checked"));
        skuCheckboxes.trigger("change");
    });

    function removeSkus(toRemove) {
        let csrf_token = $("input[name=csrfmiddlewaretoken]").val();
        $.ajax(removeSkuUrl, {
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
                makeToast("Success", data.resp, -1)
                    .done(refreshPage);
            }
        });
    }

    removeButton.on("click", function(ev) {
        let toRemove = [];
        skuCheckboxes.each(function(i, cb) {
            if (cb.checked) {
                toRemove.push(cb.id);
            }
        });
        if (toRemove.length < 0) return;
        makeModalAlert(`Remove ${toRemove.length} SKU(s)`,
            `Are you sure you want to remove ${toRemove.length} SKU(s)?\n` +
            "This will also remove their associated formulas.\n" +
            "This cannot be undone.", function() {
            removeSkus(toRemove);
            });
    });

    exportButton.click(function() {
        const original = skuFilterForm.attr("action");
        let query = "?export=1";
        if (exportFormulaCheckbox.prop("checked")) {
            query += "&formulas=1";
        }
        if (exportProductLineCheckbox.prop("checked")) {
            query += "&pl=1"
        }
        skuFilterForm.attr("action", original + query)
            .submit()
            // Reset the form action so the user can submit another filter
            // request after downloading the exported file.
            .attr("action", original);
        return false;
    });

    submitButton.click(function() {
        skuFilterForm.submit();
    });

    /************* View Formula ***********/

    let viewFormulaButtons = $(".viewFormula");
    let viewFormulaUrl = $("#viewFormulaUrl").attr("href");
    let loadingSpinner = $("#loadingSpinner");
    let modalBody = $("#modalBody");
    let modalDiv = $("#modalDiv");

    function viewFormula() {
        let skuNumber = $(this).attr("id");
        let url = viewFormulaUrl.replace("0", String(skuNumber));
        let removed = modalBody.find("div.container").remove();
        if (removed.length > 0) {
            loadingSpinner.toggle("on");
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
                loadingSpinner.toggle("off");
                $(data.resp).appendTo(modalBody);
            })
    }
    viewFormulaButtons.click(viewFormula);

    /************** Pagination ****************/
    $("#pageList").find("a").on("click", function() {
        let page = $(this).attr("page");
        $(`#${pageNumInputId}`).val(page);
        skuFilterForm.submit();
    });

    registerAutocomplete($(`#${ingredientsInputId}`), acIngredientUrl, true);
    registerAutocomplete($(`#${productLinesInputId}`), acProductLineUrl, true);

    $("#resetAllButton").click(refreshPage);
});