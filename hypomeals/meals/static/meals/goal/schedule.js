const IGNORE_SENDER_ID = 1;
const WORK_HOURS_PER_DAY = 10;  // TODO: Get this from HTML
const WORK_HOURS_START = 8;
const WORK_HOURS_END = 18;
const SECONDS_PER_HOUR = 3600;
const MILLISECONDS_PER_HOUR = SECONDS_PER_HOUR * 1000;

let timeline = null;
let items = new vis.DataSet([]);
let groups = new vis.DataSet([]);
let goalItemsMap = new Map();

$(function() {
    $("[data-toggle='tooltip']").tooltip();
    $("#showHelpButton").click(function() {
        $("#helpDiv").toggle("fast");
    });

    let mfgLines = new Set();  // Set of MLs to display groups
    $(".goalItems[data-schedulable=true]")
        .on("dragstart", function(event) {
        let src = $(this);
        let goalItemId = Number(src.attr("data-goal-item-id"));
        let itemInfo = goalItemsMap.get(goalItemId);
        let item = {
            id: goalItemId,
            content: itemInfo.name,
            type: "range"
        };
        event.originalEvent.dataTransfer.effectAllowed = "move";
        event.originalEvent.dataTransfer.setData("text", JSON.stringify(item));
        highlightGroups(itemInfo.lines, true);
    }).on("click", function() {
        let goalItemId = Number($(this).attr("data-goal-item-id"));
        if (items.get(goalItemId) !== null) {
            timeline.focus(goalItemId);
        }
    });
    $(document).on("dragend", function() {
        highlightGroups("*", false);
    });

    /****************** Sync with Form **********************/
    let form = $("form");
    form.find("div.goalItems").each(function(i, div) {
        div = $(div);
        let id = Number(div.attr("data-goal-item-id"));
        let lines = div.attr("data-lines").split(",");
        let itemInfo = {
            id: id,
            type: "range",
            content: `${div.attr("data-sku-verbose-name")}\
                (${Number(div.attr("data-quantity"))})`,
            skuId: Number(div.attr("data-sku-id")),
            goalId: Number(div.attr("data-goal-id")),
            goalItemId: Number(div.attr("data-goal-item-id")),
            deadline: moment(div.attr("data-goal-deadline")).hours(WORK_HOURS_END),
            lines: lines,
            isOrphaned: JSON.parse(div.attr("data-is-orphaned")),
            rate: Number(div.attr("data-sku-rate")),
            hours: Number(div.attr("data-hours")),
            quantity: Number(div.attr("data-quantity")),
            suppressWarning: true,
        };

        if (itemInfo.isOrphaned) {
            itemInfo.className = "bg-warning text-dark";
            itemInfo.title = "Orphaned item. Consider removing."
        }

        let line = div.find("select option:selected").val();
        if (lines.includes(line)) {
            itemInfo.group = line;
        }
        lines.forEach((l) => mfgLines.add(l));

        let endTime = moment(div.find("input[name*=end_time]").val(),
            "YYYY-MM-DD HH:mm:ss");
        if (endTime.isValid()) {
            itemInfo.end = endTime;
        }

        let startTime = moment(div.find("input[name*=start_time]").val(),
            "YYYY-MM-DD HH:mm:ss");
        if (startTime.isValid()) {
            itemInfo.start = startTime;
            if (!endTime.isValid()) {
                endTime = getCompletionTime(startTime, itemInfo.hours);
                itemInfo.end = endTime;
            }
            items.add(itemInfo);
        }
        goalItemsMap.set(id, itemInfo);
    });

    $("#submitButton").click(function(e) {
        for (let itemId of goalItemsMap.keys()) {
            let formDiv = form.find(`div[data-goal-item-id=${itemId}]`);
            let select = formDiv.find("select");
            let startTime = formDiv.find("input[name*=start_time]");
            let scheduledItem = items.get(itemId);
            if (scheduledItem !== null) {
                select.find(`option[value=${scheduledItem.group}]`).prop("selected", true);
                startTime.val(moment(scheduledItem.start).toISOString());
            } else {
                select.find("option:eq(0)").prop("selected", true);
                startTime.val("");
            }
        }
        form.submit();
    });

    /***************** Timeline *******************/

    console.log(goalItemsMap);
    console.log(mfgLines);

    groups = new vis.DataSet([]);
    mfgLines.forEach((l) => {
        groups.add({
            id: l,
            content: l,
            visible: true,
        })
    });
    groups.add({
        id: "DT3",
        content: "DT3",
        visible: true,
    });

    console.log(groups);

    items.on("update", function(event, properties, senderId) {
        if (senderId === IGNORE_SENDER_ID) return;
        let item = properties.data[0];
        let oldItem = properties.oldData[0];
        let itemInfo = goalItemsMap.get(item.id);
        if (!itemInfo.lines.includes(item.group)) {
            makeModalAlert("Cannot Schedule",
                `Manufacturing Line '${item.group}' cannot produce SKU #${itemInfo.skuId}.
                Operation will be reverted.`);
            items.update(properties.oldData[0]);
            return;
        }
        if ("start" in item) {
            if ((moment(item.end) - moment(item.start)) ===
                (moment(oldItem.end) - moment(oldItem.start))) {
                // If the user dragged the whole range in time
                // we should recompute end time, taking into considertion the
                // current start time.
                try {
                    adjustEnd(item, item.start, true);
                } catch (e) {
                    makeModalAlert("Error",
                        `Production overlaps on Manufacturing Line '${item.group}'.
                        Operation will be reverted.`,
                        null,
                        function () {
                            items.update(oldItem, IGNORE_SENDER_ID);
                        });
                }
            } else {
                // Otherwise the user has forcefully changed duration of the item
                console.log(`User force-updated item #${item.id}`);
                itemInfo.isForced = true;
                item.className = "bg-info text-white";
                items.update(item, IGNORE_SENDER_ID);
            }
        }
    });
    items.on("add", function(event, properties, senderId) {
        let item = items.get(properties.items[0]);
        let itemInfo = goalItemsMap.get(item.id);
        if (!itemInfo.lines.includes(item.group)) {
            makeModalAlert("Cannot Schedule",
                `Manufacturing Line '${item.group}' cannot produce SKU #${itemInfo.skuId}.
                This item has been removed.`);
            items.remove({id: item.id});
            return false;
        }
        toggleGoalItem(item.id, true);
        if ("start" in item) {
            try {
                adjustEnd(item, item.start, !item.suppressWarning);
            } catch (e) {
                makeModalAlert("Error",
                    `Production overlaps on Manufacturing Line '${item.group}'.
                    This item will be removed.`,
                    null,
                    function () {items.remove({id: item.id});});
            }
        }
    });
    items.on("remove", function(event, properties, senderId) {
        toggleGoalItem(properties.items[0], false);
    });

    function highlightGroups(groupIds, highlighted) {
        if (groupIds === "*") {
            groupIds = groups.distinct("id");
        }
        let updates = [];
        let className = highlighted ? "bg-success text-white" : "1";
        for (let group of groupIds) {
            updates.push({id: group, className: className});
        }
        groups.update(updates);
    }

    function checkOverlap(item) {
        let itemsInGroup = items.get({
            filter: (i) => i.group === item.group,
            returnType: "Array",
        });
        if (itemsInGroup.length === 1) return false;
        itemsInGroup.sort(function(a, b) {
            return moment(a.start) - moment(b.start);
        });
        for (let i = 0; i < itemsInGroup.length - 1; i++) {
            if (moment(itemsInGroup[i + 1].start) < moment(itemsInGroup[i].end)) {
                return true;
            }
        }
        return false;
    }

    function adjustEnd(item, start, showWarning) {
        let itemId = item.id;
        start = moment(start);
        let itemInfo = goalItemsMap.get(itemId);
        let updates = {id: itemId};
        if (!itemInfo.isForced) {
            updates["end"] = getCompletionTime(start, itemInfo.hours);
            updates["type"] = "range";
        }
        if (end > itemInfo.deadline) {
            console.log(`Item ${itemId} will exceed deadline`);
            updates["className"] = "bg-danger text-white";
            updates["title"] = `Start: ${start.format("lll")}.
        Warning: item exceeds deadline ${itemInfo.deadline.format("lll")}`;
            if (showWarning) {
                makeModalAlert("Warning",
                    `Scheduling this item to start at \
            ${start.format("lll")} will exceed predetermined \
            deadline of ${itemInfo.deadline.format("lll")} in the goal.
            Consider moving this item earlier.`);
            }
        } else {
            updates["className"] = itemInfo.isForced ? "bg-info text-white" :
                (itemInfo.isOrphaned ? "bg-warning text-dark" : "");
            updates["title"] = `Start: ${start.format("lll")}`;
        }
        items.update(updates, IGNORE_SENDER_ID);
        if (checkOverlap(item)) {
            throw "Overlap detected!";
        }
    }

    function toggleGoalItem(goalItemId, scheduled) {
        $(`a[data-goal-item-id=${goalItemId}]`)
            .toggleClass("text-muted", scheduled);
    }

    function getCompletionTime(startTime, hours) {
        startTime = moment(startTime);
        let endTime = startTime.clone();
        let numDays = Math.floor(hours / WORK_HOURS_PER_DAY);
        let remainingHours = hours % WORK_HOURS_PER_DAY;
        if (remainingHours === 0) {
            numDays--;
            remainingHours = WORK_HOURS_PER_DAY;
        }
        if (startTime.hour() >= WORK_HOURS_START && startTime.hour() <= WORK_HOURS_END) {
            let startOfDay = startTime.clone().startOf("day").hours(WORK_HOURS_START);
            remainingHours -= startTime.diff(startOfDay) / MILLISECONDS_PER_HOUR;
        }
        endTime.add(numDays, "days");
        if (remainingHours > 0) {
            endTime.add(1, "days").hours(WORK_HOURS_START).add(remainingHours, "hours");
        } else {
            endTime.startOf("day").hours(WORK_HOURS_END).add(remainingHours, "hours");
        }

        console.log("start: ", startTime.format(), "end: ", endTime.format());
        return endTime;
    }

    timeline = new vis.Timeline($("#timelineDiv")[0], items, groups, {
        editable: true,
        zoomable: true,
        start: moment().add(-3, "days"),
        end: moment().add(4, "days"),
        tooltipOnItemUpdateTime: true,
        onAdd: function(item, callback) {
            if (!goalItemsMap.has(item.id)) {
                makeModalAlert("Cannot Schedule",
                    "Invalid item detected. Double-clicking to create " +
                    "new item has been disabled.");
                callback(null);
            } else {
                if (items.get(item.id) !== null) {
                    makeModalAlert("Cannot Schedule",
                        "This item has already been scheduled.");
                    callback(null);
                    return;
                }
                callback(item);
            }
        },
    });

    $(".vis-timeline").css("visibility", "visible");


    /****************** Timeline controls *******************/
    function fitTo(unit) {
        let center = moment($("#dateInput").val());
        if (!center.isValid()) {
            center = moment();
        }
        let start = center.clone().startOf(unit);
        let end = center.clone().endOf(unit);
        timeline.setWindow(start, end);
    }
    $("#currentMonthButton").click(_.partial(fitTo, "month"));
    $("#currentQuarterButton").click(_.partial(fitTo, "quarter"));
    $("#currentYearButton").click(_.partial(fitTo, "year"));
    $("#fitAllButton").click(function() {
        timeline.fit();
    });
    $("#dateInput").change(function() {
        let center = moment($(this).val());
        if (!center.isValid()) {
            return;
        }
        timeline.setWindow(center.clone().startOf("week"),
            center.clone().endOf("week"));
    });

    /****************** Reporting ***********************/
    let html = `\
<div class="row mb-3">
<div class="col-sm">
<div class="alert alert-success">
    <h3>Generate Schedule Report</h3>
    <p class="mb-0">
    As an administrator you may generate a schedule report for a particular
    manufacturing line over a specific timespan. Select a manufacturing line
    below, and enter the start and end dates. <b>Note</b> that your current
    schedule will be saved before the report is generated.
    </p>
</div>
</div>
</div>
<div class="row">
<div class="col-sm">
<div class="input-group">
    <div class="input-group-prepend">
        <label class="input-group-text" for="mlSelect">Manufacturing Line</label>
    </div>
    <select class="custom-select" id="mlSelect">
    </select>
</div>
<small>Only manufacturing lines with at least one item is shown.</small>

<div class="form-row mt-3">
<div class="input-group col-sm-6">
    <div class="input-group-prepend">
        <label class="input-group-text" for="startDate">
            From
        </label>
    </div>
    <input type="date" id="startDate" class="form-control">
    <small>If empty, will be the start time of the earliest scheduled item.</small>
</div>

<div class="input-group col-sm-6">
    <div class="input-group-prepend">
        <label class="input-group-text" for="startDate">
            To
        </label>
    </div>
    <input type="date" id="startDate" class="form-control">
    <small>If empty, will be the end time of last scheduled item.</small>
</div>
</div>
</div>
</div>`;

    $("#reportButton").click(function(ev) {
        ev.preventDefault();
        let url = $("form").attr("action");
        let groupMap = new Map();
        for (let group of groups.get({"fields": ["id"]}).map((g) => g.id)) {
            let groupItems = items.get({
                "filter": (item) => item.group === group
            });
            if (groupItems.length > 0) {
                groupMap.set(group, groupItems);
            }
        }
        if (groupMap.size === 0) {
            makeModalAlert("Error",
                "Cannot generate report: no item was scheduled.");
            return;
        }
        let modalContent = $(html);
        let mlSelect = modalContent.find("#mlSelect");
        for (let group of groupMap.keys()) {
            mlSelect.append($("<option>", {value: group, text: group}));
        }
        let modal = makeModalAlert("Generate Report", modalContent, generateReport);
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
            url = new URL(window.location.href, url);
            let start = moment(modal.find("input[name*=startDate]"));
            let end = moment(modal.find("input[name*=endDate]"));
            options = {
                report: "1",
                l: mlSelect.find("option:selected").val(),
                s: start.isValid() ? start.format() : "",
                e: end.isValid() ? end.format() : ""
            };
            url.search = $.param(options);
            $("form").attr("action", url.href).submit();
        }
    });
});