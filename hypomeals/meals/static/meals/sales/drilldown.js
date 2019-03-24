$(function () {
    const pageNumInputId = $("#pageNumInputId").val();
    const salesUrl = $("#salesUrl").attr("href");
    let submitButton = $("#submitButton");
    let resetButton = $("#resetAllButton");
    let exportButton = $("#exportButton");
    let drilldownFilterForm = $("#drilldownFilterForm");


    function refreshPage() {
        window.location.href = salesUrl;
    }

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

    resetButton.on("click", refreshPage);

    $("#id_start").datepicker({
        changeMonth: true,
        changeYear: true,
        dateFormat: "yy-mm-dd"
    });
    $("#id_end").datepicker({
        changeMonth: true,
        changeYear: true,
        dateFormat: "yy-mm-dd"
    });

    /************** Pagination ****************/
    $("#pageList").find("a").on("click", function () {
        let page = $(this).attr("data-page");
        $(`#${pageNumInputId}`).val(page);
        drilldownFilterForm.submit();
    });

    let ctx = $("#revenueLineChart");
    let chart_data_x = $("#chart_data_x").val();
    let chart_data_y = $("#chart_data_y").val();
    let lbls = $.parseJSON(chart_data_x);
    let data = $.parseJSON(chart_data_y);
    let revenueLineChart = new Chart(ctx, {
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
            }
        }});

});