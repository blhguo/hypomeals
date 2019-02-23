$(function() {
    const nameInputId = $("#nameInputId").val();

    let form = $("#editProduct_LineForm");
    $("#nextButton").click(function() {
        form.submit();
    });

    let nameSelect = $(`#${nameInputId}`);


    function nameChanged() {
        let selected = nameSelect
            .find("option:selected")
            .prop("value")
            .toLowerCase();
    }

    nameSelect.on("change", nameChanged).trigger("change");
});