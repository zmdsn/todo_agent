"""Time parsing utilities for todo-mcp."""

from datetime import date, timedelta
from enum import Enum
from typing import Optional
import re


class TimeResolution(Enum):
    """Time resolution levels."""
    YEAR = "year"
    QUARTER = "quarter"
    MONTH = "month"
    WEEK = "week"
    DAY = "day"


class ParsedTime:
    """Represents a parsed time expression."""

    def __init__(
        self,
        resolution: TimeResolution,
        year: int,
        month: Optional[int] = None,
        day: Optional[int] = None,
        quarter: Optional[int] = None,
        week: Optional[int] = None
    ):
        self.resolution = resolution
        self.year = year
        self.month = month
        self.day = day
        self.quarter = quarter
        self.week = week

    def to_file_path(self) -> str:
        """Convert to file path format.

        Returns:
            File path string like "2026/Q1/03-March.md"
        """
        month_names = {
            1: "01-January", 2: "02-February", 3: "03-March",
            4: "04-April", 5: "05-May", 6: "06-June",
            7: "07-July", 8: "08-August", 9: "09-September",
            10: "10-October", 11: "11-November", 12: "12-December"
        }

        if self.resolution == TimeResolution.YEAR:
            return f"{self.year}/README.md"
        elif self.resolution == TimeResolution.QUARTER:
            return f"{self.year}/Q{self.quarter}/README.md"
        elif self.resolution == TimeResolution.MONTH:
            month_name = month_names[self.month]
            return f"{self.year}/Q{self.quarter}/{month_name}.md"
        elif self.resolution == TimeResolution.WEEK:
            month_name = month_names[self.month]
            return f"{self.year}/Q{self.quarter}/{month_name}.md#week-{self.week}"
        elif self.resolution == TimeResolution.DAY:
            month_name = month_names[self.month]
            return f"{self.year}/Q{self.quarter}/{month_name}.md"
        else:
            return f"{self.year}/README.md"

    def __repr__(self) -> str:
        return f"ParsedTime(resolution={self.resolution.value}, year={self.year}, month={self.month}, day={self.day}, quarter={self.quarter}, week={self.week})"


