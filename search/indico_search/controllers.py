# This file is part of Indico.
# Copyright (C) 2002 - 2016 European Organization for Nuclear Research (CERN).
#
# Indico is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# Indico is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Indico; if not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from flask import request, jsonify
from flask_pluginengine import current_plugin
from sqlalchemy.orm import undefer
from werkzeug.wrappers import Response

from indico.modules.categories import Category
from indico.modules.events import Event
from MaKaC.webinterface.rh.conferenceBase import RHCustomizable
from MaKaC.webinterface.rh.base import RH

from indico_search.views import WPSearchCategory, WPSearchConference


class RHSearch(RHCustomizable):
    """Performs a search using the search engine plugin"""
    def _checkParams(self):
        if 'confId' in request.view_args:
            self.obj = Event.get_one(request.view_args['confId'])
            self._conf = self.obj.as_legacy
            self.obj_type = 'event'
        elif 'category_id' in request.view_args:
            self.obj = Category.get_one(request.view_args['category_id'])
            self.obj_type = 'category' if not self.obj.is_root else None
        else:
            self.obj = Category.get_root()
            self.obj_type = None

    def _process(self):
        with current_plugin.engine_plugin.plugin_context():
            form = current_plugin.search_form(prefix='search-', csrf_enabled=False)
            result = None
            if form.validate_on_submit():
                result = current_plugin.perform_search(form.data, self.obj)
            if isinstance(result, Response):  # probably a redirect or a json response
                return result
            view_class = WPSearchConference if isinstance(self.obj, Event) else WPSearchCategory
            obj = self.obj.as_legacy if isinstance(self.obj, Event) else self.obj
            return view_class.render_template('results.html', obj, only_public=current_plugin.only_public,
                                              form=form, obj_type=self.obj_type, result=result)


class RHSearchCategoryTitles(RH):
    """Searches for categories with matching titles"""
    def _process(self):
        query = (Category.query
                 .filter(Category.title_matches(request.args['term']),
                         ~Category.is_deleted)
                 .options(undefer('chain_titles'))
                 .order_by(Category.title))
        results = [{
            'title': category.title,
            'path': category.chain_titles[1:-1],
            'url': unicode(category.url)
        } for category in query.limit(7)]
        return jsonify(success=True, results=results, count=query.count())
