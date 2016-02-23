# -*- coding: utf-8 -*-
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright (C) 2014-2016 GEM Foundation
#
# OpenQuake is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OpenQuake is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with OpenQuake. If not, see <http://www.gnu.org/licenses/>.

import os
import cgi
import datetime
import itertools
from docutils.examples import html_parts

from openquake.commonlib.datastore import read
from openquake.calculators.views import view_fullreport

tablecounter = itertools.count(0)


def html(header_rows):
    """
    Convert a list of tuples describing a table into a HTML string
    """
    name = 'table%d' % next(tablecounter)
    return HtmlTable([map(str, row) for row in header_rows], name).render()


class Fetcher(object):
    """
    Small wrapper over a DB API 2 cursor
    """
    def __init__(self, curs):
        self.curs = curs

    def query(self, templ, *args):
        self.curs.execute(templ, args)
        header = [r[0] for r in self.curs.description]
        return [header] + self.curs.fetchall()


class HtmlTable(object):
    """
    Convert a sequence header+body into a HTML table.
    """
    css = """\
    tr.evenRow { background-color: lightgreen }
    tr.oddRow { }
    th { background-color: lightblue }
    """
    maxrows = 5000
    border = "1"
    summary = ""

    def __init__(self, header_plus_body, name='noname',
                 empty_table='Empty table'):
        header, body = header_plus_body[0], header_plus_body[1:]
        self.name = name
        self.empty_table = empty_table
        rows = []  # rows is a finite sequence of tuples
        for i, row in enumerate(body):
            if i == self.maxrows:
                rows.append(
                    ["Table truncated because too big: more than %s rows" % i])
                break
            rows.append(row)
        self.rows = rows
        self.header = tuple(header)  # horizontal header

    def render(self, dummy_ctxt=None):
        out = "\n%s\n" % "".join(list(self._gen_table()))
        if not self.rows:
            out += '<em>%s</em>' % cgi.escape(self.empty_table, quote=True)
        return out

    def _gen_table(self):
        yield '<table id="%s" border="%s" summary="%s" class="tablesorter">\n'\
              % (self.name, self.border, self.summary)
        yield '<thead>\n'
        yield '<tr>%s</tr>\n' % ''.join(
            '<th>%s</th>\n' % h for h in self.header)
        yield '</thead>\n'
        yield '<tbody\n>'
        for r, row in enumerate(self.rows):
            yield '<tr class="%s">\n' % ["even", "odd"][r % 2]
            for col in row:
                yield '<td>%s</td>\n' % col
            yield '</tr>\n'
        yield '</tbody>\n'
        yield '</table>\n'


JOB_STATS = '''
SELECT id, user_name, start_time, stop_time, status,
stop_time - start_time AS duration FROM job WHERE id=%s;
'''

ALL_JOBS = '''
SELECT id, user_name, status, ds_calc_dir FROM job
WHERE stop_time::date = %s OR stop_time IS NULL AND start_time >= %s
ORDER BY stop_time
'''

PAGE_TEMPLATE = '''\
<html>
<head>
<script src="http://ajax.googleapis.com/ajax/libs/jquery/2.1.1/jquery.min.js"></script>
<link rel="stylesheet" href="http://ajax.googleapis.com/ajax/libs/jqueryui/1.11.2/themes/smoothness/jquery-ui.css" />
<script src="http://ajax.googleapis.com/ajax/libs/jqueryui/1.11.2/jquery-ui.min.js"></script>
<script>
$(function() {
$("#tabs").tabs();
});
</script>
</head>
<body>
%s
</body>
</html>
'''


def make_tabs(tag_ids, tag_status, tag_contents):
    """
    Return a HTML string containing all the tabs we want to display
    """
    templ = '''
<div id="tabs">
<ul>
%s
</ul>
%s
</div>'''
    lis = []
    contents = []
    for i, (tag_id, status, tag_content) in enumerate(
            zip(tag_ids, tag_status, tag_contents), 1):
        mark = '.' if status == 'complete' else '!'
        lis.append('<li><a href="#tabs-%d">%s%s</a></li>' % (i, tag_id, mark))
        contents.append('<div id="tabs-%d">%s</div>' % (
            i, tag_content))
    return templ % ('\n'.join(lis), '\n'.join(contents))


def make_report(conn, isodate='today'):
    """
    Build a HTML report with the computations performed at the given isodate.
    Return the name of the report, which is saved in the current directory.
    """
    if isodate == 'today':
        isodate = datetime.date.today().isoformat()
    curs = conn.cursor()
    fetcher = Fetcher(curs)
    tag_ids = []
    tag_status = []
    tag_contents = []

    jobs = fetcher.query(ALL_JOBS, isodate, isodate)[1:]
    page = '<h2>%d job(s) finished before midnight of %s</h2>' % (
        len(jobs), isodate)
    for job_id, user, status, ds_calc in jobs:
        tag_ids.append(job_id)
        tag_status.append(status)
        stats = fetcher.query(JOB_STATS, job_id)[1:]
        if not stats:
            continue
        (job_id, user, start_time, stop_time, status, duration) = stats[0]
        try:
            ds = read(job_id, datadir=os.path.dirname(ds_calc))
            txt = view_fullreport('fullreport', ds).decode('utf-8')
            report = html_parts(txt)
        except Exception as exc:
            report = dict(
                html_title='Could not generate report: %s' % cgi.escape(
                    unicode(exc), quote=True),
                fragment='')

        page = report['html_title']

        job_stats = html(fetcher.query(JOB_STATS, job_id))
        page += job_stats

        page += report['fragment']

        tag_contents.append(page)

    page = make_tabs(tag_ids, tag_status, tag_contents) + (
        'Report last updated: %s' % datetime.datetime.now())
    fname = 'jobs-%s.html' % isodate
    with open(fname, 'w') as f:
        f.write(PAGE_TEMPLATE % page.encode('utf-8'))
    return fname
