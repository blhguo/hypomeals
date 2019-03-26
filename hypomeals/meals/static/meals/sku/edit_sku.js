$(function () {
    const addFormulaUrl = $("#addFormulaUrl").attr("href");
    const editFormulaUrl = $("#editFormulaUrl").attr("href");
    let addFormulaButton = $("#addFormulaButton");
    let editFormulaButton = $("#editFormulaButton");
    let formulaModalDiv = $("#formulaDiv");
    let formulaModalBody = $("#formulaBody");
    let loadingSpinner = $("#loadingSpinner");
    let formulaModalSaveButton = $("#formulaSaveButton");


    function formulaModalChanged(_, newContent) {
        let container = formulaModalBody.find("div.container");
        if (container.length > 0) {
            container.remove();
        }
        newContent.appendTo(formulaModalBody);
        formulaModalForm = newContent.find("form");
        formulaModalBody.find("#formSubmitBtnGroup").toggle("false");
        formulaModalSaveButton.attr("disabled", false);
        let buttons = $("#oldButton")
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
                formulaModalDiv.modal("hide");
            })
    });

    editFormulaButton.off("click");

    editFormulaButton.click(function () {
        let formulaName = $("#id_formula option:selected").val()
        let editFormulaUrl = $("#editFormulaUrl").attr("href").replace("0", formulaName)
        $.getJSON(editFormulaUrl, {})
            .done(formulaAjaxDone)
            .fail(function (_, __, errorThrown) {
                alert(`Error loading content: ${errorThrown}`);
                formulaModalDiv.modal("hide");
            })
    });
});