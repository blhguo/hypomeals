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
let warnings = new vis.DataSet([]);

$(function() {
    $("[data-toggle='tooltip']").tooltip();
    let warningUl = $("#warningUl");
    let warningDiv = $("#warningDiv");
    let suppressWarningCheckbox = $("#suppressWarningCheckbox");
    $("#showHelpButton").click(function() {
        $("#helpDiv").toggle("fast");
    });

    let mfgLines = new Set();  // Set of MLs to display groups
    $(".goalItems[data-schedulable=true]")
        .on("dragstart", function(event) {
        let src = $(this);
        let goalItemId = Number(src.attr("data-goal-item-id"));
        let itemInfo = goalItemsMap.get(goalItemId);
        event.originalEvent.dataTransfer.effectAllowed = "move";
        event.originalEvent.dataTransfer.setData("text",
            JSON.stringify(itemInfo));
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

    /**************** Timeline event listeners ***************/
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
            try {
                adjustEnd(item, item.start, true);
            } catch (e) {
                if (e.message !== "overlap") throw e;
                makeModalAlert("Error",
                    `Production overlaps on Manufacturing Line '${item.group}'.
                    This operation will be reverted.`,
                    null,
                    function() {
                        items.update(oldItem, IGNORE_SENDER_ID);
                    });
            }
        }
        generateWarnings();
    });
    items.on("add", function(event, properties, senderId) {
        let item = items.get(properties.items[0]);
        let itemInfo = goalItemsMap.get(item.id);
        if (!itemInfo.lines.includes(item.group)) {
            makeModalAlert("Cannot Schedule",
                `Manufacturing Line '${item.group}'\
                 cannot produce SKU #${itemInfo.skuId}.
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
        generateWarnings();
    });
    items.on("remove", function(event, properties, senderId) {
        let itemInfo = goalItemsMap.get(properties.items[0]);
        toggleGoalItem(properties.items[0], itemInfo.isOrphaned);
        // generateWarnings();
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
            itemInfo.title = "Orphaned item. Consider removing.";
            itemInfo.editable = {
                add: false,
                updateTime: false,
                updateGroup: false,
                remove: true,
                overrideItems: false,
            };
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
            goalItemsMap.set(id, itemInfo);
            items.add(itemInfo);
        }
        goalItemsMap.set(id, itemInfo);
    });
    generateWarnings();

    $("#submitButton").click(function(e) {
        let scheduled = [];
        for (let itemId of goalItemsMap.keys()) {
            let formDiv = form.find(`div[data-goal-item-id=${itemId}]`);
            let select = formDiv.find("select");
            let startTime = formDiv.find("input[name*=start_time]");
            let endTime = formDiv.find("input[name*=end_time]");
            let scheduledItem = items.get(itemId);
            if (scheduledItem !== null) {
                select.find(`option[value=${scheduledItem.group}]`).prop("selected", true);
                startTime.val(moment(scheduledItem.start).toISOString());
                endTime.val(moment(scheduledItem.end).toISOString());
                scheduled.push(scheduledItem);
            } else {
                select.find("option:eq(0)").prop("selected", true);
                startTime.val("");
                endTime.val("");
            }
        }

        let html = null;
        if (scheduled.length > 0) {
            html = $(`<p>You have scheduled the following items:</p>`);
            let table = $("#confirmationTable");
            for (let item of scheduled) {
                table.find("tbody").append($("<tr>").append([
                    $("<td>").text(item.content),
                    $("<td>").text(item.group),
                    $("<td>").text(moment(item.start).format("lll")),
                    $("<td>").text(moment(item.end).format("lll")),
                ]));
            }
            html.append(table);
        } else {
            html = $("<p>No items were scheduled.</p>");
        }
        html.append($(`<p class='mb-3'>Items not listed here will 
<b>all be unscheduled.</b> Do you want to save this schedule?</p>`));
        makeModalAlert("Confirm", html, function() {
            form.submit();
        }).find(".modal-dialog")
            .addClass("modal-lg");
    });

    /***************** Timeline *******************/
    groups = new vis.DataSet([]);
    mfgLines.forEach((l) => {
        groups.add({
            id: l,
            content: l,
            visible: true,
        })
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
        let globalSuppress = suppressWarningCheckbox.prop("checked");
        start = moment(start);
        let itemInfo = goalItemsMap.get(itemId);
        let updates = {id: itemId};
        updates["end"] = getCompletionTime(start, itemInfo.hours);
        updates["type"] = "range";
        if (updates.end > itemInfo.deadline) {
            updates["className"] = "bg-danger text-white";
            updates["title"] = `Start: ${start.format("lll")}.
        Warning: item exceeds deadline ${itemInfo.deadline.format("lll")}`;
            if (showWarning && !globalSuppress) {
                makeModalAlert("Warning",
                    `Scheduling this item to start at \
            ${start.format("lll")} will exceed predetermined \
            deadline of ${itemInfo.deadline.format("lll")} in the goal.
            Consider moving this item earlier.`);
            }
        } else {
            updates["className"] = itemInfo.isOrphaned ? "bg-warning text-dark" : "";
            updates["title"] = `Start: ${start.format("lll")}`;
        }
        items.update(updates, IGNORE_SENDER_ID);
        if (checkOverlap(item)) {
            throw Error("overlap");
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

        return endTime;
    }

    function generateWarnings() {
        if (timeline === null) return;  // Timeline is not initialized yet.
        let visibleItems = timeline.getVisibleItems();
        let suppressWarning = $("#suppressWarningCheckbox").prop("checked");
        let warnings = [];
        for (let itemId of visibleItems) {
            let item = items.get(itemId);
            let itemInfo = goalItemsMap.get(itemId);
            if (itemInfo.isOrphaned) {
                warnings.push(`Item '${itemInfo.content}' is orphaned. \
                    consider removing the item.`);
                continue;  // other warnings are suppressed for orphaned items.
            }
            if (moment(item.end) > itemInfo.deadline) {
                warnings.push(`Item '${itemInfo.content}' exceeds \
                    deadline of ${itemInfo.deadline.format("lll")}`);
            }
        }
        warningDiv.toggle(warnings.length > 0 && !suppressWarning);
        warningUl.find("li").remove();
        warnings.forEach(function(warning) {
            $("<li>", {text: warning}).appendTo(warningUl);
        });
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

    timeline.on("rangechanged", generateWarnings);

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
});