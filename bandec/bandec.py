import re

from dotenv import dotenv_values
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

from storage.accounts import Accounts


class Notification:
    def __init__(self, message, account, credit, available):
        self.__message = message
        self.__account = account
        self.__credit = credit
        self.__available = available

    def message(self):
        return "Account {account} with credit {credit} and available {available}. {message}".format(account=str(self.__account), credit=str(self.__credit), available=str(self.__available), message=str(self.__message))


class Bandec:
    def __init__(self, logger):
        config = dotenv_values(".env")
        self.__username = config.get('username')
        self.__password = config.get('password')
        self.__pin = config.get('pin')
        self.__logger = logger

        entries = str(config.get('matrix')).split(';')
        self.__matrix = []
        for entry in entries:
            self.__matrix.append(str(entry).split(','))

    def accounts(self):
        self.run_check()
        return Accounts().all()

    def run_check(self):
        profile = webdriver.FirefoxProfile()
        profile.set_preference("permissions.default.image", 2)
        options = Options()
        options.add_argument('--headless')
        driver = webdriver.Firefox(profile, options=options)
        self.__logger.debug('Getting login page')
        driver.get("http://www.bandec.cu/VirtualBANDEC/")

        username = driver.find_element_by_css_selector('.panel-body-login input[name="Usuario"]')
        if username:
            username.send_keys(self.__username)
        password = driver.find_element_by_css_selector('.panel-body-login input[name="Contraseña"]')
        if password:
            password.send_keys(self.__password)
        button = driver.find_element_by_css_selector('.panel-body-login input[type="submit"]')
        if button:
            button.click()

        WebDriverWait(driver, 100).until(
            expected_conditions.presence_of_element_located(
                (By.CSS_SELECTOR, 'input[name="pin"]'),
            )
        )

        pin = coordinate = ""
        descriptions = driver.find_elements_by_css_selector('.panel-body-login .input-group-addon')
        for description in descriptions:
            text = str(description.text)
            if re.compile('^Posiciones').match(text):
                p = re.compile("Posiciones del PIN: (.+?)-(.+?)")
                matches = p.search(text)
                for position in matches.groups():
                    pin += self.__pin[int(position) - 1]
                self.__logger.debug(text + ' >> ' + pin)
            elif re.compile('^Coordenada').match(text):
                p = re.compile("Coordenada: (.+?).([0-9]+?)$")
                matches = p.search(text)
                groups = matches.groups()
                coordinate = self.__matrix[int(groups[1]) - 1][ord(groups[0]) - ord('A')]
                self.__logger.debug(text + ' >> ' + coordinate)

        pin_input = driver.find_element_by_css_selector('.panel-body-login input[name="pin"]')
        if pin_input:
            pin_input.send_keys(pin)
        coordinate_input = driver.find_element_by_css_selector('.panel-body-login input[name="matriz"]')
        if coordinate_input:
            coordinate_input.send_keys(coordinate)
        button = driver.find_element_by_css_selector('.panel-body-login input[type="submit"]')
        if button:
            button.click()

        WebDriverWait(driver, 100).until(
            expected_conditions.presence_of_element_located(
                (By.CSS_SELECTOR, '.navbar'),
            )
        )

        self.__logger.debug('Getting available credits page')
        driver.get('http://www.bandec.cu/VirtualBANDEC/Disponibilidad/Disponibilidad')

        WebDriverWait(driver, 100).until(
            expected_conditions.presence_of_element_located(
                (By.ID, 'tablacuentas'),
            )
        )
        button = driver.find_element_by_css_selector('form button[type="submit"]')
        if button:
            button.click()

        WebDriverWait(driver, 100).until(
            expected_conditions.presence_of_element_located(
                (By.CSS_SELECTOR, '.table-responsive'),
            )
        )

        self.__logger.debug('Processing credits')
        table_entries = driver.find_elements_by_css_selector('.table tbody tr')
        notifications = []
        for entry in table_entries:
            tds = entry.find_elements(By.TAG_NAME, "td")
            if len(tds) < 4:
                continue
            accounts = Accounts()
            account = accounts.by_number(tds[0].text)
            number = str(tds[0].text)
            credit = float(tds[1].text)
            available = float(tds[4].text)
            if account:
                if credit > account[1] or available > account[2]:
                    notifications.append(Notification('Notify credit movement', number, credit, available))
                accounts.update(number, credit, available)
            else:
                notifications.append(Notification('Registered account', number, credit, available))
                accounts.insert(number, credit, available)
        driver.close()
        return notifications
