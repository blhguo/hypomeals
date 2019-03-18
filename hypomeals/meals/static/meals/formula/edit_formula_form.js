$(function () {
    const emptyFormDiv = $("#emptyFormDiv");
    const ingredientInputTemplate = emptyFormDiv
        .find("input[name=form-__prefix__-ingredient]")[0];
    const quantityInputTemplate = emptyFormDiv
        .find("input[name=form-__prefix__-quantity]")[0];
    const unitInputTemplate = emptyFormDiv
        .find("select[name=form-__prefix__-unit]")[0];
    const deleteTemplate = emptyFormDiv.find("input[id*=DELETE]")[0];
    const addRowButton = $("#addRowButton");
    const emptyAlert = $("#emptyAlert");
    let totalFormCount = $("input[name=form-TOTAL_FORMS]");

    let tableBody = $("#formsetTable");
    let currentRow = tableBody.find("tr").length - 1;

    function replacePrefix(node, index) {
        for (let attr of ["id", "name"]) {
            node[attr] = node[attr].replace("__prefix__", String(index));
        }
    }

    function getIngredientInput(index) {
        let newInput = ingredientInputTemplate.cloneNode(true);
        replacePrefix(newInput, index);
        return newInput;
    }

    function getQuantityInput(index) {
        let newInput = quantityInputTemplate.cloneNode(true);
        replacePrefix(newInput, index);
        return newInput;
    }

    function getUnitInput(index) {
        let newInput = unitInputTemplate.cloneNode(true);
        replacePrefix(newInput, index);
        return newInput;
    }

    function getDeleteInput(index) {
        let newInput = deleteTemplate.cloneNode(true);
        replacePrefix(newInput, index);
        return newInput;
    }

    function deleteButtonClicked() {
        $(this).parents("tr").toggle(false);
        // Check the "DELETE" box
        $(this).parent("td")
            .find("input")
            .attr("checked", true);
        tableBody.trigger("table:changed");
    }

    function getDeleteButton(index) {
        return $("<a>")
            .attr("href", "#")
            .attr("class", "deleteButton")
            .text("Delete")
            .on("click", deleteButtonClicked);
    }

    function addRow() {
        currentRow++;
        let newRow = $("<tr>")
            .append($("<td>").append(getIngredientInput(currentRow)))
            .append($("<td>").append(getQuantityInput(currentRow)))
            .append($("<td>").append(getUnitInput(currentRow)))
            .append($("<td>")
                .append(getDeleteInput(currentRow))
                .append(getDeleteButton(currentRow)));
        tableBody.append(newRow);
        tableBody.trigger("table:changed");
    }

    addRowButton.off("click");
    addRowButton.on("click", addRow);

    function handleTableChanged() {
        // Update the management form with correct information
        let visibleRows = tableBody.find("tr:visible").length;
        let totalRows = tableBody.find("tr").length;
        totalFormCount.val(totalRows);
        if (visibleRows === 0) {
            emptyAlert.toggle(true);
        } else {
            emptyAlert.toggle(false);
        }

        tableBody.find("input[name*=DELETE]").toggle(false);

        tableBody.find("input[name*=ingredient]")
            .autocomplete({
                source: function (request, response) {
                    $.getJSON("/ac-ingredients", {
                        term: request.term,
                    }, response);
                },
                focus: function () {
                    return false;
                }
            })
            .on("keydown", function (ev) {
                if (ev.keyCode === $.ui.keyCode.TAB
                    && $(this).autocomplete("instance").menu.active) {
                    ev.preventDefault();
                }
            });
        $(".deleteButton").on("click", deleteButtonClicked);

        tableBody.find("tr").each(function (i, row) {
            const deleted = $(row).find("input[name*=DELETE]").attr("checked");
            $(row).toggle(!deleted);
        })
    }

    tableBody.off("table:changed");
    tableBody.on("table:changed", handleTableChanged).trigger("table:changed");

    const addFormulaUrl = $("#addFormulaUrl").attr("href");
    let formulaModalDiv = $("#formulaDiv");
    let formulaModalBody = $("#formulaBody");
    let formulaModalSaveButton = $("#formulaSaveButton");
    let formulaModalForm = undefined;
    formulaModalBody.off("modal:change");
    formulaModalBody.on("modal:change", formulaModalChanged);

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

    function formulaAjaxDone(data, textStatus) {
        if (!showNetworkError(data, textStatus)) {
            return;
        }
        loadingSpinner.toggle(false);
        formulaModalBody.trigger("modal:change", [$(data.resp)]);
    }

    function formulaModalSaveButtonClicked() {
        formulaModalForm = $("#formulaForm");
        // if (formulaModalForm === undefined) {
        //     return;
        // }
        formulaModalSaveButton.attr("disabled", true);
        formulaModalForm.ajaxSubmit({
            success: function (data, textStatus) {
                if (!showNetworkError(data, textStatus)) {
                    return;
                }
                if ("success" in data && data.success === true) {
                    if ("alert" in data) {
                        alert(data.alert);
                    }
                    $("#formulaDiv").modal("hide");
                    let name = data.name;
                    let formulaSelector = $("#id_formula");
                    $("<option>").text(name)
                        .attr("value", name)
                        .appendTo($(formulaSelector));
                }
                formulaModalBody.trigger("modal:change", [$(data.resp)]);
            },
        })
    }

    formulaModalSaveButton.off("click");
    formulaModalSaveButton.click(formulaModalSaveButtonClicked);
});