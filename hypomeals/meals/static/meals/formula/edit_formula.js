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
        // $(`delete-${event.data}`).parents("tr").toggle(false);
        $(this).parents("tr").toggle(false);
        $(this).parent("td")
            .find("input")
            .attr("checked", true);
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
        let numRows = tableBody.find("tr").length;
        totalFormCount.val(numRows);
        if (numRows === 0) {
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
});