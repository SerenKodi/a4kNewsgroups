# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals
from future.standard_library import install_aliases

install_aliases()

import xbmcgui

from base64 import b64encode
import requests
import time
from urllib.parse import quote

from providerModules.a4kNewsgroups import common

from resources.lib.common import source_utils
from resources.lib.modules.exceptions import PreemptiveCancellation

_exclusions = ['soundtrack', 'gesproken', 'sample', 'trailer', 'extras only', 'ost']


class sources:
    def __init__(self):
        self.language = ['en']
        self.base_link = "https://members.easynews.com"
        self.search_link = "/2.0/search/solr-search/advanced"
        self.query_link = self.base_link + self.search_link
        self.auth = self._get_auth()
        self.start_time = 0
        self.sort_params = {
            's1': 'relevance',
            's1d': '-',
            's2': 'dsize',
            's2d': '-',
            's3': 'dtime',
            's3d': '-',
        }
        self.search_params = {
            'st': 'adv',
            'fex': 'm4v,3gp,mov,divx,xvid,wmv,avi,mpg,mpeg,mp4,mkv,avc,flv,webm',
            'fty[]': 'VIDEO',
            'u': '1',
            'pby': 350,
            'safeO': 1,
        }
        self.search_params.update(self.sort_params)

    def _get_auth(self):
        auth = None
        try:
            username = common.get_setting('easynews.username')
            password = common.get_setting('easynews.password')
            if username == "" or password == "":
                return auth
            user_info = '{}:{}'.format(username, password)
            user_info = user_info.encode('utf-8')
            auth = "Basic {}".format(b64encode(user_info).decode('utf-8'))
        except:
            common.log('Could not authorize.')
        return auth

    def _return_results(self, source_type, sources, preemptive=False):
        if preemptive:
            common.log(
                "a4kNewsgroups.{}.easynews: cancellation requested".format(source_type),
                "info",
            )
        common.log(
            "a4kNewsgroups.{}.easynews: {}".format(source_type, len(sources)), "info"
        )
        common.log(
            "a4kNewsgroups.{}.easynews: took {} ms".format(
                source_type, int((time.time() - self.start_time) * 1000)
            ),
            "info",
        )
        return sources

    def _make_query(self, query):
        self.search_params["gps"] = query
        results = requests.get(
            self.query_link,
            params=self.search_params,
            headers={"Authorization": self.auth},
            timeout=20,
        ).json()

        down_url = results.get("downURL")
        dl_farm = results.get("dlFarm")
        dl_port = results.get("dlPort")
        files = results.get("data", [])

        return down_url, dl_farm, dl_port, files

    def _process_item(self, item, down_url, dl_farm, dl_port):
        post_hash, size, post_title, ext = (
            item["0"],
            item["4"],
            item["10"],
            item["11"],
        )

        if item.get("virus"):
            return
        if item.get("type", "").upper() != "VIDEO":
            return
        if self._check_exclusions(post_title):
            return
        if not self._check_languages(item.get("alangs", []), item.get("slangs", [])):
            return

        stream_url = down_url + quote(
            "/{}/{}/{}{}/{}{}".format(dl_farm, dl_port, post_hash, ext, post_title, ext)
        )
        file_dl = "{}|Authorization={}".format(stream_url, quote(self.auth))

        source = {
            "scraper": "easynews",
            "release_title": post_title,
            "info": source_utils.get_info(post_title),
            "size": source_utils.de_string_size(size),
            "quality": source_utils.get_quality(post_title),
            "url": file_dl,
        }
        return source

    def episode(self, simple_info, all_info):
        self.start_time = time.time()
        sources = []
        if not self.auth:
            return sources

        show_title = simple_info["show_title"]
        show_aliases = simple_info["show_aliases"]
        year = simple_info["year"]
        country = simple_info["country"]
        episode_title = simple_info["episode_title"]
        season_x = simple_info["season_number"]
        season_xx = season_x.zfill(2)
        episode_x = simple_info["episode_number"]
        episode_xx = episode_x.zfill(2)
        absolute_number = simple_info["absolute_number"]
        is_anime = simple_info["isanime"]

        numbers = [(season_x, episode_x), (season_xx, episode_xx), absolute_number]

        queries = []
        if is_anime and absolute_number:
            queries.append("\"{}\" {}".format(show_title, numbers[2]))
        else:
            for n in numbers[:2]:
                queries.append("\"{}\" S{}E{}".format(show_title, n[0], n[1]))

        for query in queries:
            try:
                down_url, dl_farm, dl_port, files = self._make_query(query)
            except PreemptiveCancellation:
                return self._return_results("episode", sources, preemptive=True)

            for item in files:
                source = self._process_item(item, down_url, dl_farm, dl_port)
                if source is not None:
                    sources.append(source)

        return self._return_results("episode", sources)

    def movie(self, title, year, imdb_id):
        self.start_time = time.time()
        sources = []
        if not self.auth:
            return sources

        query = "\"{}\" {}".format(title, year)
        try:
            down_url, dl_farm, dl_port, files = self._make_query(query)
        except PreemptiveCancellation:
            return self._return_results("episode", sources, preemptive=True)

        for item in files:
            source = self._process_item(item, down_url, dl_farm, dl_port)
            if source is not None:
                sources.append(source)

        return self._return_results("movie", sources)

    @staticmethod
    def _check_exclusions(release_title):
        check_title = release_title.lower()
        return any([i in check_title for i in _exclusions])

    @staticmethod
    def _check_languages(alangs, slangs):
        return alangs is None or "eng" in alangs

    @staticmethod
    def get_listitem(return_data):
        list_item = xbmcgui.ListItem(path=return_data["url"], offscreen=True)
        list_item.setContentLookup(False)
        list_item.setProperty('isFolder', 'false')
        list_item.setProperty('isPlayable', 'true')

        return list_item
