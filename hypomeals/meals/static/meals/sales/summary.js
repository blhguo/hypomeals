$(function () {
    $("[data-toggle='tooltip']").tooltip();
    let submitButton = $("#submitButton");
    let productLineFilterForm = $("#productLineFilterForm");
    const salesSummaryUrl = $("#salesSummaryUrl").attr("href");
    let exportButton = $("#exportButton");

    function refreshPage() {
        window.location.href = salesSummaryUrl;
    }

    submitButton.click(function () {
        productLineFilterForm.submit();
    });

    exportButton.click(function () {
        const original = productLineFilterForm.attr("action");
        let query = "?export=1";
        productLineFilterForm.attr("action", original + query)
            .submit()
            // Reset the form action so the user can submit another filter
            // request after downloading the exported file.
            .attr("action", original);
        return false;
    });


    $("#resetAllButton").click(refreshPage);

    $("#pageList").find("a").on("click", function () {
        let page = $(this).attr("page");
        $(`#${pageNumInputId}`).val(page);
        productLineFilterForm.submit();
    });

});