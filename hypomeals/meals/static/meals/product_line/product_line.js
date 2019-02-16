$(function() {
    let removeButton = $("#removeButton");
    let product_lineCheckboxes = $(".product_line-checkbox");
    let selectAllCheckbox = $("#selectAllCheckbox");
    let resetAllButton = $("#resetAllButton");
    let submitButton = $("#submitButton");
    const product_lineFilterForm = $("#product_lineFilterForm");
    const removeProduct_LinesUrl = $("#removeProduct_LinesUrl").attr("href");
    const product_lineUrl = $("#product_lineUrl").attr("href");
    //const acProductLineUrl = $("#acProductLineUrl").attr("href");
    const pageNumInputId = $("#pageNumInputId").val();
    //const nameInputId = $("#nameInputId").val();
    const exportButton = $("#exportButton");
    const reportButton = $("#reportButton");

    $("[data-toggle='tooltip']").tooltip();

    function refreshPage() {
        window.location.href = product_lineUrl;
    }

    product_lineCheckboxes.change(function() {
        removeButton.attr("disabled",
            $(".product_line-checkbox:selected").length > 0);
    });

    selectAllCheckbox.on("change", function(ev) {
        product_lineCheckboxes.prop("checked",
            $(this).prop("checked"));
        product_lineCheckboxes.trigger("change");
    });

    resetAllButton.click(function() {
        refreshPage();
        return false;
    });

    submitButton.click(function() {
        product_lineFilterForm.submit();
    });

    removeButton.on("click", function(ev) {
        let toRemove = [];
        product_lineCheckboxes.each(function(_, cb) {
            if (cb.checked) {
                toRemove.push(cb.id);
            }
        });
        let csrf_token = $("input[name=csrfmiddlewaretoken]").val();
        if (confirm(
            `Are you sure you want to remove ${toRemove.length} Product Lines(s)?\n` +
            "This cannot be undone."
        )) {
            $.ajax(removeProduct_LinesUrl, {
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

    exportButton.on("click", function() {
        const original = product_lineFilterForm.attr("action");
        product_lineFilterForm.attr("action", original + "?export=1")
            .submit()
            .attr("action", original);

        return false;
    });

    reportButton.click(function() {
        const original = product_lineFilterForm.attr("action");
        product_lineFilterForm.attr("action", original + "?report=1")
            .submit()
            .attr("action", original);

        return false;
    });

});