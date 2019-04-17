"""
Contains algorithms for generic auto-scheduling
"""
import functools
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Mapping, Set, Tuple, Dict, Callable

from meals.constants import WORK_HOURS_END
from meals.models import GoalItem
from meals.utils import compute_end_time, compute_start_time

logger = logging.getLogger(__name__)


@dataclass
class Item:
    item: GoalItem
    hours: int
    groups: Set[str]


@functools.total_ordering
@dataclass
class ExistingItem:
    item: GoalItem
    start: datetime
    end: datetime

    def __lt__(self, other):
        return self.start < other.start


@dataclass
class Schedule:
    item_id: int
    start: datetime
    end: datetime
    group: str

    def to_dict(self) -> Mapping[str, str]:
        return {
            "id": str(self.item_id),
            "start": int(self.start.timestamp()),
            "end": int(self.end.timestamp()),
            "group": self.group,
        }


class ScheduleException(Exception):
    """A generic exception for scheduling problems, e.g., unable to schedule"""

    pass


def _get_available_blocks(
    existing_items: Mapping[str, List[ExistingItem]], start: datetime, end: datetime
) -> Dict[str, List[Tuple[datetime, datetime]]]:
    """
    Finds available time blocks in each group. A time block is a chunk of time in
    which an item can be scheduled.
    :param existing_items: mapping of existing items
    :param start: start time
    :param end: end time
    :return: a dict mapping group to available time blocks
    """
    schedules: Dict[str, List[Tuple[datetime, datetime]]] = {}
    for ml_sn, goals in existing_items.items():
        relevant_goals = []
        for item in goals:
            if item.start <= end and item.end >= start:
                relevant_goals.append(item)
        time_block = []
        cur_start = start
        # Special check
        if relevant_goals:
            first_goal_item = relevant_goals[0]
            if first_goal_item.start < start:
                cur_start = first_goal_item.end
                relevant_goals.pop(0)
        for schedule in relevant_goals:
            time_block.append((cur_start, schedule.start))
            cur_start = schedule.end
        if cur_start < end:
            time_block.append((cur_start, end))
        schedules[ml_sn] = time_block
    return schedules


def schedule(
    items: List[Item],
    existing_items: Mapping[str, List[ExistingItem]],
    start: datetime,
    end: datetime,
) -> List[Mapping[str, str]]:
    """
    Schedules the items according the following algorithm:
    :param items: a list of Item objects to be scheduled
    :param existing_items: a mapping from group to ExistingItem objects that are
        already on the timeline and therefore cannot be changed.
    :param start: the earliest time when the items can be scheduled to start
    :param end: the latest time when the items can be scheduled to finish
    :return: a list of schedules
    """
    schedules: List[Schedule] = []
    logger.info(
        "Scheduling %d items from %s to %s",
        len(items),
        start.isoformat(),
        end.isoformat(),
    )
    # Prioritize item with earliest deadline, with a tiebreaker of shortest
    # time first
    items.sort(key=lambda item: (item.item.goal.deadline, item.hours))
    ml_schedules = _get_available_blocks(existing_items, start, end)

    for item in items:
        min_earliest_time = end
        min_ml = None
        min_block_id = None
        for ml in item.groups:
            earliest_time = end
            earliest_block_id = None
            for i, (st, et) in enumerate(ml_schedules[ml]):
                if compute_end_time(st, item.hours) <= et:
                    earliest_time = st
                    earliest_block_id = i
                    break
            if earliest_time < min_earliest_time:
                min_earliest_time = earliest_time
                min_ml = ml
                min_block_id = earliest_block_id
        if min_ml is None:
            raise ScheduleException("Unable to schedule: too many items.")
        else:
            if min_earliest_time > item.item.goal.completion_time:
                raise ScheduleException("Unable to schedule: too many items.")
            item_end_time = compute_end_time(min_earliest_time, item.hours)
            schedules.append(
                Schedule(item.item.id, min_earliest_time, item_end_time, min_ml)
            )
            st, et = ml_schedules[min_ml][min_block_id]
            if et == item_end_time:
                del ml_schedules[min_ml][min_block_id]
            else:
                ml_schedules[min_ml][min_block_id] = (item_end_time, et)
    logger.info("Scheduled %d items: %s", len(schedules), schedules)
    return list(map(Schedule.to_dict, schedules))


def schedule_max_profit(
    items: List[Item],
    existing_items: Mapping[str, List[ExistingItem]],
    start: datetime,
    end: datetime,
) -> List[Mapping[str, str]]:
    """
    Schedules the items according the following algorithm:
    :param items: a list of Item objects to be scheduled
    :param existing_items: a mapping from group to ExistingItem objects that are
        already on the timeline and therefore cannot be changed.
    :param start: the earliest time when the items can be scheduled to start
    :param end: the latest time when the items can be scheduled to finish
    :return: a list of schedules
    """
    schedules: List[Schedule] = []
    logger.info(
        "Scheduling %d items from %s to %s",
        len(items),
        start.isoformat(),
        end.isoformat(),
    )
    # Prioritize item with earliest deadline, with a tiebreaker of shortest
    # time first
    items.sort(key=lambda item: (item.item.sku.run_cost, item.hours))
    ml_schedules = _get_available_blocks(existing_items, start, end)

    for item in items:
        max_latest_time = start
        opt_ml = None
        opt_block_id = None
        item_deadline = datetime.combine(item.item.goal.deadline, WORK_HOURS_END)
        for ml in item.groups:
            latest_time = end
            latest_block_id = None
            for i, (st, et) in enumerate(reversed(list(ml_schedules[ml]))):
                deadline = et if et <= item_deadline else item_deadline
                if compute_start_time(deadline, item.hours) >= st:
                    latest_time = compute_start_time(deadline, item.hours)
                    latest_block_id = i
                    break
            if latest_time > max_latest_time:
                max_latest_time = latest_time
                opt_ml = ml
                opt_block_id = latest_block_id
        if opt_ml is None:
            raise ScheduleException("Unable to schedule: too many items.")
        else:
            item_end_time = compute_end_time(max_latest_time, item.hours)
            schedules.append(
                Schedule(item.item.id, max_latest_time, item_end_time, opt_ml)
            )
            st, et = ml_schedules[opt_ml][opt_block_id]
            if et == item_end_time:
                del ml_schedules[opt_ml][opt_block_id]
            else:
                ml_schedules[opt_ml][opt_block_id] = (item_end_time, et)
    logger.info("Scheduled %d items: %s", len(schedules), schedules)
    return list(map(Schedule.to_dict, schedules))


schedulers = {"earliest_deadline": schedule, "max_profit": schedule_max_profit}


SchedulerType = Callable[
    [List[Item], Mapping[str, List[ExistingItem]], datetime, datetime],
    List[Mapping[str, str]],
]


def get_scheduler(name) -> SchedulerType:
    if name in schedulers:
        return schedulers[name]
    else:
        logger.warning("Unknown scheduler %s, returning earliest_deadline")
        return schedulers["earliest_deadline"]
