let filteringInput = null;

$(function () {
    let formset = $("form");
    let emptyAlert = $("#emptyAlert");
    let filterSkusUrl = $("#filterSkusUrl").attr("href");

    $("#datepicker1").datetimepicker({format: "YYYY-MM-DD"});

    $(".filterButtons").click(renderModal);

    registerFormset(
        formset,
        $("#addRowButton"),
        function(row) {
            registerAutocomplete(row.find("input.meals-autocomplete"));
            toggleEmptyAlert();
        },
        toggleEmptyAlert,
    );

    function toggleEmptyAlert() {
        emptyAlert.toggle(formset.find("tbody tr:visible").length === 0);
    }
});

function renderModal() {
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