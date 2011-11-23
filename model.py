# Iron Puzzler data model

from google.appengine.ext import db

GAME_ID = 2012

GAME_KEY = db.Key.from_path("Game", GAME_ID)

class Game(db.Model):
  ingredients = db.StringListProperty()
  ingredients_visible = db.BooleanProperty()
