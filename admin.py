# Iron Puzzler administrative interface handler

import random
import re

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import model

FETCH = 1000
PUZZLE_TYPES = ["paper", "nonpaper"]

def IsUserAdmin(game):
  if users.is_current_user_admin(): return True
  user = users.get_current_user()
  return user and (user.email() in game.admin_users)


class AdminPage(webapp.RequestHandler):
  def get(self):
    user = users.get_current_user()
    if not user: return self.redirect(users.create_login_url(dest_url="/admin"))

    game = model.GetGame()
    puzzle_numbers = dict([(p, n + 1)
        for n, p in enumerate(game.puzzle_order or [])])

    team_numbers = {}
    for pk in model.Puzzle.all(keys_only=True).ancestor(game).fetch(FETCH):
      numbers = team_numbers.setdefault(pk.parent(), {})
      numbers[pk.name()] = puzzle_numbers.get(pk, "-")

    props = {
      "game": model.GetProperties(game),
      "user_email": user.email(),
      "user_logout_url": users.create_logout_url(dest_url="/admin"),
      "user_ok": IsUserAdmin(game),
      "teams": []
    }

    for team in model.Team.all().ancestor(game).order("name").fetch(FETCH):
      team_props = model.GetProperties(team)
      team_props["numbers"] = team_numbers.get(team.key(), {})
      props["teams"].append(team_props)

    self.response.out.write(template.render("admin.dj.html", props))


  def post(self):
    game = model.GetGame()
    if not IsUserAdmin(game): return self.error(403)

    ingredients = [self.request.get("ingredient%d" % i) for i in range(3)]
    admin_users = re.split(r'[,\s]+', self.request.get("admin_users"))
    game.ingredients = [i for i in ingredients if i]
    game.ingredients_visible = bool(self.request.get("ingredients_visible"))
    game.admin_users = [u for u in admin_users if u]
    game.login_enabled = bool(self.request.get("login_enabled"))

    if self.request.get("assign_numbers"):
      type_puzzles = {}
      for p in model.Puzzle.all(keys_only=True).ancestor(game).fetch(FETCH):
        type_puzzles.setdefault(p.name(), []).append(p)

      for plist in type_puzzles.values(): random.shuffle(plist)
      game.puzzle_order = []
      for ptype in PUZZLE_TYPES + type_puzzles.keys():
        plist = type_puzzles.get(ptype, [])
        game.puzzle_order.extend(plist)
        plist[:] = []

    game.put()

    if self.request.get("new_team"):
      team = model.Team(parent=game)
      team.name = self.request.get("new_team")
      team.password = self.request.get("new_password")
      team.put()
      for pt in PUZZLE_TYPES: model.Puzzle(parent=team, key_name=pt).put()

    self.redirect("/admin")


app = webapp.WSGIApplication([("/admin", AdminPage)], debug=True)
if __name__ == "__main__": run_wsgi_app(app)
