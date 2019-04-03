#!/usr/bin/env python
# -*- coding: utf-8 -*-

from itertools import chain
from operator import attrgetter
from enum import Enum, IntEnum, IntFlag

from PIL import Image as _Image
from PIL import ImageDraw as _ImageDraw
from PIL import ImageFont as _ImageFont

from .properties import Color, Point, Size, Rect


_fonts = {}


class ResamplingFilter(IntEnum):
	Nearest = _Image.NEAREST
	Bilinear = _Image.BILINEAR


class Anchor(IntFlag):
	Left = 1
	CenterX = 2
	Right = 4
	Top = 8
	CenterY = 16
	Bottom = 32
	Center = CenterX | CenterY


class Alignment(Enum):
	Left = "left"
	Center = "center"
	Right = "right"


class Join(IntFlag):
	Miter = 1
	Round = 2
	Bevel = 3


class Cap(IntFlag):
	Butt = 1
	Round = 2
	Square = 3


def _is_opaque(image):
	assert image.mode in ("RGB", "RGBA")

	if image.mode == "RGB":
		return True

	for _, _, _, a in image.getdata():
		if a != 255:
			return False

	return True


class Image:
	@staticmethod
	def new(size, background=Color(0, 0, 0)):
		assert isinstance(size, Size) and size.area > 0
		assert isinstance(background, Color)
		image = _Image.new("RGBA", tuple(size), tuple(background))
		return Image(image)

	@staticmethod
	def load(filename):
		image = _Image.open(filename)
		image.load()
		return Image(image)

	@staticmethod
	def save_gif(filename, frames, frame_rate):
		assert len(frames) > 0

		frames = list(map(attrgetter("_image"), frames))

		frames[0].save(
			filename,
			append_images=frames[1:],
			save_all=True,
			duration=1000 / frame_rate,
			loop=0,
			optimize=False)

	def __init__(self, image):
		self._image = image
		self._opaque = None

	@property
	def size(self):
		return Size(*self._image.size)

	@property
	def width(self):
		return self._image.width

	@property
	def height(self):
		return self._image.height

	@property
	def opaque(self):
		if self._opaque is None:
			self._opaque = _is_opaque(self._image)
		return self._opaque

	def save(self, filename):
		self._image.save(filename)

	def copy(self):
		return Image(self._image.copy())

	def resize(self, size, filter=ResamplingFilter.Nearest):
		assert isinstance(size, Size) and size.area > 0
		if self.size == size:
			return
		self._image = self._image.resize(size, filter)
		return self

	def resized(self, size, filter=ResamplingFilter.Nearest):
		return self.copy().resize(size, filter)

	def paste(self, image, bounds=None, *, alpha_composite=False, filter=ResamplingFilter.Nearest):
		if bounds is None:
			bounds = image.size
		if isinstance(bounds, Point):
			bounds = Rect(bounds, image.size)
		elif isinstance(bounds, Size):
			bounds = Rect(bounds)
		assert isinstance(bounds, Rect)

		if image.size != bounds.size:
			image = image.resized(bounds.size, filter)

		alpha_composite = alpha_composite and not image.opaque

		x, y, x2, y2 = map(int, chain(bounds.min, bounds.max))

		if alpha_composite:
			_image = _Image.new("RGBA", tuple(self.size), (0, 0, 0, 0))
			_image.paste(image._image, (x, y, x2, y2))
			self._image = _Image.alpha_composite(self._image, _image)
		else:
			self._image.paste(image._image, (x, y, x2, y2))

	def draw_rect(self, bounds, color, outline_color=Color(0, 0, 0, 0), outline_width=1):
		assert isinstance(bounds, Rect)
		assert isinstance(color, Color)
		assert isinstance(outline_color, Color)

		if color.alpha == 0 and outline_color.alpha == 0:
			return

		x, y, x2, y2 = map(int, chain(bounds.min, bounds.max))

		# Reference: https://github.com/python-pillow/Pillow/issues/1668
		x2 -= 1
		y2 -= 1

		color = tuple(map(int, color))
		outline_color = tuple(map(int, outline_color))

		if color[3] == 255:
			draw = _ImageDraw.Draw(self._image, "RGBA")
			draw.rectangle((x, y, x2, y2), fill=color)
		elif color[3] > 0:
			image = _Image.new("RGBA", self._image.size, (0, 0, 0, 0))
			draw = _ImageDraw.Draw(image, "RGBA")
			draw.rectangle((x, y, x2, y2), fill=color)
			self._image = _Image.alpha_composite(self._image, image)

		if outline_color[3] == 255:
			draw = _ImageDraw.Draw(self._image, "RGBA")
			draw.rectangle((x, y, x2, y2), outline=outline_color, width=int(outline_width))
		elif outline_color[3] > 0:
			image = _Image.new("RGBA", self._image.size, (0, 0, 0, 0))
			draw = _ImageDraw.Draw(image, "RGBA")
			draw.rectangle((x, y, x2, y2), outline=outline_color, width=int(outline_width))
			self._image = _Image.alpha_composite(self._image, image)

	def draw_circle(self, center, radius, color, outline_color=Color(0, 0, 0, 0), outline_width=1):
		self.draw_ellipse(center, radius, radius, color, outline_color, outline_width)

	def draw_ellipse(self, center, radius_x, radius_y, color, outline_color=Color(0, 0, 0, 0), outline_width=1):
		assert isinstance(center, Point)
		assert isinstance(color, Color)
		assert isinstance(outline_color, Color)

		if color.alpha == 0 and outline_color.alpha == 0:
			return

		x, y, x2, y2 = center.x - radius_x, center.y - radius_y, center.x + radius_x, center.y + radius_y

		color = tuple(map(int, color))
		outline_color = tuple(map(int, outline_color))

		if color[3] == 255:
			draw = _ImageDraw.Draw(self._image, "RGBA")
			draw.ellipse((x, y, x2, y2), fill=color)
		elif color[3] > 0:
			image = _Image.new("RGBA", self._image.size, (0, 0, 0, 0))
			draw = _ImageDraw.Draw(image, "RGBA")
			draw.ellipse((x, y, x2, y2), fill=color)
			self._image = _Image.alpha_composite(self._image, image)

		if outline_color[3] == 255:
			draw = _ImageDraw.Draw(self._image, "RGBA")
			draw.ellipse((x, y, x2, y2), outline=outline_color, width=int(outline_width))
		elif outline_color[3] > 0:
			image = _Image.new("RGBA", self._image.size, (0, 0, 0, 0))
			draw = _ImageDraw.Draw(image, "RGBA")
			draw.ellipse((x, y, x2, y2), outline=outline_color, width=int(outline_width))
			self._image = _Image.alpha_composite(self._image, image)

	def draw_line(self, p1, p2, color, width=1):
		assert isinstance(p1, Point)
		assert isinstance(p2, Point)
		assert isinstance(color, Color)

		if color.alpha == 0:
			return

		x, y, x2, y2 = p1.x, p1.y, p2.x, p2.y

		if color.alpha == 255:
			draw = _ImageDraw.Draw(self._image, "RGBA")
			draw.line((x, y, x2, y2), fill=tuple(map(int, color)), width=int(width))
		else:
			image = _Image.new("RGBA", self._image.size, (0, 0, 0, 0))
			draw = _ImageDraw.Draw(image, "RGBA")
			draw.line((x, y, x2, y2), fill=tuple(map(int, color)), width=int(width))
			self._image = _Image.alpha_composite(self._image, image)

	def draw_text(self, text, position, color, font, anchor=Anchor.Center, alignment=Alignment.Left):
		assert isinstance(text, str)
		assert isinstance(position, Point)
		assert isinstance(color, Color)
		assert isinstance(font, Font)
		assert isinstance(alignment, Alignment)

		if color.alpha == 0:
			return

		text_width, text_height = font.measure_text(text)
		text_offset_x, text_offset_y = font.get_offset(text)

		x, y = position

		if anchor & Anchor.CenterX:
			x -= (text_width + text_offset_x) / 2
		elif anchor & Anchor.Right:
			x -= text_width + text_offset_x

		if anchor & Anchor.CenterY:
			y -= (text_height + text_offset_y) / 2
		elif anchor & Anchor.Bottom:
			y -= text_height + text_offset_y

		position = x, y

		if color.alpha == 255:
			draw = _ImageDraw.Draw(self._image, "RGBA")
			draw.text(position, text, fill=tuple(map(int, color)), font=font._font, align=alignment.value)
		else:
			image = _Image.new("RGBA", self._image.size, (0, 0, 0, 0))
			draw = _ImageDraw.Draw(image, "RGBA")
			draw.text(position, text, fill=tuple(map(int, color)), font=font._font, align=alignment.value)
			self._image = _Image.alpha_composite(self._image, image)

	def draw_polygon(self, points, color, outline_color=Color(0, 0, 0, 0), outline_width=1):
		list_points = ()
		for p in points:
			assert isinstance(p, Point)
			list_points += (p.x, p.y)
		assert isinstance(color, Color)
		assert isinstance(outline_color, Color)

		color = tuple(map(int, color))
		outline_color = tuple(map(int, outline_color))

		if color[3] == 255:
			draw = _ImageDraw.Draw(self._image, "RGBA")
			draw.polygon(list_points, fill=color)
		elif color[3] > 0:
			image = _Image.new("RGBA", self._image.size, (0, 0, 0, 0))
			draw = _ImageDraw.Draw(image, "RGBA")
			draw.polygon(list_points, fill=color)
			self._image = _Image.alpha_composite(self._image, image)

		if outline_color[3] == 255:
			draw = _ImageDraw.Draw(self._image, "RGBA")
			for i in range(0, len(points)):
				x, y = points[i - 1].x, points[i - 1].y
				x2, y2 = points[i].x, points[i].y
				draw.line((x, y, x2, y2), fill=outline_color, width=int(outline_width))
		elif outline_color[3] > 0:
			image = _Image.new("RGBA", self._image.size, (0, 0, 0, 0))
			draw = _ImageDraw.Draw(image, "RGBA")
			for i in range(0, len(points)):
				x, y = points[i - 1].x, points[i - 1].y
				x2, y2 = points[i].x, points[i].y
				draw.line((x, y, x2, y2), fill=outline_color, width=int(outline_width))
			self._image = _Image.alpha_composite(self._image, image)

	def _create_miter_join_cap(self, x, y, x2, y2, offset):
		if x2 != x and y2 != y:
			slope = (y2 - y) / (x2 - x)
			intercept = y - (slope * x)
			if x2 > x:
				x2 = x2 + offset / 2
			else:
				x2 = x2 - offset / 2
			y2 = slope * x2 + intercept
		elif x2 == x:
			if y2 > y:
				y2 = y2 + offset
			else:
				y2 = y2 - offset
		elif y2 == y:
			if x2 > x:
				x2 = x2 + offset
			else:
				x2 = x2 - offset
		return x2, y2

	def _draw_polylines_join(self, draw, x, y, x2, y2, color, offset, join):
		if join == Join.Miter:
			x2, y2 = self._create_miter_join_cap(x, y, x2, y2, offset)
		elif join == Join.Round:
			draw.ellipse((x2 - offset, y2 - offset, x2 + offset, y2 + offset), fill=color)
		elif join == Join.Bevel:
			pass
		return x2, y2

	def _draw_polylines_cap(self, draw, points, color, offset, cap, width):
		points_size = len(points)
		x, y = points[0].x, points[0].y
		x2, y2 = points[points_size - 1].x, points[points_size - 1].y
		if cap == Cap.Round:
			draw.ellipse((x - offset, y - offset, x + offset, y + offset), fill=color)
			draw.ellipse((x2 - offset, y2 - offset, x2 + offset, y2 + offset), fill=color)
		elif cap == Cap.Square:
			x1, y1 = points[1].x, points[1].y
			cap_x, cap_y = self._create_miter_join_cap(x1, y1, x, y, offset)
			draw.line((x, y, cap_x, cap_y), fill=color, width=int(width))
			x3, y3 = points[points_size-2].x, points[points_size-2].y
			cap_x2, cap_y2 = self._create_miter_join_cap(x3, y3, x2, y2, offset)
			draw.line((x2, y2, cap_x2, cap_y2), fill=color, width=int(width))

	def _draw_polylines_helper(self, draw, points, color, width, join, cap):
		if (width % 2) == 0:
			width = width + 1
		offset = (width - 1) / 2
		for i in range(1, len(points)):
			x, y = points[i - 1].x, points[i - 1].y
			x2, y2 = points[i].x, points[i].y
			if i < len(points) - 1:
				x2, y2 = self._draw_polylines_join(draw, x, y, x2, y2, color, offset, join)
			draw.line((x, y, x2, y2), fill=color, width=int(width))
		self._draw_polylines_cap(draw, points, color, offset, cap, width)

	def draw_polylines(self, points, color=Color(0, 0, 0, 0), width=1, join=Join.Miter, cap=Cap.Butt):
		list_points = ()
		for p in points:
			assert isinstance(p, Point)
			list_points += (p.x, p.y)
		assert isinstance(color, Color)
		assert isinstance(join, Join)
		assert isinstance(cap, Cap)

		color = tuple(map(int, color))

		if color[3] == 255:
			draw = _ImageDraw.Draw(self._image, "RGBA")
			self._draw_polylines_helper(draw, points, color, width, join, cap)
		else:
			image = _Image.new("RGBA", self._image.size, (0, 0, 0, 0))
			draw = _ImageDraw.Draw(image, "RGBA")
			self._draw_polylines_helper(draw, points, color, width, join, cap)
			self._image = _Image.alpha_composite(self._image, image)


class Font:
	@staticmethod
	def load(font, size):
		size = int(size)
		try:
			return _fonts[font, size]
		except KeyError:
			font = _ImageFont.truetype(font, size)
			_fonts[font, size] = font
			return Font(font, size)

	def __init__(self, font, size):
		self._font = font
		self._size = size

	@property
	def size(self):
		return self._size

	def measure_line(self, line):
		return self._font.getsize(line)

	def measure_lines(self, text):
		for line in text.splitlines():
			yield self.measure_line(line)

	def measure_text(self, text, spacing=4):
		width, height = 0, 0

		for i, (w, h) in enumerate(self.measure_lines(text)):
			width = max(width, w)
			height += h
			if i > 0:
				height += spacing

		return width, height

	def get_offset(self, text):
		return self._font.getoffset(text)
