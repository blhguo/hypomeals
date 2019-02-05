$(function() {
    const customVendorInputId = $("#customVendorInputId").val();
    const vendorInputId = $("#vendorInputId").val();

    let form = $("#editIngredientForm");
    $("#nextButton").click(function() {
        form.submit();
    });

    let customVendorDiv = $(`#${customVendorInputId}`).parent("div");
    let vendorSelect = $(`#${vendorInputId}`);

    customVendorDiv.find("label").remove();
    customVendorDiv.toggle(false);

    function vendorChanged() {
        let selected = vendorSelect
            .find("option:selected")
            .prop("value")
            .toLowerCase();
        customVendorDiv.toggle(selected === "custom");
    }

    vendorSelect.on("change", vendorChanged).trigger("change");
});