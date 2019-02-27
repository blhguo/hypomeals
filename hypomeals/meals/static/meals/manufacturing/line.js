$(function() {
    let pageUrl = window.location.href;
    function refreshPage() {
        window.location.href = pageUrl;
    }
    $("[data-toggle='tooltip']").tooltip();

    Mousetrap.bind(["command+a", "ctrl+a"], function(ev) {
        ev.preventDefault();
        let selectAll = $("#selectAllCheckbox");
        selectAll.prop("checked", !selectAll.prop("checked"))
            .trigger("change");
    });

    Mousetrap.bind("n", function(ev) {
        ev.preventDefault();
        $("#addButton").trigger("click");
    });

    Mousetrap.bind(["del", "backspace"], function(ev) {
        ev.preventDefault();
        $("#removeButton").trigger("click");
    });

    $("#selectAllCheckbox").change(function() {
        $(".selectLineCheckboxes").prop("checked",
            $(this).prop("checked")).trigger("change");
    });

    $(".selectLineCheckboxes").change(function() {
        $("#removeButton").prop("disabled",
            $(".selectLineCheckboxes:checked").length === 0);
    });

    $("#removeButton").click(function(ev) {
        ev.preventDefault();
        let toRemove = $(".selectLineCheckboxes:checked").toArray()
            .map((l) => $(l).attr("data-line-id"));
        if (toRemove.length === 0) {
            makeModalAlert("Error",
                "You must select at least one manufacturing line.");
            return;
        }
        getJson($(this).attr("data-href"), {
            toRemove: JSON.stringify(toRemove),
        }).done(function(resp) {
            makeModalAlert("Success", resp, null, refreshPage);
        });
    });

    function onModalChanged(ev, modal) {
        modal.find("#formSubmitBtnGroup").toggle(false);
        modal.find(".meals-autocomplete")
            .each((_, e) => registerAutocomplete($(e)));
    }
    $("#addButton").click(function(ev) {
        ev.preventDefault();
        getJson($(this).attr("data-href"), {})
            .done(function(resp) {
                let modal = makeModalAlert("Add Manufacturing Line",
                    $(resp),onFormSubmit);
                modal.find(".modal-dialog").addClass("modal-lg");
                $(modal.find("input[type=text]")[0]).focus();
                modal.on("modal:changed", onModalChanged)
                    .trigger("modal:changed", [modal]);
            });
    });

    $(".editLineButtons").click(function(ev) {
        ev.preventDefault();
        getJson($(this).attr("href"), {})
            .done(function(resp) {
                let modal = makeModalAlert("Add Manufacturing Line",
                    $(resp),onFormSubmit);
                modal.find(".modal-dialog").addClass("modal-lg");
                modal.on("modal:changed", onModalChanged)
                    .trigger("modal:changed", [modal]);
            });
    });

    function onFormSubmit(modal) {
        modal.find("form").ajaxSubmit({
            success: function(data, textStatus) {
                if (!showNetworkError(data, textStatus)) {
                    return true;
                }
                if ("success" in data && data.success === true) {
                    alert(data.resp);
                    refreshPage();
                    return true;
                }
                modal.find("#formContainer").replaceWith($(data.resp));
                modal.trigger("modal:changed", [modal]);
            }
        });
        return false;
    }

    /****************** Reporting ***********************/
    let html = `\
<div class="row mb-3">
<div class="col-sm">
<div class="alert alert-success">
    <h4>Generate Schedule Report</h4>
    <p>
    A schedule report lists the SKUs, formulas and ingredients for manufacturing
    activities on this manufacturing line.
    </p>
    <p class="mb-0">
    Simply enter a start and end date below to get started.
    </p>
</div>
</div>
</div>

<div class="form-row mt-3">
<div class="input-group">
    <div class="input-group-prepend">
        <label class="input-group-text" for="startDate">
            From
        </label>
    </div>
    <input type="date" id="startDate" class="form-control">
</div>
<small>If empty, will be the start time of the earliest scheduled item on this line.</small>
</div>

<div class="form-row mt-3">
<div class="input-group">
    <div class="input-group-prepend">
        <label class="input-group-text" for="startDate">
            To
        </label>
    </div>
    <input type="date" id="endDate" class="form-control">
</div>
<small>If empty, will be the end time of last scheduled item on this line.</small>
</div>
</div>
</div>`;

    $(".scheduleReportButtons").click(function(ev) {
        ev.preventDefault();
        let line = $(this).attr("data-line-shortname");
        let reportUrl = $(this).attr("href");
        let modalContent = $(html);
        let mlSelect = modalContent.find("#mlSelect");

        let modal = makeModalAlert(`Generate Schedule Report for '${line}'`,
            modalContent, generateReport);
        modal.find(".modal-dialog").addClass("modal-lg");
        modal.find("input[type=date]").change(function() {
            let value = $(this).val();
            if (value.length === 0) {
                $(this).removeClass("is-invalid").removeClass("is-valid");
                return;
            }
            if (moment(value).isValid()) {
                $(this).removeClass("is-invalid").addClass("is-valid");
            } else {
                $(this).removeClass("is-valid").addClass("is-invalid");
            }
        });

        function generateReport() {
            let url = new URL(window.location.href);
            url.pathname = reportUrl;
            let start = moment(modal.find("input#startDate").val());
            let end = moment(modal.find("input#endDate").val());
            options = {
                l: line,
                s: start.isValid() ? start.format("YYYY-MM-DD") : "",
                e: end.isValid() ? end.format("YYYY-MM-DD") : ""
            };
            url.search = $.param(options);
            window.location.href = url;
        }
    });
});