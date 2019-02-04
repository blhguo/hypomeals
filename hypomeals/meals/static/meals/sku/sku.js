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
    let skuFilterForm = $("#skuFilterForm");

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

    removeButton.on("click", function(ev) {
        let toRemove = [];
        skuCheckboxes.forEach(function(cb) {
            if (cb.checked) {
                toRemove.push(cb.id);
            }
        });
        if (confirm(
            `Are you sure you want to remove ${toRemove.length} SKU(s)?\n` +
            "This cannot be undone."
        )) {
            $.ajax(removeSkuUrl, {
                type: "POST",
                data: {to_remove: JSON.stringify(toRemove)},
                dataType: "json",
            }).done(function(data, textStatus) {
                if (textStatus !== "success") {
                    alert(
                        `[status=${textStatus}] Error removing` +
                        `${toRemove.length} SKU(s):` +
                        ("error" in data) ? data.error : "" +
                        `\nPlease refresh the page and try again later.`
                    );
                } else {
                    if ("resp" in data) {
                        alert(data.resp);
                    }
                }
                refreshPage();
            });
        }
    });

    exportButton.click(function() {
        const original = skuFilterForm.attr("action");
        let query = "?export=1";
        if (exportFormulaCheckbox.prop("checked")) {
            query += "&formulas=1";
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

    /************** Pagination ****************/
    $("#pageList").find("a").on("click", function() {
        let page = $(this).attr("page");
        $(`#${pageNumInputId}`).val(page);
        skuFilterForm.submit();
    });

    registerAutocomplete($(`#${ingredientsInputId}`), acIngredientUrl);
    registerAutocomplete($(`#${productLinesInputId}`), acProductLineUrl);

    $("#resetAllButton").click(refreshPage);
});