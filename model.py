# Iron Puzzler data model

from google.appengine.ext import blobstore
from google.appengine.ext import db

class Game(db.Model):
  """ No parent; Key name: static game ID (see GetGame()) """
  location = db.StringProperty(default="Somewhere")
  ingredients = db.StringListProperty()
  ingredients_visible = db.BooleanProperty()
  admin_users = db.StringListProperty()
  login_enabled = db.BooleanProperty()
  solving_enabled = db.BooleanProperty()
  voting_enabled = db.BooleanProperty()
  results_enabled = db.BooleanProperty()


class Team(db.Model):
  """ Parent: Game; No key name """
  name = db.StringProperty()
  password = db.StringProperty()
  email = db.StringProperty()
  bonus = db.FloatProperty(default=0.0)


class Puzzle(db.Model):
  """ Parent: Team (author); Key name: Puzzle type ("paper", "nonpaper") """
  number = db.StringProperty(default="???")
  title = db.StringProperty(default="Untitled")
  answers = db.StringListProperty()
  errata = db.StringProperty(multiline=True)
  errata_timestamp = db.DateTimeProperty()
  solution = db.StringProperty(multiline=True)
  solution_blob = blobstore.BlobReferenceProperty()
  puzzle_blob = blobstore.BlobReferenceProperty()


class Guess(db.Model):
  """ Parent: Puzzle; No key name """
  timestamp = db.DateTimeProperty(auto_now_add=True)
  answer = db.StringProperty()
  team = db.ReferenceProperty(Team)


class Feedback(db.Model):
  """ Parent: Puzzle; Key name: Key ID of team giving feedback """
  scores = db.ListProperty(float, default=[3., 3., 3.])
  comment = db.StringProperty()


def GetProperties(entity):
  """ Convert a db.Model entity into a plain ol' dict for use in templates. """
  props = dict([(p, getattr(entity, p) or "") for p in entity.properties()])
  props["key"] = entity.key()
  props["key_id"] = entity.key().id()
  props["key_name"] = entity.key().name()
  return props


def GetGame():
  """ Return the singleton Game entity. """
  return Game.get_or_insert("2012")
