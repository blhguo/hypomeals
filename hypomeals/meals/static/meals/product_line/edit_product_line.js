$(function() {
    const nameInputId = $("#nameInputId").val();

    let form = $("#editProductLineForm");
    $("#nextButton").click(function() {
        form.submit();
    });

    $(`#${nameInputId}`).focus();
});