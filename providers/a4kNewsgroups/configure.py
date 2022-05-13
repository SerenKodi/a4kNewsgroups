import xbmc
import xbmcgui

from providerModules.a4kNewsgroups import common


def _get_set_setting(header, setting):
    kb = xbmc.Keyboard(common.get_setting(setting), header)
    kb.doModal()
    if kb.isConfirmed():
        common.set_setting(setting, kb.getText())
    else:
        raise ValueError


def get_and_store_user_login():
    def _do_failure():
        xbmcgui.Dialog().ok(
            'EasyNews Provider',
            'You will need to supply these details before you will be able to use '
            'this provider',
        )

    xbmcgui.Dialog().ok(
        'EasyNews Provider', 'To complete the setup, we need to grab your login details'
    )
    try:
        _get_set_setting('EasyNews Username', 'easynews.username')
        _get_set_setting('EasyNews Password', 'easynews.password')
    except ValueError:
        _do_failure()
        return


if not common.get_setting('easynews.username') or not common.get_setting(
    'easynews.password'
):
    get_and_store_user_login()
