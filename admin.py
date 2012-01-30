# Iron Puzzler administrative interface handler

import random
import re

from google.appengine.dist import use_library;  use_library('django', '1.2')
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import model

PUZZLE_TYPES = ["paper", "nonpaper"]

def IsUserAdmin(game):
  if users.is_current_user_admin(): return True
  user = users.get_current_user()
  return user and (user.email() in game.admin_users)


def Ordinal(n):
  if n % 100 // 10 == 1: return "%dth" % n
  return "%d%s" % (n, { 1: "st", 2: "nd", 3: "rd" }.get(n % 10, "th"))


class AdminPage(webapp.RequestHandler):
  def get(self):
    game = model.GetGame()
    user = users.get_current_user()
    if not user or not IsUserAdmin(game):
      return self.redirect(users.create_login_url(dest_url="/admin"))

    props = {
      "game": model.GetProperties(game),
      "user_email": user.email(),
      "user_logout_url": users.create_logout_url(dest_url="/admin"),
      "puzzles": [],
      "teams": [],
    }

    team_by_key = {}
    for team in model.Team.all().ancestor(game):
      team_props = team_by_key[team.key()] = model.GetProperties(team)
      props["teams"].append(team_props)

    puzzle_by_key = {}
    for n, puzzle in enumerate(model.Puzzle.get(game.puzzle_order)):
      puzzle_props = puzzle_by_key[puzzle.key()] = model.GetProperties(puzzle)
      puzzle_props["solve_count"] = 0
      puzzle_props["number"] = n + 1
      puzzle_props["team"] = team_by_key[puzzle.key().parent()]
      props["puzzles"].append(puzzle_props)

    for team_props in props["teams"]:
      team_props["puzzles"] = [pp.copy() for pp in props["puzzles"]]
      for gp in team_props["puzzles"]: gp["guess_count"] = 0

    for guess in model.Guess.all().ancestor(game).order("timestamp"):
      puzzle_props = puzzle_by_key[guess.key().parent()]
      team_props = team_by_key[guess.team.key()]
      guess_props = team_props["puzzles"][puzzle_props["number"] - 1]
      guess_props["guess_count"] += 1
      if guess.answer in puzzle_props["answers"] and \
          not guess_props.get("solve_time"):
        puzzle_props["solve_count"] += 1
        guess_props["solve_time"] = guess.timestamp
        guess_props["solve_rank"] = Ordinal(puzzle_props["solve_count"])

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
    game.solving_enabled = bool(self.request.get("solving_enabled"))
    game.voting_enabled = bool(self.request.get("voting_enabled"))
    game.results_enabled = bool(self.request.get("results_enabled"))

    for team in model.Team.all().ancestor(game):
      try: bonus = float(self.request.get("bonus.%d" % team.key().id()))
      except: bonus = 0.0
      if bonus != team.bonus:
        team.bonus = bonus
        team.put()

    if self.request.get("new_team"):  # before assign_numbers is handled
      team = model.Team(parent=game)
      team.name = self.request.get("new_team")
      team.password = self.request.get("new_password")
      team.put()
      for pt in PUZZLE_TYPES: model.Puzzle(parent=team, key_name=pt).put()

    if self.request.get("assign_numbers") and \
       self.request.get("confirm_numbers"):
      type_puzzles = {}
      for p in model.Puzzle.all(keys_only=True).ancestor(game):
        type_puzzles.setdefault(p.name(), []).append(p)

      game.puzzle_order = []
      for ptype, plist in sorted(type_puzzles.items()):
        random.shuffle(plist)
        game.puzzle_order.extend(plist)

    game.put()

    self.redirect("/admin")


app = webapp.WSGIApplication([("/admin", AdminPage)], debug=True)
if __name__ == "__main__": run_wsgi_app(app)
