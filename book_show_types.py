#!/usr/bin/env python3

"""
Game of Thrones chapters vs episodes chart generator
Copyright (c) 2013-2018, Joel Geddert

This script generates an HTML file of the table.

Software License:
	This program is free software: you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation, either version 3 of the License, or
	(at your option) any later version.

	This program is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	GNU General Public License for more details.

	You should have received a copy of the GNU General Public License
	along with this program.  If not, see <http://www.gnu.org/licenses/>.

A note from the author:
	The original chart generated by this code, as well as all remaining applicable
	source & asset files (except where noted), are licensed under a Creative Commons
	BY-SA 4.0 license <http://creativecommons.org/licenses/by-sa/4.0/>. If you are
	going to use any of this code to create a derivative work, please respect this
	CC license.
"""


from typing import List, Optional
from utils import find_unique


class Book:
	def __init__(self, number: int, name: str, abbreviation: str, chapters: Optional[List]=None):
		"""
		:param number: 1-indexed
		:param name: book name
		:param abbreviation: abbreviation, a.g. "AGoT"
		"""
		self.number = number
		self.name = name
		self.abbreviation = abbreviation
		self.chapters = chapters if chapters is not None else []

	def __str__(self):
		return self.name

	def __repr__(self):
		return 'Book(%i: %s ("%s"), %i chapters' % (
			self.number,
			self.name,
			self.abbreviation,
			len(self.chapters)
		)


class Chapter:
	def __init__(self, number: int, book: Book, number_in_book: int, name: str, pov_char: str, occurred: bool):
		"""
		:param number: chapter number (overall), 1-indexed
		:param book: reference to book
		:param number_in_book: number in book, 1-indexed
		:param name: chapter name
		:param pov_char: POV character
		:param occurred: if chapter has occurred in the show yet
		"""
		self.number = number
		self.book = book
		self.number_in_book = number_in_book
		self.name = name
		self.pov = pov_char
		self.occurred = occurred

	def __str__(self):
		return 'Chapter %i: "%s"' % (self.number, self.name)

	def __repr__(self):
		# TODO: add more details (repr should show all data)
		return 'Chapter(%s)' % str(self)


class Season:
	def __init__(self, number: int, episodes: Optional[List]=None):
		self.number = number
		self.episodes = episodes if episodes is not None else []


class Episode:
	def __init__(self, number: int, season: Season, name: str):
		"""
		:param number: episode number (overall), 1-indexed
		:param season: season number, 1-indexed
		:param name: episode name
		"""
		self.number = number
		self.season = season
		self.name = name

	def __str__(self):
		return '%i: "%s", season %i' % (self.number, self.name, self.season)

	def __repr__(self):
		return 'Episode(%s)' % str(self)


class Connection:
	def __init__(self, episode: Episode, chapter: Chapter, strength: int, major: bool, notes: str):
		"""
		:param episode: Reference to episode
		:param chapter: Reference to chapter
		:param strength:
		:param major: Is this a major storyline event?
		:param notes: Notes to be shown in alt text
		"""
		self.episode = episode
		self.chapter = chapter
		self.strength = strength
		self.major = major
		self.notes = notes

	def __str__(self):
		return 'Episode %i, Chapter %i' % (self.episode.number, self.chapter.number)

	def __repr__(self):
		# TODO: add more details (repr should show all data)
		return 'Connection(%s)' % str(self)


class DB:
	def __init__(self):
		self.books = []
		self.chapters = []
		self.chapters_interleaved = []

		self.seasons = []
		self.episodes = []

		self.connections = []

	def find_chapter(self, chap_name, book_num):
		return find_unique(self.chapters, lambda chapter: (chapter.book.number == book_num) and (chapter.name == chap_name))
