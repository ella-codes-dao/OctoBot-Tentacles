#  Drakkar-Software OctoBot-Interfaces
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import octobot_services.interfaces.util as interfaces_util
import octobot.community as octobot_community
import octobot_commons.authentication as authentication


def get_community_metrics_to_display():
    return octobot_community.get_community_metrics()


def can_get_community_metrics():
    return octobot_community.can_read_metrics(interfaces_util.get_edited_config(dict_only=False))


def get_account_tentacles_packages(authenticator):
    packages = authenticator.get_packages()
    return [octobot_community.CommunityTentaclesPackage.from_community_dict(data) for data in packages]


def get_preview_tentacles_packages(url_for):
    c1 = octobot_community.CommunityTentaclesPackage(
        "AI candles analyser",
        "Tentacles packages offering artificial intelligence analysis tools based on candles shapes.",
        None, True,
        [url_for("static", filename="img/community/tentacles_packages_previews/octobot.png")], None, None, None)
    c1.uninstalled = False
    c2 = octobot_community.CommunityTentaclesPackage(
        "Telegram portfolio management",
        "Manage your portfolio directly from the telegram interface.",
        None, False,
        [url_for("static", filename="img/community/tentacles_packages_previews/telegram.png")], None, None, None)
    c2.uninstalled = False
    c3 = octobot_community.CommunityTentaclesPackage(
        "Mobile first web interface",
        "Use a mobile oriented interface for your OctoBot.",
        None, True,
        [url_for("static", filename="img/community/tentacles_packages_previews/mobile.png")], None, None, None)
    c3.uninstalled = True
    return [c1, c2, c3]


def get_current_octobots_stats():
    return interfaces_util.run_in_bot_async_executor(octobot_community.get_current_octobots_stats())


def _format_bot(bot):
    return {
        "name": octobot_community.CommunityUserAccount.get_bot_name_or_id(bot) if bot else None,
        "id": octobot_community.CommunityUserAccount.get_bot_id(bot) if bot else None,
    }


def get_all_user_bots():
    # reload user bots to make sure the list is up to date
    interfaces_util.run_in_bot_main_loop(authentication.Authenticator.instance().load_user_bots())
    return sorted([
        _format_bot(bot)
        for bot in authentication.Authenticator.instance().user_account.get_all_user_bots_raw_data()
    ], key=lambda d: d["name"])


def get_selected_user_bot():
    return _format_bot(authentication.Authenticator.instance().user_account.get_selected_bot_raw_data())


def select_bot(bot_id):
    interfaces_util.run_in_bot_main_loop(authentication.Authenticator.instance().select_bot(bot_id))


def create_new_bot():
    return interfaces_util.run_in_bot_main_loop(authentication.Authenticator.instance().create_new_bot())
