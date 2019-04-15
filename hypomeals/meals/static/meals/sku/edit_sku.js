$(function () {
    const addFormulaUrl = $("#addFormulaUrl").attr("href");
    let addFormulaButton = $("#addFormulaButton");
    let editFormulaButton = $("#editFormulaButton");
    let formulaModal = $("#formulaModal");
    let formulaModalBody = $("#formulaBody");
    let loadingSpinner = $("#loadingSpinner");
    let formulaModalSaveButton = $("#formulaSaveButton");

    let customPLDiv = $("#id_custom_product_line").parents("div.form-group");
    let productLineSelect = $("#id_product_line");
    customPLDiv.find("label").remove();
    customPLDiv.prop("style", "display: none;");

    function showCustomProductLine() {
        let selected = productLineSelect
            .find("option:selected")
            .prop("value")
            .toLowerCase();
        if (selected === "custom") {
            customPLDiv.prop("style", "");
        } else {
            customPLDiv.prop("style", "display: none;");
        }
    }

    let randomUpcButton = $(`<button type='button' 
class='btn btn-outline-secondary'><i class="fas fa-random"></i></button>`);
    for (let input of [$("#id_case_upc"), $("#id_unit_upc")]) {
        let button = randomUpcButton.clone();
        let group = makeInputGroup(input, null, button, true);
        button.click(function() {
            let upc = generateRandomUpc();
            group.find("input").val(upc);
        })
    }

    showCustomProductLine();  // Initializes page if form is already filled
    productLineSelect.change(function() {
        showCustomProductLine();
    });

    /******************** Add/Edit Formula *******************/
    let formulaSelect = $("#id_formula");
    let formulaDiv = formulaSelect.parent("div");
    formulaSelect.addClass("custom-select").removeClass("form-control");
    let formulaInputGroup = $("#formulaInputGroup");
    formulaSelect.prependTo(formulaInputGroup);
    formulaInputGroup.appendTo(formulaDiv);

    function formulaModalChanged(_, newContent) {
        let container = formulaModalBody.find("div.container");
        if (container.length > 0) {
            container.remove();
        }
        newContent.appendTo(formulaModalBody);
        formulaModalBody.find("#formSubmitBtnGroup").toggle("false");
        formulaModalSaveButton.attr("disabled", false);
        let buttons = $("#oldButton");
        buttons.remove()
    }
    formulaModalBody.off("modal:change");
    formulaModalBody.on("modal:change", formulaModalChanged);

    function formulaAjaxDone(data, textStatus) {
        if (!showNetworkError(data, textStatus)) {
            return;
        }
        loadingSpinner.toggle(false);
        formulaModalBody.trigger("modal:change", [$(data.resp)]);
    }

    addFormulaButton.off("click");

    addFormulaButton.click(function () {
        $.getJSON(addFormulaUrl, {})
            .done(formulaAjaxDone)
            .fail(function (_, __, errorThrown) {
                alert(`Error loading content: ${errorThrown}`);
                formulaModal.modal("hide");
            })
    });

    editFormulaButton.off("click");

    editFormulaButton.click(function (e) {
        e.preventDefault();
        let formulaName = $("#id_formula option:selected").val();
        if (!formulaName) {
            makeModalAlert("Error",
                "You must select a formula before editing it.",
                null,
                () => formulaModal.modal("hide"));
            return;
        }
        let editFormulaUrl = $(this)
            .attr("data-href")
            .replace("0", formulaName);
        $.getJSON(editFormulaUrl, {})
            .done(formulaAjaxDone)
            .fail(function (_, __, errorThrown) {
                alert(`Error loading content: ${errorThrown}`);
                // formulaModal.modal("hide");
            })
    });
});