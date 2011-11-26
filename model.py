# Iron Puzzler data model

from google.appengine.ext import db

class Game(db.Model):
  ingredients = db.StringListProperty()
  ingredients_visible = db.BooleanProperty()
  admin_users = db.StringListProperty()
  login_enabled = db.BooleanProperty()
  puzzle_order = db.ListProperty(db.Key)

def GetGame(): return Game.get_or_insert("2012")


class Team(db.Model):
  name = db.StringProperty()
  password = db.StringProperty()


class Puzzle(db.Model):
  pass


def GetProperties(entity):
  props = dict([(p, getattr(entity, p)) for p in entity.properties()])
  props["key_id"] = entity.key().id()
  props["key_name"] = entity.key().name()
  return props
