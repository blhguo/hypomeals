$(function () {
    let drilldownCheckboxes = $(".drilldown-checkbox");
    const acCustomerUrl = $("#acCustomerUrl").attr("href");
    const pageNumInputId = $("#pageNumInputId").val();
    const skuInputId = $("#skuInputId").val();
    const startInputId = $("#startInputId").val()
    const endInputId = $("#endInputId").val();
    const customerInputId = $("#customerInputId").val();
    const salesUrl = $("#salesUrl").attr("href");
    let selectAllCheckbox = $("#selectAll");
    let submitButton = $("#submitButton");
    let drilldownFilterForm = $("#drilldownFilterForm");

    $("[data-toggle='tooltip']").tooltip();

    function refreshPage() {
        window.location.href = salesUrl;
    }

    selectAllCheckbox.change(function () {
        drilldownCheckboxes.prop("checked", $(this).prop("checked"));
        drilldownCheckboxes.trigger("change");
    });


    submitButton.click(function () {
        drilldownFilterForm.submit();
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
            .done(function (data, textStatus) {
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
    $("#pageList").find("a").on("click", function () {
        let page = $(this).attr("page");
        $(`#${pageNumInputId}`).val(page);
        drilldownFilterForm.submit();
    });

});