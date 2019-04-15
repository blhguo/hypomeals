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
    const reportButton = $("#reportButton");

    $("[data-toggle='tooltip']").tooltip();

    function refreshPage() {
        window.location.href = ingredientUrl;
    }

    ingredientCheckboxes.change(function() {
        removeButton.attr("disabled",
            $(".ingredient-checkbox:checked").length === 0);
    });

    selectAllCheckbox.on("change", function(ev) {
        ingredientCheckboxes.prop("checked",
            $(this).prop("checked"));
        ingredientCheckboxes.trigger("change");
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
        ingredientCheckboxes.each(function(_, cb) {
            if (cb.checked) {
                toRemove.push(cb.id);
            }
        });
        let csrf_token = $("input[name=csrfmiddlewaretoken]").val();
        if (confirm(
            `Are you sure you want to remove ${toRemove.length} Ingredient(s)?\n` +
            "This cannot be undone."
        )) {
            $.ajax(removeIngredientsUrl, {
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
        $("#ingredientFilterForm").submit();
    });

    exportButton.on("click", function() {
        const original = ingredientFilterForm.attr("action");
        ingredientFilterForm.attr("action", original + "?export=1")
            .submit()
            .attr("action", original);

        return false;
    });

    reportButton.click(function() {
        const original = ingredientFilterForm.attr("action");
        ingredientFilterForm.attr("action", original + "?report=1")
            .submit()
            .attr("action", original);

        return false;
    });

    registerAutocomplete($(`#${skusInputId}`), acSkusUrl, true);
});