$(function () {
    let formset = $("form");
    let emptyAlert = $("#emptyAlert");

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

    $("#datepicker1").datetimepicker({format: "YYYY-MM-DD"});
});