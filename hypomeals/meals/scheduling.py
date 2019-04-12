"""
Contains algorithms for generic auto-scheduling
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Mapping, Set

logger = logging.getLogger(__name__)


@dataclass
class Item:
    id: int
    hours: int
    groups: Set[str]


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
    items: List[Item], start: datetime, end: datetime
) -> List[Mapping[str, str]]:
    """
    Schedules the items according the following algorithm:
    :param items: a list of Item objects to be scheduled
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
    for item in items:
        schedules.append(
            Schedule(
                item.id,
                start,
                start + timedelta(hours=item.hours),
                next(iter(item.groups)),
            )
        )
    return list(map(Schedule.to_dict, schedules))
