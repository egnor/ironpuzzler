# Iron Puzzler main page handler

from google.appengine.dist import use_library;  use_library('django', '1.2')
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import model

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
      team_props["solve_count"] = 0
      team_props["solve_time"] = 0
      props["teams"].append(team_props)

    puzzle_by_key = {}
    for n, puzzle in enumerate(model.Puzzle.get(game.puzzle_order)):
      puzzle_props = puzzle_by_key[puzzle.key()] = model.GetProperties(puzzle)
      puzzle_props.update({
        "solve_count": 0,
        "number": n + 1,
        "team": team_by_key[puzzle.key().parent()],
        "votes": [],
      })
      props["puzzles"].append(puzzle_props)

    for feedback in model.Feedback.all().ancestor(game):
      puzzle_props = puzzle_by_key[feedback.key().parent()]
      puzzle_props["votes"].append(feedback.scores)

    for team_props in props["teams"]:
      team_props["puzzles"] = [pp.copy() for pp in props["puzzles"]]
      for gp in team_props["puzzles"]: gp["guess_count"] = 0

    for guess in model.Guess.all().ancestor(game).order("timestamp"):
      puzzle_props = puzzle_by_key[guess.key().parent()]
      if guess.answer in puzzle_props["answers"]:
        team_props = team_by_key[guess.team.key()]
        guess_props = team_props["puzzles"][puzzle_props["number"] - 1]
        if not guess_props.get("solve_time"):
          guess_props["solve_time"] = team_props["solve_time"] = guess.timestamp
          puzzle_props["solve_count"] += 1
          team_props["solve_count"] += 1

    #
    # Compute scores
    #

    no_scores = model.Feedback().scores
    for team_props in props["teams"]:
      team_score = 0.0
      team_props["author"] = {}
      for n, guess_props in enumerate(team_props["puzzles"]):
        if guess_props["team"]["key_id"] == team_props["key_id"]:
          team_props["author"][guess_props["key_name"]] = guess_props
          guess_scores = guess_props["scores"] = [0 for s in no_scores]
          for scores in guess_props["votes"]:
            for i in range(len(guess_scores)):
              if i < len(scores) and scores[i] >= 0:
                guess_scores[i] += scores[i]

          team_score += 2 * guess_scores[0] + sum(guess_scores[1:])

        if guess_props.get("solve_time"):
          points = 9 + len(props["teams"]) - props["puzzles"][n]["solve_count"]
          guess_props["score"] = points
          team_score += points

      team_score += (team_props.get("bonus") or 0) 
      team_props["score"] = team_score
      team_props["minus_score"] = -team_score

    props["teams"].sort(key = lambda tp:
        (-tp["solve_count"], tp["solve_time"], tp["name"]))

    self.response.out.write(template.render("main.dj.html", props))

app = webapp.WSGIApplication([('/', MainPage)], debug=True)
if __name__ == "__main__": run_wsgi_app(app)
