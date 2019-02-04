$(function() {
    let removeButton = $("#removeButton");
    let ingredientCheckboxes = $(".ingredient-checkbox");
    let selectAllCheckbox = $("#selectAllCheckbox");
    let resetAllButton = $("#resetAllButton");
    let submitButton = $("#submitButton");
    const ingredientFilterForm = $("#ingredientFilterForm");
    const removeIngredientsUrl = $("#removeIngredientsUrl").attr("href");
    const ingredientUrl = $("#ingredientUrl").attr("href");
    const acSkusUrl = $("#acSkusUrl").attr("href");
    const pageNumInputId = $("#pageNumInputId").val();
    const skusInputId = $("#skusInputId").val();
    const exportButton = $("#exportButton");


    function refreshPage() {
        window.location.href = ingredientUrl;
    }

    ingredientCheckboxes.change(function() {
        removeButton.attr("disabled",
            !ingredientCheckboxes.some(function (elem) {
                return elem.checked
            }));
    });

    selectAllCheckbox.on("change", function(ev) {
        ingredientCheckboxes.attr("checked",
            $(this).attr("checked"));
    });

    resetAllButton.click(function() {
        refreshPage();
        return false;
    });

    submitButton.click(function() {
        ingredientFilterForm.submit();
    });

    removeButton.on("click", function(ev) {
        let toRemove = [];
        ingredientCheckboxes.forEach(function(cb) {
            if (cb.checked) {
                toRemove.push(cb.id);
            }
        });
        ingredientCheckboxes.each(function(_, cb) {
            if (cb.attr("checked")) {
                toRemove.push(cb.attr("id"));
            }
        });
        if (confirm(
            `Are you sure you want to remove ${toRemove.length} Ingredient(s)?\n` +
            "This cannot be undone."
        )) {
            $.ajax(removeIngredientsUrl, {
                type: "POST",
                data: {to_remove: JSON.stringify(toRemove)},
                dataType: "json",
            }).done(function(data, textStatus) {
                if (textStatus !== "success") {
                    alert(
                        `[status=${textStatus}] Error removing` +
                        `${toRemove.length} Ingredient(s):` +
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

    $("#pageList").find("a").on("click", function() {
        let page = $(this).attr("page");
        $(`#${pageNumInputId}`).val(page);
        $("#ingredientFilterForm").submit();
    });

    exportButton.on("click", function() {
        const original = ingredientFilterForm.attr("action");
        ingredientFilterForm.attr("action", original + "?export=1")
            .submit()
            .attr("action", original);

        return false;
    });

    registerAutocomplete($(`#${skusInputId}`), acSkusUrl);
});