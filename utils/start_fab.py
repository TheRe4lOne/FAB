from selenium.common.exceptions import TimeoutException, WebDriverException
from urllib3.exceptions import MaxRetryError

from auth.auth_status import set_auth_status
from consts import server_status_messages
from factories.fab_loop import FabLoopFactory
from search_filters.get_user_filters import get_custom_search_filters_from_user
from utils.driver_functions import close_driver, check_if_restart_is_possible, initialize_time_left
from utils.helper_functions import server_response


def start_fab(fab, configuration_data, requested_items, user_prices):
    time_to_run_in_sec = configuration_data["time"]
    loop_type = configuration_data["loopType"]

    if time_to_run_in_sec is None:
        return server_response(msg=server_status_messages.BAD_REQUEST, code=400)
    try:
        user_filters = get_custom_search_filters_from_user()
        fab_search_response = FabLoopFactory(loop_type).get_fab_loop().start_loop(fab, configuration_data, requested_items, user_prices, user_filters)
        set_auth_status(fab.user.email, False)
        close_driver(fab.driver, fab.user.email)
        return fab_search_response

    except MaxRetryError as e:
        return server_response(msg=server_status_messages.DRIVER_OFF, code=503)

    except (WebDriverException, TimeoutException) as e:
        print(f"Oops :( Something went wrong.. {e.msg}")
        print("restarting FAB...")
        if not check_if_restart_is_possible(fab):
            close_driver(fab.driver, fab.user.email)
            return server_response(msg=server_status_messages.DRIVER_CRASHED_TOO_MANY_TIMES, code=503)
        else:
            # only if it has not started yet
            if fab.time_left_to_run == 0:
                initialize_time_left(fab, time_to_run_in_sec)
            return start_fab(fab, configuration_data, requested_items, user_prices)
