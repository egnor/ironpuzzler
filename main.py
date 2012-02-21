# Iron Puzzler main page handler

from google.appengine.dist import use_library;  use_library('django', '1.2')
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import login
import model
import puzzle

class MainPage(webapp.RequestHandler):
  def get(self):
    game = model.GetGame()
    props = {
      "game": model.GetProperties(game),
      "puzzles": [],
      "teams": [],
    }

    team_by_key = {}
    for team in model.Team.all().ancestor(game):
      team_props = team_by_key[team.key()] = model.GetProperties(team)
      team_props.update({
        "score": team_props.get("bonus") or 0.0,
        "solve_count": 0,
        "solve_score": 0,
        "solve_time": 0,
        "works": [],
        "wrote": {},
        "wrote_score": 0,
      })
      cookie = login.CookiePassword(team, self.request)
      if cookie:
        props["cookie_team"] = team_props
        props["cookie_password"] = cookie
      props["teams"].append(team_props)

    puzzle_by_key = {}
    for p in sorted(model.Puzzle.all().ancestor(game), key=puzzle.SortKey):
      puzzle_props = puzzle_by_key[p.key()] = model.GetProperties(p)
      author_props = team_by_key.get(p.key().parent(), {})
      puzzle_props.update({
        "author": author_props.get("name"),
        "author_id": author_props.get("key_id"),
        "score": 0,
        "solve_count": 0,
        "votes": [],
      })
      author_props["wrote"][p.key().name()] = puzzle_props
      props["puzzles"].append(puzzle_props)

    for feedback in model.Feedback.all().ancestor(game):
      puzzle_props = puzzle_by_key[feedback.key().parent()]
      puzzle_props["votes"].append(feedback.scores)

    work_by_keys = {}
    for team_props in props["teams"]:
      for puzzle_props in props["puzzles"]:
        work_props = work_by_keys[(team_props["key"], puzzle_props["key"])] = {
          "puzzle": puzzle_props,
          "guess_count": 0,
        }
        team_props["works"].append(work_props)

    for guess in model.Guess.all().ancestor(game).order("timestamp"):
      work_props = work_by_keys[(guess.team.key(), guess.key().parent())]
      if guess.answer in work_props["puzzle"]["answers"]:
        if not work_props.get("solve_time"):
          team_props = team_by_key[guess.team.key()]
          work_props["solve_time"] = team_props["solve_time"] = guess.timestamp
          work_props["puzzle"]["solve_count"] += 1
          team_props["solve_count"] += 1

    #
    # Compute scores
    #

    no_scores = model.Feedback().scores
    for team_props in props["teams"]:
      for puzzle_props in team_props["wrote"].values():
        wrote_scores = puzzle_props["scores"] = [0 for s in no_scores]
        for scores in puzzle_props["votes"]:
          for i in range(len(wrote_scores)):
            if i < len(scores) and scores[i] >= 0: wrote_scores[i] += scores[i]
        points = 2 * wrote_scores[0] + sum(wrote_scores[1:])
        puzzle_props["score"] = points
        team_props["score"] += points
        team_props["wrote_score"] += points

      for work_props in team_props["works"]:
        if work_props.get("solve_time"):
          points = 9 + len(props["teams"]) - work_props["puzzle"]["solve_count"]
          work_props["score"] = points
          team_props["solve_score"] += points
          team_props["score"] += points

    props["teams"].sort(key=lambda tp:
        (-tp["solve_count"], tp["solve_time"], tp["name"]))

    self.response.out.write(template.render("main.dj.html", props))

app = webapp.WSGIApplication([('/', MainPage)], debug=True)
if __name__ == "__main__": run_wsgi_app(app)
