from __future__ import annotations

import logging
import subprocess
import sys
from dataclasses import dataclass


logger = logging.getLogger(__name__)

_EXCLUDED_CALENDARS = {"Birthdays", "Holidays in Singapore", "Siri Suggestions"}


@dataclass
class CalendarEvent:
    title: str
    start_text: str
    end_text: str
    calendar_name: str
    location: str
    starts_in_minutes: int | None

    def to_context_item(self) -> dict:
        summary = f"Upcoming event from {self.calendar_name}"
        if self.location:
            summary += f" at {self.location}"
        return {
            "title": self.title,
            "summary": summary,
            "source": "local_calendar",
            "timestamp": self.start_text,
            "metadata": {
                "calendar_name": self.calendar_name,
                "location": self.location,
                "starts_in_minutes": self.starts_in_minutes,
            },
        }


def fetch_upcoming_events(limit: int = 3, lookahead_hours: int = 24) -> list[CalendarEvent]:
    if sys.platform != "darwin":
        return []

    script = [
        "-e", "set nowDate to current date",
        "-e", f"set endDate to nowDate + ({lookahead_hours} * hours)",
        "-e", 'tell application "Calendar"',
        "-e", 'set AppleScript\'s text item delimiters to linefeed',
        "-e", "set outLines to {}",
        "-e", "repeat with cal in calendars",
        "-e", "set calName to (name of cal as text)",
        "-e", 'if calName is not "Birthdays" and calName is not "Holidays in Singapore" and calName is not "Siri Suggestions" then',
        "-e", "repeat with ev in (every event of cal whose start date >= nowDate and start date <= endDate)",
        "-e", "set evLocation to location of ev",
        "-e", 'if evLocation is missing value then set evLocation to ""',
        "-e", "set deltaMinutes to ((start date of ev) - nowDate) div minutes",
        "-e", 'set end of outLines to ((summary of ev as text) & tab & ((start date of ev) as text) & tab & ((end date of ev) as text) & tab & calName & tab & evLocation & tab & (deltaMinutes as text))',
        "-e", "end repeat",
        "-e", "end if",
        "-e", "end repeat",
        "-e", "return outLines as text",
        "-e", "end tell",
    ]

    try:
        result = subprocess.run(
            ["osascript", *script],
            capture_output=True,
            text=True,
            timeout=8,
            check=True,
        )
    except Exception as exc:
        logger.warning("Could not fetch local Calendar events: %s", exc)
        return []

    lines = [line for line in result.stdout.splitlines() if line.strip()]
    events: list[CalendarEvent] = []
    for line in lines:
        parts = line.split("\t")
        if len(parts) < 6:
            continue
        title, start_text, end_text, calendar_name, location, starts_in_text = parts[:6]
        if calendar_name in _EXCLUDED_CALENDARS:
            continue
        try:
            starts_in = int(starts_in_text.strip())
        except Exception:
            starts_in = None
        events.append(
            CalendarEvent(
                title=title.strip(),
                start_text=start_text.strip(),
                end_text=end_text.strip(),
                calendar_name=calendar_name.strip(),
                location=location.strip(),
                starts_in_minutes=starts_in,
            )
        )

    events.sort(key=lambda event: event.starts_in_minutes if event.starts_in_minutes is not None else 10**9)
    return events[:limit]
