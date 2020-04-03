import datetime
from functools import wraps

import bcrypt
from flask import jsonify
from flask_jwt_extended import create_access_token
from selenium.common.exceptions import TimeoutException

from active.data import opened_drivers, active_fabs, login_attempts
from auth.selenium_login import SeleniumLogin
from consts import server_status_messages, app
from fab import Fab
from utils import db
from utils.driver import initialize_driver
from utils.globals import element_actions


def check_auth_status(func):
    @wraps(func)
    def determine_if_func_should_run(self, *args):
        if not self.is_authenticated:
            return jsonify(msg=server_status_messages.FAILED_AUTH, code=401)
        return func(self, *args)

    return determine_if_func_should_run


def start_login(email, password):
    existing_user = get_user_details_if_exists(email, password)
    # todo remove this to separate route.
    # todo create fab object with the id from the db and append it to the running fubs object.
    # if not user_details:
    #     return jsonify(msg=server_status_messages.FAILED_AUTH, code=401)  # remove this too.
    try:
        # todo if a customer trying to enter to loged user, dont allow it.
        # initialize_user_details(self, user_details)
        if email in opened_drivers:
            driver = opened_drivers.get(email)
        else:
            driver = initialize_driver(email)
        selenium_login = SeleniumLogin(driver, element_actions)
        if existing_user:
            # if check_if_user_has_saved_cookies(email, password):

            if not selenium_login.login_with_cookies(password, existing_user["cookies"]):
                return jsonify(msg=server_status_messages.FAILED_AUTH, code=401)

            # todo 1.get id of current loged in user from db.
            # todo 2. data.active_fabs[id] = current_fab(that initialized till now with driver and is_authenticated turned to true.)

        # cookies file was not found - log in the first time
        else:
            if not selenium_login.is_login_successfull_from_first_time(email, password):
                return jsonify(msg=server_status_messages.FAILED_AUTH, code=401)

            # todo if login was successfuly save to db
            # todo 1.get id of current loged in user from db.
            # todo 2. data.active_fabs[id] = current_fab(that initialized till now with driver and is_authenticated turned to true.)
            while not login_attempts[email].is_authenticated:
                if not login_attempts[email].tries_with_status_code:
                    return jsonify(msg=server_status_messages.LIMIT_TRIES, code=401)
                # todo check if driver opened more than specific time.

            remember_logged_in_user(driver)

        access_token = create_access_token({'id': str(existing_user["_id"])},
                                           expires_delta=datetime.timedelta(hours=1))
        # active_login_sessions.get(email).is_authenticated = True

        fab = Fab(driver=driver, element_actions=element_actions)
        active_fabs[existing_user["_id"]] = fab
        login_attempts.get(email).login_thread.kill()
        del login_attempts[email]
        return jsonify(msg=server_status_messages.SUCCESS_AUTH, code=200, token=access_token)


    except TimeoutException:
        print(f"Oops :( Something went wrong..")
        return jsonify(msg=server_status_messages.FAB_LOOP_FAILED, code=401)
    except Exception as e:
        print(e)
        return jsonify(msg=server_status_messages.DRIVER_ERROR, code=503)


def get_user_details_if_exists(email, password):
    user_in_db = db.users_collection.find_one({"email": email})
    if not user_in_db:
        return None
    if bcrypt.hashpw(password.encode('utf-8'), user_in_db["password"]) == user_in_db["password"]:
        # The class user_details must store unhashed password in order to send to selenium an unhashed version
        return user_in_db
    else:
        return None


def check_if_user_has_saved_cookies(email, password):
    user_details = get_user_details_if_exists(email, password)
    if user_details is None:
        return False
    return True if len(user_details["cookies"]) > 0 else False


def set_auth_status(self, is_auth):
    self.is_authenticated = is_auth


def remember_logged_in_user(self):
    eaCookies = self.driver.get_cookies()
    self.driver.get(app.SIGN_IN_URL)
    signInCookies = self.driver.get_cookies()

    for cookie in signInCookies:
        if 'expiry' in cookie:
            del cookie['expiry']
        if cookie not in eaCookies:
            eaCookies.append(cookie)
    # takes 10-15 secs
    # saveToCookiesFile(eaCookies, app.COOKIES_FILE_NAME)
    # update the user connected in fab class
    self.connected_user_details["cookies"] = eaCookies
    # update the db
    user_id = self.connected_user_details["_id"]
    db.users_collection.update({"_id": user_id}, {"$set": {"cookies": eaCookies}})
    set_auth_status(self, True)
    self.driver.back()
