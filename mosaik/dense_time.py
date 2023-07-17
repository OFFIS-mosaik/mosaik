from dataclasses import dataclass
import functools
from typing import Self, Union


@functools.total_ordering
@dataclass(frozen=True)
class DenseTime:
	# __slots__ = ["time", "microstep"]
	time: int
	microstep: int = 0
	
	def __post_init__(self):
		assert isinstance(self.time, int)
		assert isinstance(self.microstep, int)

	def __add__(self, other: Union[Self, int]) -> Self:
		if isinstance(other, int):
			return self + DenseTime(other)

		if other.time == 0:
			return DenseTime(self.time, self.microstep + other.microstep)
		else:
			return DenseTime(self.time + other.time, other.microstep)

	def __radd__(self, other: int) -> Self:
		assert isinstance(other, int)
		return DenseTime(self.time + other, self.microstep)

	def __sub__(self, other: Self) -> Self:
		if other.time == 0:
			return DenseTime(self.time, self.microstep - other.microstep)
		else:
			return DenseTime(self.time - other.time, self.microstep)

	def __lt__(self, other: Union[Self, int]) -> bool:
		if isinstance(other, int):
			return self.time < other
		else:
			return self.time < other.time or (self.time == other.time and self.microstep < other.microstep)

	def __str__(self):
		return f"{self.time}s{self.microstep}"
