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
    let exportButton = $("#exportButton");
    let drilldownFilterForm = $("#drilldownFilterForm");
    // let chart_data_x = $("#chart_data_x");
    // let chart_data_y = $("#chart_data_y");


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

    exportButton.on("click", function() {
        const original = drilldownFilterForm.attr("action");
        drilldownFilterForm.attr("action", original + "?export=1")
            .submit()
            .attr("action", original);

        return false;
    });

    /************** Pagination ****************/
    $("#pageList").find("a").on("click", function () {
        let page = $(this).attr("page");
        $(`#${pageNumInputId}`).val(page);
        drilldownFilterForm.submit();
    });

    var ctx = document.getElementById("revenueLineChart");
    var chart_data_x = document.getElementById("chart_data_x").value;
    var chart_data_y = document.getElementById("chart_data_y").value;
    var lbls = jQuery.parseJSON(chart_data_x);
    var data = jQuery.parseJSON(chart_data_y);
    var revenueLineChart = new Chart(ctx,
        {
            type: "line",
            data: {
                    labels: lbls,
                    datasets: [{
                        data: data,
                        borderColor: "#c45850"
                    }]},
            options: {
                    legend: {
                        display: false
                    },
                    scales: {
                        yAxes: [{
                            ticks: {
                                // Include a dollar sign in the ticks
                                callback: function(value, index, values) {
                                    return '$' + value;
                                }
                            }
                        }]
                    }}});
    
  registerAutocomplete($(`#${customerInputId}`), acCustomerUrl, false);

});