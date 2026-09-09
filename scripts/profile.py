#!/usr/bin/env python3
"""Render a dependency-free terminal README and simulated contribution Breakout."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from html import escape
import json
import math
import os
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
USER = 'Walid-peach'
CORAL = '#ff8b7b'
BG = '#171c22'
WHITE = '#e6edf3'
MUTED = '#a6b0bc'
LINE = '#424c58'


def graphql(query):
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if not token:
        raise RuntimeError('Set GH_TOKEN to refresh; cached rendering needs no token.')
    req = urllib.request.Request('https://api.github.com/graphql',
        data=json.dumps({'query': query}).encode(), headers={
            'Authorization': f'Bearer {token}', 'Content-Type': 'application/json',
            'User-Agent': 'quiet-terminal-profile'})
    with urllib.request.urlopen(req, timeout=45) as response:
        result = json.load(response)
    if result.get('errors'):
        raise RuntimeError(str(result['errors']))
    return result['data']


def refresh():
    # Only public, owned, non-fork repositories; paginate before aggregating.
    cursor = None
    repos = []
    while True:
        after = ',after:' + json.dumps(cursor) if cursor else ''
        result = graphql('query { user(login:"' + USER + '") { repositories('
            'first:100,privacy:PUBLIC,ownerAffiliations:OWNER,isFork:false' + after +
            ') { pageInfo { hasNextPage endCursor } nodes { languages(first:100) '
            '{ edges { size node { name } } } } } } }')['user']['repositories']
        repos.extend(result['nodes'])
        if not result['pageInfo']['hasNextPage']:
            break
        cursor = result['pageInfo']['endCursor']
    result = graphql('query { user(login:"' + USER + '") { contributionsCollection '
        '{ contributionCalendar { totalContributions weeks { contributionDays '
        '{ date contributionCount weekday } } } } } search(query:"author:' + USER +
        ' is:pr is:public",type:ISSUE,first:1) { issueCount } }')
    calendar = result['user']['contributionsCollection']['contributionCalendar']
    languages = Counter()
    for repo in repos:
        for edge in repo['languages']['edges']:
            languages[edge['node']['name']] += edge['size']
    data = {'updated': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        'contributions': calendar['totalContributions'],
        'public_repositories': len(repos),
        'public_pull_requests': result['search']['issueCount'],
        'languages': dict(languages.most_common()), 'weeks': calendar['weeks']}
    validate(data)
    path = ROOT / 'data/profile.json'
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, indent=2) + '\n')
    temp.replace(path)
    return data


def validate(data):
    for key in ('contributions', 'public_repositories', 'public_pull_requests'):
        if not isinstance(data[key], int) or data[key] < 0:
            raise ValueError('Invalid statistic: ' + key)
    if not data['weeks'] or len(data['weeks']) > 54:
        raise ValueError('Expected a rolling contribution calendar')
    for week in data['weeks']:
        for day in week['contributionDays']:
            if day['weekday'] not in range(7) or day['contributionCount'] < 0:
                raise ValueError('Invalid contribution day')


def text(x, y, value, size=23, color=WHITE, extra=''):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" {extra}>{escape(str(value))}</text>'


def command(x, y, value, size=23):
    return text(x, y, '$', size, CORAL) + text(x + size * 1.25, y, value, size, MUTED)


def rule(x1, y1, x2, y2):
    return f'<path d="M{x1} {y1}H{x2}" stroke="{LINE}"/>' if y1 == y2 else f'<path d="M{x1} {y1}V{y2}" stroke="{LINE}"/>'


def language_parts(languages):
    ranked = sorted(
        ((name, size) for name, size in languages.items() if name != 'Jupyter Notebook'),
        key=lambda pair: (-pair[1], pair[0]))
    parts = ranked[:3]
    other = sum(value for _, value in ranked[3:])
    if other:
        parts.append(('Other', other))
    return parts


def language_bar(data, x, y, width, font=16):
    parts = language_parts(data['languages'])
    total = sum(value for _, value in parts)
    if not total:
        return text(x, y, 'No language data', font, MUTED)
    out = text(x, y, 'source languages', font, MUTED)
    offset = x
    colors = [CORAL, '#87939f', '#c7ced6', '#4c5663']
    for i, (name, value) in enumerate(parts):
        w = width * value / total
        out += f'<rect x="{offset:.2f}" y="{y+14}" width="{w:.2f}" height="12" fill="{colors[i]}"><title>{escape(name)}: {value / total:.1%} of source bytes</title></rect>'
        offset += w
    labels = [name for name, _ in parts]
    out += text(x, y + 52, ' · '.join(labels[:2]), font - 1, MUTED)
    out += text(x, y + 76, ' · '.join(labels[2:]), font - 1, MUTED)
    return out


def simulate(bricks, width, height, seconds=30, fps=24):
    """Auto-play physics. Every disappearing brick corresponds to a collision."""
    x, y = width * .44, height * .67
    vx, vy = width * .37, -height * .71
    radius, paddle_width = 4, width * .12
    paddle_y = height - 22
    alive = {i for i, b in enumerate(bricks) if b['count'] > 0}
    hits, frames = {}, []
    for frame in range(int(seconds * fps) + 1):
        frames.append((x, y, max(0, min(width - paddle_width, x - paddle_width / 2))))
        if frame == int(seconds * fps):
            break
        dt = 1 / fps
        old_y = y
        x += vx * dt
        y += vy * dt
        if x < radius or x > width - radius:
            x = min(width - radius, max(radius, x))
            vx = -vx
        if y < radius:
            y, vy = radius, abs(vy)
        if y >= paddle_y - radius and vy > 0:
            y, vy = paddle_y - radius, -abs(vy)
        for i in sorted(alive):
            b = bricks[i]
            if b['x'] - radius <= x <= b['x'] + b['size'] + radius and b['y'] - radius <= y <= b['y'] + b['size'] + radius:
                alive.remove(i)
                hits[i] = (frame + 1) / fps
                if old_y < b['y'] or old_y > b['y'] + b['size']:
                    vy = -vy
                else:
                    vx = -vx
                break
    return frames, hits, paddle_width, paddle_y


def breakout(data, x, y, width, height, animated=True):
    weeks = data['weeks']
    pitch = width / len(weeks)
    size = pitch * .70
    counts = [d['contributionCount'] for w in weeks for d in w['contributionDays']]
    peak = max(counts, default=1) or 1
    bricks = []
    for col, week in enumerate(weeks):
        for day in week['contributionDays']:
            bricks.append({'x': col*pitch, 'y': day['weekday']*pitch, 'size': size,
                'count': day['contributionCount'], 'date': day['date']})
    frames, hits, pw, py = simulate(bricks, width, height)
    out = f'<g transform="translate({x} {y})">'
    shades = ['#713f40', '#ad6059', '#d5786c', CORAL]
    for i, b in enumerate(bricks):
        color = '#303943' if not b['count'] else shades[min(3, int(math.log1p(b['count']) / math.log1p(peak) * 3))]
        out += f'<rect class="brick" x="{b["x"]:.2f}" y="{b["y"]:.2f}" width="{size:.2f}" height="{size:.2f}" rx="1.5" fill="{color}"><title>{b["date"]}: {b["count"]} contributions</title>'
        if animated and i in hits:
            t = hits[i] / 32
            out += f'<animate attributeName="opacity" values="1;0;0" keyTimes="0;{t:.6f};1" calcMode="discrete" dur="32s" repeatCount="indefinite"/>'
        out += '</rect>'
    # 30 seconds play, 2 seconds hold, then restore the actual calendar.
    def anim(attr, values):
        vals = ';'.join(f'{v:.2f}' for v in values + [values[-1]])
        times = ';'.join(f'{i/24/32:.6f}' for i in range(len(values))) + ';1'
        return f'<animate attributeName="{attr}" values="{vals}" keyTimes="{times}" dur="32s" repeatCount="indefinite"/>' if animated else ''
    out += f'<circle cx="{frames[0][0]:.2f}" cy="{frames[0][1]:.2f}" r="4" fill="{CORAL}">'
    out += anim('cx', [f[0] for f in frames]) + anim('cy', [f[1] for f in frames]) + '</circle>'
    out += f'<rect x="{frames[0][2]:.2f}" y="{py}" width="{pw}" height="8" rx="4" fill="{CORAL}">'
    out += anim('x', [f[2] for f in frames]) + '</rect></g>'
    return out


def render(data, mobile=False, animated=True):
    w, h = (640, 1435) if mobile else (1200, 1060)
    x = 34 if mobile else 56
    size = 24
    title = 'Walid El Khoukh — AI & Data Engineer'
    desc = ('Turning complex data into useful tools. MonÉlu: civic data and AI. '
        'Agentarium: agent tooling, in development. Interview Prep: learning tools. '
        f'{data["contributions"]} contributions in the past year, '
        f'{data["public_repositories"]} public non-fork repositories, '
        f'{data["public_pull_requests"]} public pull requests authored, all time. '
        'Source languages measured by source bytes, excluding Jupyter notebooks. Links are below the image.')
    out = f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc"><title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc>'
    out += '<style>text{font-family:ui-monospace,SFMono-Regular,Consolas,"Liberation Mono",monospace;font-weight:400} .still{display:none}@media(prefers-reduced-motion:reduce){.motion{display:none}.still{display:inline}}</style>'
    out += f'<rect width="{w}" height="{h}" rx="8" fill="{BG}"/><rect x="1" y="1" width="{w-2}" height="{h-2}" rx="8" fill="none" stroke="{LINE}" stroke-width="1.5"/>'
    for i, c in enumerate([CORAL, '#65707d', '#65707d']):
        out += f'<circle cx="{30+i*23}" cy="27" r="6" fill="{c}"/>'
    out += text(w/2, 34, 'walid / README.md', 18, MUTED, 'text-anchor="middle"') + rule(1, 54, w-1, 54)
    out += command(x, 107, 'whoami') + text(x, 144, 'Walid El Khoukh', 27)
    out += text(x, 181, 'AI & Data Engineer', size, MUTED)
    if mobile:
        out += text(x, 218, 'Turning complex data into', 22) + text(x, 248, 'useful tools.', 22)
    else:
        out += text(x, 218, 'Turning complex data into useful tools.', size)
    offset = 32 if mobile else 0
    out += command(x, 280+offset, 'ls projects')
    for i, (name, label) in enumerate([('MonÉlu', 'civic data & AI'), ('Agentarium', 'agent tooling'), ('Interview Prep', 'learning tools')]):
        yy = 317 + offset + i * (67 if mobile else 36)
        out += text(x, yy, name, 23)
        out += text(x+20 if mobile else x+235, yy+27 if mobile else yy, label, 19 if mobile else 22, MUTED)
    yy = 561 if mobile else 451
    out += command(x, yy, 'building →') + text(x+185, yy, 'Agentarium', 23)
    yy += 62
    out += command(x, yy, 'contact')
    out += text(x, yy+37, 'Portfolio ↗  LinkedIn ↗  Email ↗', 23)
    divider = yy + 77
    out += rule(30, divider, w-30, divider)
    ty = divider + 45
    out += command(x, ty, 'telemetry')
    if mobile:
        stats = [(str(f'{data["contributions"]:,}'), 'contributions / year'),
            (str(data['public_repositories']), 'public repos'),
            (str(data['public_pull_requests']), 'public PRs · all time')]
        for i, (value, label) in enumerate(stats):
            out += text(x, ty+43+i*39, value, 25) + text(x+107, ty+43+i*39, label, 20, MUTED)
        out += language_bar(data, x, ty+188, w-2*x, 20)
        bx, by, bw, bh = x, ty+320, w-2*x, 224
    else:
        for i, (key, label) in enumerate([('contributions','contributions / year'), ('public_repositories','public repos'), ('public_pull_requests','public PRs · all time')]):
            out += text(x, ty+44+i*65, f'{data[key]:,}', 24) + text(x, ty+69+i*65, label, 17, MUTED)
        out += language_bar(data, x, ty+266, 277, 17)
        out += rule(366, ty-12, 366, h-56)
        bx, by, bw, bh = 396, ty+32, w-428, 287
    if animated:
        out += '<g class="motion">' + breakout(data, bx, by, bw, bh, True) + '</g>'
        out += '<g class="still">' + breakout(data, bx, by, bw, bh, False) + '</g>'
    else:
        out += breakout(data, bx, by, bw, bh, False)
    out += text(w-30, h-22, 'snapshot ' + data['updated'] + ' UTC', 14 if not mobile else 16, MUTED, 'text-anchor="end"')
    return out + '</svg>\n'


def readme(data):
    return f'''<picture>
  <source media="(max-width: 640px)" srcset="./assets/terminal-mobile.svg">
  <img src="./assets/terminal.svg" width="1200" alt="Walid El Khoukh — AI &amp; Data Engineer. A quiet terminal with projects, GitHub telemetry and animated contribution Breakout. Project and contact links follow below.">
</picture>

<p align="center">
  <a href="https://mon-elu.vercel.app/">MonÉlu ↗</a> ·
  <a href="https://walid-peach.github.io/interview-prep/">Interview Prep ↗</a> ·
  <a href="https://walidelkhoukh.com">Portfolio ↗</a> ·
  <a href="https://www.linkedin.com/in/walid-elkhoukh">LinkedIn ↗</a> ·
  <a href="mailto:contact@walidelkhoukh.com">Email ↗</a>
</p>

<details>
<summary>Text version &amp; data notes</summary>

**Walid El Khoukh · AI & Data Engineer**

Turning complex data into useful tools.

- [MonÉlu](https://mon-elu.vercel.app/) — civic data & AI · [source](https://github.com/Walid-peach/MonElu)
- Agentarium — agent tooling; currently building. No public demo linked yet.
- [Interview Prep](https://walid-peach.github.io/interview-prep/) — learning tools · [source](https://github.com/Walid-peach/interview-prep)

**Snapshot: {data['updated']} UTC.** {data['contributions']:,} contributions in GitHub's rolling-year calendar; {data['public_repositories']} public, owned, non-fork repositories; {data['public_pull_requests']} public pull requests authored, all time.

Language proportions measure source bytes across public, owned, non-fork repositories, excluding Jupyter notebooks from both the bar and its percentages. They are not proficiency ratings. Breakout auto-plays over the calendar; cells disappear when hit and reset each loop. It is an animation, not an interactive game. Reduced-motion preferences show a static calendar.

[Portfolio](https://walidelkhoukh.com) · [LinkedIn](https://www.linkedin.com/in/walid-elkhoukh) · [Email](mailto:contact@walidelkhoukh.com)

</details>
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    data = refresh() if args.refresh else json.loads((ROOT / 'data/profile.json').read_text())
    validate(data)
    for name, mobile in [('terminal.svg', False), ('terminal-mobile.svg', True)]:
        (ROOT / 'assets' / name).write_text(render(data, mobile))
    (ROOT / 'README.md').write_text(readme(data))


if __name__ == '__main__':
    main()
