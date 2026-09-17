#!/usr/bin/env python3
"""Compose the résumé from the shared fixed-cell terminal grid."""

import json
import textwrap
from pathlib import Path

from tui import Grid

ROOT = Path(__file__).parent
WIDTH = 96
LETTER_ROWS = 72


def wrapped(value, width):
    value = value.replace('-|', '-').replace('|', ' ')
    lines = textwrap.wrap(value, width=width, break_long_words=False, break_on_hyphens=False) or ['']
    if any(len(line) > width for line in lines):
        raise ValueError(f'text contains a word wider than {width} cells')
    return lines


def paired(grid, y, left, right, inset=3, style='strong', right_inset=None):
    if right_inset is None:
        right_inset = inset
    if len(left) + len(right) + 1 > WIDTH - inset - right_inset:
        raise ValueError('left and right resume fields overlap')
    grid.text(inset, y, left, style)
    grid.text(WIDTH - right_inset - len(right), y, right, 'dim')


def render(data):
    person = data['person']
    skills = []
    if data.get('skills'):
        for label, value in data['skills'].items():
            if len(label) > 14:
                raise ValueError('skill label is wider than 14 cells')
            skills.append((label, wrapped(value, WIDTH - 26)))

    projects = []
    for project in data['projects']:
        projects.append((project['name'], wrapped(project['description'], WIDTH - 10), project['stack']))

    jobs = []
    for job in data['experience']:
        bullets = [wrapped(item, WIDTH - 10) for item in job['bullets']]
        jobs.append((job, bullets))

    # Build the row plan first. Every content line contributes to this same
    # cursor, so the capacity check cannot drift from what gets drawn.
    rows = [('section', 'EXPERIENCE')]
    for index, (job, bullets) in enumerate(jobs):
        if index:
            rows.append(('blank',))
        rows.append(('job', job))
        for lines in bullets:
            rows.extend(('bullet', line, first) for first, line in enumerate(lines))
    rows.extend([('blank',), ('section', 'PROJECTS')])
    for index, (name, description, stack) in enumerate(projects):
        if index:
            rows.append(('blank',))
        rows.append(('project', name, stack))
        rows.extend(('project-description', line) for line in description)
    if data.get('skills'):
        rows.extend([('blank',), ('section', 'SKILLS')])
        for label, lines in skills:
            rows.append(('skill', label, lines[0]))
            rows.extend(('skill-cont', line) for line in lines[1:])
    rows.extend([('blank',), ('section', 'SPEAKING'), ('speaking', data['speaking']),
                 ('speaking-detail', data['speaking']['detail'])])
    # Header occupies rows 2–4; content starts at row 6.
    # Reserve two rows of breathing room at the bottom of the page.
    if 6 + len(rows) > LETTER_ROWS - 2:
        raise ValueError(f'resume needs {6 + len(rows) + 1} terminal rows; letter capacity is {LETTER_ROWS}')

    grid = Grid(WIDTH, LETTER_ROWS)
    contact = person['phone'] + ' / ' + person['email']
    links = person['linkedin'] + ' / ' + person['github']
    if len(person['name']) * 2 + max(len(person['location']), len(contact)) + 2 > WIDTH - 10:
        raise ValueError('double-size name and contact fields overlap')
    grid.text(6, 2, person['name'], 'strong', scale=2)
    grid.text(WIDTH - 4 - len(person['location']), 2, person['location'], 'dim')
    grid.text(WIDTH - 4 - len(contact), 3, contact, 'dim')
    # Keep the header grouped without introducing a box or a full-width rule.
    grid.line(6, 1, 19, 1, 'accent')
    paired(grid, 4, person['tagline'], links, inset=6, right_inset=4, style='accent')
    y = 6
    for row in rows:
        kind = row[0]
        if kind == 'section':
            grid.text(6, y, row[1], 'accent strong')
            grid.line(8 + len(row[1]), y, WIDTH - 5, y, 'rule')
        elif kind == 'job':
            job = row[1]
            role = ' / ' + job['title']
            date_x = WIDTH - 4 - len(job['period'])
            if 6 + len(job['company']) + len(role) + 2 > date_x:
                raise ValueError('company, role, and date fields overlap')
            grid.image(3, y, 2, 1, 'assets/' + job['logo'])
            grid.text(6, y, job['company'], 'strong')
            grid.text(6 + len(job['company']), y, role, 'dim')
            grid.text(date_x, y, job['period'], 'dim')
        elif kind == 'bullet':
            _, line, first = row
            if first == 0:
                grid.text(4, y, '→', 'dim')
            grid.text(6, y, line)
        elif kind == 'project':
            _, name, stack = row
            paired(grid, y, name, stack, inset=6, style='accent strong', right_inset=4)
        elif kind == 'project-description':
            grid.text(6, y, row[1])
        elif kind == 'skill':
            grid.text(6, y, row[1], 'strong')
            grid.text(22, y, row[2], 'dim')
        elif kind == 'skill-cont':
            grid.text(22, y, row[1], 'dim')
        elif kind == 'speaking':
            speaking = row[1]
            paired(grid, y, speaking['title'], speaking['year'], inset=6, right_inset=4)
        elif kind == 'speaking-detail':
            grid.text(6, y, row[1], 'dim')
        y += 1
    return grid.render()


def main():
    data = json.loads((ROOT / 'resume.json').read_text())
    for job in data['experience']:
        logo = ROOT / 'assets' / job['logo']
        if not logo.is_file():
            raise ValueError(f'missing company logo: {logo}')
    content = render(data)
    template = (ROOT / 'index.template.html').read_text()
    output = template.replace('<!-- GENERATED_RESUME -->', content)
    (ROOT / 'index.html').write_text(output)


if __name__ == '__main__':
    main()
