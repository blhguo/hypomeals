"""
Contains algorithms for generic auto-scheduling
"""
import functools
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Mapping, Set

from meals.models import GoalItem

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
    id: int
    start: datetime
    end: datetime
    group: str

    def to_dict(self) -> Mapping[str, str]:
        return {
            "id": str(self.id),
            "start": int(self.start.timestamp()),
            "end": int(self.end.timestamp()),
            "group": self.group,
        }


class ScheduleException(Exception):
    """A generic exception for scheduling problems, e.g., unable to schedule"""

    pass


def schedule(
    items: List[Item],
    existing_items: Mapping[str, List[ExistingItem]],
    start: datetime,
    end: datetime,
) -> List[Mapping[str, str]]:
    """
    Schedules the items according the following algorithm:
    :param items: a list of Item objects to be scheduled
    :param existing_items: a list of ExistingItem objects that are already on the
        timeline and therefore cannot be changed.
    :param start: the earliest time when the items can be scheduled to start
    :param end: the latest time when the items can be scheduled to finish
    :return: a list of schedules
    """
    if len(items) > 1:
        raise ScheduleException("Unable to schedule: too many items.")
    schedules: List[Schedule] = []
    logger.info(
        "Scheduling %d items from %s to %s",
        len(items),
        start.isoformat(),
        end.isoformat(),
    )
    logger.info("Existing=%s", existing_items)
    for item in items:
        schedules.append(
            Schedule(
                item.item.id,
                start,
                start + timedelta(hours=item.hours),
                next(iter(item.groups)),
            )
        )
    return list(map(Schedule.to_dict, schedules))
