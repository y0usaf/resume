#!/usr/bin/env python3
import json
from itertools import groupby
import re
from html import escape
from pathlib import Path

ROOT = Path(__file__).parent

GITHUB_MARK = '<svg class="mark" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>'


def rich(text):
    parts = re.split(r'\*\*(.+?)\*\*', text)
    return ''.join(f'<strong>{escape(part)}</strong>' if index % 2 else escape(part) for index, part in enumerate(parts))


def link(href, text):
    return f'<a href="{escape(href)}">{escape(text)}</a>'


def logo(name):
    if not name:
        return ''
    if not (ROOT / 'assets' / name).is_file():
        raise ValueError(f'missing logo: assets/{name}')
    return f'<img class="logo" src="assets/{escape(name)}" alt="">'


def section(title, body):
    return f'<section><h2>{escape(title)}</h2>{body}</section>'


def header(person):
    phone = person['phone']
    contact = [
        f'<span>{escape(person["location"])}</span>',
        link('tel:' + re.sub(r'[^+\d]', '', phone), phone),
        link('mailto:' + person['email'], person['email']),
        link('https://' + person['linkedin'], person['linkedin']),
        link('https://' + person['github'], person['github']),
    ]
    separator = '<span class="sep" aria-hidden="true">/</span>'
    return f'<header><h1>{escape(person["name"])}</h1><p class="contact">{separator.join(contact)}</p></header>'


def bullets(items):
    return '<ul>' + ''.join(f'<li>{rich(item)}</li>' for item in items) + '</ul>'


def experience(jobs):
    entries = []
    for company, group in groupby(jobs, key=lambda job: job['company']):
        group = list(group)
        roles = ''.join(
            f'<div class="head"><span class="role">{escape(job["title"])}</span>'
            f'<time>{escape(job["period"])}</time></div>'
            f'{bullets(job["bullets"])}'
            for job in group
        )
        entries.append(
            '<article class="entry">'
            f'{logo(group[0].get("logo"))}<h3>{escape(company)}</h3>'
            f'{roles}</article>'
        )
    return ''.join(entries)


def projects(items):
    entries = []
    for project in items:
        name = escape(project['name'])
        if project.get('url'):
            name = f'<a href="{escape(project["url"])}">{name}</a>'
        entries.append(
            '<article class="project">'
            f'<div class="head">{GITHUB_MARK}<h3>{name}</h3>'
            f'<span class="stack">{escape(project["stack"])}</span></div>'
            f'<p>{rich(project["description"])}</p></article>'
        )
    return ''.join(entries)


def skills(groups):
    rows = ''.join(f'<dt>{escape(label)}</dt><dd>{rich(value)}</dd>' for label, value in groups.items())
    return f'<dl class="skills">{rows}</dl>'


def speaking(talk):
    return (
        '<article class="entry">'
        f'<div class="head"><h3>{escape(talk["title"])}</h3><time>{escape(talk["year"])}</time></div>'
        f'<p class="detail">{rich(talk["detail"])}</p></article>'
    )


def education(schools):
    return ''.join(
        '<article class="entry">'
        f'<div class="head">{logo(school.get("logo"))}<h3>{escape(school["school"])}</h3>'
        f'<span class="role">{escape(school["degree"])}</span>'
        f'<time>{escape(school["period"])}</time></div></article>'
        for school in schools
    )


def render(data):
    parts = [
        header(data['person']),
        section('Experience', experience(data['experience'])),
        section('Speaking', speaking(data['speaking'])),
        section('Selected Projects', projects(data['projects'])),
        section('Technical Skills', skills(data['skills'])),
        section('Education', education(data['education'])),
    ]
    return '\n'.join(parts)


def main():
    data = json.loads((ROOT / 'resume.json').read_text())
    template = (ROOT / 'index.template.html').read_text()
    (ROOT / 'index.html').write_text(template.replace('{{resume}}', render(data)))


if __name__ == '__main__':
    main()
