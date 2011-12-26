# Iron Puzzler data model

from google.appengine.dist import use_library;  use_library('django', '1.2')
from google.appengine.ext import db

class Game(db.Model):
  """ No parent; Key name: static game ID (see GetGame()) """
  ingredients = db.StringListProperty()
  ingredients_visible = db.BooleanProperty()
  admin_users = db.StringListProperty()
  puzzle_order = db.ListProperty(db.Key)
  login_enabled = db.BooleanProperty()
  solving_enabled = db.BooleanProperty()
  voting_enabled = db.BooleanProperty()
  results_enabled = db.BooleanProperty()


class Team(db.Model):
  """ Parent: Game; No key name """
  name = db.StringProperty()
  password = db.StringProperty()
  email = db.StringProperty()


class Puzzle(db.Model):
  """ Parent: Team (author); Key name: Puzzle type ("paper", "nonpaper") """
  title = db.StringProperty(default="Untitled")
  answers = db.StringListProperty()
  errata = db.StringProperty(multiline=True)
  errata_timestamp = db.DateTimeProperty()
  solution = db.StringProperty(multiline=True)


class Guess(db.Model):
  """ Parent: Puzzle; No key name """
  timestamp = db.DateTimeProperty(auto_now_add=True)
  answer = db.StringProperty()
  team = db.ReferenceProperty(Team)


class Feedback(db.Model):
  """ Parent: Puzzle; Key name: Key ID of team giving feedback """
  scores = db.ListProperty(float, default=[-1., -1., -1.])  # negative means N/A
  comment = db.StringProperty()


def GetProperties(entity):
  """ Convert a db.Model entity into a plain ol' dict for use in templates. """
  props = dict([(p, getattr(entity, p) or "") for p in entity.properties()])
  props["key_id"] = entity.key().id()
  props["key_name"] = entity.key().name()
  return props


def GetGame():
  """ Return the singleton Game entity. """
  return Game.get_or_insert("2012")
