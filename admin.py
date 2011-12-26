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

FETCH = 1000
PUZZLE_TYPES = ["paper", "nonpaper"]

def IsUserAdmin(game):
  if users.is_current_user_admin(): return True
  user = users.get_current_user()
  return user and (user.email() in game.admin_users)


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

    puzzles = model.Puzzle.get(game.puzzle_order)
    props_by_team = {}
    for team in model.Team.all().ancestor(game).order("name").fetch(FETCH):
      team_props = props_by_team[team.key()] = model.GetProperties(team)
      team_props["puzzles"] = [{
          "number": n + 1,
          "title": puzzle.title,
          "name": (puzzle.key().parent() == team.key()) and puzzle.key().name(),
        } for n, puzzle in enumerate(puzzles)]
      props["teams"].append(team_props)

    for n, puzzle in enumerate(puzzles):
      puzzle_props = model.GetProperties(puzzle)
      puzzle_props["number"] = n + 1
      puzzle_props["team"] = props_by_team[puzzle.key().parent()]
      props["puzzles"].append(puzzle_props)

    n_by_key = dict([(k, n) for n, k in enumerate(game.puzzle_order)])
    solve_rank = {}
    query = model.Guess.all().ancestor(game)
    for guess in query.order("timestamp").fetch(FETCH):
      n = n_by_key[guess.key().parent()]
      puzzle = puzzles[n]
      guess_props = props_by_team[guess.team.key()]["puzzles"][n]
      guess_props["guess_count"] = guess_props.get("guess_count", 0) + 1
      guess_props["guess_time"] = guess.timestamp
      if guess.answer in puzzle.answers and not guess_props.get("solve_time"):
        guess_props["solve_time"] = guess.timestamp
        guess_props["solve_rank"] = solve_rank.get(puzzle.key(), 1)
        solve_rank[puzzle.key()] = guess_props["solve_rank"] + 1

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

    if self.request.get("new_team"):  # before assign_numbers is handled
      team = model.Team(parent=game)
      team.name = self.request.get("new_team")
      team.password = self.request.get("new_password")
      team.put()
      for pt in PUZZLE_TYPES: model.Puzzle(parent=team, key_name=pt).put()

    if self.request.get("assign_numbers") and self.request.get("confirm_numbers"):
      type_puzzles = {}
      for p in model.Puzzle.all(keys_only=True).ancestor(game).fetch(FETCH):
        type_puzzles.setdefault(p.name(), []).append(p)

      game.puzzle_order = []
      for ptype, plist in sorted(type_puzzles.items()):
        random.shuffle(plist)
        game.puzzle_order.extend(plist)

    game.put()

    self.redirect("/admin")


app = webapp.WSGIApplication([("/admin", AdminPage)], debug=True)
if __name__ == "__main__": run_wsgi_app(app)
