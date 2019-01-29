$(function() {
    const emptyFormDiv = $("#emptyFormDiv");
    const ingredientInputTemplate = emptyFormDiv.find("input[id*=ingredient]")[0];
    const quantityInputTemplate = emptyFormDiv.find("input[id*=quantity]")[0];
    const deleteTemplate = emptyFormDiv.find("input[id*=DELETE]")[0];
    const addRowButton = $("#addRowButton");
    const emptyAlert = $("#emptyAlert");
    let totalFormCount = $("input[name=form-TOTAL_FORMS]");

    let tableBody = $("#formsetTable");
    let currentRow = tableBody.find("tr").length - 1;

    console.log(ingredientInputTemplate);
    console.log(quantityInputTemplate);
    console.log(deleteTemplate);
    console.log(currentRow);

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

    function addRow() {
        currentRow++;
        let newRow = $("<tr>")
            .append($("<td>").append(getDeleteInput(currentRow)))
            .append($("<td>").append(getIngredientInput(currentRow)))
            .append($("<td>").append(getQuantityInput(currentRow)));
        tableBody.append(newRow);
        tableBody.trigger("table:changed");
    }
    addRowButton.on("click", addRow);

    tableBody.on("table:changed", function(event) {
        // Update the management form with correct information
        let numRows = tableBody.find("tr").length;
        totalFormCount.val(numRows);
        if (numRows === 0) {
            emptyAlert.toggle(true);
        } else {
            emptyAlert.toggle(false);
        }

    });
    tableBody.trigger("table:changed");
});