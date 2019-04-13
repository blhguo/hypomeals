$(function () {
    let removeButton = $("#removeButton");
    let skuCheckboxes = $(".sku-checkbox");
    const pageNumInputId = $("#pageNumInputId").val();
    const skuUrl = $("#skuUrl").attr("href");
    const removeSkuUrl = $("#removeSkuUrl").attr("href");
    let selectAllCheckbox = $("#selectAll");
    let submitButton = $("#submitButton");
    let exportButton = $("#exportButton");
    let exportFormulaCheckbox = $("#exportFormulaCheckbox");
    let exportProductLineCheckbox = $("#exportProductLineCheckbox");
    let skuFilterForm = $("#skuFilterForm");
    let bulkButton = $("#bulkButton");

    $("[data-toggle='tooltip']").tooltip();

    function refreshPage() {
        window.location.href = skuUrl;
    }

    skuCheckboxes.change(function () {
        let numChecked = $(".sku-checkbox:checked").length;
        removeButton.attr("disabled", numChecked === 0);
        bulkButton.attr("disabled", numChecked === 0);
    });

    selectAllCheckbox.change(function () {
        skuCheckboxes.prop("checked", $(this).prop("checked"));
        skuCheckboxes.trigger("change");
    });

    function removeSkus(toRemove) {
        let csrf_token = $("input[name=csrfmiddlewaretoken]").val();
        postJson(removeSkuUrl, {
            to_remove: JSON.stringify(toRemove),
            csrfmiddlewaretoken: csrf_token
        }).done(function(data) {
            refreshPage();
        })
    }

    removeButton.on("click", function (ev) {
        let toRemove = [];
        skuCheckboxes.each(function (i, cb) {
            if (cb.checked) {
                toRemove.push($(cb).attr("data-sku-id"));
            }
        });
        if (toRemove.length < 0) return;
        makeModalAlert(`Remove ${toRemove.length} SKU(s)`,
            `Are you sure you want to remove ${toRemove.length} SKU(s)?
            This cannot be undone.`, function () {
                removeSkus(toRemove);
            });
    });

    exportButton.click(function () {
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

    submitButton.click(function () {
        skuFilterForm.submit();
    });

    /************* View Formula ***********/

    let viewFormulaButtons = $(".viewFormula");
    let loadingSpinner = $("#loadingSpinner");

    function viewFormula(e) {
        e.preventDefault();
        let url = $(this).attr("href");
        let modal = makeModalAlert("View Formula", loadingSpinner);
        modal.find(".modal-dialog").addClass("modal-lg");
        getJson(url, {})
            .done(function(data) {
                modal.find("#loadingSpinner").toggle(false);
                $(data).appendTo(modal.find(".modal-body"));
            }).fail(function(error) {modal.modal("hide");});
        return false;
    }

    viewFormulaButtons.click(viewFormula);


    /************** Pagination ****************/
    $("#pageList").find("a").on("click", function () {
        let page = $(this).attr("page");
        $(`#${pageNumInputId}`).val(page);
        skuFilterForm.submit();
    });

    /************** Add Bulk Edit Modal *************/
    const viewLinesUrl = $("#viewLinesUrl").attr("href");
    const editLinesUrl = $("#editLinesUrl").attr("href");
    let bulkModal = null;


    function ajaxDone(data, textStatus) {
        bulkModal.find("#loadingSpinner").toggle(false);
        bulkModal.find(".modal-body").append($(data.resp));
        bulkModal.find(".indeterminate").prop("indeterminate", true);
    }

    bulkButton.click(function () {
        if ($(".sku-checkbox:checked").length === 0) {
            makeModalAlert("Error",
                "You must select at least one SKU before bulk editing manufacturing lines.");
            return;
        }
        $("#ml-content").remove();
        let skus = [];
        skuCheckboxes.each(function (i, cb) {
            if (cb.checked) {
                skus.push($(cb).attr("data-sku-id"));
            }
        });
        if (skus.length <= 0) return;
        bulkModal = makeModalAlert("Edit Manufacturing Line Mapping",
            loadingSpinner,
            saveMappings);
        bulkModal.find(".modal-dialog").addClass("modal-lg");
        $.getJSON(viewLinesUrl, {"skus": JSON.stringify(skus)})
            .done(ajaxDone)
            .fail(function (_, __, errorThrown) {
                alert(`Error loading content: ${errorThrown}`);
                bulkModal.modal("hide");
            })
    });
    function saveDone(data, textStatus) {
        if (!showNetworkError(data, textStatus)) {
            return
        }
        alert(data.resp);
        skuFilterForm.submit();
    }

    function saveMappings() {
        let skus = [];
        skuCheckboxes.each(function (i, cb) {
            if (cb.checked) {
                skus.push($(cb).attr("data-sku-id"));
            }
        });
        let checked = [];
        let unchecked = [];
        let boxes = $(".ml-line-box");
        boxes.each((i, box) => {
            if ($(box).prop("checked")) {
                checked.push(box.id)
            }
            if (!$(box).prop("checked") && !$(box).prop("indeterminate")) {
                unchecked.push(box.id)
            }
        });
        $.getJSON(editLinesUrl, {
            "skus": JSON.stringify(skus),
            "checked": JSON.stringify(checked),
            "unchecked": JSON.stringify(unchecked)
        })
            .done(saveDone)
            .fail(function (_, __, errorThrown) {
                alert(`Error loading content: ${errorThrown}`);
            })

    }

    $("#resetAllButton").click(refreshPage);
});

$(function() {
    Mousetrap.bind("n", function(e) {
        e.preventDefault();
        $("#addSkuButton")[0].click();
    });
    Mousetrap.bind(["command+a", "ctrl+a"], function(e) {
        e.preventDefault();
        $("#selectAll").trigger("click");
    })
});