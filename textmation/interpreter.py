#!/usr/bin/env python
# -*- coding: utf-8 -*-

from contextlib import contextmanager
from inspect import isclass

from . import elements
from . import parser
from .elements import Element
from .parser import parse


internal_templates = {}

for name, cls in elements.__dict__.items():
	if not isclass(cls):
		continue
	if issubclass(cls, Element) and cls is not Element:
		internal_templates[name] = cls

internal_templates["Rect"] = internal_templates["Rectangle"]


class InterpreterError(Exception):
	pass


class Interpreter:
	def __init__(self):
		self.templates = None
		self._elements = None

	def _get_template(self, name, *, token=None):
		try:
			return self.templates[name]
		except KeyError:
			raise self._create_error(f"Creating undefined {name!r} template", token=token) from None

	@staticmethod
	def _apply_template(template, element):
		if isclass(template):
			assert issubclass(template, Element)
			template = template()
		assert isinstance(template, Element)
		return template.apply(element)

	@staticmethod
	def _instantiate_template(template):
		return Interpreter._apply_template(template, Element())

	@property
	def _element(self):
		return self._elements[-1]

	@contextmanager
	def _push_element(self, element):
		self._elements.append(element)
		yield
		assert self._elements.pop() is element

	@staticmethod
	def _create_error(message, *, token=None):
		if token is not None:
			begin, end = token.span
			return InterpreterError("%s at %d:%d to %d:%d" % (message, *begin, *end))
		else:
			return InterpreterError(message)

	def _fail(self, message, *, token=None):
		raise self._create_error(message, token=token)

	def interpret(self, string):
		if isinstance(string, str):
			return self.interpret(parse(string))
		else:
			assert isinstance(string, parser.Create)
			assert string.element == "Scene"

			self.templates = dict(internal_templates)
			self._elements = []

			scene = self._interpret(string)
			# assert isinstance(scene, elements.Scene)
			assert isinstance(scene, elements.Scene) or scene.name == "Scene"

			return scene

	def _interpret(self, node):
		assert isinstance(node, parser.Node)
		method = "_interpret_%s" % node.__class__.__name__
		visitor = getattr(self, method)
		return visitor(node)

	def _interpret_children(self, node):
		for child in node.children:
			yield self._interpret(child)

	def _interpret_Create(self, create):
		template = self._get_template(create.element, token=create.token)
		element = self._instantiate_template(template)

		if create.name:
			raise NotImplementedError

		with self._push_element(element):
			for child in self._interpret_children(create):
				if child is None:
					continue
				assert isinstance(child, Element)
				element.add(child)

		return element

	def _interpret_Template(self, template):
		element_template = Element()
		element_template.name = template.name

		if template.name in self.templates:
			self._fail(f"Redeclaration of {template.name!r}", token=template.token)

		if template.inherit is not None:
			_template = self._get_template(template.inherit, token=template.token)
			self._apply_template(_template, element_template)

		with self._push_element(element_template):
			for child in self._interpret_children(template):
				if child is None:
					continue
				assert isinstance(child, Element)
				element_template.add(child)

		self.templates[template.name] = element_template

		return None

	def _interpret_BinOp(self, bin_op):
		raise NotImplementedError

	def _interpret_UnaryOp(self, unary_op):
		raise NotImplementedError

	def _interpret_Assign(self, assign):
		name, value = self._interpret_children(assign)
		self._element.set(name, value)
		return None

	def _interpret_Name(self, name):
		assert len(name.children) == 0
		return name.name

	def _interpret_Number(self, number):
		assert len(number.children) == 0
		return number

	def _interpret_String(self, string):
		assert len(string.children) == 0
		return string.string