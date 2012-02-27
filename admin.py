# Iron Puzzler administrative interface handler

import random
import re

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import model
import puzzle

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
      # TODO(egnor): Without multilogin, this creates redirect loops.
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
      team_props.update({
        "feedback_count": 0,
        "works": [],
      })
      props["teams"].append(team_props)

    puzzle_by_key = {}
    for p in sorted(model.Puzzle.all().ancestor(game), key=puzzle.SortKey):
      puzzle_props = puzzle_by_key[p.key()] = model.GetProperties(p)
      author_props = team_by_key.get(p.key().parent(), {})
      puzzle_props.update({
        "author": author_props.get("name"),
        "author_id": author_props.get("key_id"),
        "comment_count": 0,
        "solve_count": 0,
      })
      props["puzzles"].append(puzzle_props)

    work_by_keys = {}
    for tp in props["teams"]:
      for pp in props["puzzles"]:
        work_props = work_by_keys[(tp["key"], pp["key"])] = {
          "puzzle": pp,
          "guess_count": 0,
        }
        tp["works"].append(work_props)

    for guess in model.Guess.all().ancestor(game).order("timestamp"):
      wp = work_by_keys[(guess.team.key(), guess.key().parent())]
      wp["guess_count"] += 1
      if guess.answer in wp["puzzle"]["answers"] and not wp.get("solve_time"):
        wp["puzzle"]["solve_count"] += 1
        wp["solve_time"] = guess.timestamp
        wp["solve_rank"] = Ordinal(wp["puzzle"]["solve_count"])

    for feedback in model.Feedback.all().ancestor(game):
      if feedback.key().parent().parent() == db.Key(feedback.key().name()):
        feedback.delete()  # Remove bogus self-votes from older versions.
      else:
        team_props = team_by_key[db.Key(feedback.key().name())]
        team_props["feedback_count"] += 1
        if feedback.comment and feedback.comment.strip():
          puzzle_props = puzzle_by_key[feedback.key().parent()]
          puzzle_props["comment_count"] += 1

    self.response.out.write(template.render("admin.dj.html", props))


  def post(self):
    game = model.GetGame()
    if not IsUserAdmin(game): return self.error(403)

    ingredients = [self.request.get("ingredient%d" % i) for i in range(3)]
    admin_users = re.split(r'[,\s]+', self.request.get("admin_users"))
    game.location = self.request.get("location")
    game.ingredients = [i for i in ingredients if i]
    game.ingredients_visible = bool(self.request.get("ingredients_visible"))
    game.admin_users = [u for u in admin_users if u]
    game.login_enabled = bool(self.request.get("login_enabled"))
    game.solving_enabled = bool(self.request.get("solving_enabled"))
    game.voting_enabled = bool(self.request.get("voting_enabled"))
    game.results_enabled = bool(self.request.get("results_enabled"))
    game.put()

    for team in model.Team.all().ancestor(game):
      try: bonus = float(self.request.get("bonus.%d" % team.key().id()))
      except: bonus = 0.0
      if bonus != team.bonus:
        team.bonus = bonus
        team.put()

    n = self.request.get("delete_team")
    if n:
      for tk in model.Team.all(keys_only=True).ancestor(game).filter("name", n):
        db.delete(
            model.Guess.all(keys_only=True).ancestor(game).filter("team", tk))
        db.delete([
            db.Key.from_path("Feedback", str(tk), parent=p.key())
            for p in model.Puzzle.all().ancestor(game)])
        db.delete(db.Query(keys_only=True).ancestor(tk))

    if self.request.get("new_team"):  # before assign_numbers is handled
      team = model.Team(parent=game)
      team.name = self.request.get("new_team")
      team.password = self.request.get("new_password")
      team.put()
      for pt in PUZZLE_TYPES: model.Puzzle(parent=team, key_name=pt).put()

    nonum = model.Puzzle().number
    puzzles = list(model.Puzzle.all().ancestor(game))
    for puzzle in puzzles:
      k = puzzle.key()
      num = self.request.get("number.%d.%s" % (k.parent().id(), k.name()))
      orig = self.request.get("number.%d.%s.orig" % (k.parent().id(), k.name()))
      if num != orig:
        puzzle.number = num or nonum
        puzzle.put()

    if self.request.get("assign_numbers"):
      try: n = int(self.request.get("assign_start"))
      except: n = 1

      taken = {}  # numbers already used
      type_puzzles = {}  # group puzzles by type before scrambling order
      for p in puzzles:
        if p.number == nonum or not p.number:
          type_puzzles.setdefault(p.key().name(), []).append(p)
        else:
          taken[p.number] = 1

      for ptype, plist in sorted(type_puzzles.iteritems()):
        random.shuffle(plist)
        for p in plist:
          while taken.has_key(str(n)): n += 1
          p.number = str(n)
          p.put()
          n += 1

    self.redirect("/admin")


app = webapp.WSGIApplication([("/admin", AdminPage)], debug=True)
if __name__ == "__main__": run_wsgi_app(app)