class TimeParser:
    """Parser for time expressions in both Chinese and English."""

    def __init__(self, base_date: Optional[date] = None):
        """Initialize the parser.

        Args:
            base_date: Base date for relative calculations. Defaults to today.
        """
        self.base_date = base_date or date.today()

    def get_quarter(self, month: int) -> int:
        """Get quarter from month.

        Args:
            month: Month number (1-12)

        Returns:
            Quarter number (1-4)
        """
        return (month - 1) // 3 + 1

    def get_week_of_year(self, d: date) -> int:
        """Get week number of the year.

        Args:
            d: Date object

        Returns:
            Week number (1-53)
        """
        return d.isocalendar()[1]

    def parse(self, text: str) -> ParsedTime:
        """Parse a time expression.

        Args:
            text: Time expression string

        Returns:
            ParsedTime object

        Raises:
            ValueError: If the expression cannot be parsed
        """
        text = text.strip().lower()

        # Try each pattern in order
        patterns = [
            self._parse_today,
            self._parse_tomorrow,
            self._parse_this_week,
            self._parse_year,
            self._parse_quarter,
            self._parse_month,
            self._parse_date,
        ]

        for pattern_func in patterns:
            result = pattern_func(text)
            if result is not None:
                return result

        raise ValueError(f"Unable to parse time expression: {text}")

    def _parse_today(self, text: str) -> Optional[ParsedTime]:
        """Parse 'today' expressions."""
        if text in ["今天", "today", "今日"]:
            return ParsedTime(
                resolution=TimeResolution.DAY,
                year=self.base_date.year,
                month=self.base_date.month,
                day=self.base_date.day,
                quarter=self.get_quarter(self.base_date.month)
            )
        return None

    def _parse_tomorrow(self, text: str) -> Optional[ParsedTime]:
        """Parse 'tomorrow' expressions."""
        if text in ["明天", "tomorrow", "明日"]:
            tomorrow = self.base_date + timedelta(days=1)
            return ParsedTime(
                resolution=TimeResolution.DAY,
                year=tomorrow.year,
                month=tomorrow.month,
                day=tomorrow.day,
                quarter=self.get_quarter(tomorrow.month)
            )
        return None

    def _parse_this_week(self, text: str) -> Optional[ParsedTime]:
        """Parse 'this week' expressions."""
        if text in ["本周", "this week", "这周", "这星期"]:
            return ParsedTime(
                resolution=TimeResolution.WEEK,
                year=self.base_date.year,
                month=self.base_date.month,
                week=self.get_week_of_year(self.base_date),
                quarter=self.get_quarter(self.base_date.month)
            )
        return None

    def _parse_year(self, text: str) -> Optional[ParsedTime]:
        """Parse year expressions."""
        # 4-digit year: 2026
        if re.match(r"^\d{4}$", text):
            year = int(text)
            return ParsedTime(
                resolution=TimeResolution.YEAR,
                year=year
            )

        # Chinese year expressions
        if text in ["今年", "this year"]:
            return ParsedTime(
                resolution=TimeResolution.YEAR,
                year=self.base_date.year
            )
        if text in ["去年", "last year"]:
            return ParsedTime(
                resolution=TimeResolution.YEAR,
                year=self.base_date.year - 1
            )
        if text in ["明年", "next year"]:
            return ParsedTime(
                resolution=TimeResolution.YEAR,
                year=self.base_date.year + 1
            )

        return None

    def _parse_quarter(self, text: str) -> Optional[ParsedTime]:
        """Parse quarter expressions."""
        # Q1, q1, Q2, etc.
        match = re.match(r"^q(\d)$", text)
        if match:
            quarter = int(match.group(1))
            if 1 <= quarter <= 4:
                return ParsedTime(
                    resolution=TimeResolution.QUARTER,
                    year=self.base_date.year,
                    quarter=quarter
                )

        # Chinese quarter expressions
        quarter_map = {
            "第一季度": 1, "q1": 1,
            "第二季度": 2, "q2": 2,
            "第三季度": 3, "q3": 3,
            "第四季度": 4, "q4": 4,
        }
        if text in quarter_map:
            return ParsedTime(
                resolution=TimeResolution.QUARTER,
                year=self.base_date.year,
                quarter=quarter_map[text]
            )

        # "本季度"
        if text in ["本季度", "this quarter"]:
            return ParsedTime(
                resolution=TimeResolution.QUARTER,
                year=self.base_date.year,
                quarter=self.get_quarter(self.base_date.month)
            )

        return None

    def _parse_month(self, text: str) -> Optional[ParsedTime]:
        """Parse month expressions."""
        # 3月, mar, march
        month_names = {
            "january": 1, "jan": 1, "1月": 1,
            "february": 2, "feb": 2, "2月": 2,
            "march": 3, "mar": 3, "3月": 3,
            "april": 4, "apr": 4, "4月": 4,
            "may": 5, "5月": 5,
            "june": 6, "jun": 6, "6月": 6,
            "july": 7, "jul": 7, "7月": 7,
            "august": 8, "aug": 8, "8月": 8,
            "september": 9, "sep": 9, "9月": 9,
            "october": 10, "oct": 10, "10月": 10,
            "november": 11, "nov": 11, "11月": 11,
            "december": 12, "dec": 12, "12月": 12,
        }

        if text in month_names:
            month = month_names[text]
            return ParsedTime(
                resolution=TimeResolution.MONTH,
                year=self.base_date.year,
                month=month,
                quarter=self.get_quarter(month)
            )

        # "本月"
        if text in ["本月", "this month"]:
            return ParsedTime(
                resolution=TimeResolution.MONTH,
                year=self.base_date.year,
                month=self.base_date.month,
                quarter=self.get_quarter(self.base_date.month)
            )

        # "上个月", "下个月"
        if text in ["上个月", "last month"]:
            month = self.base_date.month - 1
            year = self.base_date.year
            if month < 1:
                month = 12
                year -= 1
            return ParsedTime(
                resolution=TimeResolution.MONTH,
                year=year,
                month=month,
                quarter=self.get_quarter(month)
            )

        if text in ["下个月", "next month"]:
            month = self.base_date.month + 1
            year = self.base_date.year
            if month > 12:
                month = 1
                year += 1
            return ParsedTime(
                resolution=TimeResolution.MONTH,
                year=year,
                month=month,
                quarter=self.get_quarter(month)
            )

        return None

    def _parse_date(self, text: str) -> Optional[ParsedTime]:
        """Parse date expressions."""
        # 3月9日, mar 9, march 9
        match = re.match(r"^(\d{1,2})月(\d{1,2})[日号]?$", text)
        if match:
            month = int(match.group(1))
            day = int(match.group(2))
            if 1 <= month <= 12 and 1 <= day <= 31:
                return ParsedTime(
                    resolution=TimeResolution.DAY,
                    year=self.base_date.year,
                    month=month,
                    day=day,
                    quarter=self.get_quarter(month)
                )

        # English date: mar 9, march 9
        month_names = {
            "january": 1, "jan": 1,
            "february": 2, "feb": 2,
            "march": 3, "mar": 3,
            "april": 4, "apr": 4,
            "may": 5,
            "june": 6, "jun": 6,
            "july": 7, "jul": 7,
            "august": 8, "aug": 8,
            "september": 9, "sep": 9,
            "october": 10, "oct": 10,
            "november": 11, "nov": 11,
            "december": 12, "dec": 12,
        }

        for month_name, month_num in month_names.items():
            match = re.match(rf"^{month_name}\s+(\d{{1,2}})$", text)
            if match:
                day = int(match.group(1))
                if 1 <= day <= 31:
                    return ParsedTime(
                        resolution=TimeResolution.DAY,
                        year=self.base_date.year,
                        month=month_num,
                        day=day,
                        quarter=self.get_quarter(month_num)
                    )

        return None
