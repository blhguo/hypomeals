let filteringInput = null;
let filterSkusUrl = null;
const SKU_NUMBER_REGEX = /^.*\(#(\d+)\)$/gm;

$(function () {
    let formset = $("form");
    let emptyAlert = $("#emptyAlert");
    let deadlineInputId = $("#deadlineInputId").val();
    let deadlineInput = $(`#${deadlineInputId}`);
    let isScheduled = $("#isScheduledCheckbox").prop("checked");

    $("#id_name").trigger("focus");

    filterSkusUrl = $("#filterSkusUrl").attr("href");


    $("#datepicker1").datetimepicker({format: "YYYY-MM-DD"});

    $(".filterButtons").click(renderProductLineModal);
    registerFilterTooltip();

    $(".salesButtons").click(showSalesProjection);
    registerSalesProjectionTooltip();

    registerFormset(
        formset,
        $("#addRowButton"),
        function(row) {
            registerAutocomplete(row.find("input.meals-autocomplete"));
            row.find(".filterButtons").click(renderProductLineModal);
            toggleEmptyAlert();
            registerFilterTooltip();
            registerSalesProjectionTooltip();
        },
        toggleEmptyAlert,
    );

    function toggleEmptyAlert() {
        emptyAlert.toggle(formset.find("tbody tr:visible").length === 0);
    }

    deadlineInput.on("focus", function() {
        let calendarPopover = $("#calendarIcon");
        calendarPopover.popover({
            container: "body",
            placement: "top",
            offset: 100,
            title: "Show Calendar",
            content: "Click here to show the calendar widget."
        }).popover("show");
        setTimeout(function() {
            calendarPopover.popover("hide");
        }, 2000);
    });
});

function renderProductLineModal() {
    // "this" is the button being clicked.
    filteringInput = $(this).parents("td").find("input");
    let modal = makeModalAlert("Filter by Product Line", $("#productLineFilter"));

    modal.find("#productLineSelect").change(function() {
        $.getJSON(filterSkusUrl, {product_line: $(this).val()}, populateSkus);
    });

    let skuListGroup = modal.find("#skuListGroup");

    function populateSkus(data, textStatus) {
        if (!showNetworkError(data, textStatus)) {
            return;
        }
        let skus = data.resp;
        let listGroup = $(`<ul class="list-group"></ul>`);
        for (let i = 0; i < skus.length; i++) {
            $(`<li class="list-group-item list-group-item-action">`)
                .text(skus[i])
                .click(function() {
                    filteringInput.val(skus[i]);
                    modal.modal("hide");
                })
                .appendTo(listGroup);
        }
        skuListGroup.children().remove();
        skuListGroup.append(listGroup);
    }
}

function changeSalesProjectionModal() {
    let salesProjectionUrl = $("#salesProjectionUrl").attr("href");

    let skuNumber = $("#sku_number").attr("href");
    let startDate = $("#id_start").val();
    let endDate = $("#id_end").val();

    getJson(salesProjectionUrl, {
        sku: skuNumber, start_date: startDate, end_date: endDate
    }).done(function(data) {
        let modal = makeModalAlert("Sales Projection", $(data),
            changeSalesProjectionModal);
    });
}

function querySalesProjection(skuNumber, start, end, quantityInput) {
    let salesProjectionUrl = $("#salesProjectionUrl").attr("href");
    getJson(salesProjectionUrl, {
        sku: skuNumber,
        start: start,
        end: end,
    }).done(ajaxDone);
    function ajaxDone(data) {
        let modal = makeModalAlert("Sales Projection", $(data));
        modal.find("[data-toggle=tooltip]").tooltip();
        modal.find(".modal-dialog").addClass("modal-lg");
        modal.find(".copyButtons").click(function() {
            quantityInput.val($(this).attr("data-quantity"));
            modal.modal("hide");
        });
        modal.find("#submitButton").click(function() {
            let start = modal.find("#id_start").val();
            let end = modal.find("#id_end").val();
            querySalesProjection(skuNumber, start, end, quantityInput);
            modal.modal("hide");
        });
    }
}

function showSalesProjection() {
    let quantityInput = $(this).parents("td").find("input");
    let skuInputValue = $($(this).parents("tr").find("td")[0])
        .find("input").val();
    if (!skuInputValue.match(SKU_NUMBER_REGEX)) {
        makeModalAlert("Error",
            "Please select a valid SKU before using this tool.");
        return;
    }
    let skuNumber = SKU_NUMBER_REGEX.exec(skuInputValue)[1];
    querySalesProjection(skuNumber, null, null, quantityInput);
}

function registerFilterTooltip() {
    $(".filterButtons").tooltip({
        placement: "right",
        title: "Click here to filter by product lines"
    });
}

function registerSalesProjectionTooltip() {
    $(".salesButtons").tooltip({
        placement: "right",
        title: "Click here to view sales projections"
    })
}