from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

class TestLoginnew():
  def setup_method(self, method):

    brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
    driver_path = r"C:\tools\chromedriver-win64\chromedriver-win64\chromedriver.exe"

    options = Options()
    options.binary_location = brave_path

    service = Service(driver_path)
    self.driver = webdriver.Chrome(service=service, options=options)

    self.vars = {}

  def teardown_method(self, method):
    self.driver.quit()

  def test_loginnew(self):
    self.driver.get("http://127.0.0.1:8000/api/auth/jwt-login/")
    self.driver.set_window_size(1350, 822)
    self.driver.find_element(By.ID, "email").send_keys("jaouher2002@gmail.com")
    self.driver.find_element(By.ID, "password").send_keys("aaaa")
    self.driver.find_element(By.CSS_SELECTOR, "button:nth-child(4)").click()
