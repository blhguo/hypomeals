$(function() {
    $(".selectUserCheckboxes").change(function() {
        $("#actionsToggleButton").prop("disabled",
            $(".selectUserCheckboxes:checked").length === 0);
    });

    $("#selectAllCheckbox").change(function() {
        $(".selectUserCheckboxes")
            .prop("checked", $(this).prop("checked"))
            .trigger("change");
    });

    $("#removeUserButton").click(function() {
        let userIds = $(".selectUserCheckboxes:checked")
            .toArray()
            .map((i) => $(i).attr("data-user-id"));
        if (userIds.length === 0) {
            makeModalAlert("Error",
                "You need to select at least one user.");
            return;
        }
        $.getJSON(templateData.get("removeUsersUrl"), {
            u: JSON.stringify(userIds),
        }).done(function(data, textStatus) {
            if (!showNetworkError(data, textStatus)) {
                return;
            }
            // if ("error" in data) {
            //     makeModalAlert("Error", data.error);
            //     return;
            // }
            makeModalAlert("Success", data.resp);
        })
    })
});