import json
import os
import urllib.request
from datetime import datetime

USERNAME = "Shistuu"
TOKEN = os.environ.get("GH_STATS_TOKEN")

if not TOKEN:
    raise RuntimeError("GH_STATS_TOKEN is not set")

QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(
      ownerAffiliations: OWNER
      privacy: PUBLIC
    ) {
      totalCount
    }

    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions

      contributionCalendar {
        totalContributions

        weeks {
          contributionDays {
            contributionCount
            date
          }
        }
      }
    }
  }
}
"""

payload = json.dumps({
    "query": QUERY,
    "variables": {"login": USERNAME}
}).encode("utf-8")

request = urllib.request.Request(
    "https://api.github.com/graphql",
    data=payload,
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "Shistuu-GitHub-Profile"
    }
)

with urllib.request.urlopen(request) as response:
    result = json.loads(response.read().decode("utf-8"))

if "errors" in result:
    raise RuntimeError(result["errors"])

user = result["data"]["user"]

if user is None:
    raise RuntimeError(f"GitHub user {USERNAME} was not found")

collection = user["contributionsCollection"]
calendar = collection["contributionCalendar"]

total_contributions = calendar["totalContributions"]
commits = collection["totalCommitContributions"]
pull_requests = collection["totalPullRequestContributions"]
public_repos = user["repositories"]["totalCount"]

weeks = calendar["weeks"]

# Flatten contribution days.
days = []

for week in weeks:
    for day in week["contributionDays"]:
        days.append(day)

active_days = sum(
    1 for day in days
    if day["contributionCount"] > 0
)

# Longest consecutive contribution streak.
longest_streak = 0
current_streak = 0

for day in days:
    if day["contributionCount"] > 0:
        current_streak += 1
        longest_streak = max(longest_streak, current_streak)
    else:
        current_streak = 0

max_count = max(
    [day["contributionCount"] for day in days],
    default=1
)

# ---------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------

WIDTH = 900
HEIGHT = 400

BACKGROUND = "#0d1117"
PANEL = "#111820"
BORDER = "#263241"
TEXT = "#e6edf3"
MUTED = "#7d8590"
ACCENT = "#d29922"

HEAT = [
    "#161b22",
    "#3b2f18",
    "#665020",
    "#9b7626",
    "#d29922",
]

def escape(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )

def heat_color(count):
    if count == 0:
        return HEAT[0]

    ratio = count / max_count

    if ratio <= 0.25:
        return HEAT[1]
    if ratio <= 0.50:
        return HEAT[2]
    if ratio <= 0.75:
        return HEAT[3]

    return HEAT[4]

svg = []

svg.append(f"""
<svg
  xmlns="http://www.w3.org/2000/svg"
  width="{WIDTH}"
  height="{HEIGHT}"
  viewBox="0 0 {WIDTH} {HEIGHT}"
>

<style>
  text {{
    font-family:
      ui-monospace,
      SFMono-Regular,
      Menlo,
      Monaco,
      Consolas,
      "Liberation Mono",
      "Courier New",
      monospace;
  }}

  .title {{
    font-size: 18px;
    font-weight: 700;
    fill: {TEXT};
    letter-spacing: 2px;
  }}

  .label {{
    font-size: 11px;
    font-weight: 600;
    fill: {MUTED};
    letter-spacing: 1.5px;
  }}

  .number {{
    font-size: 30px;
    font-weight: 700;
    fill: {TEXT};
  }}

  .small {{
    font-size: 11px;
    fill: {MUTED};
  }}

  .accent {{
    fill: {ACCENT};
  }}
</style>

<rect
  width="100%"
  height="100%"
  rx="16"
  fill="{BACKGROUND}"
/>

<rect
  x="0.5"
  y="0.5"
  width="{WIDTH - 1}"
  height="{HEIGHT - 1}"
  rx="16"
  fill="none"
  stroke="{BORDER}"
/>

<!-- terminal controls -->

<circle cx="26" cy="25" r="5" fill="#ff5f56"/>
<circle cx="43" cy="25" r="5" fill="#ffbd2e"/>
<circle cx="60" cy="25" r="5" fill="#27c93f"/>

<text
  x="82"
  y="30"
  class="small"
>
  shistata@github: ~/activity
</text>

<line
  x1="20"
  y1="48"
  x2="880"
  y2="48"
  stroke="{BORDER}"
