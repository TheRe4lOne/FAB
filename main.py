import os.path
import os.path

from selenium.common.exceptions import TimeoutException, WebDriverException

from auth.login import set_auth_status, check_auth_status, login_with_cookies, initialize_user_details, is_login_success_from_first_time, _wait_for_code, \
    remember_logged_in_user, get_status_code_from_user
from consts import app, server_status_messages
from utils.driver import initialize_driver, DriverState, restart_driver_when_crashed, close_driver, initialize_time_left, check_if_web_app_is_available
from elements.elements_manager import initialize_element_actions
from utils.fab_loop import run_loop
from players.players_actions import PlayerActions
from utils.server_status import ServerStatus


class Fab:
    def __init__(self):
        self.is_authenticated = False
        self.driver = None
        self.statusCode = ''
        self.element_actions = None
        self.player_actions = None
        self.driver_state = DriverState.OFF
        self.connected_user_details = {}
        self.time_left_to_run = 0

    def start_login(self, email, password):
        if email is None or password is None:
            return ServerStatus(server_status_messages.BAD_REQUEST, 400).jsonify()
        try:
            initialize_user_details(self, email, password)
            initialize_driver(self)
            initialize_element_actions(self)
            if os.path.isfile(app.COOKIES_FILE_NAME):
                if not login_with_cookies(self, password):
                    return ServerStatus(server_status_messages.FAILED_AUTH, 401).jsonify()

            # cookies file was not found - log in the first time
            else:
                if not is_login_success_from_first_time(self, email, password):
                    return ServerStatus(server_status_messages.FAILED_AUTH, 401).jsonify()
                status_code_response = get_status_code_from_user(self)
                if not status_code_response:
                    return ServerStatus(server_status_messages.LIMIT_TRIES, 401).jsonify()
                remember_logged_in_user(self)
                set_auth_status(self, True)
            return ServerStatus(server_status_messages.SUCCESS_AUTH, 200).jsonify()

        except TimeoutException as e:
            print(f"Oops :( Something went wrong.. {e.msg}")
            return ServerStatus(server_status_messages.FAILED_AUTH, 401).jsonify()
        except Exception as e:
            print(f"Server problem.. kill all drivers {e.msg}")
            return ServerStatus(server_status_messages.DRIVER_ERROR, 503).jsonify()

    @check_auth_status
    def start_loop(self, time_to_run_in_sec, requested_players):
        if time_to_run_in_sec is None:
            return ServerStatus(server_status_messages.BAD_REQUEST, 400).jsonify()
        try:
            self.player_actions = PlayerActions(self.driver)
            self.element_actions.wait_for_page_to_load()

            if not check_if_web_app_is_available(self):
                run_loop_response =  ServerStatus(server_status_messages.WEB_APP_NOT_AVAILABLE, 503).jsonify()
            else:
                self.element_actions.remove_unexpected_popups()
                run_loop_response = run_loop(self, time_to_run_in_sec, requested_players)

            close_driver(self)
            set_auth_status(self,False)
            return run_loop_response

        except (WebDriverException, TimeoutException) as e:
            print(f"Oops :( Something went wrong.. {e.msg}")
            print("restarting FAB...")
            # only if it has not started yet
            if self.time_left_to_run == 0:
                initialize_time_left(self,time_to_run_in_sec)
            restart_driver_when_crashed(self, requested_players)
