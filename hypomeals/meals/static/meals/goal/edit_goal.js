let filteringInput = null;
let filterSkusUrl = null;

$(function () {
    let formset = $("form");
    let emptyAlert = $("#emptyAlert");
    let deadlineInputId = $("#deadlineInputId").val();
    let deadlineInput = $(`#${deadlineInputId}`);

    $("#id_name").trigger("focus");

    filterSkusUrl = $("#filterSkusUrl").attr("href");

    $("#datepicker1").datetimepicker({format: "YYYY-MM-DD"});

<<<<<<< HEAD
    $(".filterButtons").click(renderModal);
    $(".projectionButtons").click(renderModal)
=======
    $(".filterButtons").click(renderProductLineModal);
>>>>>>> 73cf12d55d809bb86572aff57d8d2436c4ae911f
    registerFilterTooltip();

    $(".salesButtons").click(renderSalesProjectionModal);
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
        console.log(`selected: ${$(this).val()}`);
        $.getJSON(filterSkusUrl, {product_line: $(this).val()}, populateSkus);
    });

    let skuListGroup = modal.find("#skuListGroup");

    function populateSkus(data, textStatus) {
        if (!showNetworkError(data, textStatus)) {
            return;
        }
        let skus = data.resp;
        console.log("SKUs: ", skus);
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

function renderSalesProjectionModal() {
    // TODO: Implement this.
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