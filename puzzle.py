# Iron Puzzler puzzle page handler

import datetime
import logging
import re
import urllib

from google.appengine.dist import use_library;  use_library('django', '1.2')
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import login
import model

def MaybeGetPuzzle(game, request):
  try: key = game.puzzle_order[int(request.get("p")) - 1]
  except Exception: return None
  return model.Puzzle.get(key)


def NormalizeAnswer(answer):
  return re.sub('[\W]+', '', answer).upper()


def NormalizeScore(score):
  try: score = float(score)
  except: return -1.0
  return (score < 0.0 or score > 10.0) and -1.0 or score


class PuzzlePage(webapp.RequestHandler):
  def get(self):
    game = model.GetGame()
    team = login.GetTeamOrRedirect(game, self.request, self.response)
    if not team: return

    puzzle = MaybeGetPuzzle(game, self.request)
    if not puzzle: return self.error(404)
    if puzzle.parent_key() != team.key(): return self.error(403)

    props = {
      "game": model.GetProperties(game),
      "team": model.GetProperties(team),
      "puzzle": model.GetProperties(puzzle),
      "comments": [],
      "votes": [],
    }

    no_scores = model.Feedback().scores
    for feedback in model.Feedback.all().ancestor(puzzle):
      comment = (feedback.comment or "").strip()
      if comment: props["comments"].append(comment)
      if feedback.scores != no_scores: props["votes"].append(feedback.scores)

    props["comments"].sort(key=unicode.lower)
    props["votes"].sort(reverse=True)
    props["puzzle"]["answers"] = "\n".join(props["puzzle"].get("answers", []))
    props["puzzle"]["number"] = self.request.get("p")

    self.response.out.write(template.render("puzzle.dj.html", props))


  def post(self):
    game = model.GetGame()
    team = login.GetTeamOrRedirect(game, self.request, self.response)
    if not team: return

    puzzle = MaybeGetPuzzle(game, self.request)
    if not puzzle: return self.error(404)
    if puzzle.parent_key() != team.key(): return self.error(403)
    self.redirect("/team?t=%d" % team.key().id())

    updates = {}
    for arg in self.request.arguments():
      if arg.endswith(".orig"): continue
      orig_value = urllib.unquote(self.request.get(arg + ".orig", ""))
      new_value = self.request.get(arg)
      if new_value != orig_value: updates[arg] = new_value

    if "title" in updates: puzzle.title = updates.get("title")

    if "answers" in updates:
      puzzle.answers = []
      for answer in updates.get("answers").split("\n"):
        answer = NormalizeAnswer(answer)
        if answer: puzzle.answers.append(answer)

    if "errata" in updates:
      puzzle.errata_timestamp = datetime.datetime.now()
      puzzle.errata = updates.get("errata")

    if "solution" in updates: puzzle.solution = updates.get("solution")

    puzzle.put()


app = webapp.WSGIApplication([("/puzzle", PuzzlePage)], debug=True)
if __name__ == "__main__": run_wsgi_app(app)
