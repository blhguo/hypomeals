$(function() {
    const emptyFormDiv = $("#emptyFormDiv");
    const ingredientInputTemplate = emptyFormDiv
        .find("input[name=form-__prefix__-ingredient]")[0];
    const quantityInputTemplate = emptyFormDiv
        .find("input[name=form-__prefix__-quantity]")[0];
    const deleteTemplate = emptyFormDiv.find("input[id*=DELETE]")[0];
    const addRowButton = $("#addRowButton");
    const emptyAlert = $("#emptyAlert");
    let totalFormCount = $("input[name=form-TOTAL_FORMS]");
    // let hasChangePerm = $("input#hasChangePerm").attr("checked");
    //
    // if (!hasChangePerm) {
    //     $("input").attr("disabled", true);
    // }

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
            .append($("<td>")
                .append(getDeleteInput(currentRow))
                .append(getDeleteButton(currentRow)));
        tableBody.append(newRow);
        tableBody.trigger("table:changed");
    }
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
                focus: function() {
                    return false;
                }
            })
            .on("keydown", function(ev) {
                if (ev.keyCode === $.ui.keyCode.TAB
                    && $(this).autocomplete("instance").menu.active) {
                    ev.preventDefault();
                }
            });
        $(".deleteButton").on("click", deleteButtonClicked);

        tableBody.find("tr").each(function(i, row) {
            const deleted = $(row).find("input[name*=DELETE]").attr("checked");
            $(row).toggle(!deleted);
        })
    }

    tableBody.on("table:changed", handleTableChanged).trigger("table:changed");

    /************* Create Ingredient Modal *************/

    const addIngredientUrl = $("#addIngredientUrl").attr("href");
    let createIngrButton = $("#createIngrButton");
    let loadingSpinner = $("#loadingSpinner");
    let modalDiv = $("#modalDiv");
    let modalBody = $("#modalBody");
    let modalSaveButton = $("#modalSaveButton");
    let modalForm = undefined;

    function modalSaveButtonClicked() {
        if (modalForm === undefined) {
            return;
        }
        modalSaveButton.attr("disabled", true);
        modalForm.ajaxSubmit({
            success: function(data, textStatus) {
                if (!showNetworkError(data, textStatus)) {
                    return;
                }
                if ("success" in data && data.success === true) {
                    if ("alert" in data) {
                        alert(data.alert);
                    }
                    modalDiv.modal("hide");
                }
                modalBody.trigger("modal:change", [$(data.resp)]);
            },
        })
    }

    modalBody.on("modal:change", modalChanged);
    function modalChanged(_, newContent) {
        let container = modalBody.find("div.container");
        if (container.length > 0) {
            container.remove();
        }
        newContent.appendTo(modalBody);
        modalForm = newContent.find("form");
        modalBody.find("#formSubmitBtnGroup").toggle("false");
        modalSaveButton.attr("disabled", false);
    }

    function ajaxDone(data, textStatus) {
        if (!showNetworkError(data, textStatus)) {
            return;
        }
        loadingSpinner.toggle(false);
        modalBody.trigger("modal:change", [$(data.resp)]);
    }

    createIngrButton.click(function() {
        $.getJSON(addIngredientUrl, {})
            .done(ajaxDone)
            .fail(function(_, __, errorThrown) {
                alert(`Error loading content: ${errorThrown}`);
                modalDiv.modal("hide");
            })
    });

    modalSaveButton.click(modalSaveButtonClicked);
});
