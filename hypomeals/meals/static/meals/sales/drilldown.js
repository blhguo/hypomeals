$(function () {
    let drilldownCheckboxes = $(".drilldown-checkbox");
    const acCustomerUrl = $("#acCustomerUrl").attr("href");
    const acSkusUrl = $("#acSkusUrl").attr("href");
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


    /************** Pagination ****************/
    $("#pageList").find("a").on("click", function () {
        let page = $(this).attr("page");
        $(`#${pageNumInputId}`).val(page);
        drilldownFilterForm.submit();
    });
        registerAutocomplete(customerInputId, acCustomerUrl, false);

});