/>

<!-- heading -->

<text
  x="30"
  y="82"
  class="title"
>
  SHISTATA / GITHUB ACTIVITY
</text>

<text
  x="870"
  y="82"
  text-anchor="end"
  class="small"
>
  last 12 months
</text>
""")

# ---------------------------------------------------------
# Stats cards
# ---------------------------------------------------------

stats = [
    ("CONTRIBUTIONS", total_contributions),
    ("ACTIVE DAYS", active_days),
    ("LONGEST STREAK", f"{longest_streak}d"),
    ("PUBLIC REPOS", public_repos),
]

card_width = 197
card_height = 78
gap = 15
start_x = 30
card_y = 105

for i, (label, value) in enumerate(stats):
    x = start_x + i * (card_width + gap)

    svg.append(f"""
    <rect
      x="{x}"
      y="{card_y}"
      width="{card_width}"
      height="{card_height}"
      rx="8"
      fill="{PANEL}"
      stroke="{BORDER}"
    />

    <text
      x="{x + 16}"
      y="{card_y + 24}"
      class="label"
    >
      {escape(label)}
    </text>

    <text
      x="{x + 16}"
      y="{card_y + 60}"
      class="number"
    >
      {escape(value)}
    </text>
    """)

# ---------------------------------------------------------
# Contribution heatmap
# ---------------------------------------------------------

heatmap_x = 30
heatmap_y = 222

cell = 8
cell_gap = 3

svg.append(f"""
<text
  x="{heatmap_x}"
  y="{heatmap_y - 17}"
  class="label"
>
  CONTRIBUTION SIGNAL
</text>
""")

visible_weeks = weeks[-52:]

for week_index, week in enumerate(visible_weeks):
    contribution_days = week["contributionDays"]

    for day_index, day in enumerate(contribution_days):
        x = heatmap_x + week_index * (cell + cell_gap)
        y = heatmap_y + day_index * (cell + cell_gap)

        color = heat_color(day["contributionCount"])

        svg.append(f"""
        <rect
          x="{x}"
          y="{y}"
          width="{cell}"
          height="{cell}"
          rx="2"
          fill="{color}"
        />
        """)

# ---------------------------------------------------------
# Secondary stats
# ---------------------------------------------------------

info_x = 645

svg.append(f"""
<rect
  x="{info_x}"
  y="205"
  width="225"
  height="105"
  rx="8"
  fill="{PANEL}"
  stroke="{BORDER}"
/>

<text
  x="{info_x + 18}"
  y="230"
  class="label"
>
  ACTIVITY BREAKDOWN
</text>

<text
  x="{info_x + 18}"
  y="256"
  class="small"
>
  commits
</text>

<text
  x="{info_x + 205}"
  y="256"
  text-anchor="end"
  class="small accent"
>
  {commits}
</text>

<text
  x="{info_x + 18}"
  y="278"
  class="small"
>
  pull requests
</text>

<text
  x="{info_x + 205}"
  y="278"
  text-anchor="end"
  class="small accent"
>
  {pull_requests}
</text>

<text
  x="{info_x + 18}"
  y="300"
  class="small"
>
  active days
</text>

<text
  x="{info_x + 205}"
  y="300"
  text-anchor="end"
  class="small accent"
>
  {active_days}
</text>
""")

# ---------------------------------------------------------
# Footer
# ---------------------------------------------------------

updated = datetime.utcnow().strftime("%Y-%m-%d")

svg.append(f"""
<line
  x1="30"
  y1="340"
  x2="870"
  y2="340"
  stroke="{BORDER}"
/>

<text
  x="30"
  y="368"
  class="small"
>
  $ build · measure · break · understand
</text>

<text
  x="870"
  y="368"
  text-anchor="end"
  class="small"
>
  updated {updated}
</text>

</svg>
""")

os.makedirs("assets", exist_ok=True)

output = "assets/github-dashboard.svg"

with open(output, "w", encoding="utf-8") as file:
    file.write("".join(svg))

print(f"Generated {output}")
print(f"Contributions: {total_contributions}")
print(f"Active days: {active_days}")
print(f"Longest streak: {longest_streak}")
print(f"Commits: {commits}")
print(f"Pull requests: {pull_requests}")
print(f"Public repositories: {public_repos}")
