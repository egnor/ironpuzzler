# Iron Puzzler data model
# Key structure: Game -> Team -> Puzzle

from google.appengine.ext import db

class Game(db.Model):
  ingredients = db.StringListProperty()
  ingredients_visible = db.BooleanProperty()
  admin_users = db.StringListProperty()
  puzzle_order = db.ListProperty(db.Key)
  login_enabled = db.BooleanProperty()
  solving_enabled = db.BooleanProperty()


class Team(db.Model):
  name = db.StringProperty()
  password = db.StringProperty()
  email = db.StringProperty()


class Puzzle(db.Model):
  title = db.StringProperty()
  answers = db.StringListProperty()
  errata = db.StringProperty(multiline=True)
  solution = db.StringProperty(multiline=True)


def GetProperties(entity):
  """ Convert a db.Model entity into a plain ol' dict for use in templates. """
  props = dict([(p, getattr(entity, p) or "") for p in entity.properties()])
  props["key_id"] = entity.key().id()
  props["key_name"] = entity.key().name()
  return props


def GetGame():
  """ Return the singleton Game entity. """
  return Game.get_or_insert("2012")


def GetPuzzleNumber(game, puzzle):
  """ Get the assigned number of a puzzle, None if unassigned. """
  try: return game.puzzle_order.index(puzzle.key()) + 1
  except ValueError: return None
